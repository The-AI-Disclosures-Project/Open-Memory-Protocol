"""Filesystem backends: read agents' on-disk session stores directly.

Each agent's transcript files have an idiosyncratic shape, so we have one
parser per supported agent. Backends are stateless; they yield session
records + turn rows and the poller funnels them into the same Index used by
the ACP backend.

Incremental scanning uses each session file's mtime, stashed in
`sessions.raw_meta_json` as `{"source_mtime": <epoch>}`. On a re-scan, files
whose mtime hasn't moved are skipped without parsing."""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
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


def _iso_to_epoch(s: str | None) -> int | None:
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


def _safe_json(v: Any) -> str | None:
    if v is None:
        return None
    try:
        return json.dumps(v, default=str)
    except Exception:  # noqa: BLE001
        return None


def _content_to_text(content: Any) -> str:
    """Squash an arbitrary Claude/OpenAI-shaped content value into searchable text."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                if item.get("type") == "text" and isinstance(item.get("text"), str):
                    parts.append(item["text"])
                elif item.get("type") == "input_text" and isinstance(item.get("text"), str):
                    parts.append(item["text"])
                elif item.get("type") == "output_text" and isinstance(item.get("text"), str):
                    parts.append(item["text"])
                elif item.get("type") == "image":
                    parts.append("<image>")
                elif item.get("type") == "tool_use":
                    parts.append(f"<tool {item.get('name','')}>")
                elif item.get("type") == "tool_result":
                    sub = item.get("content")
                    parts.append(_content_to_text(sub))
                else:
                    parts.append(str(item.get("text", "")))
            elif isinstance(item, str):
                parts.append(item)
        return " ".join(p for p in parts if p)
    if isinstance(content, dict):
        if "text" in content:
            return str(content["text"])
        return json.dumps(content, default=str)[:2000]
    return str(content)[:2000]


# ----------------- Claude Code -----------------


def _claude_code_root() -> Path:
    return Path.home() / ".claude" / "projects"


def scan_claude_code(idx: Index, agent_id: str) -> Iterator[ScanResult]:
    root = _claude_code_root()
    if not root.is_dir():
        return

    for project_dir in root.iterdir():
        if not project_dir.is_dir():
            continue
        for session_file in project_dir.rglob("*.jsonl"):
            if session_file.is_dir():
                continue
            try:
                result = _scan_claude_code_file(idx, agent_id, session_file)
            except Exception:  # noqa: BLE001
                log.exception("claude-code parse failed: %s", session_file)
                continue
            if result is not None:
                yield result


def _scan_claude_code_file(idx: Index, agent_id: str, path: Path) -> ScanResult | None:
    mtime = int(path.stat().st_mtime)

    # session_id = filename stem (UUID)
    session_id = path.stem

    existing = idx.session_watermark(agent_id, session_id)
    is_update = existing is not None
    # mtime-based skip: only read raw_meta if we have an existing record.
    if is_update:
        prior_mtime = _existing_mtime(idx, agent_id, session_id)
        if prior_mtime is not None and prior_mtime >= mtime:
            return None  # unchanged

    cwd: str | None = None
    title: str | None = None
    started_at: int | None = None
    last_turn_at: int | None = None
    turns: list[IndexedTurn] = []
    next_idx = 0

    with path.open() as fh:
        for raw in fh:
            raw = raw.strip()
            if not raw:
                continue
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError:
                continue

            if cwd is None and isinstance(obj.get("cwd"), str):
                cwd = obj["cwd"]
            if title is None and isinstance(obj.get("aiTitle"), str):
                title = obj["aiTitle"]

            ts = _iso_to_epoch(obj.get("timestamp"))
            if ts is not None:
                if started_at is None:
                    started_at = ts
                last_turn_at = ts

            t = obj.get("type")

            if t == "user" and isinstance(obj.get("message"), dict):
                msg = obj["message"]
                content = _content_to_text(msg.get("content"))
                if content:
                    turns.append(
                        IndexedTurn(
                            agent_id=agent_id,
                            session_id=session_id,
                            turn_index=next_idx,
                            role="user",
                            content_text=content,
                            ts=ts or 0,
                            raw_blob=raw,
                        )
                    )
                    next_idx += 1
            elif t == "assistant" and isinstance(obj.get("message"), dict):
                msg = obj["message"]
                content = _content_to_text(msg.get("content"))
                if content:
                    turns.append(
                        IndexedTurn(
                            agent_id=agent_id,
                            session_id=session_id,
                            turn_index=next_idx,
                            role="agent",
                            content_text=content,
                            ts=ts or 0,
                            raw_blob=raw,
                        )
                    )
                    next_idx += 1
                # Also pull tool_use blocks out as separate "tool" turns so they're searchable
                # by tool name and arguments.
                msg_content = msg.get("content")
                if isinstance(msg_content, list):
                    for item in msg_content:
                        if isinstance(item, dict) and item.get("type") == "tool_use":
                            tool_name = item.get("name") or "tool"
                            args = item.get("input")
                            try:
                                args_json = json.dumps(args, default=str) if args is not None else None
                            except Exception:  # noqa: BLE001
                                args_json = None
                            turns.append(
                                IndexedTurn(
                                    agent_id=agent_id,
                                    session_id=session_id,
                                    turn_index=next_idx,
                                    role="tool",
                                    content_text=f"{tool_name} {args_json or ''}".strip(),
                                    tool_name=tool_name,
                                    tool_args_json=args_json,
                                    ts=ts or 0,
                                )
                            )
                            next_idx += 1
            # type=tool_use / tool_result top-level entries (some claude versions)
            elif t == "tool_use":
                tool_name = obj.get("name") or "tool"
                args = obj.get("input")
                try:
                    args_json = json.dumps(args, default=str) if args is not None else None
                except Exception:  # noqa: BLE001
                    args_json = None
                turns.append(
                    IndexedTurn(
                        agent_id=agent_id,
                        session_id=session_id,
                        turn_index=next_idx,
                        role="tool",
                        content_text=f"{tool_name} {args_json or ''}".strip(),
                        tool_name=tool_name,
                        tool_args_json=args_json,
                        ts=ts or 0,
                    )
                )
                next_idx += 1
            elif t == "tool_result":
                content = _content_to_text(obj.get("content"))
                if content:
                    turns.append(
                        IndexedTurn(
                            agent_id=agent_id,
                            session_id=session_id,
                            turn_index=next_idx,
                            role="tool",
                            content_text=content,
                            ts=ts or 0,
                        )
                    )
                    next_idx += 1
            # ignore queue-operation, attachment, ai-title, system meta lines

    if not turns:
        return None  # nothing to index

    if is_update and next_idx == existing[0]:
        # Same number of turns as before — likely unchanged content with bumped mtime.
        # Skip rewriting to avoid churn.
        return None

    record = SessionRecord(
        agent_id=agent_id,
        session_id=session_id,
        cwd=cwd,
        title=title,
        started_at=started_at,
        last_turn_at=last_turn_at,
        turn_count=next_idx,
    )
    raw_meta = json.dumps(
        {"source_path": str(path), "source_mtime": mtime, "title": title},
        default=str,
    )
    return ScanResult(record=record, turns=turns, raw_meta=raw_meta, is_update=is_update)


# ----------------- Codex -----------------


def _codex_root() -> Path:
    return Path.home() / ".codex" / "sessions"


def scan_codex(idx: Index, agent_id: str) -> Iterator[ScanResult]:
    root = _codex_root()
    if not root.is_dir():
        return

    for session_file in root.rglob("*.jsonl"):
        if session_file.is_dir():
            continue
        try:
            result = _scan_codex_file(idx, agent_id, session_file)
        except Exception:  # noqa: BLE001
            log.exception("codex parse failed: %s", session_file)
            continue
        if result is not None:
            yield result


def _extract_codex_session_id(path: Path, session_meta: dict[str, Any] | None) -> str:
    if session_meta and isinstance(session_meta.get("id"), str):
        return session_meta["id"]
    # Fallback: parse from filename (e.g., rollout-<datetime>-<uuid>.jsonl)
    stem = path.stem
    parts = stem.split("-")
    if len(parts) >= 5:
        candidate = "-".join(parts[-5:])
        if len(candidate) == 36:
            return candidate
    return stem


def _scan_codex_file(idx: Index, agent_id: str, path: Path) -> ScanResult | None:
    """Codex JSONL shape:
        {"timestamp": "...", "type": "<wrapper>", "payload": {...}}
    Wrapper types we care about:
        - session_meta:   payload has id, cwd, timestamp, instructions
        - response_item:  payload.type in {message, function_call, function_call_output, reasoning, ghost_snapshot, ...}
        - event_msg:      payload.type in {user_message, agent_reasoning, ...}
    Outer `timestamp` is the per-event time; session start time comes from session_meta."""
    mtime = int(path.stat().st_mtime)

    cwd: str | None = None
    started_at: int | None = None
    last_turn_at: int | None = None
    turns: list[IndexedTurn] = []
    next_idx = 0
    session_meta: dict[str, Any] | None = None

    with path.open() as fh:
        for raw in fh:
            raw = raw.strip()
            if not raw:
                continue
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError:
                continue

            outer = obj.get("type")
            payload = obj.get("payload") if isinstance(obj.get("payload"), dict) else None
            ts = _iso_to_epoch(obj.get("timestamp"))
            if ts is not None:
                last_turn_at = ts

            if outer == "session_meta" and payload is not None:
                session_meta = payload
                if isinstance(payload.get("cwd"), str) and cwd is None:
                    cwd = payload["cwd"]
                if started_at is None:
                    started_at = _iso_to_epoch(payload.get("timestamp")) or ts
                continue

            if outer == "turn_context" and payload is not None:
                if cwd is None and isinstance(payload.get("cwd"), str):
                    cwd = payload["cwd"]
                continue

            if payload is None:
                continue

            inner = payload.get("type")

            if outer == "response_item" and inner == "message":
                role_raw = payload.get("role") or "assistant"
                role = "user" if role_raw == "user" else "agent"
                content = _content_to_text(payload.get("content"))
                if content:
                    turns.append(
                        IndexedTurn(
                            agent_id=agent_id,
                            session_id="__placeholder__",
                            turn_index=next_idx,
                            role=role,
                            content_text=content,
                            ts=ts or 0,
                        )
                    )
                    next_idx += 1
            elif outer == "response_item" and inner == "function_call":
                name = payload.get("name") or "tool"
                args = payload.get("arguments")
                args_json = args if isinstance(args, str) else _safe_json(args)
                turns.append(
                    IndexedTurn(
                        agent_id=agent_id,
                        session_id="__placeholder__",
                        turn_index=next_idx,
                        role="tool",
                        content_text=f"{name} {args_json or ''}".strip(),
                        tool_name=name,
                        tool_args_json=args_json,
                        ts=ts or 0,
                    )
                )
                next_idx += 1
            elif outer == "response_item" and inner == "function_call_output":
                output = payload.get("output")
                content = _content_to_text(output) if output is not None else _content_to_text(payload.get("content"))
                if content:
                    turns.append(
                        IndexedTurn(
                            agent_id=agent_id,
                            session_id="__placeholder__",
                            turn_index=next_idx,
                            role="tool",
                            content_text=content,
                            ts=ts or 0,
                        )
                    )
                    next_idx += 1
            elif outer == "response_item" and inner == "reasoning":
                summary = payload.get("summary")
                content = ""
                if isinstance(summary, list):
                    content = " ".join(s.get("text", "") for s in summary if isinstance(s, dict))
                content = content or _content_to_text(payload.get("content"))
                if content:
                    turns.append(
                        IndexedTurn(
                            agent_id=agent_id,
                            session_id="__placeholder__",
                            turn_index=next_idx,
                            role="thought",
                            content_text=content,
                            ts=ts or 0,
                        )
                    )
                    next_idx += 1
            elif outer == "event_msg" and inner == "user_message":
                # event_msg/user_message is the user turn before model expansion
                content = payload.get("message")
                content = content if isinstance(content, str) else _content_to_text(content)
                if content:
                    turns.append(
                        IndexedTurn(
                            agent_id=agent_id,
                            session_id="__placeholder__",
                            turn_index=next_idx,
                            role="user",
                            content_text=content,
                            ts=ts or 0,
                        )
                    )
                    next_idx += 1
            elif outer == "event_msg" and inner == "agent_reasoning":
                text = payload.get("text")
                if isinstance(text, str) and text:
                    turns.append(
                        IndexedTurn(
                            agent_id=agent_id,
                            session_id="__placeholder__",
                            turn_index=next_idx,
                            role="thought",
                            content_text=text,
                            ts=ts or 0,
                        )
                    )
                    next_idx += 1

    session_id = _extract_codex_session_id(path, session_meta)
    if not turns:
        return None

    # Now that we have the real session_id, fix up the placeholders.
    for t in turns:
        t.session_id = session_id

    existing = idx.session_watermark(agent_id, session_id)
    is_update = existing is not None
    if is_update:
        prior_mtime = _existing_mtime(idx, agent_id, session_id)
        if prior_mtime is not None and prior_mtime >= mtime:
            return None
        if next_idx == existing[0]:
            return None

    record = SessionRecord(
        agent_id=agent_id,
        session_id=session_id,
        cwd=cwd,
        title=None,
        started_at=started_at,
        last_turn_at=last_turn_at,
        turn_count=next_idx,
    )
    raw_meta = json.dumps({"source_path": str(path), "source_mtime": mtime}, default=str)
    return ScanResult(record=record, turns=turns, raw_meta=raw_meta, is_update=is_update)


# ----------------- mtime watermark helper -----------------


def _existing_mtime(idx: Index, agent_id: str, session_id: str) -> int | None:
    """Look up the previously stored source_mtime for a session, if any."""
    import sqlite3

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
        m = meta.get("source_mtime")
        return int(m) if m is not None else None
    except (json.JSONDecodeError, ValueError, TypeError):
        return None


# ----------------- Backend dispatch -----------------


SCANNERS = {
    "claude-acp": scan_claude_code,
    "claude-code-acp": scan_claude_code,
    "codex-acp": scan_codex,
}


def has_filesystem_backend(agent_id: str) -> bool:
    return agent_id in SCANNERS


def scan(idx: Index, agent_id: str) -> Iterator[ScanResult]:
    fn = SCANNERS.get(agent_id)
    if fn is None:
        raise ValueError(f"no filesystem backend for {agent_id}")
    yield from fn(idx, agent_id)
