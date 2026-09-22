"""`semantic-core`: validate, import/export, COGX conversion, fixtures."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from semantic_core.cogx import read_cogx, write_cogx
from semantic_core.schema import Exchange
from semantic_core.store import SemanticStore
from semantic_core.validator import FIXTURES_DIR, run_all_fixtures, validate_exchange


def _load(path: str) -> Exchange:
    p = Path(path)
    if p.is_dir() or p.name.endswith((".tar.gz", ".cogx")):
        return read_cogx(p)
    data = json.loads(p.read_text(encoding="utf-8"))
    if "exchange" in data and "manifest" not in data:  # a fixture file
        data = data["exchange"]
    return Exchange.model_validate(data)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="semantic-core")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser(
        "validate", help="validate an exchange (.json) or COGX archive (dir / .cogx.tar.gz)"
    )
    s.add_argument("path")
    s = sub.add_parser("import", help="import into a receiver and print the receipt")
    s.add_argument("path")
    s.add_argument("--receiver", default="receiver")
    s.add_argument("--mode", choices=["preserve", "re_derive", "hybrid"], default="preserve")
    s.add_argument(
        "--map", action="append", default=[], metavar="SRC=DST", help="principal mapping"
    )
    s.add_argument("--ext", action="append", default=[], help="supported extension/profile names")
    s.add_argument(
        "--state",
        default=None,
        help="JSON file to persist the receiver's exchange to (export after import)",
    )
    s = sub.add_parser("to-cogx", help="write an exchange as a COGX archive")
    s.add_argument("path")
    s.add_argument("out")
    s.add_argument("--pack", action="store_true")
    s = sub.add_parser("from-cogx", help="read a COGX archive and print the exchange JSON")
    s.add_argument("path")
    s = sub.add_parser("fixtures", help="run the §6 fixtures")
    s.add_argument("--dir", default=str(FIXTURES_DIR))
    s = sub.add_parser("from-ibm", help="export an IBM-draft store file as an exchange")
    s.add_argument("store")
    s.add_argument("--system", default="local")
    s = sub.add_parser("from-packer", help="export a Packer-draft memory directory as an exchange")
    s.add_argument("memory_dir")
    args = p.parse_args(argv)

    if args.cmd == "validate":
        ex = _load(args.path)
        findings = validate_exchange(ex)
        for f in findings:
            print(f)
        errs = sum(1 for f in findings if f.level == "error")
        print(
            f"{len(ex.objects)} objects, {len(ex.events)} events, {errs} error(s), {len(findings) - errs} warning(s)"
        )
        for n in ex.manifest.notes:
            print(f"  note: {n}")
        return 1 if errs else 0
    if args.cmd == "import":
        ex = _load(args.path)
        store = SemanticStore(
            args.receiver,
            supported_extensions=set(args.ext),
            principal_map=dict(m.split("=", 1) for m in args.map),
        )
        rcpt = store.import_exchange(ex, mode=args.mode)
        for e in rcpt.entries:
            extra = f" -> {e.local_id[:8]}" if e.local_id else ""
            why = f"  ({e.reason})" if e.reason else ""
            tr = f"  [{'; '.join(e.transformations)}]" if e.transformations else ""
            print(f"{e.kind:6} {e.target[:8]} {e.status.value:11}{extra}{why}{tr}")
        print(
            f"receipt: {rcpt.counts}  conflicts={rcpt.conflicts or 'none'}  retry={len(rcpt.retry)}  move_complete={rcpt.move_complete}"
        )
        print(f"current: {len(store.current())} object(s)")
        if args.state:
            Path(args.state).write_text(store.export().model_dump_json(indent=2), encoding="utf-8")
        return 0
    if args.cmd == "to-cogx":
        losses = write_cogx(_load(args.path), args.out, pack=args.pack)
        print(f"wrote {args.out}" + (f"; {len(losses)} loss(es):" if losses else ""))
        for l in losses:
            print("  -", l)
        return 0
    if args.cmd == "from-cogx":
        print(read_cogx(args.path).model_dump_json(indent=2))
        return 0
    if args.cmd == "fixtures":
        results = run_all_fixtures(Path(args.dir))
        for r in results:
            print(f"{'PASS' if r.passed else 'FAIL'}  {r.name}: {r.detail}")
        return 0 if all(r.passed for r in results) else 1
    if args.cmd == "from-ibm":
        from ibm_memory import MemoryStore

        from semantic_core.adapters import from_ibm_store

        print(from_ibm_store(MemoryStore(args.system, path=args.store)).model_dump_json(indent=2))
        return 0
    if args.cmd == "from-packer":
        from semantic_core.adapters import from_packer_dir

        print(from_packer_dir(args.memory_dir).model_dump_json(indent=2))
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
