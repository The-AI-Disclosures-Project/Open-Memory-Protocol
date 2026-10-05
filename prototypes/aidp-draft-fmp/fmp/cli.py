"""CLI entry points: `fmp-server` (run a memory server) and `fmp-agent` (federated agent)."""

from __future__ import annotations

import argparse
import sys
import tomllib
from pathlib import Path

from fmp.models import load_env


def server_main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="fmp-server", description="Run an FMP memory server.")
    p.add_argument("--name", required=True, help='server name, e.g. "personal" or "work"')
    p.add_argument("--description", default="")
    p.add_argument(
        "--db", default=None, help="SQLite file for the read/write backend (default: ./<name>.db)"
    )
    p.add_argument(
        "--acp-index",
        default=None,
        help="serve the acp_memory_server SQLite index read-only instead of --db "
        "(e.g. ~/.local/share/acp-memory/db.sqlite)",
    )
    p.add_argument(
        "--disable",
        default="",
        help="comma-separated endpoints to disable, e.g. upload_transcript,delete",
    )
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8801)
    args = p.parse_args(argv)

    import uvicorn

    from fmp.server import create_app
    from fmp.store import ACPIndexStore, SQLiteStore

    store = (
        ACPIndexStore(args.acp_index)
        if args.acp_index
        else SQLiteStore(args.db or f"./{args.name}.db")
    )
    disabled = {d.strip() for d in args.disable.split(",") if d.strip()}
    app = create_app(store, name=args.name, description=args.description, disabled=disabled)
    caps = ", ".join(k for k, v in app.state.info.capabilities.items() if v)
    print(
        f"fmp-server '{args.name}' on http://{args.host}:{args.port}/fmp  ·  endpoints: {caps}",
        file=sys.stderr,
    )
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")
    return 0


def _load_servers(path: Path):
    from fmp.client import ServerConfig

    data = tomllib.loads(path.read_text())
    return [
        ServerConfig(
            name=s["name"],
            url=s["url"],
            send_transcripts=s.get("send_transcripts", True),
            accept_inferences=s.get("accept_inferences", True),
            headers=s.get("headers", {}),
        )
        for s in data.get("servers", [])
    ]


def agent_main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="fmp-agent", description="LangChain agent over federated FMP memory."
    )
    p.add_argument(
        "--config", default="fmp.toml", help="TOML with [[servers]] entries (default ./fmp.toml)"
    )
    p.add_argument("--model", default="openrouter:nvidia/nemotron-3-nano-30b-a3b")
    p.add_argument(
        "--packer-memory",
        default=None,
        help="also mount a Packer-draft memory directory (needs the packer extra)",
    )
    p.add_argument("--no-upload", action="store_true", help="do not send transcripts to servers")
    p.add_argument("-q", "--quiet", action="store_true")
    p.add_argument("prompt", nargs="*")
    args = p.parse_args(argv)
    load_env()

    from langchain.agents import create_agent
    from langchain.messages import HumanMessage

    from fmp.client import FederatedMemory
    from fmp.middleware import FMPMiddleware

    servers = _load_servers(Path(args.config))
    if not servers:
        print(f"no [[servers]] in {args.config}", file=sys.stderr)
        return 2
    fm = FederatedMemory(servers)
    fmp_mw = FMPMiddleware(
        fm, agent_name="fmp-agent", model_name=args.model, upload_transcripts=not args.no_upload
    )
    stack: list = []
    trace = None
    system_prompt = "You are a helpful assistant with access to the user's federated memory."
    if args.packer_memory:
        from omp_langchain import ActivitySink, OpenMemoryMiddleware, TraceMiddleware
        from omp_langchain.middleware import DEFAULT_SYSTEM_PROMPT

        omp = OpenMemoryMiddleware(args.packer_memory)
        stack.append(omp)
        system_prompt = DEFAULT_SYSTEM_PROMPT
        if not args.quiet:
            trace = TraceMiddleware(ActivitySink(), memory=omp)
    else:
        try:
            from omp_langchain import ActivitySink, TraceMiddleware

            if not args.quiet:
                trace = TraceMiddleware(ActivitySink())
        except ImportError:
            pass
    stack.append(fmp_mw)
    if trace is not None:
        stack.append(trace)

    from fmp.models import resolve_model

    agent = create_agent(
        resolve_model(args.model), tools=[], system_prompt=system_prompt, middleware=stack
    )

    if not args.quiet:
        print(
            f"fmp-agent · model {args.model} · session {fmp_mw.session_id[:8]}\n{fm.describe()}\n",
            file=sys.stderr,
        )

    messages: list = []

    def turn(text: str) -> None:
        messages.append(HumanMessage(content=text))
        result = agent.invoke({"messages": messages})
        messages[:] = result["messages"]
        final = result["messages"][-1]
        if not args.quiet:
            print(file=sys.stderr, flush=True)
        print((final.text if hasattr(final, "text") else str(final.content)).strip(), flush=True)
        if not args.quiet:
            up = fmp_mw.last_upload
            if up:
                print(
                    "\n--- transcript "
                    + (f"error: {up['error']}" if "error" in up else "sent to " + ", ".join(up)),
                    file=sys.stderr,
                )
            else:
                print(
                    "\n--- transcript not sent (no server configured to receive it)",
                    file=sys.stderr,
                )

    if args.prompt:
        turn(" ".join(args.prompt))
        return 0
    print("fmp-agent interactive mode. Ctrl-D to exit.", file=sys.stderr)
    try:
        while True:
            text = input("> ").strip()
            if text:
                turn(text)
    except (EOFError, KeyboardInterrupt):
        print(file=sys.stderr)
    return 0
