"""Storage backends for the FMP reference server.

The protocol says nothing about how a server stores or searches memory; these are two
concrete choices:

- SQLiteStore   : full read/write backend. One SQLite file, FTS5 for search.
- ACPIndexStore : read-only view over the SQLite index built by prototypes/acp_memory_server,
                  so every locally installed coding agent's history becomes an FMP server
                  with zero new indexing. Upload/delete endpoints are reported unsupported.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, ClassVar, Protocol

from fmp.schema import (
    FileRecord,
    FileUpload,
    InferenceRecord,
    InferenceUpload,
    MemoryType,
    Message,
    SearchHit,
    SearchRequest,
    TranscriptRecord,
    TranscriptUpload,
    new_id,
    now_iso,
)


class Store(Protocol):
    """What fmp.server needs from a backend. Any method may raise NotImplementedError,
    in which case the server reports that endpoint as unsupported in /fmp/info."""

    memory_types: list[MemoryType]
    unsupported: frozenset[str]
    """Endpoint names this backend does not implement (reported false in /fmp/info)."""

    def upload_files(self, files: list[FileUpload]) -> list[str]: ...
    def upload_transcript(self, t: TranscriptUpload) -> str: ...
    def upload_inferences(self, items: list[InferenceUpload]) -> list[str]: ...
    def search(self, req: SearchRequest) -> list[SearchHit]: ...
    def read_transcripts(
        self, offset: int, limit: int, include_messages: bool
    ) -> tuple[list[TranscriptRecord], int]: ...
    def read_inferences(self, offset: int, limit: int) -> tuple[list[InferenceRecord], int]: ...
    def delete(self, type_: MemoryType, id_: str) -> bool: ...


def _iso_floor(since: str | None) -> str | None:
    if not since:
        return None
    dt = datetime.fromisoformat(since)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.isoformat(timespec="seconds")


def _fts_query(q: str) -> str:
    """Quote each term so user punctuation cannot break FTS5 syntax.

    Terms are OR-ed and ranked by bm25, so a query with one unknown word still returns the
    records that match the others.
    """
    terms = [t.replace('"', '""') for t in q.split() if t]
    return " OR ".join(f'"{t}"' for t in terms) or '""'


# =============================================================================== SQLite


_SCHEMA = """
CREATE TABLE IF NOT EXISTS files (
    id TEXT PRIMARY KEY, name TEXT NOT NULL, mime TEXT NOT NULL, content TEXT NOT NULL,
    uploaded_at TEXT NOT NULL, metadata TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS transcripts (
    id TEXT PRIMARY KEY, source TEXT NOT NULL, started_at TEXT, title TEXT,
    partial INTEGER NOT NULL DEFAULT 0, metadata TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS messages (
    transcript_id TEXT NOT NULL, idx INTEGER NOT NULL, role TEXT NOT NULL,
    content TEXT NOT NULL, ts TEXT, tool_name TEXT, metadata TEXT NOT NULL,
    PRIMARY KEY (transcript_id, idx)
);
CREATE TABLE IF NOT EXISTS inferences (
    id TEXT PRIMARY KEY, content TEXT NOT NULL, date TEXT NOT NULL, created_by TEXT NOT NULL,
    based_on TEXT NOT NULL, metadata TEXT NOT NULL
);
CREATE VIRTUAL TABLE IF NOT EXISTS fts USING fts5(
    type UNINDEXED, ref UNINDEXED, id UNINDEXED, ts UNINDEXED, source UNINDEXED, text,
    tokenize='porter unicode61'
);
"""


class SQLiteStore:
    memory_types: ClassVar[list[MemoryType]] = [
        MemoryType.file,
        MemoryType.transcript,
        MemoryType.inference,
    ]
    unsupported: frozenset[str] = frozenset()

    def __init__(self, path: str | Path = ":memory:") -> None:
        self.path = str(path)
        self._conn = sqlite3.connect(self.path, isolation_level=None, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)

    # --- files
    def upload_files(self, files: list[FileUpload]) -> list[str]:
        ids = []
        for f in files:
            fid = new_id()
            ts = now_iso()
            self._conn.execute(
                "INSERT INTO files VALUES (?,?,?,?,?,?)",
                (fid, f.name, f.mime, f.content, ts, json.dumps(f.metadata)),
            )
            self._conn.execute(
                "INSERT INTO fts VALUES (?,?,?,?,?,?)",
                ("file", f"file:{fid}", fid, ts, f.name, f"{f.name}\n{f.content}"),
            )
            ids.append(fid)
        return ids

    # --- transcripts
    def upload_transcript(self, t: TranscriptUpload) -> str:
        tid = t.id or new_id()
        existing = self._conn.execute(
            "SELECT COUNT(*) FROM messages WHERE transcript_id=?", (tid,)
        ).fetchone()[0]
        self._conn.execute(
            """INSERT INTO transcripts VALUES (?,?,?,?,?,?,?)
               ON CONFLICT(id) DO UPDATE SET partial=excluded.partial, updated_at=excluded.updated_at,
               title=COALESCE(excluded.title, transcripts.title),
               started_at=COALESCE(transcripts.started_at, excluded.started_at)""",
            (
                tid,
                t.source,
                t.started_at,
                t.title,
                int(t.partial),
                json.dumps(t.metadata),
                now_iso(),
            ),
        )
        # Partial uploads of a known session append after what is already stored; a full
        # upload replaces the session's messages.
        if not t.partial and existing:
            self._conn.execute("DELETE FROM messages WHERE transcript_id=?", (tid,))
            self._conn.execute("DELETE FROM fts WHERE type='transcript' AND id=?", (tid,))
            existing = 0
        for i, m in enumerate(t.messages, start=existing):
            self._conn.execute(
                "INSERT INTO messages VALUES (?,?,?,?,?,?,?)",
                (tid, i, m.role, m.content, m.ts, m.tool_name, json.dumps(m.metadata)),
            )
            self._conn.execute(
                "INSERT INTO fts VALUES (?,?,?,?,?,?)",
                (
                    "transcript",
                    f"transcript:{tid}#{i}",
                    tid,
                    m.ts or t.started_at,
                    t.source,
                    f"{m.role}: {m.content}",
                ),
            )
        return tid

    # --- inferences
    def upload_inferences(self, items: list[InferenceUpload]) -> list[str]:
        ids = []
        for inf in items:
            iid = new_id()
            self._conn.execute(
                "INSERT INTO inferences VALUES (?,?,?,?,?,?)",
                (
                    iid,
                    inf.content,
                    inf.date,
                    inf.created_by.model_dump_json(),
                    json.dumps(inf.based_on),
                    json.dumps(inf.metadata),
                ),
            )
            self._conn.execute(
                "INSERT INTO fts VALUES (?,?,?,?,?,?)",
                ("inference", f"inference:{iid}", iid, inf.date, inf.created_by.name, inf.content),
            )
            ids.append(iid)
        return ids

    # --- search
    def search(self, req: SearchRequest) -> list[SearchHit]:
        sql = """SELECT type, ref, id, ts, source, bm25(fts) AS score,
                        snippet(fts, 5, '[', ']', ' … ', 16) AS snippet
                 FROM fts WHERE fts MATCH ?"""
        params: list[Any] = [_fts_query(req.query)]
        if req.types:
            sql += f" AND type IN ({','.join('?' * len(req.types))})"
            params.extend(t.value for t in req.types)
        floor = _iso_floor(req.since)
        if floor:
            sql += " AND ts >= ?"
            params.append(floor)
        sql += " ORDER BY score LIMIT ?"
        params.append(req.limit)
        return [
            SearchHit(
                id=r["id"],
                type=MemoryType(r["type"]),
                score=-float(r["score"]),
                snippet=r["snippet"],
                ts=r["ts"],
                source=r["source"],
                ref=r["ref"],
            )
            for r in self._conn.execute(sql, params)
        ]

    # --- paginated reads
    def read_transcripts(self, offset: int, limit: int, include_messages: bool):
        total = self._conn.execute("SELECT COUNT(*) FROM transcripts").fetchone()[0]
        rows = self._conn.execute(
            """SELECT t.*, (SELECT COUNT(*) FROM messages m WHERE m.transcript_id=t.id) AS n
               FROM transcripts t ORDER BY updated_at DESC LIMIT ? OFFSET ?""",
            (limit, offset),
        ).fetchall()
        out = []
        for r in rows:
            msgs = None
            if include_messages:
                msgs = [
                    Message(
                        role=m["role"],
                        content=m["content"],
                        ts=m["ts"],
                        tool_name=m["tool_name"],
                        metadata=json.loads(m["metadata"]),
                    )
                    for m in self._conn.execute(
                        "SELECT * FROM messages WHERE transcript_id=? ORDER BY idx", (r["id"],)
                    )
                ]
            out.append(
                TranscriptRecord(
                    id=r["id"],
                    source=r["source"],
                    started_at=r["started_at"],
                    title=r["title"],
                    partial=bool(r["partial"]),
                    message_count=r["n"],
                    metadata=json.loads(r["metadata"]),
                    messages=msgs,
                )
            )
        return out, total

    def read_inferences(self, offset: int, limit: int):
        total = self._conn.execute("SELECT COUNT(*) FROM inferences").fetchone()[0]
        rows = self._conn.execute(
            "SELECT * FROM inferences ORDER BY date DESC LIMIT ? OFFSET ?", (limit, offset)
        ).fetchall()
        return [
            InferenceRecord(
                id=r["id"],
                content=r["content"],
                date=r["date"],
                created_by=json.loads(r["created_by"]),
                based_on=json.loads(r["based_on"]),
                metadata=json.loads(r["metadata"]),
            )
            for r in rows
        ], total

    # --- delete
    def delete(self, type_: MemoryType, id_: str) -> bool:
        table = {"file": "files", "transcript": "transcripts", "inference": "inferences"}[
            type_.value
        ]
        cur = self._conn.execute(f"DELETE FROM {table} WHERE id=?", (id_,))
        if type_ == MemoryType.transcript:
            self._conn.execute("DELETE FROM messages WHERE transcript_id=?", (id_,))
        self._conn.execute("DELETE FROM fts WHERE type=? AND id=?", (type_.value, id_))
        return cur.rowcount > 0

    def get_file(self, id_: str) -> FileRecord | None:
        r = self._conn.execute("SELECT * FROM files WHERE id=?", (id_,)).fetchone()
        if not r:
            return None
        return FileRecord(
            id=r["id"],
            name=r["name"],
            mime=r["mime"],
            content=r["content"],
            uploaded_at=r["uploaded_at"],
            metadata=json.loads(r["metadata"]),
        )


# ============================================================== ACP transcript index


def _epoch_to_iso(ts: int | None) -> str | None:
    if not ts:
        return None
    return datetime.fromtimestamp(int(ts), tz=UTC).isoformat(timespec="seconds")


class ACPIndexStore:
    """Read-only FMP view over prototypes/acp_memory_server's SQLite index.

    Sessions become transcripts (id = "<agent_id>/<session_id>"), turns become messages,
    and search goes through the index's existing turns_fts table.
    """

    memory_types: ClassVar[list[MemoryType]] = [MemoryType.transcript]
    unsupported = frozenset(
        {"upload_files", "upload_transcript", "upload_inferences", "delete", "read_inferences"}
    )

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path).expanduser()
        if not self.path.exists():
            raise FileNotFoundError(f"ACP index not found: {self.path}")
        self._conn = sqlite3.connect(f"file:{self.path}?mode=ro", uri=True, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row

    def search(self, req: SearchRequest) -> list[SearchHit]:
        if req.types and MemoryType.transcript not in req.types:
            return []
        sql = """SELECT t.agent_id, t.session_id, t.turn_index, t.role, t.ts, s.title,
                        bm25(turns_fts) AS score,
                        snippet(turns_fts, 0, '[', ']', ' … ', 16) AS snippet
                 FROM turns_fts JOIN turns t ON t.rowid = turns_fts.rowid
                 LEFT JOIN sessions s ON s.agent_id=t.agent_id AND s.session_id=t.session_id
                 WHERE turns_fts MATCH ?"""
        params: list[Any] = [_fts_query(req.query)]
        floor = _iso_floor(req.since)
        if floor:
            sql += " AND t.ts >= ?"
            params.append(int(datetime.fromisoformat(floor).timestamp()))
        sql += " ORDER BY score LIMIT ?"
        params.append(req.limit)
        hits = []
        for r in self._conn.execute(sql, params):
            tid = f"{r['agent_id']}/{r['session_id']}"
            hits.append(
                SearchHit(
                    id=tid,
                    type=MemoryType.transcript,
                    score=-float(r["score"]),
                    snippet=f"{r['role']}: {r['snippet']}",
                    ts=_epoch_to_iso(r["ts"]),
                    source=r["agent_id"],
                    ref=f"transcript:{tid}#{r['turn_index']}",
                )
            )
        return hits

    def read_transcripts(self, offset: int, limit: int, include_messages: bool):
        total = self._conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
        rows = self._conn.execute(
            """SELECT * FROM sessions ORDER BY COALESCE(last_turn_at, started_at, 0) DESC
               LIMIT ? OFFSET ?""",
            (limit, offset),
        ).fetchall()
        out = []
        for r in rows:
            tid = f"{r['agent_id']}/{r['session_id']}"
            msgs = None
            if include_messages:
                msgs = [
                    Message(
                        role=_norm_role(m["role"]),
                        content=m["content_text"] or "",
                        ts=_epoch_to_iso(m["ts"]),
                        tool_name=m["tool_name"],
                    )
                    for m in self._conn.execute(
                        """SELECT role, content_text, tool_name, ts FROM turns
                           WHERE agent_id=? AND session_id=? ORDER BY turn_index""",
                        (r["agent_id"], r["session_id"]),
                    )
                ]
            out.append(
                TranscriptRecord(
                    id=tid,
                    source=r["agent_id"],
                    started_at=_epoch_to_iso(r["started_at"]),
                    title=r["title"],
                    partial=False,
                    message_count=int(r["turn_count"] or 0),
                    metadata={"cwd": r["cwd"]},
                    messages=msgs,
                )
            )
        return out, total


def _norm_role(role: str) -> str:
    r = (role or "").lower()
    if r in ("user", "human"):
        return "user"
    if r in ("assistant", "ai", "agent"):
        return "assistant"
    if r in ("tool", "tool_result", "function"):
        return "tool"
    return "system"
