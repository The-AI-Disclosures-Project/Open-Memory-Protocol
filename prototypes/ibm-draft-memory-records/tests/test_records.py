"""Tests mapping to the IBM draft's interface elements and implications."""

from __future__ import annotations

import time
from pathlib import Path

import pytest
from pydantic import ValidationError

from ibm_memory import MemoryStore, Provenance, ScopeDenied, ScopePolicy
from ibm_memory.schema import SCHEMA_VERSION, ExportBundle
from ibm_memory.store import dump_bundle, load_bundle


def _store(**kw):
    return MemoryStore("sysA", **kw)


def test_record_has_every_interface_element():
    s = _store()
    r = s.write(
        "User prefers dark mode",
        author="sruly",
        provenance=Provenance(ai_used=True, model="m", how="extracted"),
        semantic_tags=["preference"],
        scope_tags=["user:sruly"],
        source_material=["transcript:1#3"],
    )
    assert r.id and r.body and r.lifecycle.author == "sruly"
    assert (
        r.lifecycle.provenance.ai_used
        and r.lifecycle.created_at
        and r.lifecycle.invalidated_at is None
    )
    assert r.lifecycle.version == 1 and r.lifecycle.source_material == ["transcript:1#3"]
    assert r.semantic_tags == ["preference"] and r.scope_tags == ["user:sruly"]


def test_records_are_immutable():
    r = _store().write("x", author="a")
    with pytest.raises(ValidationError):
        r.body = "y"  # type: ignore[misc]


def test_override_and_invalidate_give_time_travel():
    s = _store()
    old = s.write("Lives in Boston", author="u", scope_tags=["user:u"])
    t_between = old.lifecycle.created_at
    time.sleep(1.1)  # second-resolution timestamps
    new = s.override(old.id, "Lives in Brooklyn", author="u")
    assert new.supersedes == old.id and new.lifecycle.version == 2
    assert (
        not s.get(old.id).is_valid
        and s.get(old.id).lifecycle.invalidated_at == new.lifecycle.created_at
    )
    now_bodies = [r.body for r in s.as_of()]
    assert now_bodies == ["Lives in Brooklyn"]
    then_bodies = [r.body for r in s.as_of(t_between)]
    assert then_bodies == ["Lives in Boston"]
    assert [r.lifecycle.version for r in s.history(new.id)] == [2, 1]
    # recall honours the timestamp too
    assert [r.body for r in s.recall("lives", at=t_between)] == ["Lives in Boston"]
    assert [r.body for r in s.recall("lives")] == ["Lives in Brooklyn"]


def test_no_update_only_write_invalidate_delete():
    s = _store()
    assert not hasattr(s, "update")
    r = s.write("x", author="a")
    s.invalidate(r.id)
    assert not s.get(r.id).is_valid and s.get(r.id) is not None
    s.delete(r.id)
    assert s.get(r.id) is None


def test_scope_acl_enforced_on_recall_and_write():
    pol = ScopePolicy(
        read={"alice": {"user:alice", "team:eng"}},
        write={"alice": {"user:alice"}},
        public_scopes={"public"},
    )
    s = _store(policy=pol)
    s.write("eng standup 9:30", author="bob", scope_tags=["team:eng"])
    s.write("finance forecast", author="carol", scope_tags=["team:finance"])
    s.write("company holiday Friday", author="hr", scope_tags=["public"])
    s.write("alice likes tea", author="alice", scope_tags=["user:alice"])

    # default: everything alice may read, nothing else
    bodies = {r.body for r in s.recall("", principal="alice")}
    assert bodies == {"eng standup 9:30", "company holiday Friday", "alice likes tea"}
    # explicit scope she may not read -> MUST be rejected
    with pytest.raises(ScopeDenied):
        s.recall("forecast", principal="alice", scope_tags=["team:finance"])
    # writes outside her write scopes are rejected
    with pytest.raises(ScopeDenied):
        s.write("sneaky", author="alice", scope_tags=["team:eng"], principal="alice")


def test_recall_by_query_and_semantic_tags():
    s = _store()
    s.write("deploys with blue-green", author="u", semantic_tags=["ops"])
    s.write("prefers espresso", author="u", semantic_tags=["preference"])
    assert [r.body for r in s.recall("espresso")] == ["prefers espresso"]
    assert [r.body for r in s.recall("", semantic_tags=["ops"])] == ["deploys with blue-green"]
    assert s.recall("nothing matches this") == []


def test_export_import_creates_new_memories_with_mapping(tmp_path: Path):
    a = _store()
    old = a.write("Lives in Boston", author="u", scope_tags=["acct:123"], semantic_tags=["home"])
    a.override(old.id, "Lives in Brooklyn", author="u")
    bundle = a.export(tag_context={"home": "https://schema.org/homeLocation"})
    assert (
        bundle.schema_version == SCHEMA_VERSION
        and bundle.system_id == "sysA"
        and len(bundle.records) == 2
    )
    dump_bundle(bundle, tmp_path / "a.json")
    loaded = load_bundle(tmp_path / "a.json")
    assert loaded == bundle

    b = MemoryStore("sysB")
    imported = b.import_bundle(
        loaded, scope_map={"acct:123": "user:sruly"}, semantic_map={"home": "residence"}
    )
    assert len(imported) == 2
    ids_a = {r.id for r in bundle.records}
    assert not ({r.id for r in imported} & ids_a)  # new identifiers in the new system
    assert all(r.origin.startswith("sysA:") for r in imported)
    assert all(
        r.scope_tags == ["user:sruly"] and r.semantic_tags == ["residence"] for r in imported
    )
    # supersedes chain remapped to new ids; invalidation state preserved
    valid = b.as_of()
    assert [r.body for r in valid] == ["Lives in Brooklyn"]
    assert b.history(valid[0].id)[1].body == "Lives in Boston"
    assert any(sm.startswith("import:sysA:") for sm in valid[0].lifecycle.source_material)
    # the origin system is untouched
    assert [r.body for r in a.as_of()] == ["Lives in Brooklyn"]


def test_drop_unmapped_scopes(tmp_path):
    a = _store()
    a.write("x", author="u", scope_tags=["acct:1", "team:eng"])
    b = MemoryStore("sysB")
    (r,) = b.import_bundle(a.export(), scope_map={"acct:1": "user:u"}, drop_unmapped_scopes=True)
    assert r.scope_tags == ["user:u"]


def test_persistence_round_trip(tmp_path: Path):
    p = tmp_path / "store.json"
    s = MemoryStore("sys", path=p)
    s.write("persisted", author="u")
    s2 = MemoryStore("sys", path=p)
    assert [r.body for r in s2.all()] == ["persisted"]
    assert ExportBundle.model_validate_json(p.read_text()).system_id == "sys"


def test_short_id_prefixes_resolve():
    s = _store()
    r = s.write("x", author="a")
    assert s.get(r.id[:8]) == r
    new = s.override(r.id[:8], "y", author="a")
    assert new.supersedes == r.id
    with pytest.raises(KeyError, match="no memory with id"):
        s.override("zzzzzzzz", "y", author="a")
