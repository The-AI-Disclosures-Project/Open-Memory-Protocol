"""`nest-agent`: plug a LangChain agent into a Context Nest (local directory or hosted alias)."""

from __future__ import annotations

import argparse
import json
import sys

from langchain.agents import create_agent
from langchain.messages import HumanMessage

from contextnest_adapter.ctx import CtxClient
from contextnest_adapter.middleware import ContextNestMiddleware
from contextnest_adapter.models import DEFAULT_MODEL, load_env, resolve_model


def _client(args) -> CtxClient:
    return CtxClient(args.nest)


def cmd_context(args) -> int:
    mw = ContextNestMiddleware(_client(args), load=args.load, hops=args.hops)
    print(mw.render_context_block())
    return 0


def cmd_resolve(args) -> int:
    """Resolve one selector N times against one or more nests and compare the sets."""
    rows = []
    for nest in args.nests or [args.nest]:
        c = CtxClient(nest)
        sets = [tuple(c.query(args.selector, hops=args.hops).ids) for _ in range(args.runs)]
        rows.append({"nest": c.location, "stable": len(set(sets)) == 1, "ids": list(sets[0])})
    print(json.dumps(rows, indent=2))
    return 0 if all(r["stable"] for r in rows) else 1


def cmd_ask(args) -> int:
    load_env()
    mw = ContextNestMiddleware(
        _client(args), load=args.load, hops=args.hops, writable=args.writable
    )
    agent = create_agent(model=resolve_model(args.model), tools=[], middleware=[mw])
    messages: list = []

    def turn(text: str) -> None:
        messages.append(HumanMessage(content=text))
        result = agent.invoke({"messages": messages})
        messages[:] = result["messages"]
        final = result["messages"][-1]
        print((final.text if hasattr(final, "text") else str(final.content)).strip(), flush=True)

    print(f"nest-agent · model {args.model} · nest {mw.client.location}", file=sys.stderr)
    if args.prompt:
        turn(" ".join(args.prompt))
    else:
        try:
            while True:
                text = input("> ").strip()
                if text:
                    turn(text)
        except (EOFError, KeyboardInterrupt):
            print(file=sys.stderr)
    print("\n--- reads\n" + json.dumps(mw.reads, indent=2), file=sys.stderr)
    if mw.proposed:
        print("--- proposed (pending_review)\n" + "\n".join(mw.proposed), file=sys.stderr)
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="nest-agent", description=__doc__)
    p.add_argument(
        "--nest",
        default=".",
        help="nest directory, or a ctx vault alias for a hosted nest (default: .)",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("context", help="print the block the harness injects, no model call")
    s.add_argument("--load", help='selector or pack loaded into context, e.g. "pack:core"')
    s.add_argument("--hops", type=int, default=0)
    s.set_defaults(fn=cmd_context)

    s = sub.add_parser("resolve", help="resolve a selector repeatedly and check the set is stable")
    s.add_argument("selector")
    s.add_argument("--runs", type=int, default=5)
    s.add_argument("--hops", type=int, default=0)
    s.add_argument("--nests", nargs="+", help="compare several nests (paths or aliases)")
    s.set_defaults(fn=cmd_resolve)

    s = sub.add_parser("ask", help="run the agent (needs OPENROUTER_API_KEY or another model)")
    s.add_argument("--load", help="selector or pack loaded into context every turn")
    s.add_argument("--hops", type=int, default=0)
    s.add_argument("--writable", action="store_true", help="expose nest_propose")
    s.add_argument("--model", default=DEFAULT_MODEL)
    s.add_argument("prompt", nargs="*")
    s.set_defaults(fn=cmd_ask)

    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
