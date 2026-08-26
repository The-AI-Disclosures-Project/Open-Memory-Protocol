"""MCP stdio server. Runs the FastMCP-style `MCPServer` with six tools and orchestrates
the background poller via the lifespan hook so polling starts on connect."""

from __future__ import annotations

import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

from mcp.server.fastmcp import Context, FastMCP

from acp_memory_server.config import config_path, db_path, ensure_dirs, load_config
from acp_memory_server.detect import detect_agents
from acp_memory_server.index import Index, parse_since
from acp_memory_server.poller import Poller
from acp_memory_server.registry import fetch_registry, parse_registry

log = logging.getLogger(__name__)


@dataclass
class ServerContext:
    idx: Index
    poller: Poller


@asynccontextmanager
async def _lifespan(server: FastMCP) -> AsyncIterator[ServerContext]:
    if os.environ.get("ACP_MEMORY_DISABLE_RECURSION") == "1":
        log.warning(
            "ACP_MEMORY_DISABLE_RECURSION=1 detected — running in degraded mode "
            "(no polling) to avoid recursive ACP memory server invocations"
        )

    ensure_dirs()
    cfg = load_config()
    idx = Index(db_path())
    idx.init()
    await idx.start_writer()

    agents: list[Any] = []
    if os.environ.get("ACP_MEMORY_DISABLE_RECURSION") != "1":
        try:
            payload = await fetch_registry(cfg.registry_url, cfg.registry_cache_ttl_seconds)
            registry_agents = parse_registry(payload)
        except Exception as e:  # noqa: BLE001
            log.warning("registry fetch failed; proceeding with config-only agents: %s", e)
            registry_agents = []
        agents = detect_agents(registry_agents, cfg)
        for spec in agents:
            await idx.upsert_agent(spec)

    poller = Poller(idx, cfg, agents)
    if agents:
        poller.start()

    try:
        yield ServerContext(idx=idx, poller=poller)
    finally:
        await poller.stop()
        await idx.stop_writer()


mcp = FastMCP(
    name="acp-memory",
    instructions=(
        "Unified search across past ACP coding-agent transcripts (Claude Code, Codex, Goose, ...). "
        "Polls each detected agent in the background; indexed via SQLite FTS5. "
        "Use search_memory for FTS queries, list_agents to see what's indexed, "
        "get_session for full transcripts, and refresh to force a poll cycle."
    ),
    lifespan=_lifespan,
)


def _ctx(ctx: Context) -> ServerContext:
    return ctx.request_context.lifespan_context


@mcp.tool()
def search_memory(
    ctx: Context,
    query: str,
    agent: str | None = None,
    since: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Full-text search across indexed agent transcripts.

    `query` is an FTS5 MATCH expression (supports phrase queries with quotes, AND/OR, NEAR).
    `agent` optionally restricts to one agent id (see list_agents).
    `since` optionally limits to recent turns; accepts '7d', '24h', '30m', or ISO-8601.
    """
    state = _ctx(ctx)
    since_ts = parse_since(since)
    return state.idx.search(query=query, agent=agent, since_ts=since_ts, limit=max(1, min(limit, 100)))


@mcp.tool()
def list_agents(ctx: Context) -> list[dict[str, Any]]:
    """List ACP agents detected on this machine and their poll status."""
    state = _ctx(ctx)
    return [
        {
            "id": a.id,
            "name": a.name,
            "status": a.status,
            "last_polled_at": a.last_polled_at,
            "session_count": a.session_count,
            "last_error": a.last_error,
        }
        for a in state.idx.list_agents()
    ]


@mcp.tool()
def list_sessions(
    ctx: Context, agent: str | None = None, limit: int = 50
) -> list[dict[str, Any]]:
    """Recent indexed sessions, optionally filtered to a single agent."""
    state = _ctx(ctx)
    return state.idx.list_sessions(agent=agent, limit=max(1, min(limit, 500)))


@mcp.tool()
def get_session(
    ctx: Context,
    agent: str,
    session_id: str,
    offset: int = 0,
    limit: int = 200,
    only_human: bool = False,
    roles: list[str] | None = None,
) -> dict[str, Any]:
    """Reconstruct a session transcript with pagination and optional role filtering.

    `offset` / `limit` paginate (default returns turns 0..199; set offset=200 for the
    next page). Use the returned `total` and `has_more` to drive pagination.

    `only_human=True` returns just user turns (convenience equivalent to roles=["user"]).
    `roles=["user","agent"]` keeps human + assistant messages, drops tools and thoughts.
    If both are passed, `roles` wins.
    """
    state = _ctx(ctx)
    safe_limit = max(1, min(limit, 5000))
    safe_offset = max(0, offset)

    role_filter = roles if roles else (["user"] if only_human else None)

    turns, total = state.idx.get_session_turns(
        agent, session_id, offset=safe_offset, limit=safe_limit, roles=role_filter
    )
    return {
        "agent": agent,
        "session_id": session_id,
        "turns": turns,
        "total": total,
        "offset": safe_offset,
        "limit": safe_limit,
        "has_more": safe_offset + len(turns) < total,
        "roles_filter": role_filter,
    }


@mcp.tool()
async def refresh(ctx: Context, agent: str | None = None) -> dict[str, Any]:
    """Trigger an immediate poll cycle. Returns when the cycle is queued (not yet complete)."""
    state = _ctx(ctx)
    await state.poller.request_refresh(agent)
    return {"queued": True, "agent": agent}


@mcp.tool()
async def refresh_agents(ctx: Context) -> list[dict[str, Any]]:
    """Re-run agent discovery (registry + PATH) and reset the poller."""
    state = _ctx(ctx)
    cfg = load_config()
    try:
        payload = await fetch_registry(cfg.registry_url, cfg.registry_cache_ttl_seconds)
        registry_agents = parse_registry(payload)
    except Exception as e:  # noqa: BLE001
        log.warning("registry refetch failed: %s", e)
        registry_agents = []
    agents = detect_agents(registry_agents, cfg)
    for spec in agents:
        await state.idx.upsert_agent(spec)
    state.poller.replace_agents(agents)
    if agents and state.poller._task is None:
        state.poller.start()
    return [{"id": a.id, "name": a.name, "launch_cmd": a.launch_cmd} for a in agents]


def run() -> None:
    """Entrypoint: start the MCP stdio server."""
    logging.basicConfig(
        level=os.environ.get("ACP_MEMORY_LOG_LEVEL", "INFO").upper(),
        stream=__import__("sys").stderr,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    log.info("acp-memory server: db=%s config=%s", db_path(), config_path())
    mcp.run(transport="stdio")
