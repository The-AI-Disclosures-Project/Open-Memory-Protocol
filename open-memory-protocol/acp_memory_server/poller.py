"""Per-agent ACP poll cycle and the global scheduler.

For each agent, on every tick:
  1. spawn the ACP subprocess (lazy)
  2. initialize -> check `loadSession` capability and `authMethods`
  3. session/list -> diff against indexed watermark
  4. for each new/changed session_id: session/load -> drain session/update notifications
  5. normalize + insert turns; upsert session record
  6. terminate the subprocess

Subprocesses are not kept alive between ticks. The recursion guard env var
(`ACP_MEMORY_DISABLE_RECURSION=1`) is set so spawned agents skip auto-loading us back."""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
import time
from typing import Any

from acp import (
    PROTOCOL_VERSION,
    spawn_agent_process,
)
from acp.schema import (
    ClientCapabilities,
    Implementation,
)

from acp_memory_server.acp_client import CollectingClient
from acp_memory_server.config import Config
from acp_memory_server.cwds import discover_cwds
from acp_memory_server.filesystem_backend import has_filesystem_backend, scan as scan_filesystem
from acp_memory_server.index import Index
from acp_memory_server.models import AgentSpec, IndexedTurn, SessionRecord
from acp_memory_server.normalizer import normalize_update

log = logging.getLogger(__name__)

CLIENT_INFO = Implementation(
    name="acp-memory-server",
    title="ACP Memory MCP Server",
    version="0.1.0",
)

# Time to wait for a session/load to drain via session/update notifications before giving up.
SESSION_LOAD_TIMEOUT_SECONDS = 60.0

# Quiet period after the last session/update notification before we declare the replay done,
# since session/load is fire-and-forget on notifications and there's no explicit "end" signal.
SESSION_LOAD_QUIET_SECONDS = 1.5

# A single session/update line can carry an entire prior turn (whole agent message + diffs).
# Default asyncio StreamReader limit is 64KB, far too small. Bump to 16MB.
ACP_STDIO_BUFFER_LIMIT = 16 * 1024 * 1024


class Poller:
    def __init__(self, idx: Index, cfg: Config, agents: list[AgentSpec]) -> None:
        self.idx = idx
        self.cfg = cfg
        self.agents = agents
        self._task: asyncio.Task[None] | None = None
        self._stop_event = asyncio.Event()
        self._poll_locks: dict[str, asyncio.Lock] = {}
        self._refresh_request: asyncio.Event = asyncio.Event()
        self._refresh_filter: str | None = None

    def replace_agents(self, agents: list[AgentSpec]) -> None:
        self.agents = agents
        self._poll_locks = {a.id: self._poll_locks.get(a.id, asyncio.Lock()) for a in agents}

    def start(self) -> None:
        if self._task is not None:
            return
        self._poll_locks = {a.id: asyncio.Lock() for a in self.agents}
        self._task = asyncio.create_task(self._scheduler_loop(), name="acp-memory-poller")

    async def stop(self) -> None:
        if self._task is None:
            return
        self._stop_event.set()
        self._refresh_request.set()
        await self._task
        self._task = None

    async def request_refresh(self, agent_id: str | None = None) -> None:
        self._refresh_filter = agent_id
        self._refresh_request.set()

    async def _scheduler_loop(self) -> None:
        # Initial pass on startup.
        await self._poll_all(filter_agent=None)

        while not self._stop_event.is_set():
            try:
                await asyncio.wait_for(
                    self._refresh_request.wait(), timeout=self.cfg.poll_interval_seconds
                )
                # explicit refresh
                fltr = self._refresh_filter
                self._refresh_filter = None
                self._refresh_request.clear()
                await self._poll_all(filter_agent=fltr)
            except asyncio.TimeoutError:
                # scheduled poll
                await self._poll_all(filter_agent=None)

    async def _poll_all(self, filter_agent: str | None) -> None:
        targets = [a for a in self.agents if filter_agent is None or a.id == filter_agent]
        if not targets:
            return
        log.info("poll cycle starting for %d agents", len(targets))
        await asyncio.gather(
            *(self._poll_one_safe(a) for a in targets),
            return_exceptions=True,
        )

    async def _poll_one_safe(self, agent: AgentSpec) -> None:
        lock = self._poll_locks.setdefault(agent.id, asyncio.Lock())
        if lock.locked():
            log.debug("agent %s already polling, skipping this tick", agent.id)
            return
        async with lock:
            try:
                if self._backend_for(agent) == "filesystem":
                    await self._poll_one_filesystem(agent)
                else:
                    await self._poll_one(agent)
            except Exception as e:  # noqa: BLE001
                log.exception("agent %s poll failed", agent.id)
                await self.idx.set_agent_status(agent.id, "error", str(e))

    def _backend_for(self, agent: AgentSpec) -> str:
        """Resolve which backend to use for this agent.

        Priority: explicit override > "auto" (use filesystem if available) > "acp"."""
        override = self.cfg.agent_overrides.get(agent.id)
        if override is not None and override.backend in ("acp", "filesystem"):
            return override.backend
        if has_filesystem_backend(agent.id):
            return "filesystem"
        return "acp"

    async def _poll_one_filesystem(self, agent: AgentSpec) -> None:
        await self.idx.upsert_agent(agent)
        new_or_updated = 0
        seen = 0
        # The scanner is sync (file IO); run in a thread to keep the loop responsive.
        results = await asyncio.to_thread(lambda: list(scan_filesystem(self.idx, agent.id)))
        for r in results:
            seen += 1
            await self.idx.upsert_session(r.record, r.raw_meta)
            await self.idx.insert_turns(r.turns)
            new_or_updated += 1
        await self.idx.drain()
        await self.idx.set_agent_status(agent.id, "ok", None)
        log.info(
            "agent %s filesystem poll done: %d sessions seen, %d new/updated",
            agent.id,
            seen,
            new_or_updated,
        )

    async def _poll_one(self, agent: AgentSpec) -> None:
        await self.idx.upsert_agent(agent)

        env = {**os.environ, **agent.launch_env, "ACP_MEMORY_DISABLE_RECURSION": "1"}

        client = CollectingClient()

        async with spawn_agent_process(
            client,
            agent.launch_cmd,
            *agent.launch_args,
            env=env,
            cwd=agent.cwd,
            transport_kwargs={"limit": ACP_STDIO_BUFFER_LIMIT},
        ) as (conn, proc):
            try:
                init_resp = await conn.initialize(
                    protocol_version=PROTOCOL_VERSION,
                    client_capabilities=ClientCapabilities(),
                    client_info=CLIENT_INFO,
                )
            except Exception as e:  # noqa: BLE001
                await self.idx.set_agent_status(agent.id, "error", f"initialize failed: {e}")
                _kill(proc)
                return

            caps = init_resp.agent_capabilities
            auth_methods = init_resp.auth_methods or []

            if not (caps and getattr(caps, "load_session", False)):
                await self.idx.set_agent_status(
                    agent.id,
                    "unsupported",
                    "agent does not advertise loadSession capability",
                )
                _kill(proc)
                return

            # Some ACP adapters silently filter session/list to the spawning cwd. We may
            # need to call it once per known project root to enumerate everything. Resolve
            # the cwd list: explicit override > auto-discovery > [None] (single unscoped call).
            cwds_to_query = self._resolve_cwds(agent)

            new_or_updated_count = 0
            seen_session_ids: set[str] = set()

            for cwd in cwds_to_query:
                try:
                    sessions_page = await conn.list_sessions(cwd=cwd) if cwd else await conn.list_sessions()
                except Exception as e:  # noqa: BLE001
                    msg = str(e)
                    if "auth" in msg.lower() or "unauthorized" in msg.lower() or "401" in msg:
                        await self.idx.set_agent_status(
                            agent.id,
                            "needs_auth",
                            "session/list rejected; authenticate manually then retry",
                        )
                        _kill(proc)
                        return
                    if "not_found" in msg.lower() or "method not found" in msg.lower():
                        await self.idx.set_agent_status(agent.id, "unsupported", "session/list not supported")
                        _kill(proc)
                        return
                    log.warning("agent %s list_sessions(cwd=%r) failed: %s", agent.id, cwd, e)
                    continue

                page = sessions_page
                while True:
                    for info in page.sessions or []:
                        if info.session_id in seen_session_ids:
                            continue
                        seen_session_ids.add(info.session_id)
                        if await self._maybe_index_session(agent, conn, client, info):
                            new_or_updated_count += 1
                    if not page.next_cursor:
                        break
                    try:
                        page = await conn.list_sessions(
                            cursor=page.next_cursor, cwd=cwd
                        ) if cwd else await conn.list_sessions(cursor=page.next_cursor)
                    except Exception as e:  # noqa: BLE001
                        log.warning("agent %s list_sessions pagination failed: %s", agent.id, e)
                        break

            await self.idx.set_agent_status(agent.id, "ok", None)
            log.info(
                "agent %s poll done: %d sessions seen, %d new/updated",
                agent.id,
                len(seen_session_ids),
                new_or_updated_count,
            )
            _kill(proc)

    def _resolve_cwds(self, agent: AgentSpec) -> list[str | None]:
        """Return the list of cwds to feed `list_sessions`.

        - Explicit override in config wins. `cwds=[]` means "single unscoped call".
        - Otherwise auto-discover via cwds.py.
        - Auto-discovery falling back empty means "single unscoped call" (preserves
          current behavior for agents we don't know about)."""
        override = self.cfg.agent_overrides.get(agent.id)
        if override is not None and override.cwds is not None:
            return list(override.cwds) if override.cwds else [None]

        discovered = discover_cwds(agent.id)
        if discovered:
            log.info("agent %s: querying %d cwds", agent.id, len(discovered))
            return list(discovered)
        return [None]

    async def _maybe_index_session(
        self,
        agent: AgentSpec,
        conn: Any,
        client: CollectingClient,
        info: Any,
    ) -> bool:
        """Diff the session against our watermark; replay it if new or grown.
        Returns True if any work was done."""
        existing = self.idx.session_watermark(agent.id, info.session_id)
        # We don't get turn_count from list_sessions in current ACP; rely on updated_at + first-seen.
        updated_at_ts = _parse_iso8601(info.updated_at) if info.updated_at else None

        if existing is not None and updated_at_ts is not None:
            _, last_turn_at = existing
            if last_turn_at and updated_at_ts <= last_turn_at:
                return False  # already up to date

        return await self._replay_session(agent, conn, client, info)

    async def _replay_session(
        self,
        agent: AgentSpec,
        conn: Any,
        client: CollectingClient,
        info: Any,
    ) -> bool:
        """Issue session/load and drain notifications until the agent goes quiet."""
        client.reset(info.session_id)
        queue = client.queue_for(info.session_id)

        cwd = info.cwd or agent.cwd or os.getcwd()
        try:
            await conn.load_session(cwd=cwd, session_id=info.session_id, mcp_servers=[])
        except Exception as e:  # noqa: BLE001
            log.warning(
                "agent %s session/load %s failed: %s", agent.id, info.session_id, e
            )
            return False

        turns: list[IndexedTurn] = []
        next_idx = self.idx.session_watermark(agent.id, info.session_id)
        next_turn_index = next_idx[0] if next_idx else 0

        deadline = asyncio.get_event_loop().time() + SESSION_LOAD_TIMEOUT_SECONDS
        last_msg_at = asyncio.get_event_loop().time()

        while True:
            now = asyncio.get_event_loop().time()
            timeout = max(0.05, min(SESSION_LOAD_QUIET_SECONDS, deadline - now))
            try:
                update = await asyncio.wait_for(queue.get(), timeout=timeout)
            except asyncio.TimeoutError:
                # Quiet period elapsed -> assume replay finished.
                if now - last_msg_at >= SESSION_LOAD_QUIET_SECONDS or now >= deadline:
                    break
                continue

            if update is None:
                break

            last_msg_at = asyncio.get_event_loop().time()
            normalized = normalize_update(
                agent.id, info.session_id, next_turn_index, update
            )
            if normalized is not None:
                turns.append(normalized)
                next_turn_index += 1

            if asyncio.get_event_loop().time() >= deadline:
                log.warning(
                    "agent %s session/load %s hit deadline; partial replay (%d turns)",
                    agent.id,
                    info.session_id,
                    len(turns),
                )
                break

        await self.idx.insert_turns(turns)

        with contextlib.suppress(Exception):
            await conn.close_session(info.session_id)

        rec = SessionRecord(
            agent_id=agent.id,
            session_id=info.session_id,
            cwd=cwd,
            title=getattr(info, "title", None),
            started_at=int(time.time()) if next_idx is None else None,
            last_turn_at=int(time.time()),
            turn_count=next_turn_index,
        )
        raw_meta = json.dumps(
            {
                "title": getattr(info, "title", None),
                "updated_at": getattr(info, "updated_at", None),
                "additional_directories": getattr(info, "additional_directories", None),
            },
            default=str,
        )
        await self.idx.upsert_session(rec, raw_meta)
        return bool(turns)


def _kill(proc: Any) -> None:
    try:
        if getattr(proc, "returncode", 0) is None:
            proc.terminate()
    except ProcessLookupError:
        pass
    except Exception:  # noqa: BLE001
        pass


def _parse_iso8601(s: str | None) -> int | None:
    if not s:
        return None
    from datetime import datetime, timezone

    try:
        s = s.replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp())
    except ValueError:
        return None
