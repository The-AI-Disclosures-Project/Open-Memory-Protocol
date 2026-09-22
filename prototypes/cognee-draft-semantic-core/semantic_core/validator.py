"""Validate an exchange against the six-part contract, and run the §6 fixtures.

Findings are (level, part, message). `error` means the draft says MUST; `warn` is SHOULD.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from semantic_core.schema import (
    EvidenceRole,
    Exchange,
    LifecycleKind,
    ReceiptStatus,
)
from semantic_core.store import _CREDENTIAL_RE, SemanticStore

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


@dataclass
class Finding:
    level: Literal["error", "warn"]
    part: str
    message: str

    def __str__(self) -> str:
        return f"[{self.level}] §{self.part}: {self.message}"


def validate_exchange(ex: Exchange) -> list[Finding]:
    f: list[Finding] = []
    m = ex.manifest
    # 3.6 manifest
    if not m.format_version:
        f.append(Finding("error", "3.6", "manifest.format_version missing"))
    if not m.source_system:
        f.append(Finding("error", "3.6", "manifest.source_system missing"))
    if not m.complete_snapshot:
        f.append(Finding("warn", "3.6", "partial export: absence must not be read as deletion"))
    revs = {o.revision_id for o in ex.objects}
    seen_ref_rev: dict[str, str] = {}
    for o in ex.objects:
        tag = f"{o.ref}@{o.revision_id[:8]}"
        # 3.1
        if not o.ref.authority or not o.ref.local_id:
            f.append(Finding("error", "3.1", f"{tag}: identity must be origin-qualified"))
        if o.revision_id in seen_ref_rev and seen_ref_rev[o.revision_id] != o.digest:
            f.append(
                Finding(
                    "error", "3.1", f"{tag}: same revision id with different content (conflict)"
                )
            )
        seen_ref_rev[o.revision_id] = o.digest
        if o.predecessor and o.predecessor not in revs:
            f.append(
                Finding("warn", "3.1", f"{tag}: predecessor {o.predecessor[:8]} not in exchange")
            )
        # 3.2
        if o.text is None and o.media is None and not o.extensions:
            f.append(Finding("error", "3.2", f"{tag}: no text, media or extension payload"))
        if o.media and not o.media.digest:
            f.append(Finding("error", "3.2", f"{tag}: media without integrity digest"))
        # 3.3
        if not o.scope.origin_system:
            f.append(Finding("error", "3.3", f"{tag}: scope.origin_system missing"))
        if o.text and _CREDENTIAL_RE.search(o.text):
            f.append(Finding("error", "3.3", f"{tag}: credential material inside memory content"))
        for r in o.policy.rules:
            if not r.principals or not r.actions:
                f.append(Finding("error", "3.3", f"{tag}: policy rule without principals/actions"))
        # 3.4
        if o.role == EvidenceRole.machine_derived:
            if o.derivation is None:
                f.append(
                    Finding(
                        "error",
                        "3.4",
                        f"{tag}: machine_derived without derivation (say unknown explicitly)",
                    )
                )
            elif not o.derivation.unknown and not o.derivation.used and not o.derivation.spans:
                f.append(Finding("warn", "3.4", f"{tag}: derivation names no inputs"))
            elif o.derivation.used and any(u not in revs for u in o.derivation.used):
                f.append(
                    Finding(
                        "warn",
                        "3.4",
                        f"{tag}: derivation input not in exchange (evidence unavailable must be declared)",
                    )
                )
        # 3.5
        if o.applies_from and o.applies_until and o.applies_until < o.applies_from:
            f.append(Finding("error", "3.5", f"{tag}: applies_until before applies_from"))
    # events
    by_target: dict[str, list] = {}
    for e in ex.events:
        by_target.setdefault((e.kind, e.target), []).append(e)
        if e.kind == LifecycleKind.supersede and not e.replacement:
            f.append(
                Finding("error", "3.5", f"event {e.event_id[:8]}: supersede without replacement")
            )
        if e.kind == LifecycleKind.supersede and e.replacement and e.replacement not in revs:
            f.append(
                Finding(
                    "warn",
                    "3.5",
                    f"event {e.event_id[:8]}: replacement {e.replacement[:8]} not in exchange",
                )
            )
        if not e.actor:
            f.append(Finding("error", "3.5", f"event {e.event_id[:8]}: no authorized actor"))
        if e.kind == LifecycleKind.delete and not e.coverage:
            f.append(Finding("warn", "3.5", f"event {e.event_id[:8]}: delete declares no coverage"))
    for (kind, target), evs in by_target.items():
        if kind == LifecycleKind.supersede and len({e.replacement for e in evs}) > 1:
            f.append(
                Finding(
                    "error",
                    "3.5",
                    f"conflicting supersessions of {target[:8]} (must surface as conflict)",
                )
            )
    return f


# ---------------------------------------------------------------- fixtures


@dataclass
class FixtureResult:
    name: str
    passed: bool
    detail: str


def load_fixture(path: Path) -> tuple[Exchange, dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return Exchange.model_validate(data["exchange"]), data["expect"]


def run_fixture(path: Path, store_factory=None) -> FixtureResult:
    """Each fixture imports into a fresh receiver and checks the receipt/statuses it expects."""
    ex, expect = load_fixture(path)
    store = (
        store_factory
        or (
            lambda: SemanticStore(
                "receiver", supported_extensions={"cogx"}, principal_map={"alice@source": "alice"}
            )
        )
    )()
    if "pre" in expect:  # objects/events already in the receiver before import (e.g. a tombstone)
        pre = Exchange.model_validate(expect["pre"])
        store.import_exchange(pre)
        for ev in pre.events:
            store.apply_event(ev)
    rcpt = store.import_exchange(ex, mode=expect.get("mode", "preserve"))
    got = {e.target: e.status.value for e in rcpt.entries if e.kind == "object"}
    problems = []
    for target, status in expect.get("statuses", {}).items():
        if got.get(target) != status:
            problems.append(f"{target[:8]}: expected {status}, got {got.get(target)}")
    if expect.get("conflicts") is not None and bool(rcpt.conflicts) != expect["conflicts"]:
        problems.append(f"conflicts expected={expect['conflicts']} got={rcpt.conflicts}")
    if "current_texts" in expect:
        texts = sorted(o.text for o in store.current() if o.text)
        if texts != sorted(expect["current_texts"]):
            problems.append(f"current={texts} expected={expect['current_texts']}")
    if "validator_errors" in expect:
        n = sum(1 for x in validate_exchange(ex) if x.level == "error")
        if n != expect["validator_errors"]:
            problems.append(f"validator errors={n} expected={expect['validator_errors']}")
    if "retry" in expect and (len(rcpt.retry) > 0) != expect["retry"]:
        problems.append(f"retry boundary expected={expect['retry']} got={rcpt.retry}")
    # idempotency: importing again must not duplicate
    n_before = len(store.objects)
    store.import_exchange(ex, mode=expect.get("mode", "preserve"))
    if len(store.objects) != n_before:
        problems.append("re-import duplicated objects")
    return FixtureResult(path.stem, not problems, "; ".join(problems) or f"receipt {rcpt.counts}")


def run_all_fixtures(directory: Path = FIXTURES_DIR) -> list[FixtureResult]:
    return [run_fixture(p) for p in sorted(directory.glob("*.json"))]


_ = ReceiptStatus  # re-exported for callers
