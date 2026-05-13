"""Cursor (`~/Library/Application Support/Cursor/User/globalStorage/state.vscdb`, SQLite).

VS Code-style state.vscdb with two tables:
  - `ItemTable`: kv blobs keyed by string. We read `composer.composerHeaders`, which is
    `{"allComposers": [{composerId, name, workspaceIdentifier:{uri:{fsPath}}, createdAt,
    lastUpdatedAt, isArchived, ...}, ...]}` — one entry per Composer/Agent conversation.
  - `cursorDiskKV`: kv blobs keyed by namespaced keys:
      `composerData:<composerId>` → conversation index: `{fullConversationHeadersOnly: [{bubbleId, type}], ...}`
      `bubbleId:<composerId>:<bubbleId>` → per-message: `{type: 1|2, text, richText, toolResults, allThinkingBlocks, createdAt, ...}`
      `messageRequestContext:<composerId>:<bubbleId>` → request context (we ignore)

Type code: 1 = user, 2 = assistant.

Per-composer incremental: we use composerHeaders.lastUpdatedAt as the watermark stored as
`cursor_last_updated_ms` in raw_meta. We re-read the conversation when the header bumps."""

from __future__ import annotations

import json
import logging
import sqlite3
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from acp_memory_server.index import Index
from acp_memory_server.models import IndexedTurn, SessionRecord

from ._common import ScanResult, content_to_text, existing_watermark_field, iso_to_epoch

log = logging.getLogger(__name__)


def candidate_dbs() -> list[Path]:
    """Return all known Cursor variants' state.vscdb paths that exist on disk."""
    base = Path.home() / "Library" / "Application Support"
    candidates = [
        base / "Cursor" / "User" / "globalStorage" / "state.vscdb",
        base / "Cursor Nightly" / "User" / "globalStorage" / "state.vscdb",
    ]
    return [p for p in candidates if p.is_file()]


def available() -> bool:
    return bool(candidate_dbs())


def scan(idx: Index, agent_id: str) -> Iterator[ScanResult]:
    for db in candidate_dbs():
        try:
            yield from _scan_db(idx, agent_id, db)
        except Exception:  # noqa: BLE001
            log.exception("cursor: scan failed for %s", db)


def _scan_db(idx: Index, agent_id: str, db: Path) -> Iterator[ScanResult]:
    try:
        conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
    except sqlite3.OperationalError:
        log.warning("cursor: could not open %s read-only", db)
        return

    try:
        # composer.composerHeaders is the "active" composer list — only ~16 entries on a
        # typical install. The full set of composers lives in cursorDiskKV under
        # `composerData:*` keys; Cursor doesn't delete archived/old composers from there.
        # We union both so we capture historical conversations the UI no longer shows.
        headers_by_id: dict[str, dict[str, Any]] = {}
        headers_row = conn.execute(
            "SELECT value FROM ItemTable WHERE key='composer.composerHeaders'"
        ).fetchone()
        if headers_row:
            try:
                headers = json.loads(headers_row["value"])
                for h in (headers.get("allComposers") if isinstance(headers, dict) else None) or []:
                    if isinstance(h, dict) and isinstance(h.get("composerId"), str):
                        headers_by_id[h["composerId"]] = h
            except (TypeError, json.JSONDecodeError):
                pass

        all_ids: list[str] = []
        for row in conn.execute("SELECT key FROM cursorDiskKV WHERE key LIKE 'composerData:%'"):
            cid = row["key"].split(":", 1)[1] if ":" in row["key"] else None
            if cid:
                all_ids.append(cid)

        for cid in all_ids:
            try:
                yield from _scan_composer(idx, agent_id, conn, cid, headers_by_id.get(cid))
            except Exception:  # noqa: BLE001
                log.exception("cursor: composer %s failed", cid)
    finally:
        conn.close()


def _scan_composer(
    idx: Index,
    agent_id: str,
    conn: sqlite3.Connection,
    cid: str,
    header: dict[str, Any] | None,
) -> Iterator[ScanResult]:
    composer_row = conn.execute(
        "SELECT value FROM cursorDiskKV WHERE key=?", (f"composerData:{cid}",)
    ).fetchone()
    if not composer_row or not composer_row["value"]:
        return
    try:
        composer = json.loads(composer_row["value"])
    except (TypeError, json.JSONDecodeError):
        return
    bubble_hdrs = composer.get("fullConversationHeadersOnly") or []
    if not isinstance(bubble_hdrs, list) or not bubble_hdrs:
        return

    # Pick the freshest lastUpdatedAt available (composerData often has it; header may be stale).
    last_updated_ms = _coerce_int(
        (header or {}).get("lastUpdatedAt") or composer.get("lastUpdatedAt"),
    )

    prev_ms = existing_watermark_field(idx, agent_id, cid, "cursor_last_updated_ms") or 0
    if prev_ms and last_updated_ms and prev_ms >= last_updated_ms:
        return

    cwd = _workspace_path(header) if header else None
    if cwd is None:
        # Some orphan composers carry workspace info inside their composerData / bubbles.
        cwd = _workspace_path(composer) or _cwd_from_bubbles(conn, cid, bubble_hdrs)
    title = (header or {}).get("name") or composer.get("name") or composer.get("subtitle") or None

    turns: list[IndexedTurn] = []
    started_ts: int | None = None
    last_ts: int | None = None
    for bh in bubble_hdrs:
        if not isinstance(bh, dict):
            continue
        bid = bh.get("bubbleId")
        if not isinstance(bid, str):
            continue
        bubble_row = conn.execute(
            "SELECT value FROM cursorDiskKV WHERE key=?", (f"bubbleId:{cid}:{bid}",)
        ).fetchone()
        if not bubble_row or not bubble_row["value"]:
            continue
        try:
            bubble = json.loads(bubble_row["value"])
        except (TypeError, json.JSONDecodeError):
            continue

        btype = bubble.get("type")  # 1 = user, 2 = assistant
        text = bubble.get("text") or ""
        if not text:
            # Some bubble shapes carry text inside richText.children.text — best-effort flatten.
            text = _extract_rich_text(bubble.get("richText"))
        thinking_blocks = bubble.get("allThinkingBlocks") or []
        tool_results = bubble.get("toolResults") or []

        ts = iso_to_epoch(bubble.get("createdAt")) or 0
        if ts:
            started_ts = started_ts if started_ts is not None else ts
            last_ts = ts

        if btype == 1 and text:
            turns.append(IndexedTurn(
                agent_id=agent_id, session_id=cid, turn_index=len(turns),
                role="user", content_text=text, ts=ts,
            ))
        elif btype == 2:
            if isinstance(thinking_blocks, list):
                for tb in thinking_blocks:
                    tb_text = tb.get("text") if isinstance(tb, dict) else None
                    if isinstance(tb_text, str) and tb_text:
                        turns.append(IndexedTurn(
                            agent_id=agent_id, session_id=cid, turn_index=len(turns),
                            role="thought", content_text=tb_text, ts=ts,
                        ))
            if text:
                turns.append(IndexedTurn(
                    agent_id=agent_id, session_id=cid, turn_index=len(turns),
                    role="agent", content_text=text, ts=ts,
                ))
            if isinstance(tool_results, list):
                for tr in tool_results:
                    if not isinstance(tr, dict):
                        continue
                    name = tr.get("toolName") or tr.get("name") or "tool"
                    args = tr.get("input") or tr.get("args")
                    try:
                        args_json = json.dumps(args, default=str) if args is not None else None
                    except Exception:  # noqa: BLE001
                        args_json = None
                    output = tr.get("result") or tr.get("output") or tr.get("content")
                    output_text = content_to_text(output) if output is not None else ""
                    summary = f"{name} {args_json or ''}".strip()
                    turns.append(IndexedTurn(
                        agent_id=agent_id, session_id=cid, turn_index=len(turns),
                        role="tool",
                        content_text=(summary + ("\n" + output_text if output_text else "")).strip(),
                        tool_name=name, tool_args_json=args_json, ts=ts,
                    ))

    if not turns:
        return

    record = SessionRecord(
        agent_id=agent_id, session_id=cid,
        cwd=cwd, title=title,
        started_at=started_ts or _ms_to_s((header or {}).get("createdAt") or composer.get("createdAt")),
        last_turn_at=last_ts or _ms_to_s(last_updated_ms),
        turn_count=len(turns),
    )
    raw_meta = json.dumps(
        {
            "source": "cursor.state.vscdb",
            "cursor_last_updated_ms": last_updated_ms,
            "title": title,
            "workspaceIdentifier": (header or {}).get("workspaceIdentifier"),
            "orphan": header is None,
        },
        default=str,
    )
    yield ScanResult(record=record, turns=turns, raw_meta=raw_meta, is_update=prev_ms > 0)


def _workspace_path(obj: dict[str, Any]) -> str | None:
    """Pull a workspace path out of either a header dict or a composerData dict."""
    if not isinstance(obj, dict):
        return None
    wi = obj.get("workspaceIdentifier")
    if isinstance(wi, dict):
        uri = wi.get("uri")
        if isinstance(uri, dict):
            p = uri.get("fsPath") or uri.get("path")
            if isinstance(p, str) and p:
                return p
        if isinstance(uri, str) and uri.startswith("file://"):
            return uri[len("file://"):]
    wuris = obj.get("workspaceUris")
    if isinstance(wuris, list) and wuris:
        first = wuris[0]
        if isinstance(first, str):
            return first[len("file://"):] if first.startswith("file://") else first
        if isinstance(first, dict):
            p = first.get("fsPath") or first.get("path")
            if isinstance(p, str) and p:
                return p
    return None


def _cwd_from_bubbles(conn: sqlite3.Connection, cid: str, bubble_hdrs: list) -> str | None:
    """For orphan composers, the workspace can sometimes be recovered from any bubble's
    `workspaceUris` array. Probe up to the first 5 bubbles."""
    for bh in bubble_hdrs[:5]:
        if not isinstance(bh, dict):
            continue
        bid = bh.get("bubbleId")
        if not isinstance(bid, str):
            continue
        row = conn.execute(
            "SELECT value FROM cursorDiskKV WHERE key=?", (f"bubbleId:{cid}:{bid}",)
        ).fetchone()
        if not row or not row["value"]:
            continue
        try:
            b = json.loads(row["value"])
        except (TypeError, json.JSONDecodeError):
            continue
        path = _workspace_path(b)
        if path:
            return path
    return None


def _coerce_int(v: Any) -> int:
    try:
        return int(v) if v is not None else 0
    except (TypeError, ValueError):
        return 0


def _extract_rich_text(rich: Any) -> str:
    """Walk a Lexical-style rich text tree and concatenate any `text` leaves."""
    pieces: list[str] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            t = node.get("text")
            if isinstance(t, str):
                pieces.append(t)
            for k in ("children", "root"):
                v = node.get(k)
                if v is not None:
                    walk(v)
        elif isinstance(node, list):
            for el in node:
                walk(el)

    if isinstance(rich, str):
        try:
            rich = json.loads(rich)
        except json.JSONDecodeError:
            return ""
    walk(rich)
    return " ".join(p for p in pieces if p)


def _ms_to_s(v: Any) -> int | None:
    try:
        ms = int(v)
    except (TypeError, ValueError):
        return None
    return ms // 1000 if ms > 0 else None
