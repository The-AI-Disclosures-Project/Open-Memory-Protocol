"""Codex CLI (`~/.codex/sessions/<y>/<m>/<d>/rollout-*.jsonl`).

Each JSONL line wraps an event: `{timestamp, type: <wrapper>, payload: {...}}`.
Wrappers we care about:
  - `session_meta`: payload has `id`, `cwd`, `timestamp`, `instructions`
  - `response_item`: payload.type in {message, function_call, function_call_output, reasoning, ...}
  - `event_msg`:     payload.type in {user_message, agent_reasoning, ...}
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from acp_memory_server.index import Index
from acp_memory_server.models import IndexedTurn, SessionRecord

from ._common import ScanResult, content_to_text, existing_mtime, iso_to_epoch, safe_json

log = logging.getLogger(__name__)


def root() -> Path:
    return Path.home() / ".codex" / "sessions"


def available() -> bool:
    return root().is_dir()


def scan(idx: Index, agent_id: str) -> Iterator[ScanResult]:
    base = root()
    if not base.is_dir():
        return

    for session_file in base.rglob("*.jsonl"):
        if session_file.is_dir():
            continue
        try:
            result = _scan_file(idx, agent_id, session_file)
        except Exception:  # noqa: BLE001
            log.exception("codex parse failed: %s", session_file)
            continue
        if result is not None:
            yield result


def _extract_session_id(path: Path, session_meta: dict[str, Any] | None) -> str:
    if session_meta and isinstance(session_meta.get("id"), str):
        return session_meta["id"]
    stem = path.stem
    parts = stem.split("-")
    if len(parts) >= 5:
        candidate = "-".join(parts[-5:])
        if len(candidate) == 36:
            return candidate
    return stem


def _scan_file(idx: Index, agent_id: str, path: Path) -> ScanResult | None:
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
            ts = iso_to_epoch(obj.get("timestamp"))
            if ts is not None:
                last_turn_at = ts

            if outer == "session_meta" and payload is not None:
                session_meta = payload
                if isinstance(payload.get("cwd"), str) and cwd is None:
                    cwd = payload["cwd"]
                if started_at is None:
                    started_at = iso_to_epoch(payload.get("timestamp")) or ts
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
                text = content_to_text(payload.get("content"))
                if text:
                    turns.append(IndexedTurn(
                        agent_id=agent_id, session_id="__placeholder__", turn_index=next_idx,
                        role=role, content_text=text, ts=ts or 0,
                    ))
                    next_idx += 1
            elif outer == "response_item" and inner == "function_call":
                name = payload.get("name") or "tool"
                args = payload.get("arguments")
                args_json = args if isinstance(args, str) else safe_json(args)
                turns.append(IndexedTurn(
                    agent_id=agent_id, session_id="__placeholder__", turn_index=next_idx,
                    role="tool",
                    content_text=f"{name} {args_json or ''}".strip(),
                    tool_name=name, tool_args_json=args_json, ts=ts or 0,
                ))
                next_idx += 1
            elif outer == "response_item" and inner == "function_call_output":
                output = payload.get("output")
                text = content_to_text(output) if output is not None else content_to_text(payload.get("content"))
                if text:
                    turns.append(IndexedTurn(
                        agent_id=agent_id, session_id="__placeholder__", turn_index=next_idx,
                        role="tool", content_text=text, ts=ts or 0,
                    ))
                    next_idx += 1
            elif outer == "response_item" and inner == "reasoning":
                summary = payload.get("summary")
                text = ""
                if isinstance(summary, list):
                    text = " ".join(s.get("text", "") for s in summary if isinstance(s, dict))
                text = text or content_to_text(payload.get("content"))
                if text:
                    turns.append(IndexedTurn(
                        agent_id=agent_id, session_id="__placeholder__", turn_index=next_idx,
                        role="thought", content_text=text, ts=ts or 0,
                    ))
                    next_idx += 1
            elif outer == "event_msg" and inner == "user_message":
                content = payload.get("message")
                text = content if isinstance(content, str) else content_to_text(content)
                if text:
                    turns.append(IndexedTurn(
                        agent_id=agent_id, session_id="__placeholder__", turn_index=next_idx,
                        role="user", content_text=text, ts=ts or 0,
                    ))
                    next_idx += 1
            elif outer == "event_msg" and inner == "agent_reasoning":
                text = payload.get("text")
                if isinstance(text, str) and text:
                    turns.append(IndexedTurn(
                        agent_id=agent_id, session_id="__placeholder__", turn_index=next_idx,
                        role="thought", content_text=text, ts=ts or 0,
                    ))
                    next_idx += 1

    session_id = _extract_session_id(path, session_meta)
    if not turns:
        return None

    for t in turns:
        t.session_id = session_id

    existing = idx.session_watermark(agent_id, session_id)
    is_update = existing is not None
    if is_update:
        prior_mtime = existing_mtime(idx, agent_id, session_id)
        if prior_mtime is not None and prior_mtime >= mtime:
            return None
        if next_idx == existing[0]:
            return None

    record = SessionRecord(
        agent_id=agent_id, session_id=session_id,
        cwd=cwd, title=None,
        started_at=started_at, last_turn_at=last_turn_at,
        turn_count=next_idx,
    )
    raw_meta = json.dumps({"source_path": str(path), "source_mtime": mtime}, default=str)
    return ScanResult(record=record, turns=turns, raw_meta=raw_meta, is_update=is_update)
