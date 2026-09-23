"""`omp-agent`: run a LangChain agent over an OMP memory directory from the terminal."""

from __future__ import annotations

import argparse
import sys

from langchain.messages import HumanMessage

from omp_langchain.middleware import OpenMemoryMiddleware, create_omp_agent
from omp_langchain.models import DEFAULT_MODEL, load_env
from omp_langchain.trace import ActivitySink, ConsoleSink, JsonlSink


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="omp-agent", description=__doc__)
    p.add_argument("--memory", default="./memory", help="OMP memory root (default ./memory)")
    p.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=(
            f"model string (default {DEFAULT_MODEL}); openrouter:<model> uses "
            "OPENROUTER_API_KEY, otherwise any init_chat_model string like "
            "anthropic:claude-sonnet-4-6"
        ),
    )
    p.add_argument("--writable", action="store_true", help="expose the write_memory tool")
    p.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="detailed trace on stderr: -v = per-call stats and token usage, -vv = full payloads",
    )
    p.add_argument(
        "-q", "--quiet", action="store_true", help="print only the answer (no activity lines)"
    )
    p.add_argument("--trace", metavar="FILE.jsonl", help="append a machine-readable trace here")
    p.add_argument(
        "--show-context",
        action="store_true",
        help="print the memory block the harness injects, then exit (no model call)",
    )
    p.add_argument("prompt", nargs="*", help="one-shot prompt; omit for an interactive loop")
    args = p.parse_args(argv)
    load_env()

    if args.show_context:
        print(OpenMemoryMiddleware(args.memory, writable=args.writable).render_memory_block())
        return 0

    sinks: list = []
    if args.verbose:
        sinks.append(ConsoleSink(level=args.verbose))
    elif not args.quiet:
        sinks.append(ActivitySink())
    if args.trace:
        sinks.append(JsonlSink(args.trace))

    agent = create_omp_agent(args.memory, args.model, writable=args.writable, trace=sinks or None)
    if not args.quiet:
        mem = agent.omp_memory
        mem.render_memory_block()
        st = mem.last_stats
        print(
            f"omp-agent · model {args.model} · memory {mem.memory_root}\n"
            f"           {len(st['core_files'])} core file(s) always in context, "
            f"{st['external_files_total']} deferred file(s) readable via read_memory"
            + (" · writes enabled" if args.writable else "")
            + "\n",
            file=sys.stderr,
        )
    messages: list = []

    def turn(text: str) -> None:
        messages.append(HumanMessage(content=text))
        result = agent.invoke({"messages": messages})
        messages[:] = result["messages"]
        final = result["messages"][-1]
        answer = (final.text if hasattr(final, "text") else str(final.content)).strip()
        if not args.quiet:
            print(file=sys.stderr, flush=True)
        print(answer, flush=True)
        if not args.quiet and agent.omp_trace is not None:
            print(f"\n--- {agent.omp_trace.format_summary()}", file=sys.stderr, flush=True)

    if args.prompt:
        turn(" ".join(args.prompt))
        return 0

    print("omp-agent interactive mode. Ctrl-D to exit.", file=sys.stderr)
    try:
        while True:
            text = input("> ").strip()
            if text:
                turn(text)
    except (EOFError, KeyboardInterrupt):
        print(file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
