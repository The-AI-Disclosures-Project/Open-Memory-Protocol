"""An immutable memory store with the operations the IBM draft allows.

    Memories have Write / Invalidate / Delete, but no Update (immutable).

Plus `override` (write a new version + invalidate the old, atomically), `as_of` time travel,
scope-tag ACL enforcement on recall, and export/import between systems.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from pathlib import Path

from pydantic import BaseModel, Field

from ibm_memory.schema import ExportBundle, Lifecycle, MemoryRecord, Provenance, now_iso


class ScopeDenied(PermissionError):
    pass


class ScopePolicy(BaseModel):
    """Which scope tags each principal may read and write. The draft leaves the tag values
    undefined and says they "will be linked to ACL policies"; this is the smallest such link."""

    read: dict[str, set[str]] = Field(default_factory=dict)
    write: dict[str, set[str]] = Field(default_factory=dict)
    public_scopes: set[str] = Field(default_factory=set)
    """Scopes every principal may read."""

    def readable(self, principal: str) -> set[str]:
        return self.read.get(principal, set()) | self.public_scopes

    def writable(self, principal: str) -> set[str]:
        return self.write.get(principal, set())

    def check_read(self, principal: str, scopes: Iterable[str]) -> None:
        bad = set(scopes) - self.readable(principal)
        if bad:
            raise ScopeDenied(f"{principal} may not read scopes {sorted(bad)}")

    def check_write(self, principal: str, scopes: Iterable[str]) -> None:
        bad = set(scopes) - self.writable(principal)
        if bad:
            raise ScopeDenied(f"{principal} may not write scopes {sorted(bad)}")


def _tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9][a-z0-9+#._-]*", text.lower()) if len(t) > 1}


class MemoryStore:
    def __init__(
        self, system_id: str, *, policy: ScopePolicy | None = None, path: str | Path | None = None
    ) -> None:
        self.system_id = system_id
        self.policy = policy
        self.path = Path(path) if path else None
        self._records: dict[str, MemoryRecord] = {}
        if self.path and self.path.exists():
            bundle = ExportBundle.model_validate_json(self.path.read_text(encoding="utf-8"))
            self._records = {r.id: r for r in bundle.records}

    # --------------------------------------------------------------- ids
    def resolve_id(self, id_or_prefix: str) -> str:
        """Accept a full id or an unambiguous prefix (recall output shows 8 chars)."""
        if id_or_prefix in self._records:
            return id_or_prefix
        matches = [k for k in self._records if k.startswith(id_or_prefix)]
        if len(matches) == 1:
            return matches[0]
        if not matches:
            raise KeyError(f"no memory with id {id_or_prefix!r}")
        raise KeyError(f"ambiguous id prefix {id_or_prefix!r} ({len(matches)} matches)")

    # --------------------------------------------------------------- persistence
    def save(self) -> None:
        if self.path:
            self.path.write_text(self.export().model_dump_json(indent=2), encoding="utf-8")

    # --------------------------------------------------------------- the verbs
    def write(
        self,
        body: str,
        *,
        author: str,
        provenance: Provenance | None = None,
        semantic_tags: Iterable[str] = (),
        scope_tags: Iterable[str] = (),
        source_material: Iterable[str] = (),
        principal: str | None = None,
        supersedes: str | None = None,
        version: int = 1,
        created_at: str | None = None,
    ) -> MemoryRecord:
        scope_tags = sorted(set(scope_tags))
        if self.policy and principal is not None:
            self.policy.check_write(principal, scope_tags)
        rec = MemoryRecord(
            body=body,
            lifecycle=Lifecycle(
                author=author,
                provenance=provenance or Provenance(),
                source_material=list(source_material),
                version=version,
                created_at=created_at or now_iso(),
            ),
            semantic_tags=sorted(set(semantic_tags)),
            scope_tags=scope_tags,
            supersedes=supersedes,
        )
        self._records[rec.id] = rec
        self.save()
        return rec

    def invalidate(
        self, id_: str, *, at: str | None = None, principal: str | None = None
    ) -> MemoryRecord:
        rec = self._records[id_]
        if self.policy and principal is not None:
            self.policy.check_write(principal, rec.scope_tags)
        rec = rec.invalidated(at)
        self._records[id_] = rec
        self.save()
        return rec

    def override(
        self,
        id_: str,
        body: str,
        *,
        author: str,
        provenance: Provenance | None = None,
        semantic_tags: Iterable[str] | None = None,
        scope_tags: Iterable[str] | None = None,
        source_material: Iterable[str] = (),
        principal: str | None = None,
    ) -> MemoryRecord:
        """Logical mutation: new record (version+1) supersedes the old, old is invalidated at
        the same instant, so `as_of` before that instant still sees the old body."""
        id_ = self.resolve_id(id_)
        old = self._records[id_]
        at = now_iso()
        new = self.write(
            body,
            author=author,
            provenance=provenance,
            semantic_tags=old.semantic_tags if semantic_tags is None else semantic_tags,
            scope_tags=old.scope_tags if scope_tags is None else scope_tags,
            source_material=[*source_material, f"supersedes:{id_}"],
            principal=principal,
            supersedes=id_,
            version=old.lifecycle.version + 1,
            created_at=at,
        )
        self.invalidate(id_, at=at, principal=principal)
        return new

    def delete(self, id_: str, *, principal: str | None = None) -> None:
        id_ = self.resolve_id(id_)
        rec = self._records[id_]
        if self.policy and principal is not None:
            self.policy.check_write(principal, rec.scope_tags)
        del self._records[id_]
        self.save()

    # --------------------------------------------------------------- reads
    def get(self, id_: str) -> MemoryRecord | None:
        try:
            return self._records[self.resolve_id(id_)]
        except KeyError:
            return None

    def all(self) -> list[MemoryRecord]:
        return sorted(self._records.values(), key=lambda r: r.lifecycle.created_at)

    def as_of(self, ts: str | None = None) -> list[MemoryRecord]:
        """Time travel: every record that was valid at `ts` (default now)."""
        return [r for r in self.all() if r.valid_at(ts)]

    def recall(
        self,
        query: str,
        *,
        principal: str | None = None,
        at: str | None = None,
        semantic_tags: Iterable[str] = (),
        scope_tags: Iterable[str] | None = None,
        limit: int = 10,
    ) -> list[MemoryRecord]:
        """Draft §Recall Interface: query seed, optional timestamp (default now), optional
        semantic and scope tags. "System MUST validate requested scopes against ACLs"."""
        if self.policy and principal is not None:
            if scope_tags is not None:
                self.policy.check_read(principal, scope_tags)
                allowed = set(scope_tags)
            else:
                allowed = self.policy.readable(principal)
        else:
            allowed = None if scope_tags is None else set(scope_tags)
        want_sem = set(semantic_tags)
        q = _tokens(query)
        scored = []
        for r in self.as_of(at):
            if allowed is not None and not (set(r.scope_tags) & allowed):
                continue
            if want_sem and not want_sem <= set(r.semantic_tags):
                continue
            overlap = len(q & (_tokens(r.body) | set(r.semantic_tags)))
            if q and overlap == 0:
                continue
            scored.append((overlap, r.lifecycle.created_at, r))
        scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
        return [r for _, _, r in scored[:limit]]

    def history(self, id_: str) -> list[MemoryRecord]:
        """Follow the supersedes chain back from a record: newest first."""
        out = []
        cur = self.get(id_)
        while cur is not None:
            out.append(cur)
            cur = self._records.get(cur.supersedes) if cur.supersedes else None
        return out

    # --------------------------------------------------------------- export / import
    def export(
        self, *, tag_context: dict | None = None, include_invalid: bool = True
    ) -> ExportBundle:
        recs = self.all() if include_invalid else self.as_of()
        return ExportBundle(system_id=self.system_id, records=recs, tag_context=tag_context or {})

    def import_bundle(
        self,
        bundle: ExportBundle,
        *,
        scope_map: dict[str, str] | None = None,
        semantic_map: dict[str, str] | None = None,
        drop_unmapped_scopes: bool = False,
    ) -> list[MemoryRecord]:
        """Draft: "when imported into another [system], it becomes a new memory in that
        system"; "Discontinuity between semantic and scope tags may necessitate a
        mapping/migration step"; "ACLs bound to scope tags would need explicit mapping"."""
        scope_map = scope_map or {}
        semantic_map = semantic_map or {}
        id_map: dict[str, str] = {}
        imported: list[MemoryRecord] = []
        for old in sorted(bundle.records, key=lambda r: r.lifecycle.created_at):
            scopes = []
            for s in old.scope_tags:
                if s in scope_map:
                    scopes.append(scope_map[s])
                elif not drop_unmapped_scopes:
                    scopes.append(s)
            new = MemoryRecord(
                body=old.body,
                lifecycle=old.lifecycle.model_copy(
                    update={
                        "source_material": [
                            *old.lifecycle.source_material,
                            f"import:{bundle.system_id}:{old.id}",
                        ]
                    }
                ),
                semantic_tags=sorted({semantic_map.get(t, t) for t in old.semantic_tags}),
                scope_tags=sorted(set(scopes)),
                supersedes=id_map.get(old.supersedes) if old.supersedes else None,
                origin=f"{bundle.system_id}:{old.id}",
            )
            id_map[old.id] = new.id
            self._records[new.id] = new
            imported.append(new)
        self.save()
        return imported


def load_bundle(path: str | Path) -> ExportBundle:
    return ExportBundle.model_validate_json(Path(path).read_text(encoding="utf-8"))


def dump_bundle(bundle: ExportBundle, path: str | Path) -> None:
    Path(path).write_text(json.dumps(bundle.model_dump(mode="json"), indent=2), encoding="utf-8")
