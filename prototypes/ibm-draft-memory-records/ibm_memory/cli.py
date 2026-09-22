"""`ibm-memory`: inspect, export/import, bridge to Packer directories, and run an agent."""

from __future__ import annotations

import argparse
import os
import sys


from ibm_memory.models import load_env
from ibm_memory.packer_bridge import memory_dir_from_records, records_from_memory_dir
from ibm_memory.store import MemoryStore, ScopePolicy, dump_bundle, load_bundle


def _store(args) -> MemoryStore:
    return MemoryStore(args.system, path=args.store)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="ibm-memory")
    p.add_argument("--store", default="./memory.ibm.json", help="store file (JSON export bundle)")
    p.add_argument("--system", default="local", help="this memory system's id")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("show", help="list records valid now (or --as-of)")
    s.add_argument("--as-of", default=None)
    s.add_argument("--all", action="store_true", help="include invalidated")

    s = sub.add_parser("write", help="write a human-authored record")
    s.add_argument("body")
    s.add_argument("--author", default=os.environ.get("USER", "user"))
    s.add_argument("--scope", action="append", default=[])
    s.add_argument("--tag", action="append", default=[])

    s = sub.add_parser("override", help="supersede a record with a new body")
    s.add_argument("id")
    s.add_argument("body")
    s.add_argument("--author", default=os.environ.get("USER", "user"))

    s = sub.add_parser("invalidate")
    s.add_argument("id")
    s = sub.add_parser("delete")
    s.add_argument("id")
    s = sub.add_parser("history")
    s.add_argument("id")

    s = sub.add_parser("export")
    s.add_argument("out")
    s.add_argument("--valid-only", action="store_true")
    s = sub.add_parser("import", help="import another system's bundle as new records")
    s.add_argument("bundle")
    s.add_argument("--map-scope", action="append", default=[], metavar="OLD=NEW")
    s.add_argument("--map-tag", action="append", default=[], metavar="OLD=NEW")
    s.add_argument("--drop-unmapped-scopes", action="store_true")

    s = sub.add_parser("from-packer", help="ingest a Packer-draft memory directory")
    s.add_argument("memory_dir")
    s.add_argument("--scope", action="append", default=[])
    s = sub.add_parser(
        "to-packer", help="write valid records with path: scopes as a Packer directory"
    )
    s.add_argument("out_dir")

    s = sub.add_parser("agent", help="run a LangChain agent with Remember/Recall/Observe/Decorate")
    s.add_argument("--model", default="openrouter:nvidia/nemotron-3-nano-30b-a3b")
    s.add_argument("--principal", default=os.environ.get("USER", "user"))
    s.add_argument("--write-scope", action="append", default=None)
    s.add_argument(
        "--read-scope",
        action="append",
        default=None,
        help="scopes the principal may read (default: same as write scopes)",
    )
    s.add_argument("--no-observe", action="store_true")
    s.add_argument("--no-decorate", action="store_true")
    s.add_argument("-q", "--quiet", action="store_true")
    s.add_argument("prompt", nargs="*")

    args = p.parse_args(argv)
    load_env()
    store = _store(args)

    if args.cmd == "show":
        recs = store.all() if args.all else store.as_of(args.as_of)
        for r in recs:
            lc = r.lifecycle
            flag = "" if r.is_valid else f"  [invalidated {lc.invalidated_at}]"
            print(
                f"{r.id[:8]} v{lc.version} {lc.created_at} {lc.author}"
                f"{' AI' if lc.provenance.ai_used else ''} scope={','.join(r.scope_tags)} "
                f"tags={','.join(r.semantic_tags)}{flag}\n    {r.body.strip()[:200]}"
            )
        return 0
    if args.cmd == "write":
        r = store.write(
            args.body, author=args.author, semantic_tags=args.tag, scope_tags=args.scope
        )
        print(r.id)
        return 0
    if args.cmd == "override":
        print(store.override(args.id, args.body, author=args.author).id)
        return 0
    if args.cmd == "invalidate":
        store.invalidate(args.id)
        return 0
    if args.cmd == "delete":
        store.delete(args.id)
        return 0
    if args.cmd == "history":
        for r in store.history(args.id):
            print(
                f"v{r.lifecycle.version} {r.id[:8]} {r.lifecycle.created_at} "
                f"{'valid' if r.is_valid else 'invalidated ' + str(r.lifecycle.invalidated_at)}: {r.body.strip()[:120]}"
            )
        return 0
    if args.cmd == "export":
        dump_bundle(store.export(include_invalid=not args.valid_only), args.out)
        print(f"exported {len(store.all())} records to {args.out}")
        return 0
    if args.cmd == "import":
        kv = lambda items: dict(i.split("=", 1) for i in items)
        recs = store.import_bundle(
            load_bundle(args.bundle),
            scope_map=kv(args.map_scope),
            semantic_map=kv(args.map_tag),
            drop_unmapped_scopes=args.drop_unmapped_scopes,
        )
        print(f"imported {len(recs)} records as new memories in {store.system_id}")
        return 0
    if args.cmd == "from-packer":
        recs = records_from_memory_dir(args.memory_dir, store, extra_scopes=args.scope)
        print(f"ingested {len(recs)} files from {args.memory_dir}")
        return 0
    if args.cmd == "to-packer":
        paths = memory_dir_from_records(store.as_of(), args.out_dir)
        print(f"wrote {len(paths)} files to {args.out_dir}")
        return 0
    if args.cmd == "agent":
        return _agent(args, store)
    return 1


def _agent(args, store: MemoryStore) -> int:
    from langchain.agents import create_agent
    from langchain.messages import HumanMessage

    from ibm_memory.middleware import IBMMemoryMiddleware
    from ibm_memory.models import resolve_model

    write_scopes = args.write_scope or [f"user:{args.principal}"]
    read_scopes = set(args.read_scope or write_scopes)
    store.policy = ScopePolicy(
        read={args.principal: read_scopes}, write={args.principal: set(write_scopes)}
    )
    mw = IBMMemoryMiddleware(
        store,
        principal=args.principal,
        write_scopes=write_scopes,
        agent_name="ibm-memory-agent",
        model_name=args.model,
        observe=not args.no_observe,
        decorate=not args.no_decorate,
    )
    stack: list = [mw]
    if not args.quiet:
        try:
            from omp_langchain import ActivitySink, TraceMiddleware

            stack.append(TraceMiddleware(ActivitySink()))
        except ImportError:
            pass
    agent = create_agent(
        resolve_model(args.model),
        tools=[],
        middleware=stack,
        system_prompt="You are a helpful assistant with persistent memory.",
    )
    if not args.quiet:
        print(
            f"ibm-memory agent · {args.model} · principal {args.principal} · "
            f"write {write_scopes} · read {sorted(read_scopes)} · {len(store.as_of())} valid records",
            file=sys.stderr,
        )
    messages: list = []

    def turn(text: str) -> None:
        messages.append(HumanMessage(content=text))
        result = agent.invoke({"messages": messages})
        messages[:] = result["messages"]
        final = result["messages"][-1]
        if not args.quiet:
            if mw.last_decorated:
                print(
                    f"● decorated prompt with {len(mw.last_decorated)} recalled memories",
                    file=sys.stderr,
                )
            print(file=sys.stderr, flush=True)
        print((final.text if hasattr(final, "text") else str(final.content)).strip(), flush=True)
        if not args.quiet and mw.last_observed:
            print(
                f"\n--- observe: stored {len(mw.last_observed)} user turn(s) as ground truth",
                file=sys.stderr,
            )

    if args.prompt:
        turn(" ".join(args.prompt))
        return 0
    print("ibm-memory agent interactive mode. Ctrl-D to exit.", file=sys.stderr)
    try:
        while True:
            text = input("> ").strip()
            if text:
                turn(text)
    except (EOFError, KeyboardInterrupt):
        print(file=sys.stderr)
    return 0
