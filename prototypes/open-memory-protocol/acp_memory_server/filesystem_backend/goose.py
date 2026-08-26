"""Goose CLI (`~/.local/share/goose/sessions/sessions.db`, SQLite).

Schema:
    sessions(id, name, working_dir, created_at, updated_at, ...)
    messages(session_id, role, content_json, created_timestamp, ...)

`content_json` is a JSON list of content blocks:
    {"type": "text"|"toolRequest"|"toolResponse"|"thinking"|"image"|"systemNotification", ...}

Per-session incremental: we use `messages.MAX(created_timestamp)` as the watermark stored in
`sessions.raw_meta_json` as `goose_last_msg_ts`. If the database's per-session max hasn't
advanced past our watermark, we skip the session."""

from __future__ import annotations

import json
import logging
import sqlite3
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path

from acp_memory_server.index import Index
from acp_memory_server.models import IndexedTurn, SessionRecord

from ._common import ScanResult, existing_watermark_field

log = logging.getLogger(__name__)


def db_path() -> Path:
    return Path.home() / ".local" / "share" / "goose" / "sessions" / "sessions.db"


def available() -> bool:
    return db_path().is_file()


def scan(idx: Index, agent_id: str) -> Iterator[ScanResult]:
    path = db_path()
    if not path.is_file():
        return

    # Open read-only via URI to avoid contending with the live agent on the WAL.
    try:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
    except sqlite3.OperationalError:
        log.warning("goose: could not open %s read-only", path)
        return

    try:
        sessions = conn.execute(
            """SELECT s.id, s.name, s.working_dir, s.created_at, s.updated_at,
                      MAX(m.created_timestamp) AS max_ts, COUNT(m.id) AS n_msgs
               FROM sessions s
               LEFT JOIN messages m ON m.session_id = s.id
               GROUP BY s.id"""
        ).fetchall()

        for s in sessions:
            sid = s["id"]
            max_ts = s["max_ts"] or 0
            if s["n_msgs"] == 0:
                continue

            prev_ts = existing_watermark_field(idx, agent_id, sid, "goose_last_msg_ts") or 0
            if prev_ts and prev_ts >= max_ts:
                continue  # nothing new

            rows = conn.execute(
                """SELECT role, content_json, created_timestamp
                   FROM messages WHERE session_id=? ORDER BY id ASC""",
                (sid,),
            ).fetchall()

            turns: list[IndexedTurn] = []
            for i, m in enumerate(rows):
                for sub in _flatten_content(m["content_json"]):
                    role = _role(m["role"], sub["block_type"])
                    if role is None:
                        continue
                    turns.append(IndexedTurn(
                        agent_id=agent_id, session_id=sid, turn_index=len(turns),
                        role=role,
                        content_text=sub["text"],
                        tool_name=sub.get("tool_name"),
                        tool_args_json=sub.get("tool_args_json"),
                        ts=int(m["created_timestamp"] or 0),
                    ))

            if not turns:
                continue

            record = SessionRecord(
                agent_id=agent_id, session_id=sid,
                cwd=s["working_dir"], title=s["name"] or None,
                started_at=_parse_pg_ts(s["created_at"]),
                last_turn_at=int(max_ts) or _parse_pg_ts(s["updated_at"]),
                turn_count=len(turns),
            )
            raw_meta = json.dumps(
                {
                    "source": str(path),
                    "goose_last_msg_ts": int(max_ts),
                    "title": s["name"],
                },
                default=str,
            )
            yield ScanResult(record=record, turns=turns, raw_meta=raw_meta, is_update=prev_ts > 0)
    finally:
        conn.close()


def _flatten_content(content_json: str | None) -> list[dict]:
    """Turn one row's `content_json` array into one or more flat blocks.

    Each returned dict has `block_type` plus `text` plus optional `tool_name`/`tool_args_json`."""
    if not content_json:
        return []
    try:
        arr = json.loads(content_json)
    except json.JSONDecodeError:
        return []
    if not isinstance(arr, list):
        return []
    out: list[dict] = []
    for el in arr:
        if not isinstance(el, dict):
            continue
        t = el.get("type")
        if t == "text":
            txt = el.get("text")
            if isinstance(txt, str) and txt:
                out.append({"block_type": "text", "text": txt})
        elif t == "thinking":
            txt = el.get("thinking") or el.get("text")
            if isinstance(txt, str) and txt:
                out.append({"block_type": "thinking", "text": txt})
        elif t == "toolRequest":
            tc = el.get("toolCall") or {}
            value = tc.get("value") if isinstance(tc, dict) else {}
            name = (value or {}).get("name") or "tool"
            args = (value or {}).get("arguments")
            try:
                args_json = json.dumps(args, default=str) if args is not None else None
            except Exception:  # noqa: BLE001
                args_json = None
            out.append({
                "block_type": "tool_request",
                "text": f"{name} {args_json or ''}".strip(),
                "tool_name": name,
                "tool_args_json": args_json,
            })
        elif t == "toolResponse":
            tr = el.get("toolResult") or {}
            value = tr.get("value") if isinstance(tr, dict) else tr
            # Flatten nested content arrays inside the result.
            text = ""
            if isinstance(value, dict) and isinstance(value.get("content"), list):
                pieces = []
                for c in value["content"]:
                    if isinstance(c, dict) and isinstance(c.get("text"), str):
                        pieces.append(c["text"])
                text = "\n".join(pieces)
            elif isinstance(value, str):
                text = value
            elif value is not None:
                text = json.dumps(value, default=str)[:2000]
            if text:
                out.append({"block_type": "tool_response", "text": text})
        elif t == "image":
            out.append({"block_type": "image", "text": "<image>"})
        elif t == "systemNotification":
            msg = el.get("msg")
            if isinstance(msg, str) and msg:
                out.append({"block_type": "system", "text": msg})
    return out


def _role(row_role: str, block_type: str) -> str | None:
    if block_type == "thinking":
        return "thought"
    if block_type in ("tool_request", "tool_response"):
        return "tool"
    if block_type == "system":
        return "system"
    if row_role == "user":
        return "user"
    if row_role == "assistant":
        return "agent"
    return None


def _parse_pg_ts(s: str | None) -> int | None:
    """Goose stores timestamps as RFC3339 with nanosecond precision. Strip ns and parse."""
    if not s:
        return None
    s2 = s.replace("Z", "+00:00")
    # Trim nanoseconds (Python's datetime supports microseconds only).
    if "." in s2:
        head, _, rest = s2.partition(".")
        frac, _, tz = rest.partition("+")
        if not tz and "-" in rest[1:]:
            # negative tz offset
            for i in range(1, len(rest)):
                if rest[i] in "+-":
                    frac, tz = rest[:i], rest[i:]
                    break
        s2 = f"{head}.{frac[:6]}+{tz}" if tz else f"{head}.{frac[:6]}"
    try:
        dt = datetime.fromisoformat(s2)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp())
    except ValueError:
        return None
