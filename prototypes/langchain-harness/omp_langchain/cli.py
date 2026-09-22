"""`omp-agent`: run a LangChain agent over an OMP memory directory from the terminal."""

from __future__ import annotations

import argparse
import sys

from langchain.messages import HumanMessage

from omp_langchain.middleware import OpenMemoryMiddleware, create_omp_agent


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="omp-agent", description=__doc__)
    p.add_argument("--memory", default="./memory", help="OMP memory root (default ./memory)")
    p.add_argument(
        "--model",
        default="anthropic:claude-sonnet-4-6",
        help="LangChain model string, e.g. anthropic:claude-sonnet-4-6 or openai:gpt-5",
    )
    p.add_argument("--writable", action="store_true", help="expose the write_memory tool")
    p.add_argument(
        "--show-context",
        action="store_true",
        help="print the memory block the harness injects, then exit (no model call)",
    )
    p.add_argument("prompt", nargs="*", help="one-shot prompt; omit for an interactive loop")
    args = p.parse_args(argv)

    if args.show_context:
        print(OpenMemoryMiddleware(args.memory, writable=args.writable).render_memory_block())
        return 0

    agent = create_omp_agent(args.memory, args.model, writable=args.writable)
    messages: list = []

    def turn(text: str) -> None:
        messages.append(HumanMessage(content=text))
        result = agent.invoke({"messages": messages})
        messages[:] = result["messages"]
        final = result["messages"][-1]
        print(final.text if hasattr(final, "text") else final.content)

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
