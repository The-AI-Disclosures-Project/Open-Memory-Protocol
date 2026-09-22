"""COGX 0.1 (§4) reader/writer with no Cognee dependency.

Layout: a directory with manifest.json and documents/episodes/entities/facts/memories/
memory_blocks/nodes .jsonl, optionally packed as .cogx.tar.gz. Field names follow
cognee/modules/migration/cogx.py at the draft's pinned revision.

Mapping to the core (losses are reported in the exchange manifest notes and, on the way
back, returned from `write_cogx`):

    document      -> source_artifact
    episode       -> transcript (turns rendered as "role: content" lines; turn refs as spans)
    entity, fact, memory -> machine_derived (fact provenance -> derivation.used; valid_at /
                     invalid_at -> applies_from / applies_until)
    memory_block  -> human_assertion? unknown. COGX does not say who wrote a block, so it is
                     imported as machine_derived with Derivation(unknown=True)
    raw_node      -> extension "cogx.raw_node" (opaque unless the receiver supports it)
"""

from __future__ import annotations

import io
import json
import tarfile
from pathlib import Path
from typing import Any

from semantic_core.schema import (
    Derivation,
    EvidenceRole,
    Exchange,
    Manifest,
    MemoryObject,
    ObjectRef,
    Profile,
    Scope,
)

COGX_VERSION = "0.1"
RECORD_FILES = {
    "document": "documents.jsonl",
    "episode": "episodes.jsonl",
    "entity": "entities.jsonl",
    "fact": "facts.jsonl",
    "memory": "memories.jsonl",
    "memory_block": "memory_blocks.jsonl",
}
RAW_NODES_FILE = "nodes.jsonl"
MANIFEST_FILE = "manifest.json"
RAW_NODE_EXTENSION = "cogx.raw_node"


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def _iso(v: Any) -> str | None:
    return None if v is None else str(v)


def _scope(rec: dict[str, Any], system: str) -> Scope:
    sc = rec.get("scope") or {}
    ctx = {k.removesuffix("_id"): v for k, v in sc.items() if v}
    return Scope(
        subject=sc.get("user_id"),
        owner=sc.get("user_id"),
        agent=sc.get("agent_id"),
        origin_system=system,
        context=ctx,
    )


def read_cogx(path: str | Path) -> Exchange:
    path = Path(path)
    if path.is_file():  # .cogx.tar.gz
        with tarfile.open(path, "r:*") as tar:
            members = {
                m.name.split("/")[-1]: tar.extractfile(m).read()
                for m in tar.getmembers()
                if m.isfile()
            }
        read = lambda name: [
            json.loads(l) for l in members.get(name, b"").decode().splitlines() if l.strip()
        ]
        manifest = json.loads(members[MANIFEST_FILE])
    else:
        read = lambda name: _read_jsonl(path / name)
        manifest = json.loads((path / MANIFEST_FILE).read_text(encoding="utf-8"))

    major = str(manifest.get("cogx_version", "0")).split(".")[0]
    if int(major) > int(COGX_VERSION.split(".")[0]):
        raise ValueError(f"COGX {manifest['cogx_version']} is newer than supported {COGX_VERSION}")
    system = manifest.get("source_system", "unknown")
    notes = [
        f"cogx_version={manifest.get('cogx_version')}",
        "complete_snapshot unknown: COGX manifests do not declare it",
        "COGX carries no policy, lifecycle events or tombstones; none imported",
    ]
    objects: list[MemoryObject] = []

    def ref(rec: dict[str, Any], kind: str) -> ObjectRef:
        return ObjectRef(
            authority=rec.get("external_system") or system,
            namespace=f"cogx.{kind}",
            local_id=rec["external_id"],
        )

    for rec in read(RECORD_FILES["document"]):
        objects.append(
            MemoryObject(
                ref=ref(rec, "document"),
                role=EvidenceRole.source_artifact,
                text=rec["content"],
                scope=_scope(rec, system),
                recorded_at=_iso(rec.get("created_at")) or "",
                extensions={
                    "cogx": {
                        "title": rec.get("title"),
                        "mime_type": rec.get("mime_type"),
                        "metadata": rec.get("metadata", {}),
                    }
                },
            )
        )
    for rec in read(RECORD_FILES["episode"]):
        turns = rec.get("turns", [])
        text = "\n".join(f"{t['role']}: {t['content']}" for t in turns)
        objects.append(
            MemoryObject(
                ref=ref(rec, "episode"),
                role=EvidenceRole.transcript,
                text=text,
                scope=_scope(rec, system),
                recorded_at=_iso(rec.get("created_at")) or "",
                extensions={
                    "cogx": {
                        "title": rec.get("title"),
                        "turns": turns,
                        "metadata": rec.get("metadata", {}),
                    }
                },
            )
        )
    for kind in ("entity", "fact", "memory", "memory_block"):
        for rec in read(RECORD_FILES[kind]):
            if kind == "entity":
                text = rec["name"] + (f": {rec['description']}" if rec.get("description") else "")
                deriv = Derivation(activity="cogx.entity_extraction", unknown=True)
            elif kind == "fact":
                text = (
                    rec.get("fact_text")
                    or f"{rec['subject_ref']} {rec['predicate']} {rec['object_ref']}"
                )
                prov = rec.get("provenance") or []
                deriv = Derivation(
                    activity="cogx.fact_extraction", used=list(prov), unknown=not prov
                )
            elif kind == "memory":
                text = rec["content"]
                deriv = Derivation(activity="cogx.memory", unknown=True)
            else:
                text = f"{rec['label']}: {rec['value']}"
                deriv = Derivation(activity="cogx.memory_block", unknown=True)
            objects.append(
                MemoryObject(
                    ref=ref(rec, kind),
                    role=EvidenceRole.machine_derived,
                    text=text,
                    scope=_scope(rec, system),
                    derivation=deriv,
                    recorded_at=_iso(rec.get("created_at")) or "",
                    applies_from=_iso(rec.get("valid_at")),
                    applies_until=_iso(rec.get("invalid_at")),
                    extensions={
                        "cogx": {k: v for k, v in rec.items() if k not in ("scope", "content")}
                    },
                )
            )
    raw = read(RAW_NODES_FILE)
    for i, rec in enumerate(raw):
        objects.append(
            MemoryObject(
                ref=ObjectRef(
                    authority=system,
                    namespace="cogx.raw_node",
                    local_id=str(rec.get("properties", {}).get("id", i)),
                ),
                role=EvidenceRole.machine_derived,
                text=None,
                scope=Scope(origin_system=system),
                derivation=Derivation(activity="cogx.raw_node", unknown=True),
                extensions={RAW_NODE_EXTENSION: rec.get("properties", {})},
            )
        )
    if raw:
        notes.append(
            f"{len(raw)} raw nodes carried as extension {RAW_NODE_EXTENSION} (opaque unless supported)"
        )
    return Exchange(
        manifest=Manifest(
            source_system=system,
            profiles=[
                Profile(name="cogx", version=str(manifest.get("cogx_version", COGX_VERSION)))
            ],
            object_kinds=sorted({o.role.value for o in objects}),
            complete_snapshot=False,
            notes=notes + list(manifest.get("notes", [])),
        ),
        objects=objects,
    )


def write_cogx(ex: Exchange, path: str | Path, *, pack: bool = False) -> list[str]:
    """Write an exchange as a COGX directory (or .cogx.tar.gz). Returns the list of losses."""
    path = Path(path)
    losses: list[str] = []
    files: dict[str, list[dict[str, Any]]] = {f: [] for f in RECORD_FILES.values()}
    files[RAW_NODES_FILE] = []
    for o in ex.objects:
        base = {
            "external_system": o.ref.authority,
            "external_id": o.ref.local_id,
            "scope": {
                "user_id": o.scope.context.get("user") or o.scope.subject,
                "agent_id": o.scope.context.get("agent") or o.scope.agent,
                "session_id": o.scope.context.get("session"),
                "run_id": o.scope.context.get("run"),
            },
            "created_at": o.recorded_at or None,
            "updated_at": None,
            "metadata": {
                "omp_revision_id": o.revision_id,
                "omp_predecessor": o.predecessor,
                "omp_role": o.role.value,
            },
        }
        if o.policy.rules:
            losses.append(f"{o.revision_id}: policy rules not representable in COGX")
        if RAW_NODE_EXTENSION in o.extensions:
            files[RAW_NODES_FILE].append(
                {"kind": "raw_node", "properties": o.extensions[RAW_NODE_EXTENSION]}
            )
            continue
        cx = o.extensions.get("cogx", {})
        if o.role == EvidenceRole.source_artifact:
            files["documents.jsonl"].append(
                {
                    **base,
                    "kind": "document",
                    "content": o.text or "",
                    "title": cx.get("title"),
                    "mime_type": cx.get("mime_type"),
                }
            )
        elif o.role == EvidenceRole.transcript:
            turns = cx.get("turns") or [
                {"role": ln.split(":", 1)[0], "content": ln.split(":", 1)[1].strip()}
                for ln in (o.text or "").splitlines()
                if ":" in ln
            ]
            files["episodes.jsonl"].append(
                {**base, "kind": "episode", "turns": turns, "title": cx.get("title")}
            )
        elif o.role == EvidenceRole.human_assertion:
            files["memory_blocks.jsonl"].append(
                {
                    **base,
                    "kind": "memory_block",
                    "label": cx.get("label", o.ref.local_id),
                    "value": o.text or "",
                    "limit": cx.get("limit"),
                }
            )
            losses.append(
                f"{o.revision_id}: human_assertion role becomes a memory_block (authorship not carried)"
            )
        else:
            if cx.get("kind") == "fact":
                files["facts.jsonl"].append(
                    {
                        **base,
                        "kind": "fact",
                        "subject_ref": cx["subject_ref"],
                        "predicate": cx["predicate"],
                        "object_ref": cx["object_ref"],
                        "fact_text": o.text,
                        "valid_at": o.applies_from,
                        "invalid_at": o.applies_until,
                        "confidence": cx.get("confidence"),
                        "provenance": list(o.derivation.used) if o.derivation else [],
                    }
                )
            elif cx.get("kind") == "entity":
                files["entities.jsonl"].append(
                    {
                        **base,
                        "kind": "entity",
                        "name": cx["name"],
                        "entity_type": cx.get("entity_type"),
                        "description": cx.get("description"),
                        "aliases": cx.get("aliases", []),
                        "attributes": cx.get("attributes", {}),
                    }
                )
            else:
                rec = {
                    **base,
                    "kind": "memory",
                    "content": o.text or "",
                    "categories": cx.get("categories", []),
                }
                if o.derivation and (o.derivation.used or o.derivation.spans):
                    rec["metadata"]["omp_derivation"] = o.derivation.model_dump()
                    losses.append(
                        f"{o.revision_id}: derivation kept only in metadata (COGX memories have no provenance field)"
                    )
                files["memories.jsonl"].append(rec)
    if ex.events:
        losses.append(f"{len(ex.events)} lifecycle event(s) not representable in COGX; dropped")
    manifest = {
        "cogx_version": COGX_VERSION,
        "source_system": ex.manifest.source_system,
        "exported_at": ex.manifest.exported_at,
        "counts": {f.removesuffix(".jsonl"): len(v) for f, v in files.items()},
        "embedding_model": None,
        "migration_revision": None,
        "notes": [f"omp_exchange_id={ex.manifest.exchange_id}", *losses],
    }

    def dump(name: str, rows: list[dict[str, Any]]) -> bytes:
        return "".join(json.dumps(r, default=str) + "\n" for r in rows).encode("utf-8")

    if pack:
        with tarfile.open(path, "w:gz") as tar:

            def add(name: str, data: bytes) -> None:
                info = tarfile.TarInfo(name)
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))

            add(MANIFEST_FILE, json.dumps(manifest, indent=2, default=str).encode())
            for name, rows in files.items():
                add(name, dump(name, rows))
    else:
        path.mkdir(parents=True, exist_ok=True)
        (path / MANIFEST_FILE).write_text(
            json.dumps(manifest, indent=2, default=str), encoding="utf-8"
        )
        for name, rows in files.items():
            (path / name).write_bytes(dump(name, rows))
    return losses
