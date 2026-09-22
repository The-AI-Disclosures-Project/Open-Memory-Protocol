"""A store that enforces the contract's stated rules on import, export, and lifecycle.

Rules from the draft implemented here, each cited in the code:
  3.1  retain origin-to-local mapping; same revision id + different content = conflict;
       matching content does not merge distinct revisions
  3.3  unmapped principals / unsupported required rules -> reject or restricted staging;
       credentials are outside memory exchange
  3.4  derived object with unavailable evidence must say so
  3.5  current reads exclude superseded/invalidated/expired/deleted; historical reads are
       explicit and permission-checked; a tombstone prevents resurrection; concurrent or
       unordered events surface as conflicts; dependents of a deletion are invalidated
  3.6  newer major version / unsupported required extension -> reject; absence in a partial
       export never implies deletion; preserve / re_derive / hybrid; object-level receipts;
       retries never duplicate; move completes only after a conforming import
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Literal

from semantic_core.schema import (
    FORMAT_VERSION,
    Derivation,
    EvidenceRole,
    Exchange,
    LifecycleEvent,
    LifecycleKind,
    Manifest,
    MemoryObject,
    ObjectRef,
    ObjectState,
    Receipt,
    ReceiptEntry,
    ReceiptStatus,
    new_id,
    now_iso,
)

_CREDENTIAL_RE = re.compile(
    r"(sk-[A-Za-z0-9_-]{16,}|ghp_[A-Za-z0-9]{20,}|xox[abp]-[A-Za-z0-9-]{10,}|AKIA[0-9A-Z]{16}"
    r"|-----BEGIN [A-Z ]*PRIVATE KEY-----|eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.)"
)


class PermissionDenied(PermissionError):
    pass


class SemanticStore:
    def __init__(
        self,
        system_id: str,
        *,
        supported_extensions: Iterable[str] = (),
        enforceable_actions: Iterable[str] = ("read", "write", "derive", "export", "delete"),
        principal_map: dict[str, str] | None = None,
    ) -> None:
        self.system_id = system_id
        self.supported_extensions = set(supported_extensions)
        self.enforceable_actions = set(enforceable_actions)
        self.principal_map = dict(principal_map or {})
        self.objects: dict[str, MemoryObject] = {}  # local revision id -> object
        self.events: dict[str, LifecycleEvent] = {}
        self.origin_map: dict[str, str] = {}  # origin revision id -> local revision id
        self.tombstones: set[str] = set()  # revision ids (origin or local) that may not return
        self.conflicts: list[str] = []

    # ============================================================ §3.5 state
    def state(self, revision_id: str, at: str | None = None) -> ObjectState:
        at = at or now_iso()
        obj = self.objects.get(revision_id)
        if obj is None:
            return ObjectState.deleted
        evs = [e for e in self.events.values() if e.target == revision_id and e.effective_at <= at]
        kinds = {e.kind for e in evs}
        if LifecycleKind.delete in kinds or LifecycleKind.tombstone in kinds:
            return ObjectState.deleted
        if LifecycleKind.retract in kinds:
            return ObjectState.retracted
        if LifecycleKind.invalidate in kinds:
            return ObjectState.invalidated
        if LifecycleKind.supersede in kinds:
            return ObjectState.superseded
        if LifecycleKind.expire in kinds or (obj.expires_at and obj.expires_at <= at):
            return ObjectState.expired
        return ObjectState.active

    def current(self, principal: str | None = None) -> list[MemoryObject]:
        """Current reads exclude invalidated, superseded, expired and deleted claims."""
        return [
            o
            for rid, o in self.objects.items()
            if self.state(rid) == ObjectState.active and self._may(principal, o, "read")
        ]

    def historical(self, at: str, principal: str) -> list[MemoryObject]:
        """Historical reads are explicit and permission-checked."""
        out = []
        for rid, o in self.objects.items():
            if o.recorded_at > at:
                continue
            if not self._may(principal, o, "read_history") and not self._may(principal, o, "read"):
                raise PermissionDenied(f"{principal} may not read history of {rid}")
            if self.state(rid, at) in (ObjectState.active, ObjectState.superseded):
                out.append(o)
        return out

    def _may(self, principal: str | None, obj: MemoryObject, action: str) -> bool:
        if principal is None or not obj.policy.rules:
            return True
        for rule in obj.policy.rules:
            if (principal in rule.principals or "*" in rule.principals) and (
                action in rule.actions or "*" in rule.actions
            ):
                return True
        return False

    # ============================================================ writes
    def add(self, obj: MemoryObject) -> MemoryObject:
        if obj.revision_id in self.tombstones:
            raise ValueError(f"revision {obj.revision_id} is tombstoned")
        existing = self.objects.get(obj.revision_id)
        if existing is not None and existing.digest != obj.digest:
            raise ValueError(f"revision {obj.revision_id} already exists with different content")
        self.objects[obj.revision_id] = obj
        return obj

    def apply_event(self, ev: LifecycleEvent) -> LifecycleEvent:
        """Idempotent by event_id; conflicting supersessions are recorded, not silently ordered."""
        if ev.event_id in self.events:
            return ev
        if ev.kind == LifecycleKind.supersede:
            others = [
                e
                for e in self.events.values()
                if e.kind == LifecycleKind.supersede
                and e.target == ev.target
                and e.replacement != ev.replacement
            ]
            if others:
                self.conflicts.append(
                    f"supersede conflict on {ev.target}: {others[0].replacement} vs {ev.replacement}"
                )
        self.events[ev.event_id] = ev
        if ev.kind in (LifecycleKind.delete, LifecycleKind.tombstone):
            self.tombstones.add(ev.target)
        return ev

    def correct(
        self, revision_id: str, new_text: str, *, actor: str, activity: str = "correction"
    ) -> MemoryObject:
        old = self.objects[revision_id]
        new = old.model_copy(
            update={
                "revision_id": new_id(),
                "predecessor": revision_id,
                "text": new_text,
                "recorded_at": now_iso(),
                "derivation": Derivation(
                    activity=activity, used=[revision_id], agent=actor, at=now_iso()
                ),
            }
        )
        self.add(new)
        self.apply_event(
            LifecycleEvent(
                kind=LifecycleKind.supersede,
                target=revision_id,
                actor=actor,
                replacement=new.revision_id,
            )
        )
        return new

    def consolidate(
        self, inputs: list[str], text: str, *, actor: str, ref: ObjectRef | None = None
    ) -> MemoryObject:
        """Consolidation must name all inputs; it does not supersede them by itself."""
        first = self.objects[inputs[0]]
        obj = MemoryObject(
            ref=ref or ObjectRef(authority=self.system_id, local_id=new_id()),
            role=EvidenceRole.machine_derived,
            text=text,
            scope=first.scope,
            policy=first.policy,
            derivation=Derivation(
                activity="consolidation", used=list(inputs), agent=actor, at=now_iso()
            ),
        )
        return self.add(obj)

    def delete(
        self,
        revision_id: str,
        *,
        actor: str,
        reason: str | None = None,
        tombstone: bool = True,
        coverage: Iterable[str] = ("derivations", "indexes"),
    ) -> LifecycleEvent:
        """Deletion covers dependents: derived objects that used this revision are invalidated."""
        ev = LifecycleEvent(
            kind=LifecycleKind.tombstone if tombstone else LifecycleKind.delete,
            target=revision_id,
            actor=actor,
            reason=reason,
            coverage=list(coverage),
        )
        self.apply_event(ev)
        if "derivations" in ev.coverage:
            for rid, o in list(self.objects.items()):
                if (
                    o.derivation
                    and revision_id in o.derivation.used
                    and self.state(rid) == ObjectState.active
                ):
                    self.apply_event(
                        LifecycleEvent(
                            kind=LifecycleKind.invalidate,
                            target=rid,
                            actor=actor,
                            reason=f"evidence {revision_id} deleted",
                        )
                    )
        # content is removed; the lineage relationship (the event) survives
        self.objects.pop(revision_id, None)
        return ev

    # ============================================================ §3.6 export
    def export(
        self,
        *,
        selection: Iterable[str] | None = None,
        intent: Literal["copy", "move", "federate"] = "copy",
        extensions: Iterable[str] = (),
    ) -> Exchange:
        ids = set(selection) if selection is not None else set(self.objects)
        objs = [o for rid, o in self.objects.items() if rid in ids]
        evs = [e for e in self.events.values() if e.target in ids or (e.replacement in ids)]
        return Exchange(
            manifest=Manifest(
                source_system=self.system_id,
                complete_snapshot=selection is None,
                object_kinds=sorted({o.role.value for o in objs}),
                scope_coverage=sorted(
                    {f"{k}={v}" for o in objs for k, v in o.scope.context.items()}
                ),
                required_extensions=sorted(extensions),
                transfer_intent=intent,
            ),
            objects=objs,
            events=evs,
        )

    # ============================================================ §3.6 import
    def import_exchange(
        self,
        ex: Exchange,
        *,
        mode: Literal["preserve", "re_derive", "hybrid"] = "preserve",
        principal_map: dict[str, str] | None = None,
        rederive: callable | None = None,
    ) -> Receipt:
        pmap = {**self.principal_map, **(principal_map or {})}
        rcpt = Receipt(exchange_id=ex.manifest.exchange_id, receiver=self.system_id, mode=mode)

        # --- manifest gate
        major = ex.manifest.format_version.rsplit("-", 1)[-1].split(".")[0]
        if major != FORMAT_VERSION.rsplit("-", 1)[-1].split(".")[0]:
            reason = f"format {ex.manifest.format_version} newer/other major than {FORMAT_VERSION}"
            rcpt.entries = [
                ReceiptEntry(target=o.revision_id, status=ReceiptStatus.rejected, reason=reason)
                for o in ex.objects
            ]
            return rcpt
        missing_ext = set(ex.manifest.required_extensions) - self.supported_extensions
        if missing_ext:
            reason = f"required extension(s) unsupported: {sorted(missing_ext)}"
            rcpt.entries = [
                ReceiptEntry(target=o.revision_id, status=ReceiptStatus.rejected, reason=reason)
                for o in ex.objects
            ]
            return rcpt
        missing_profiles = [
            p.name
            for p in ex.manifest.profiles
            if p.required and p.name not in self.supported_extensions
        ]
        if missing_profiles:
            reason = f"required profile(s) unsupported: {missing_profiles}"
            rcpt.entries = [
                ReceiptEntry(target=o.revision_id, status=ReceiptStatus.rejected, reason=reason)
                for o in ex.objects
            ]
            return rcpt

        known = {o.revision_id for o in ex.objects} | set(self.objects) | set(self.origin_map)

        for obj in ex.objects:
            rid = obj.revision_id
            # retries never duplicate (3.6)
            if rid in self.origin_map:
                rcpt.entries.append(
                    ReceiptEntry(
                        target=rid,
                        status=ReceiptStatus.accepted,
                        local_id=self.origin_map[rid],
                        reason="already imported",
                    )
                )
                continue
            # tombstone prevents resurrection (3.5)
            if rid in self.tombstones or (
                obj.predecessor
                and obj.predecessor in self.tombstones
                and obj.ref.local_id == obj.ref.local_id
            ):
                rcpt.entries.append(
                    ReceiptEntry(
                        target=rid,
                        status=ReceiptStatus.rejected,
                        reason="tombstoned revision; resurrection prevented",
                    )
                )
                continue
            # identity conflict (3.1)
            local_same = self.objects.get(rid)
            if local_same is not None and local_same.digest != obj.digest:
                rcpt.entries.append(
                    ReceiptEntry(
                        target=rid,
                        status=ReceiptStatus.rejected,
                        reason="revision id exists with different content",
                    )
                )
                rcpt.conflicts.append(f"revision {rid}: content differs")
                continue
            # credentials are outside exchange (3.3)
            if obj.text and _CREDENTIAL_RE.search(obj.text):
                rcpt.entries.append(
                    ReceiptEntry(
                        target=rid,
                        status=ReceiptStatus.rejected,
                        reason="credential material is outside memory exchange",
                    )
                )
                continue
            # policy mapping (3.3)
            transformations: list[str] = []
            rules = []
            staged = False
            for rule in obj.policy.rules:
                unmapped = [p for p in rule.principals if p != "*" and p not in pmap]
                unsupported = [
                    a for a in rule.actions if a != "*" and a not in self.enforceable_actions
                ]
                if unmapped or unsupported:
                    if obj.policy.required:
                        staged = True
                        rcpt.entries.append(
                            ReceiptEntry(
                                target=rid,
                                status=ReceiptStatus.unresolved,
                                reason=f"unmapped principals {unmapped} / unsupported actions {unsupported}; staged",
                            )
                        )
                        rcpt.retry.append(rid)
                        break
                    transformations.append(f"dropped rule for {unmapped or unsupported}")
                    continue
                rules.append(
                    rule.model_copy(
                        update={"principals": [pmap.get(p, p) for p in rule.principals]}
                    )
                )
            if staged:
                continue
            # evidence availability (3.4)
            derivation = obj.derivation
            if obj.role == EvidenceRole.machine_derived:
                if derivation is None:
                    derivation = Derivation(activity="unknown", unknown=True)
                    transformations.append("provenance unknown (declared)")
                else:
                    missing = [u for u in derivation.used if u not in known]
                    if missing:
                        transformations.append(f"evidence unavailable: {missing}")
            # extensions (3.6): unsupported optional extensions are reported opaque
            for ext in obj.extensions:
                if ext not in self.supported_extensions:
                    transformations.append(f"extension {ext} retained opaque")

            imported = obj.model_copy(
                update={
                    "policy": obj.policy.model_copy(update={"rules": rules}),
                    "derivation": derivation,
                }
            )
            if mode in ("preserve", "hybrid"):
                self.objects[rid] = imported
                self.origin_map[rid] = rid
                status = ReceiptStatus.transformed if transformations else ReceiptStatus.accepted
                rcpt.entries.append(
                    ReceiptEntry(
                        target=rid, status=status, local_id=rid, transformations=transformations
                    )
                )
            if mode in ("re_derive", "hybrid"):
                # new identity linked to what was actually processed (3.6)
                text = rederive(imported) if rederive else imported.text
                new = MemoryObject(
                    ref=ObjectRef(authority=self.system_id, local_id=new_id()),
                    role=EvidenceRole.machine_derived,
                    text=text,
                    scope=imported.scope,
                    policy=imported.policy,
                    derivation=Derivation(
                        activity="re_derive", used=[rid], agent=self.system_id, at=now_iso()
                    ),
                )
                self.objects[new.revision_id] = new
                if mode == "re_derive":
                    self.origin_map[rid] = new.revision_id
                rcpt.entries.append(
                    ReceiptEntry(
                        target=rid,
                        status=ReceiptStatus.transformed,
                        local_id=new.revision_id,
                        transformations=[*transformations, "re-derived"],
                    )
                )

        # --- events (idempotent; unordered/conflicting surface in receipt)
        before = len(self.conflicts)
        for ev in ex.events:
            if (
                ev.target not in self.objects
                and ev.target not in self.origin_map
                and ev.kind not in (LifecycleKind.tombstone, LifecycleKind.delete)
            ):
                rcpt.entries.append(
                    ReceiptEntry(
                        target=ev.event_id,
                        kind="event",
                        status=ReceiptStatus.unresolved,
                        reason=f"target {ev.target} not present",
                    )
                )
                rcpt.retry.append(ev.event_id)
                continue
            self.apply_event(ev)
            rcpt.entries.append(
                ReceiptEntry(target=ev.event_id, kind="event", status=ReceiptStatus.accepted)
            )
        rcpt.conflicts.extend(self.conflicts[before:])

        if ex.manifest.transfer_intent == "move":
            rcpt.move_complete = all(
                e.status in (ReceiptStatus.accepted, ReceiptStatus.transformed)
                for e in rcpt.entries
                if e.kind == "object"
            )
        return rcpt
