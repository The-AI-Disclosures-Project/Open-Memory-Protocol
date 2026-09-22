from __future__ import annotations

from pathlib import Path

import pytest

from semantic_core import (
    Derivation,
    EvidenceRole,
    LifecycleEvent,
    LifecycleKind,
    MemoryObject,
    ObjectRef,
    Policy,
    PolicyRule,
    Scope,
    SemanticStore,
)
from semantic_core.cogx import read_cogx, write_cogx
from semantic_core.schema import ObjectState
from semantic_core.store import PermissionDenied
from semantic_core.validator import FIXTURES_DIR, run_all_fixtures, validate_exchange


def _obj(text, role=EvidenceRole.human_assertion, **kw):
    return MemoryObject(
        ref=ObjectRef(authority="a", local_id=text[:6]),
        role=role,
        text=text,
        scope=Scope(origin_system="a", context={"user": "u"}),
        **kw,
    )


def test_fixtures_all_pass():
    results = run_all_fixtures(FIXTURES_DIR)
    assert len(results) == 11
    failed = [r for r in results if not r.passed]
    assert not failed, "\n".join(f"{r.name}: {r.detail}" for r in failed)


def test_correction_time_travel_and_history_permission():
    s = SemanticStore("s")
    v1 = s.add(
        _obj(
            "Lives in Boston",
            policy=Policy(rules=[PolicyRule(principals=["alice"], actions=["read"])]),
        )
    )
    v2 = s.correct(v1.revision_id, "Lives in Brooklyn", actor="alice")
    assert (
        s.state(v1.revision_id) == ObjectState.superseded
        and s.state(v2.revision_id) == ObjectState.active
    )
    assert [o.text for o in s.current("alice")] == ["Lives in Brooklyn"]
    assert s.current("mallory") == []
    with pytest.raises(PermissionDenied):
        s.historical(v2.recorded_at, "mallory")
    assert {o.text for o in s.historical("2999-01-01", "alice")} == {
        "Lives in Boston",
        "Lives in Brooklyn",
    }


def test_delete_invalidates_dependents_and_tombstone_blocks_readd():
    s = SemanticStore("s")
    t = s.add(_obj("user: secret thing", role=EvidenceRole.transcript))
    d = s.add(
        _obj(
            "derived secret",
            role=EvidenceRole.machine_derived,
            derivation=Derivation(activity="extraction", used=[t.revision_id]),
        )
    )
    s.delete(t.revision_id, actor="user", reason="erasure")
    assert (
        s.state(t.revision_id) == ObjectState.deleted
        and s.state(d.revision_id) == ObjectState.invalidated
    )
    assert s.current() == []
    with pytest.raises(ValueError, match="tombstoned"):
        s.add(t)
    # lineage relationship survives without content
    assert any(
        e.kind == LifecycleKind.tombstone and e.target == t.revision_id for e in s.events.values()
    )


def test_move_intent_and_idempotent_retry():
    src, dst = SemanticStore("src"), SemanticStore("dst")
    a = src.add(_obj("alpha"))
    ex = src.export(intent="move")
    r1 = dst.import_exchange(ex)
    assert r1.move_complete is True and dst.origin_map[a.revision_id] == a.revision_id
    r2 = dst.import_exchange(ex)  # retry
    assert len(dst.objects) == 1 and r2.entries[0].reason == "already imported"


def test_supersede_conflict_is_surfaced():
    s = SemanticStore("s")
    base = s.add(_obj("base"))
    r1, r2 = s.add(_obj("r1")), s.add(_obj("r2"))
    s.apply_event(
        LifecycleEvent(
            kind=LifecycleKind.supersede,
            target=base.revision_id,
            actor="a",
            replacement=r1.revision_id,
        )
    )
    s.apply_event(
        LifecycleEvent(
            kind=LifecycleKind.supersede,
            target=base.revision_id,
            actor="b",
            replacement=r2.revision_id,
        )
    )
    assert s.conflicts and "supersede conflict" in s.conflicts[0]


def test_validator_flags_machine_derived_without_derivation():
    from semantic_core.schema import Exchange, Manifest

    ex = Exchange(
        manifest=Manifest(source_system="x", complete_snapshot=True),
        objects=[_obj("guess", role=EvidenceRole.machine_derived)],
    )
    errs = [f for f in validate_exchange(ex) if f.level == "error"]
    assert len(errs) == 1 and "3.4" == errs[0].part


def test_cogx_round_trip(tmp_path: Path):
    s = SemanticStore("s")
    doc = s.add(_obj("The runbook says blue-green.", role=EvidenceRole.source_artifact))
    ep = s.add(
        MemoryObject(
            ref=ObjectRef(authority="s", local_id="ep1"),
            role=EvidenceRole.transcript,
            text="user: hi\nassistant: hello",
            scope=Scope(origin_system="s", context={"user": "u", "session": "sess1"}),
        )
    )
    s.add(
        _obj(
            "Deploys blue-green",
            role=EvidenceRole.machine_derived,
            derivation=Derivation(
                activity="extraction", used=[doc.revision_id], spans=[f"{ep.revision_id}#turn:0"]
            ),
        )
    )
    ex = s.export()
    losses = write_cogx(ex, tmp_path / "a")
    assert (tmp_path / "a" / "manifest.json").exists() and (
        tmp_path / "a" / "memories.jsonl"
    ).read_text().count("\n") == 1
    assert any("derivation kept only in metadata" in l for l in losses)

    back = read_cogx(tmp_path / "a")
    by_role = {o.role: o for o in back.objects}
    assert by_role[EvidenceRole.source_artifact].text == doc.text
    assert by_role[EvidenceRole.transcript].extensions["cogx"]["turns"][1]["role"] == "assistant"
    assert by_role[EvidenceRole.transcript].scope.context["session"] == "sess1"
    assert (
        by_role[EvidenceRole.machine_derived].derivation.unknown is True
    )  # COGX memories carry no provenance
    assert any("no policy, lifecycle events or tombstones" in n for n in back.manifest.notes)
    # packed form
    write_cogx(ex, tmp_path / "a.cogx.tar.gz", pack=True)
    assert len(read_cogx(tmp_path / "a.cogx.tar.gz").objects) == 3
    # receiver that does not support raw nodes reports them opaque
    (tmp_path / "a" / "nodes.jsonl").write_text(
        '{"kind":"raw_node","properties":{"id":"n1","x":1}}\n'
    )
    ex2 = read_cogx(tmp_path / "a")
    rcpt = SemanticStore("r").import_exchange(ex2)
    raw = next(
        e
        for e in rcpt.entries
        if e.target == next(o.revision_id for o in ex2.objects if "cogx.raw_node" in o.extensions)
    )
    assert raw.status.value == "transformed" and "retained opaque" in raw.transformations[0]


def test_adapters_from_siblings(tmp_path: Path):
    ibm = pytest.importorskip("ibm_memory")
    from semantic_core.adapters import from_ibm_store, from_packer_dir

    store = ibm.MemoryStore("ibm-sys")
    old = store.write("Lives in Boston", author="sruly", scope_tags=["user:sruly"])
    store.override(old.id, "Lives in Brooklyn", author="sruly")
    ex = from_ibm_store(store)
    assert not [f for f in validate_exchange(ex) if f.level == "error"]
    r = SemanticStore("recv").import_exchange(ex)
    assert r.counts.get("accepted", 0) >= 2 and not r.conflicts
    recv = SemanticStore("recv")
    recv.import_exchange(ex)
    assert [o.text for o in recv.current()] == ["Lives in Brooklyn"]

    packer = (
        Path(__file__).resolve().parents[2]
        / "packer-draft-langchain-harness"
        / "examples"
        / "memory"
    )
    exp = from_packer_dir(packer)
    assert len(exp.objects) == 7 and not [f for f in validate_exchange(exp) if f.level == "error"]
