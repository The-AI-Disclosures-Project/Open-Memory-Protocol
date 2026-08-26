"""Shared helpers for filesystem scanners.

Each agent's parser produces `ScanResult` records that the poller funnels into
the same Index used by the ACP backend. Helpers here cover the conversions that
recur across agents: ISO-8601 → epoch, content-block flattening, mtime
watermark lookup, etc."""

from __future__ import annotations

import json
import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from acp_memory_server.index import Index
from acp_memory_server.models import IndexedTurn, SessionRecord

log = logging.getLogger(__name__)


@dataclass
class ScanResult:
    record: SessionRecord
    turns: list[IndexedTurn]
    raw_meta: str
    is_update: bool   # False for first index, True for re-index of an existing session


def iso_to_epoch(s: str | None) -> int | None:
    if not s:
        return None
    try:
        s2 = s.replace("Z", "+00:00")
        dt = datetime.fromisoformat(s2)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp())
    except ValueError:
        return None


def safe_json(v: Any) -> str | None:
    if v is None:
        return None
    try:
        return json.dumps(v, default=str)
    except Exception:  # noqa: BLE001
        return None


def content_to_text(content: Any) -> str:
    """Squash an arbitrary content value (Anthropic-shaped or plain) into searchable text.

    Recognizes the standard content-block types most agents use: text, image, tool_use,
    tool_result, reasoning/thinking, input_text/output_text. Anything else gets a
    JSON-stringified fallback truncated at 2000 chars."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                t = item.get("type")
                if t in ("text", "input_text", "output_text") and isinstance(item.get("text"), str):
                    parts.append(item["text"])
                elif t == "image":
                    parts.append("<image>")
                elif t == "tool_use":
                    parts.append(f"<tool {item.get('name', '')}>")
                elif t == "tool_result":
                    parts.append(content_to_text(item.get("content")))
                elif t in ("thinking", "reasoning") and isinstance(item.get("thinking") or item.get("text"), str):
                    parts.append(item.get("thinking") or item.get("text") or "")
                elif isinstance(item.get("text"), str):
                    parts.append(item["text"])
            elif isinstance(item, str):
                parts.append(item)
        return " ".join(p for p in parts if p)
    if isinstance(content, dict):
        if isinstance(content.get("text"), str):
            return content["text"]
        return json.dumps(content, default=str)[:2000]
    return str(content)[:2000]


def existing_meta(idx: Index, agent_id: str, session_id: str) -> dict[str, Any] | None:
    """Look up the previously stored raw_meta_json for a session, parsed as a dict."""
    conn = sqlite3.connect(idx.path)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT raw_meta_json FROM sessions WHERE agent_id=? AND session_id=?",
            (agent_id, session_id),
        ).fetchone()
    finally:
        conn.close()
    if row is None or not row["raw_meta_json"]:
        return None
    try:
        meta = json.loads(row["raw_meta_json"])
        return meta if isinstance(meta, dict) else None
    except json.JSONDecodeError:
        return None


def existing_mtime(idx: Index, agent_id: str, session_id: str) -> int | None:
    """Convenience wrapper: pull the previously stored `source_mtime` from raw_meta."""
    meta = existing_meta(idx, agent_id, session_id)
    if meta is None:
        return None
    m = meta.get("source_mtime")
    try:
        return int(m) if m is not None else None
    except (ValueError, TypeError):
        return None


def existing_watermark_field(idx: Index, agent_id: str, session_id: str, field: str) -> int | None:
    """Pull a custom watermark field from raw_meta (e.g. `last_updated_ms`)."""
    meta = existing_meta(idx, agent_id, session_id)
    if meta is None:
        return None
    v = meta.get(field)
    try:
        return int(v) if v is not None else None
    except (ValueError, TypeError):
        return None
