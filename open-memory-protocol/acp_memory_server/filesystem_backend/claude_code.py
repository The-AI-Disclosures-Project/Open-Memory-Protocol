"""Claude Code (`~/.claude/projects/<dashed-cwd>/<uuid>.jsonl`).

Each `.jsonl` is one session. Each line is one event with `{type, message, timestamp, cwd}`.
Event types we care about: `user`, `assistant`, `tool_use`, `tool_result`."""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from pathlib import Path

from acp_memory_server.index import Index
from acp_memory_server.models import IndexedTurn, SessionRecord

from ._common import ScanResult, content_to_text, existing_mtime, iso_to_epoch

log = logging.getLogger(__name__)


def root() -> Path:
    return Path.home() / ".claude" / "projects"


def available() -> bool:
    return root().is_dir()


def scan(idx: Index, agent_id: str) -> Iterator[ScanResult]:
    base = root()
    if not base.is_dir():
        return

    for project_dir in base.iterdir():
        if not project_dir.is_dir():
            continue
        for session_file in project_dir.rglob("*.jsonl"):
            if session_file.is_dir():
                continue
            try:
                result = _scan_file(idx, agent_id, session_file)
            except Exception:  # noqa: BLE001
                log.exception("claude-code parse failed: %s", session_file)
                continue
            if result is not None:
                yield result


def _scan_file(idx: Index, agent_id: str, path: Path) -> ScanResult | None:
    mtime = int(path.stat().st_mtime)

    session_id = path.stem
    existing = idx.session_watermark(agent_id, session_id)
    is_update = existing is not None
    if is_update:
        prior_mtime = existing_mtime(idx, agent_id, session_id)
        if prior_mtime is not None and prior_mtime >= mtime:
            return None

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

            ts = iso_to_epoch(obj.get("timestamp"))
            if ts is not None:
                if started_at is None:
                    started_at = ts
                last_turn_at = ts

            t = obj.get("type")

            if t == "user" and isinstance(obj.get("message"), dict):
                msg = obj["message"]
                text = content_to_text(msg.get("content"))
                if text:
                    turns.append(IndexedTurn(
                        agent_id=agent_id, session_id=session_id, turn_index=next_idx,
                        role="user", content_text=text, ts=ts or 0, raw_blob=raw,
                    ))
                    next_idx += 1
            elif t == "assistant" and isinstance(obj.get("message"), dict):
                msg = obj["message"]
                text = content_to_text(msg.get("content"))
                if text:
                    turns.append(IndexedTurn(
                        agent_id=agent_id, session_id=session_id, turn_index=next_idx,
                        role="agent", content_text=text, ts=ts or 0, raw_blob=raw,
                    ))
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
                            turns.append(IndexedTurn(
                                agent_id=agent_id, session_id=session_id, turn_index=next_idx,
                                role="tool",
                                content_text=f"{tool_name} {args_json or ''}".strip(),
                                tool_name=tool_name, tool_args_json=args_json, ts=ts or 0,
                            ))
                            next_idx += 1
            elif t == "tool_use":
                tool_name = obj.get("name") or "tool"
                args = obj.get("input")
                try:
                    args_json = json.dumps(args, default=str) if args is not None else None
                except Exception:  # noqa: BLE001
                    args_json = None
                turns.append(IndexedTurn(
                    agent_id=agent_id, session_id=session_id, turn_index=next_idx,
                    role="tool",
                    content_text=f"{tool_name} {args_json or ''}".strip(),
                    tool_name=tool_name, tool_args_json=args_json, ts=ts or 0,
                ))
                next_idx += 1
            elif t == "tool_result":
                text = content_to_text(obj.get("content"))
                if text:
                    turns.append(IndexedTurn(
                        agent_id=agent_id, session_id=session_id, turn_index=next_idx,
                        role="tool", content_text=text, ts=ts or 0,
                    ))
                    next_idx += 1

    if not turns:
        return None

    if is_update and next_idx == existing[0]:
        return None

    record = SessionRecord(
        agent_id=agent_id, session_id=session_id,
        cwd=cwd, title=title,
        started_at=started_at, last_turn_at=last_turn_at,
        turn_count=next_idx,
    )
    raw_meta = json.dumps(
        {"source_path": str(path), "source_mtime": mtime, "title": title},
        default=str,
    )
    return ScanResult(record=record, turns=turns, raw_meta=raw_meta, is_update=is_update)
