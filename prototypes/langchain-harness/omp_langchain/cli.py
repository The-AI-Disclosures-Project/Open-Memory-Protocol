"""`omp-agent`: run a LangChain agent over an OMP memory directory from the terminal."""

from __future__ import annotations

import argparse
import sys

from dotenv import load_dotenv
from langchain.messages import HumanMessage

from omp_langchain.middleware import OpenMemoryMiddleware, create_omp_agent
from omp_langchain.models import DEFAULT_MODEL


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
        "--show-context",
        action="store_true",
        help="print the memory block the harness injects, then exit (no model call)",
    )
    p.add_argument("prompt", nargs="*", help="one-shot prompt; omit for an interactive loop")
    args = p.parse_args(argv)
    load_dotenv()  # picks up OPENROUTER_API_KEY etc. from ./.env if present

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
