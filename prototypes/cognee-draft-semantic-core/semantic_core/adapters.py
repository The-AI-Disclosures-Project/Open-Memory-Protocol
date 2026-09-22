"""The sibling prototypes as exchanges. Each import is lazy so the package works without them.

These are mappings, not judgments: each draft keeps its own model, and the notes in the
resulting manifest say what that model does not carry.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from semantic_core.schema import (
    Derivation,
    EvidenceRole,
    Exchange,
    LifecycleEvent,
    LifecycleKind,
    Manifest,
    MemoryObject,
    ObjectRef,
    Policy,
    PolicyRule,
    Profile,
    Scope,
)


def from_ibm_store(store: Any) -> Exchange:
    """ibm_memory.MemoryStore -> exchange. IBM records already carry most of the core."""
    objects, events = [], []
    for r in store.all():
        lc = r.lifecycle
        scopes = {s.split(":", 1)[0]: s.split(":", 1)[1] for s in r.scope_tags if ":" in s}
        objects.append(
            MemoryObject(
                ref=ObjectRef(authority=store.system_id, namespace="ibm.record", local_id=r.id),
                revision_id=r.id,
                predecessor=r.supersedes,
                role=EvidenceRole.machine_derived
                if lc.provenance.ai_used
                else EvidenceRole.human_assertion,
                text=r.body,
                scope=Scope(
                    subject=scopes.get("user"),
                    owner=lc.author,
                    author=None if lc.provenance.ai_used else lc.author,
                    agent=lc.provenance.agent,
                    origin_system=store.system_id,
                    context=scopes,
                ),
                policy=Policy(
                    rules=[PolicyRule(principals=[s for s in r.scope_tags], actions=["read"])],
                    required=False,
                ),
                derivation=Derivation(
                    activity=lc.provenance.how or "ibm.remember",
                    used=[
                        s.removeprefix("supersedes:")
                        for s in lc.source_material
                        if s.startswith("supersedes:")
                    ],
                    spans=[s for s in lc.source_material if not s.startswith("supersedes:")],
                    agent=lc.provenance.model,
                    at=lc.created_at,
                )
                if lc.provenance.ai_used
                else None,
                recorded_at=lc.created_at,
                extensions={"ibm": {"version": lc.version, "semantic_tags": r.semantic_tags}},
            )
        )
        if lc.invalidated_at:
            events.append(
                LifecycleEvent(
                    kind=LifecycleKind.invalidate,
                    target=r.id,
                    actor=lc.author,
                    effective_at=lc.invalidated_at,
                )
            )
        if r.supersedes:
            events.append(
                LifecycleEvent(
                    kind=LifecycleKind.supersede,
                    target=r.supersedes,
                    actor=lc.author,
                    effective_at=lc.created_at,
                    replacement=r.id,
                )
            )
    return Exchange(
        manifest=Manifest(
            source_system=store.system_id,
            complete_snapshot=True,
            profiles=[Profile(name="ibm-draft", version="0.1")],
            object_kinds=sorted({o.role.value for o in objects}),
            notes=[
                "IBM scope tags mapped to read-only policy rules (draft leaves ACLs to the system)",
                "IBM has no deletion coverage or tombstones; deleted records are simply absent",
            ],
        ),
        objects=objects,
        events=events,
    )


def from_packer_dir(root: str | Path, *, authority: str = "packer") -> Exchange:
    """A Packer memory directory -> exchange of human_assertion objects (one per file)."""
    root = Path(root).resolve()
    objects = []
    for md in sorted(root.rglob("*.md")):
        rel = md.relative_to(root).as_posix()
        if any(p.startswith(".") for p in rel.split("/")):
            continue
        objects.append(
            MemoryObject(
                ref=ObjectRef(authority=authority, namespace="packer.file", local_id=rel),
                role=EvidenceRole.human_assertion,
                text=md.read_text(encoding="utf-8"),
                scope=Scope(
                    origin_system=authority,
                    context={"tier": "core" if "/" not in rel else "deferred"},
                ),
                extensions={"packer": {"path": rel}},
            )
        )
    return Exchange(
        manifest=Manifest(
            source_system=authority,
            complete_snapshot=True,
            profiles=[Profile(name="packer-markdown", version="0.2")],
            object_kinds=["human_assertion"],
            notes=[
                "Packer files carry no identity, provenance, policy or lifecycle; role assumed human_assertion",
                "file depth mapped to scope.context.tier; imported text has no instruction authority",
            ],
        ),
        objects=objects,
    )


def from_fmp(client: Any, *, limit: int = 200) -> Exchange:
    """fmp.FMPClient -> exchange of transcripts + machine_derived inferences."""
    name = client.name
    objects = []
    if client.supports("read_transcripts"):
        ts, _, _ = client.read_transcripts(limit=limit, include_messages=True)
        for t in ts:
            text = "\n".join(f"{m.role}: {m.content}" for m in (t.messages or []))
            objects.append(
                MemoryObject(
                    ref=ObjectRef(authority=name, namespace="fmp.transcript", local_id=t.id),
                    revision_id=f"transcript:{t.id}",
                    role=EvidenceRole.transcript,
                    text=text,
                    scope=Scope(origin_system=name, context={"session": t.id}),
                    recorded_at=t.started_at or "",
                    extensions={"fmp": {"source": t.source, "partial": t.partial}},
                )
            )
    if client.supports("read_inferences"):
        infs, _, _ = client.read_inferences(limit=limit)
        for i in infs:
            objects.append(
                MemoryObject(
                    ref=ObjectRef(authority=name, namespace="fmp.inference", local_id=i.id),
                    revision_id=f"inference:{i.id}",
                    role=EvidenceRole.machine_derived,
                    text=i.content,
                    scope=Scope(origin_system=name, agent=i.created_by.name),
                    derivation=Derivation(
                        activity="fmp.inference",
                        used=[b for b in i.based_on if "#" not in b],
                        spans=[b for b in i.based_on if "#" in b],
                        agent=i.created_by.model,
                        at=i.date,
                    ),
                    recorded_at=i.date,
                )
            )
    return Exchange(
        manifest=Manifest(
            source_system=name,
            complete_snapshot=False,
            profiles=[Profile(name="aidp-fmp", version="0.1")],
            object_kinds=sorted({o.role.value for o in objects}),
            notes=[
                "FMP has no policy, lifecycle events or receipts; server-local permissions not carried",
                "paginated read; partial unless every page was fetched",
            ],
        ),
        objects=objects,
    )
