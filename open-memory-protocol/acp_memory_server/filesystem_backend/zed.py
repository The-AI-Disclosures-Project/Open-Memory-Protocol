"""Zed assistant / agent panel.

Two SQLite databases under `~/Library/Application Support/Zed/`:
  - `threads/threads.db`            — payload store. `threads(id, summary, updated_at,
                                        data_type, data BLOB, parent_id, folder_paths, ...)`.
                                        `data` is JSON (data_type='json') or Zstd-compressed
                                        JSON (data_type='zstd'); decoded form is a `DbThread`.
  - `db/0-stable/db.sqlite`         — sidebar index. `sidebar_threads(thread_id, title,
                                        updated_at, main_worktree_paths, ...)`.

Linux uses `~/.local/share/zed/` instead.

Legacy: Zed used to write JSON conversations to `~/.config/zed/conversations/*.json`. That
path is dead in current builds — we don't try to parse it.

Zstd decompression requires the `zstandard` package (optional dep). Without it, Zstd rows
are skipped with a one-time warning."""

from __future__ import annotations

import json
import logging
import sqlite3
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from acp_memory_server.index import Index
from acp_memory_server.models import IndexedTurn, SessionRecord

from ._common import ScanResult, content_to_text, existing_watermark_field, iso_to_epoch

log = logging.getLogger(__name__)


def _base_dirs() -> list[Path]:
    out = [Path.home() / "Library" / "Application Support" / "Zed"]
    if sys.platform == "linux":
        out.append(Path.home() / ".local" / "share" / "zed")
    return [p for p in out if p.is_dir()]


def threads_db() -> Path | None:
    for base in _base_dirs():
        p = base / "threads" / "threads.db"
        if p.is_file():
            return p
    return None


def sidebar_db() -> Path | None:
    for base in _base_dirs():
        p = base / "db" / "0-stable" / "db.sqlite"
        if p.is_file():
            return p
    return None


def available() -> bool:
    return threads_db() is not None


def scan(idx: Index, agent_id: str) -> Iterator[ScanResult]:
    tdb = threads_db()
    if tdb is None:
        return

    sidebar = _load_sidebar_metadata(sidebar_db())
    zstd = _maybe_import_zstd()

    try:
        conn = sqlite3.connect(f"file:{tdb}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
    except sqlite3.OperationalError:
        log.warning("zed: could not open %s read-only", tdb)
        return

    try:
        rows = conn.execute(
            "SELECT id, summary, updated_at, data_type, data, parent_id, folder_paths FROM threads"
        ).fetchall()
    finally:
        conn.close()

    for r in rows:
        try:
            result = _scan_row(idx, agent_id, r, sidebar, zstd)
        except Exception:  # noqa: BLE001
            log.exception("zed: row %s parse failed", r["id"])
            continue
        if result is not None:
            yield result


def _scan_row(
    idx: Index,
    agent_id: str,
    row: sqlite3.Row,
    sidebar: dict[str, dict[str, Any]],
    zstd: Any,
) -> ScanResult | None:
    tid = row["id"]
    if not isinstance(tid, str):
        return None
    if row["parent_id"]:
        return None  # skip subagent threads

    updated_at_ts = iso_to_epoch(row["updated_at"]) or 0
    prev_ts = existing_watermark_field(idx, agent_id, tid, "zed_updated_at_ts") or 0
    if prev_ts and prev_ts >= updated_at_ts:
        return None

    payload = _decode_payload(row["data_type"], row["data"], zstd)
    if payload is None:
        return None
    # `DbThread` JSON often wraps the actual content in a versioned envelope.
    # Try common shapes.
    thread = payload
    if isinstance(payload, dict):
        for key in ("thread", "data", "DbThread"):
            inner = payload.get(key)
            if isinstance(inner, dict):
                thread = inner
                break

    turns = list(_extract_turns(thread, agent_id, tid))
    if not turns:
        return None

    side = sidebar.get(tid) or {}
    cwd = _first_path(side.get("main_worktree_paths")) or _first_path(row["folder_paths"]) \
        or _first_path(thread.get("folder_paths") if isinstance(thread, dict) else None)
    title = side.get("title") or side.get("title_override") or row["summary"] or None

    existing = idx.session_watermark(agent_id, tid)
    is_update = existing is not None

    record = SessionRecord(
        agent_id=agent_id, session_id=tid,
        cwd=cwd, title=title,
        started_at=iso_to_epoch(side.get("created_at")),
        last_turn_at=updated_at_ts or None,
        turn_count=len(turns),
    )
    raw_meta = json.dumps(
        {
            "source": "zed.threads.db",
            "zed_updated_at_ts": updated_at_ts,
            "title": title,
        },
        default=str,
    )
    return ScanResult(record=record, turns=turns, raw_meta=raw_meta, is_update=is_update)


def _extract_turns(thread: Any, agent_id: str, sid: str) -> Iterator[IndexedTurn]:
    """DbThread shape varies by Zed version. We probe `messages` (list of dicts with
    `role` and either `text`, `parts`, or `content`) and fall back to walking any list of
    objects with a `role` field."""
    if not isinstance(thread, dict):
        return
    messages = thread.get("messages")
    if not isinstance(messages, list):
        for v in thread.values():
            if isinstance(v, list) and v and isinstance(v[0], dict) and "role" in v[0]:
                messages = v
                break
    if not isinstance(messages, list):
        return

    idx = 0
    for m in messages:
        if not isinstance(m, dict):
            continue
        role_raw = (m.get("role") or "").lower()
        if role_raw == "user":
            role = "user"
        elif role_raw in ("assistant", "agent"):
            role = "agent"
        elif role_raw == "system":
            role = "system"
        else:
            continue

        text = ""
        parts = m.get("parts") if isinstance(m.get("parts"), list) else None
        if parts:
            text = content_to_text(parts)
        else:
            text = content_to_text(m.get("content") or m.get("text"))
        if not text:
            continue

        ts = iso_to_epoch(m.get("timestamp") or m.get("created_at")) or 0
        yield IndexedTurn(
            agent_id=agent_id, session_id=sid, turn_index=idx,
            role=role, content_text=text, ts=ts,
        )
        idx += 1


def _decode_payload(data_type: str | None, data: Any, zstd: Any) -> Any:
    if data is None:
        return None
    if data_type == "json" or data_type is None:
        if isinstance(data, (bytes, bytearray)):
            data = data.decode("utf-8", errors="replace")
        try:
            return json.loads(data)
        except (json.JSONDecodeError, TypeError):
            return None
    if data_type == "zstd":
        if zstd is None:
            return None
        try:
            blob = bytes(data) if not isinstance(data, (bytes, bytearray)) else data
            raw = zstd.ZstdDecompressor().decompress(blob)
            return json.loads(raw.decode("utf-8", errors="replace"))
        except Exception:  # noqa: BLE001
            return None
    return None


_zstd_warned = False


def _maybe_import_zstd() -> Any | None:
    global _zstd_warned
    try:
        import zstandard
        return zstandard
    except ImportError:
        if not _zstd_warned:
            log.warning(
                "zed: zstandard not installed; zstd-compressed threads will be skipped. "
                "Run `pip install zstandard` to index them."
            )
            _zstd_warned = True
        return None


def _load_sidebar_metadata(path: Path | None) -> dict[str, dict[str, Any]]:
    if path is None:
        return {}
    try:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
    except sqlite3.OperationalError:
        return {}
    out: dict[str, dict[str, Any]] = {}
    try:
        rows = conn.execute(
            """SELECT thread_id, title, title_override, created_at, updated_at,
                      interacted_at, main_worktree_paths
               FROM sidebar_threads"""
        ).fetchall()
    except sqlite3.OperationalError:
        return {}
    finally:
        conn.close()
    for r in rows:
        tid_raw = r["thread_id"]
        tid = tid_raw if isinstance(tid_raw, str) else (
            tid_raw.decode("utf-8", errors="replace") if isinstance(tid_raw, (bytes, bytearray)) else None
        )
        if not tid:
            continue
        out[tid] = {k: r[k] for k in r.keys()}
    return out


def _first_path(blob: Any) -> str | None:
    if isinstance(blob, str):
        s = blob.strip()
        if not s:
            return None
        if s.startswith("["):
            try:
                arr = json.loads(s)
                if isinstance(arr, list) and arr:
                    return str(arr[0])
            except json.JSONDecodeError:
                pass
        return s
    if isinstance(blob, list) and blob:
        return str(blob[0])
    return None
