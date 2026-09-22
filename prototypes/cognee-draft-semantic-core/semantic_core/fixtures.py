"""Generate the §6 fixtures deterministically: `python -m semantic_core.fixtures`.

Each fixture is an exchange plus what a conforming receiver must do with it.
"""

from __future__ import annotations

import json
from pathlib import Path

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
    Scope,
)
from semantic_core.validator import FIXTURES_DIR

SRC = "source"
T0, T1, T2, T3 = (
    "2026-09-01T00:00:00+00:00",
    "2026-09-02T00:00:00+00:00",
    "2026-09-03T00:00:00+00:00",
    "2026-09-04T00:00:00+00:00",
)


def _obj(
    lid: str,
    role: EvidenceRole,
    text: str,
    *,
    rev: str | None = None,
    pred: str | None = None,
    deriv: Derivation | None = None,
    policy: Policy | None = None,
    at: str = T0,
    **kw,
) -> MemoryObject:
    return MemoryObject(
        ref=ObjectRef(authority=SRC, local_id=lid),
        revision_id=rev or f"rev-{lid}",
        predecessor=pred,
        role=role,
        text=text,
        scope=Scope(subject="alice", owner="alice", origin_system=SRC, context={"user": "alice"}),
        policy=policy or Policy(rules=[], required=False),
        derivation=deriv,
        recorded_at=at,
        **kw,
    )


def _ex(objects, events=(), complete=True, **m) -> Exchange:
    return Exchange(
        manifest=Manifest(
            source_system=SRC,
            complete_snapshot=complete,
            object_kinds=sorted({o.role.value for o in objects}),
            **m,
        ),
        objects=list(objects),
        events=list(events),
    )


def build() -> dict[str, dict]:
    fx: dict[str, dict] = {}

    # 1. evidence and derivation: a transcript, and a memory derived from it with a span
    t = _obj("t1", EvidenceRole.transcript, "user: I take my coffee black\nassistant: noted")
    m = _obj(
        "m1",
        EvidenceRole.machine_derived,
        "Alice takes coffee black",
        deriv=Derivation(
            activity="extraction",
            used=[t.revision_id],
            spans=[f"{t.revision_id}#turn:0"],
            agent="model-x",
            at=T1,
        ),
        at=T1,
    )
    orphan = _obj(
        "m2",
        EvidenceRole.machine_derived,
        "Alice likes tea",
        deriv=Derivation(activity="extraction", used=["rev-missing"], agent="model-x", at=T1),
        at=T1,
    )
    fx["01_evidence_and_derivation"] = {
        "exchange": _ex([t, m, orphan]).model_dump(mode="json"),
        "expect": {
            "statuses": {
                t.revision_id: "accepted",
                m.revision_id: "accepted",
                orphan.revision_id: "transformed",
            },
            "current_texts": [t.text, m.text, orphan.text],
            "validator_errors": 0,
        },
    }

    # 2. correction: v2 supersedes v1; current shows only v2
    v1 = _obj("home", EvidenceRole.human_assertion, "Lives in Boston")
    v2 = _obj(
        "home",
        EvidenceRole.human_assertion,
        "Lives in Brooklyn",
        rev="rev-home-2",
        pred=v1.revision_id,
        at=T2,
    )
    sup = LifecycleEvent(
        event_id="ev-sup-1",
        kind=LifecycleKind.supersede,
        target=v1.revision_id,
        actor="alice",
        effective_at=T2,
        replacement=v2.revision_id,
    )
    fx["02_correction"] = {
        "exchange": _ex([v1, v2], [sup]).model_dump(mode="json"),
        "expect": {
            "statuses": {v1.revision_id: "accepted", v2.revision_id: "accepted"},
            "current_texts": ["Lives in Brooklyn"],
            "validator_errors": 0,
        },
    }

    # 3. consolidation: summary names all inputs; inputs remain current unless superseded
    a = _obj(
        "a",
        EvidenceRole.machine_derived,
        "Standup Tuesday",
        deriv=Derivation(activity="extraction", unknown=True),
    )
    b = _obj(
        "b",
        EvidenceRole.machine_derived,
        "Standup moved to Friday",
        deriv=Derivation(activity="extraction", unknown=True),
        at=T1,
    )
    s = _obj(
        "sum",
        EvidenceRole.machine_derived,
        "Standup is Friday (was Tuesday)",
        deriv=Derivation(
            activity="consolidation", used=[a.revision_id, b.revision_id], agent="model-x", at=T2
        ),
        at=T2,
    )
    sup_a = LifecycleEvent(
        event_id="ev-sup-a",
        kind=LifecycleKind.supersede,
        target=a.revision_id,
        actor="model-x",
        effective_at=T1,
        replacement=b.revision_id,
    )
    fx["03_consolidation"] = {
        "exchange": _ex([a, b, s], [sup_a]).model_dump(mode="json"),
        "expect": {
            "statuses": {s.revision_id: "accepted"},
            "current_texts": [b.text, s.text],
            "validator_errors": 0,
        },
    }

    # 4. policy mapping: mapped principal accepted; unmapped principal on required policy is staged
    ok = _obj(
        "p1",
        EvidenceRole.human_assertion,
        "Team roster",
        policy=Policy(rules=[PolicyRule(principals=["alice@source"], actions=["read"])]),
    )
    bad = _obj(
        "p2",
        EvidenceRole.human_assertion,
        "Salary band",
        policy=Policy(rules=[PolicyRule(principals=["hr@source"], actions=["read"])]),
    )
    unsup = _obj(
        "p3",
        EvidenceRole.human_assertion,
        "Board minutes",
        policy=Policy(
            rules=[PolicyRule(principals=["alice@source"], actions=["read", "watermark"])]
        ),
    )
    fx["04_policy_mapping"] = {
        "exchange": _ex([ok, bad, unsup]).model_dump(mode="json"),
        "expect": {
            "statuses": {
                ok.revision_id: "accepted",
                bad.revision_id: "unresolved",
                unsup.revision_id: "unresolved",
            },
            "current_texts": ["Team roster"],
            "retry": True,
            "validator_errors": 0,
        },
    }

    # 5. partial export: receiver already holds x; exchange omits it; x must survive
    x = _obj("x", EvidenceRole.human_assertion, "Keep me")
    y = _obj("y", EvidenceRole.human_assertion, "New arrival", at=T1)
    fx["05_partial_export"] = {
        "exchange": _ex([y], complete=False).model_dump(mode="json"),
        "expect": {
            "pre": _ex([x]).model_dump(mode="json"),
            "statuses": {y.revision_id: "accepted"},
            "current_texts": ["Keep me", "New arrival"],
            "validator_errors": 0,
        },
    }

    # 6. conflicting revisions: same revision id, different content, and two supersessions of one target
    c1 = _obj("c", EvidenceRole.human_assertion, "Version A")
    c1_other = _obj("c", EvidenceRole.human_assertion, "Version B")  # same revision id!
    r1 = _obj(
        "c",
        EvidenceRole.human_assertion,
        "Replacement 1",
        rev="rev-c-r1",
        pred=c1.revision_id,
        at=T1,
    )
    r2 = _obj(
        "c",
        EvidenceRole.human_assertion,
        "Replacement 2",
        rev="rev-c-r2",
        pred=c1.revision_id,
        at=T1,
    )
    e1 = LifecycleEvent(
        event_id="ev-c-1",
        kind=LifecycleKind.supersede,
        target=c1.revision_id,
        actor="alice",
        effective_at=T1,
        replacement=r1.revision_id,
    )
    e2 = LifecycleEvent(
        event_id="ev-c-2",
        kind=LifecycleKind.supersede,
        target=c1.revision_id,
        actor="bob",
        effective_at=T1,
        replacement=r2.revision_id,
    )
    fx["06_conflicting_revisions"] = {
        "exchange": _ex([c1, c1_other, r1, r2], [e1, e2]).model_dump(mode="json"),
        "expect": {
            "statuses": {r1.revision_id: "accepted", r2.revision_id: "accepted"},
            "conflicts": True,
            "validator_errors": 2,
        },
    }

    # 7. required extension: receiver does not support it -> whole exchange rejected
    z = _obj(
        "z",
        EvidenceRole.human_assertion,
        "Needs graph ext",
        extensions={"acme.graph": {"edges": 3}},
    )
    fx["07_required_extension"] = {
        "exchange": _ex([z], required_extensions=["acme.graph"]).model_dump(mode="json"),
        "expect": {"statuses": {z.revision_id: "rejected"}, "current_texts": []},
    }

    # 8. expiry: an object with expires_at in the past is not current after import
    fresh = _obj("f", EvidenceRole.human_assertion, "Still valid")
    stale = _obj("s", EvidenceRole.human_assertion, "Expired promo code", expires_at=T1)
    fx["08_expiry"] = {
        "exchange": _ex([fresh, stale]).model_dump(mode="json"),
        "expect": {
            "statuses": {fresh.revision_id: "accepted", stale.revision_id: "accepted"},
            "current_texts": ["Still valid"],
        },
    }

    # 9. deletion + tombstone + resurrection attempt: an old archive re-sends a tombstoned revision
    d = _obj("d", EvidenceRole.transcript, "user: my SSN is 123")
    derived = _obj(
        "dd",
        EvidenceRole.machine_derived,
        "Alice's SSN is 123",
        deriv=Derivation(activity="extraction", used=[d.revision_id], agent="model-x", at=T1),
        at=T1,
    )
    tomb = LifecycleEvent(
        event_id="ev-tomb",
        kind=LifecycleKind.tombstone,
        target=d.revision_id,
        actor="alice",
        effective_at=T2,
        reason="user erasure",
        coverage=["derivations", "indexes"],
    )
    inv = LifecycleEvent(
        event_id="ev-inv",
        kind=LifecycleKind.invalidate,
        target=derived.revision_id,
        actor="alice",
        effective_at=T2,
        reason="evidence deleted",
    )
    keep = _obj("k", EvidenceRole.human_assertion, "Unrelated fact")
    fx["09_deletion_tombstone_resurrection"] = {
        "exchange": _ex([d, derived, keep], complete=False).model_dump(
            mode="json"
        ),  # the OLD archive
        "expect": {
            "pre": _ex([], [tomb, inv]).model_dump(mode="json"),
            "statuses": {d.revision_id: "rejected", keep.revision_id: "accepted"},
            "current_texts": ["Unrelated fact"],
        },
    }

    # 10. credentials are outside memory exchange
    secret = _obj(
        "sec", EvidenceRole.human_assertion, "my token is sk-abcdefghijklmnopqrstuvwxyz123456"
    )
    fx["10_credentials_rejected"] = {
        "exchange": _ex([secret]).model_dump(mode="json"),
        "expect": {
            "statuses": {secret.revision_id: "rejected"},
            "current_texts": [],
            "validator_errors": 1,
        },
    }

    # 11. re-derive mode: new identities linked to actual inputs
    src = _obj("src", EvidenceRole.source_artifact, "The runbook says deploy blue-green.")
    fx["11_rederive_mode"] = {
        "exchange": _ex([src]).model_dump(mode="json"),
        "expect": {
            "mode": "re_derive",
            "statuses": {src.revision_id: "transformed"},
            "current_texts": [src.text],
        },
    }
    return fx


def write(directory: Path = FIXTURES_DIR) -> list[Path]:
    directory.mkdir(parents=True, exist_ok=True)
    out = []
    for name, data in build().items():
        p = directory / f"{name}.json"
        p.write_text(json.dumps(data, indent=2), encoding="utf-8")
        out.append(p)
    return out


if __name__ == "__main__":
    for p in write():
        print(p.name)
