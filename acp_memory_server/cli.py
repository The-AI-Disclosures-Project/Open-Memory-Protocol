"""acp-memory CLI: serve | doctor | reindex."""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import time
from datetime import datetime, timezone
from typing import Any

from acp_memory_server.config import (
    cache_dir,
    config_path,
    data_dir,
    db_path,
    ensure_dirs,
    load_config,
)
from acp_memory_server.detect import detect_agents
from acp_memory_server.index import Index
from acp_memory_server.registry import fetch_registry, parse_registry


def _setup_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        stream=sys.stderr,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def cmd_serve(args: argparse.Namespace) -> int:
    _setup_logging(args.verbose)
    from acp_memory_server.server import run

    run()
    return 0


async def _doctor() -> int:
    cfg = load_config()
    print(f"config:    {config_path()}{'  (missing — using defaults)' if not config_path().exists() else ''}")
    print(f"data dir:  {data_dir()}")
    print(f"cache dir: {cache_dir()}")
    print(f"db:        {db_path()}{'  (will be created on first serve)' if not db_path().exists() else ''}")
    print()
    print(f"poll interval: {cfg.poll_interval_seconds}s")
    print(f"registry URL:  {cfg.registry_url}")

    # Registry fetch
    print()
    print("--- registry ---")
    try:
        payload = await fetch_registry(cfg.registry_url, cfg.registry_cache_ttl_seconds)
        registry_agents = parse_registry(payload)
        print(f"OK: {len(registry_agents)} agent entries available")
    except Exception as e:  # noqa: BLE001
        print(f"ERROR: registry fetch failed: {e}")
        registry_agents = []

    # Local detection
    print()
    print("--- local detection ---")
    detected = detect_agents(registry_agents, cfg)
    if not detected:
        print("(no agents detected — none of the registered agents have their tooling on PATH)")
    for spec in detected:
        print(f"  - {spec.id}: {spec.launch_cmd} {' '.join(spec.launch_args)}")

    # Indexed status
    print()
    print("--- indexed status ---")
    if db_path().exists():
        idx = Index(db_path())
        for a in idx.list_agents():
            ts = "never" if not a.last_polled_at else datetime.fromtimestamp(
                a.last_polled_at, tz=timezone.utc
            ).isoformat()
            err = f"  err={a.last_error}" if a.last_error else ""
            print(
                f"  - {a.id:<24} status={a.status:<12} sessions={a.session_count:<5} "
                f"last_poll={ts}{err}"
            )
    else:
        print("(database not created yet — run `acp-memory serve` to start indexing)")

    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    _setup_logging(args.verbose)
    ensure_dirs()
    return asyncio.run(_doctor())


async def _reindex(agent_id: str | None) -> int:
    ensure_dirs()
    idx = Index(db_path())
    idx.init()
    await idx.start_writer()
    try:
        if agent_id is not None:
            # Wipe sessions+turns for one agent so the next poll repopulates from scratch.
            from acp_memory_server.index import _connect

            conn = _connect(db_path())
            try:
                conn.execute("DELETE FROM turns WHERE agent_id=?", (agent_id,))
                conn.execute("DELETE FROM sessions WHERE agent_id=?", (agent_id,))
            finally:
                conn.close()
            print(f"wiped {agent_id} sessions and turns; will repopulate on next serve poll")
        await idx.reindex_fts()
        await idx.drain()
        print("FTS index rebuilt")
    finally:
        await idx.stop_writer()
    return 0


def cmd_reindex(args: argparse.Namespace) -> int:
    _setup_logging(args.verbose)
    return asyncio.run(_reindex(args.agent))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="acp-memory", description="ACP Memory MCP server")
    parser.add_argument("-v", "--verbose", action="store_true", help="debug logging")
    sub = parser.add_subparsers(dest="cmd")

    sp_serve = sub.add_parser("serve", help="run the MCP stdio server")
    sp_serve.set_defaults(func=cmd_serve)

    sp_doctor = sub.add_parser("doctor", help="diagnose discovery & indexing state")
    sp_doctor.set_defaults(func=cmd_doctor)

    sp_reindex = sub.add_parser("reindex", help="rebuild the FTS index")
    sp_reindex.add_argument("--agent", help="wipe and re-fetch only this agent on next poll")
    sp_reindex.set_defaults(func=cmd_reindex)

    args = parser.parse_args(argv)
    if not args.cmd:
        # Default to `serve` so `acp-memory` (no args) works as the MCP entry point.
        args.cmd = "serve"
        args.func = cmd_serve
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
