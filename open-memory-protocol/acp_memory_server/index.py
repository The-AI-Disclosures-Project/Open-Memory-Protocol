from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
import time
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from acp_memory_server.models import AgentSpec, AgentStatus, IndexedTurn, SessionRecord

log = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS agents (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    launch_cmd TEXT,
    launch_args_json TEXT,
    launch_env_json TEXT,
    enabled INTEGER NOT NULL DEFAULT 1,
    status TEXT NOT NULL DEFAULT 'unknown',
    last_polled_at INTEGER,
    last_error TEXT
);

CREATE TABLE IF NOT EXISTS sessions (
    agent_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    cwd TEXT,
    title TEXT,
    started_at INTEGER,
    last_turn_at INTEGER,
    turn_count INTEGER NOT NULL DEFAULT 0,
    raw_meta_json TEXT,
    PRIMARY KEY (agent_id, session_id)
);
CREATE INDEX IF NOT EXISTS sessions_last_turn ON sessions(last_turn_at DESC);

CREATE TABLE IF NOT EXISTS turns (
    rowid INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    turn_index INTEGER NOT NULL,
    role TEXT NOT NULL,
    content_text TEXT,
    tool_name TEXT,
    tool_args_json TEXT,
    raw_blob TEXT,
    ts INTEGER NOT NULL,
    UNIQUE(agent_id, session_id, turn_index)
);
CREATE INDEX IF NOT EXISTS turns_session ON turns(agent_id, session_id, turn_index);
CREATE INDEX IF NOT EXISTS turns_ts ON turns(ts DESC);

CREATE VIRTUAL TABLE IF NOT EXISTS turns_fts USING fts5(
    content_text,
    tool_summary,
    tokenize='porter unicode61'
);

CREATE TRIGGER IF NOT EXISTS turns_ai AFTER INSERT ON turns BEGIN
    INSERT INTO turns_fts(rowid, content_text, tool_summary)
    VALUES (new.rowid, COALESCE(new.content_text,''),
            COALESCE(new.tool_name,'') || ' ' || COALESCE(new.tool_args_json,''));
END;

CREATE TRIGGER IF NOT EXISTS turns_ad AFTER DELETE ON turns BEGIN
    DELETE FROM turns_fts WHERE rowid = old.rowid;
END;

CREATE TRIGGER IF NOT EXISTS turns_au AFTER UPDATE ON turns BEGIN
    DELETE FROM turns_fts WHERE rowid = old.rowid;
    INSERT INTO turns_fts(rowid, content_text, tool_summary)
    VALUES (new.rowid, COALESCE(new.content_text,''),
            COALESCE(new.tool_name,'') || ' ' || COALESCE(new.tool_args_json,''));
END;
"""


def _connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, isolation_level=None, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


class Index:
    """SQLite + FTS5 store. A single writer task drains an asyncio queue, so all
    write traffic is serialized; reads use short-lived connections to avoid lock contention."""

    _SHUTDOWN: object = object()

    def __init__(self, path: Path) -> None:
        self.path = path
        self._writer_conn: sqlite3.Connection | None = None
        self._write_queue: asyncio.Queue[Any] = asyncio.Queue()
        self._writer_task: asyncio.Task[None] | None = None

    def init(self) -> None:
        conn = _connect(self.path)
        try:
            self._migrate(conn)
            conn.executescript(SCHEMA)
        finally:
            conn.close()

    @staticmethod
    def _migrate(conn: sqlite3.Connection) -> None:
        """Detect and replace obsolete schema versions that pre-date the current code."""
        # Earlier versions used `content='turns'` external-content FTS, which fails because
        # the underlying table doesn't have a `tool_summary` column. Drop and let SCHEMA
        # rebuild as a regular FTS5 table; turns_ai trigger will re-index on insert. We
        # also need to repopulate from existing turns since the recreated table is empty.
        row = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='turns_fts'"
        ).fetchone()
        if row is None:
            return
        if "content='turns'" in (row["sql"] or ""):
            log.info("migrating turns_fts: dropping obsolete external-content FTS")
            conn.execute("DROP TABLE IF EXISTS turns_fts")
            for trig in ("turns_ai", "turns_ad", "turns_au"):
                conn.execute(f"DROP TRIGGER IF EXISTS {trig}")
            conn.executescript(SCHEMA)
            # Repopulate FTS from existing turns.
            conn.execute(
                """
                INSERT INTO turns_fts(rowid, content_text, tool_summary)
                SELECT rowid, COALESCE(content_text,''),
                       COALESCE(tool_name,'') || ' ' || COALESCE(tool_args_json,'')
                FROM turns
                """
            )
            log.info("migration done: FTS rebuilt")

    async def start_writer(self) -> None:
        if self._writer_task is not None:
            return
        self._writer_conn = _connect(self.path)
        self._writer_task = asyncio.create_task(self._writer_loop(), name="acp-memory-writer")

    async def stop_writer(self) -> None:
        if self._writer_task is None:
            return
        await self._write_queue.put(self._SHUTDOWN)
        await self._writer_task
        self._writer_task = None
        if self._writer_conn is not None:
            self._writer_conn.close()
            self._writer_conn = None

    async def _writer_loop(self) -> None:
        assert self._writer_conn is not None
        conn = self._writer_conn
        while True:
            item = await self._write_queue.get()
            if item is self._SHUTDOWN:
                return
            op = item[0]
            args = item[1:]
            try:
                if op == "drain":
                    args[0].set()
                elif op == "upsert_agent":
                    self._upsert_agent_sync(conn, *args)
                elif op == "set_agent_status":
                    self._set_agent_status_sync(conn, *args)
                elif op == "upsert_session":
                    self._upsert_session_sync(conn, *args)
                elif op == "insert_turns":
                    self._insert_turns_sync(conn, *args)
                elif op == "delete_session":
                    self._delete_session_sync(conn, *args)
                elif op == "reindex_fts":
                    self._reindex_fts_sync(conn)
            except Exception:  # noqa: BLE001
                log.exception("Index write op %s failed", op)

    # ----- write helpers (sync) -----

    @staticmethod
    def _upsert_agent_sync(conn: sqlite3.Connection, agent: AgentSpec) -> None:
        conn.execute(
            """
            INSERT INTO agents(id, name, launch_cmd, launch_args_json, launch_env_json, enabled)
            VALUES(?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name=excluded.name,
                launch_cmd=excluded.launch_cmd,
                launch_args_json=excluded.launch_args_json,
                launch_env_json=excluded.launch_env_json,
                enabled=excluded.enabled
            """,
            (
                agent.id,
                agent.name,
                agent.launch_cmd,
                json.dumps(agent.launch_args),
                json.dumps(agent.launch_env),
                1 if agent.enabled else 0,
            ),
        )

    @staticmethod
    def _set_agent_status_sync(
        conn: sqlite3.Connection, agent_id: str, status: str, last_error: str | None
    ) -> None:
        conn.execute(
            "UPDATE agents SET status=?, last_polled_at=?, last_error=? WHERE id=?",
            (status, int(time.time()), last_error, agent_id),
        )

    @staticmethod
    def _upsert_session_sync(conn: sqlite3.Connection, rec: SessionRecord, raw_meta: str | None) -> None:
        conn.execute(
            """
            INSERT INTO sessions(agent_id, session_id, cwd, title, started_at, last_turn_at,
                                  turn_count, raw_meta_json)
            VALUES(?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(agent_id, session_id) DO UPDATE SET
                cwd=excluded.cwd,
                title=excluded.title,
                started_at=COALESCE(sessions.started_at, excluded.started_at),
                last_turn_at=excluded.last_turn_at,
                turn_count=excluded.turn_count,
                raw_meta_json=excluded.raw_meta_json
            """,
            (
                rec.agent_id,
                rec.session_id,
                rec.cwd,
                rec.title,
                rec.started_at,
                rec.last_turn_at,
                rec.turn_count,
                raw_meta,
            ),
        )

    @staticmethod
    def _insert_turns_sync(conn: sqlite3.Connection, turns: list[IndexedTurn]) -> None:
        if not turns:
            return
        conn.executemany(
            """
            INSERT OR IGNORE INTO turns(agent_id, session_id, turn_index, role,
                                         content_text, tool_name, tool_args_json, raw_blob, ts)
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    t.agent_id,
                    t.session_id,
                    t.turn_index,
                    t.role,
                    t.content_text,
                    t.tool_name,
                    t.tool_args_json,
                    t.raw_blob,
                    t.ts,
                )
                for t in turns
            ],
        )

    @staticmethod
    def _delete_session_sync(conn: sqlite3.Connection, agent_id: str, session_id: str) -> None:
        conn.execute("DELETE FROM turns WHERE agent_id=? AND session_id=?", (agent_id, session_id))
        conn.execute(
            "DELETE FROM sessions WHERE agent_id=? AND session_id=?", (agent_id, session_id)
        )

    @staticmethod
    def _reindex_fts_sync(conn: sqlite3.Connection) -> None:
        conn.execute("DELETE FROM turns_fts")
        conn.execute(
            """
            INSERT INTO turns_fts(rowid, content_text, tool_summary)
            SELECT rowid, COALESCE(content_text, ''),
                   COALESCE(tool_name,'') || ' ' || COALESCE(tool_args_json,'')
            FROM turns
            """
        )

    # ----- write API (async) -----

    async def upsert_agent(self, agent: AgentSpec) -> None:
        await self._write_queue.put(("upsert_agent", agent))

    async def set_agent_status(self, agent_id: str, status: str, last_error: str | None = None) -> None:
        await self._write_queue.put(("set_agent_status", agent_id, status, last_error))

    async def upsert_session(self, rec: SessionRecord, raw_meta: str | None = None) -> None:
        await self._write_queue.put(("upsert_session", rec, raw_meta))

    async def insert_turns(self, turns: list[IndexedTurn]) -> None:
        if not turns:
            return
        await self._write_queue.put(("insert_turns", turns))

    async def delete_session(self, agent_id: str, session_id: str) -> None:
        await self._write_queue.put(("delete_session", agent_id, session_id))

    async def reindex_fts(self) -> None:
        await self._write_queue.put(("reindex_fts",))

    async def drain(self) -> None:
        """Block until every write enqueued before this call has been applied."""
        evt = asyncio.Event()
        await self._write_queue.put(("drain", evt))
        await evt.wait()

    # ----- read API (sync, short-lived connections) -----

    def list_agents(self) -> list[AgentStatus]:
        conn = _connect(self.path)
        try:
            rows = conn.execute(
                """
                SELECT a.id, a.name, a.status, a.last_polled_at, a.last_error,
                       (SELECT COUNT(*) FROM sessions s WHERE s.agent_id=a.id) AS session_count
                FROM agents a
                ORDER BY a.id
                """
            ).fetchall()
        finally:
            conn.close()
        return [
            AgentStatus(
                id=r["id"],
                name=r["name"],
                status=r["status"],
                last_polled_at=r["last_polled_at"],
                session_count=r["session_count"],
                last_error=r["last_error"],
            )
            for r in rows
        ]

    def list_sessions(self, agent: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        conn = _connect(self.path)
        try:
            if agent:
                rows = conn.execute(
                    """
                    SELECT * FROM sessions WHERE agent_id=?
                    ORDER BY COALESCE(last_turn_at, started_at, 0) DESC
                    LIMIT ?
                    """,
                    (agent, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT * FROM sessions
                    ORDER BY COALESCE(last_turn_at, started_at, 0) DESC
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()
        finally:
            conn.close()
        return [dict(r) for r in rows]

    def get_session_turns(
        self,
        agent: str,
        session_id: str,
        offset: int = 0,
        limit: int = 200,
        roles: list[str] | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """Return (turns, total). `total` is the count after `roles` filter is applied,
        so callers can paginate with (offset, limit) without needing a second query."""
        conn = _connect(self.path)
        try:
            base_sql = "FROM turns WHERE agent_id=? AND session_id=?"
            params: list[Any] = [agent, session_id]
            if roles:
                placeholders = ",".join("?" for _ in roles)
                base_sql += f" AND role IN ({placeholders})"
                params.extend(roles)

            total = conn.execute(f"SELECT COUNT(*) {base_sql}", params).fetchone()[0]

            rows = conn.execute(
                f"""
                SELECT turn_index, role, content_text, tool_name, tool_args_json, ts
                {base_sql}
                ORDER BY turn_index ASC
                LIMIT ? OFFSET ?
                """,
                [*params, limit, offset],
            ).fetchall()
        finally:
            conn.close()
        return [dict(r) for r in rows], int(total)

    def session_watermark(self, agent: str, session_id: str) -> tuple[int, int] | None:
        conn = _connect(self.path)
        try:
            row = conn.execute(
                "SELECT turn_count, last_turn_at FROM sessions WHERE agent_id=? AND session_id=?",
                (agent, session_id),
            ).fetchone()
        finally:
            conn.close()
        if row is None:
            return None
        return int(row["turn_count"] or 0), int(row["last_turn_at"] or 0)

    def search(
        self,
        query: str,
        agent: str | None = None,
        since_ts: int | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        conn = _connect(self.path)
        try:
            sql = """
            SELECT t.agent_id, t.session_id, t.turn_index, t.role, t.tool_name,
                   t.ts, snippet(turns_fts, 0, '[', ']', ' … ', 12) AS snippet,
                   bm25(turns_fts) AS score,
                   s.cwd, s.title
            FROM turns_fts
            JOIN turns t ON t.rowid = turns_fts.rowid
            LEFT JOIN sessions s ON s.agent_id = t.agent_id AND s.session_id = t.session_id
            WHERE turns_fts MATCH ?
            """
            params: list[Any] = [query]
            if agent:
                sql += " AND t.agent_id=?"
                params.append(agent)
            if since_ts:
                sql += " AND t.ts >= ?"
                params.append(since_ts)
            sql += " ORDER BY score ASC LIMIT ?"
            params.append(limit)
            rows = conn.execute(sql, params).fetchall()
        finally:
            conn.close()
        return [dict(r) for r in rows]


def parse_since(since: str | None) -> int | None:
    """Parse 'since' into an epoch-seconds floor. Accepts ISO-8601 or '7d', '24h', '30m'."""
    if not since:
        return None
    s = since.strip().lower()
    units = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 86400 * 7}
    if s and s[-1] in units and s[:-1].isdigit():
        return int(time.time()) - int(s[:-1]) * units[s[-1]]
    from datetime import datetime, timezone

    try:
        dt = datetime.fromisoformat(s.replace("z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp())
    except ValueError:
        return None


def iter_session_ids(idx: Index, agent_id: str) -> Iterable[str]:
    conn = _connect(idx.path)
    try:
        rows = conn.execute(
            "SELECT session_id FROM sessions WHERE agent_id=?", (agent_id,)
        ).fetchall()
    finally:
        conn.close()
    return [r["session_id"] for r in rows]
