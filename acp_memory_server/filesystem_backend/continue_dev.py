"""Continue (`~/.continue/sessions/<sessionId>.json`).

Each session file is a self-contained JSON object:
    {
      sessionId, title, workspaceDirectory,
      history: [{
        message: { role: "user"|"assistant", content: str|Block[], toolCalls?: [], reasoning? },
        contextItems?: [], toolCallStates?: [{output, ...}]
      }],
      ...
    }

`~/.continue/sessions/sessions.json` is the index — useful for titles and dateCreated but
not required: we walk the session files directly."""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from pathlib import Path

from acp_memory_server.index import Index
from acp_memory_server.models import IndexedTurn, SessionRecord

from ._common import ScanResult, content_to_text, existing_mtime

log = logging.getLogger(__name__)


def root() -> Path:
    return Path.home() / ".continue" / "sessions"


def available() -> bool:
    return root().is_dir()


def scan(idx: Index, agent_id: str) -> Iterator[ScanResult]:
    base = root()
    if not base.is_dir():
        return
    for f in base.iterdir():
        if not f.is_file() or f.suffix != ".json" or f.name == "sessions.json":
            continue
        try:
            result = _scan_file(idx, agent_id, f)
        except Exception:  # noqa: BLE001
            log.exception("continue parse failed: %s", f)
            continue
        if result is not None:
            yield result


def _scan_file(idx: Index, agent_id: str, path: Path) -> ScanResult | None:
    mtime = int(path.stat().st_mtime)
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None

    session_id = data.get("sessionId") or path.stem
    if not isinstance(session_id, str):
        return None

    existing = idx.session_watermark(agent_id, session_id)
    is_update = existing is not None
    if is_update:
        prior_mtime = existing_mtime(idx, agent_id, session_id)
        if prior_mtime is not None and prior_mtime >= mtime:
            return None

    history = data.get("history") or []
    if not isinstance(history, list):
        return None

    turns: list[IndexedTurn] = []
    for entry in history:
        if not isinstance(entry, dict):
            continue
        msg = entry.get("message") or {}
        role_raw = msg.get("role") if isinstance(msg, dict) else None
        if role_raw == "user":
            role = "user"
        elif role_raw == "assistant":
            role = "agent"
        else:
            continue

        text = content_to_text(msg.get("content"))
        if text:
            turns.append(IndexedTurn(
                agent_id=agent_id, session_id=session_id, turn_index=len(turns),
                role=role, content_text=text, ts=0,
            ))

        reasoning = msg.get("reasoning") if isinstance(msg, dict) else None
        if isinstance(reasoning, str) and reasoning:
            turns.append(IndexedTurn(
                agent_id=agent_id, session_id=session_id, turn_index=len(turns),
                role="thought", content_text=reasoning, ts=0,
            ))

        tool_calls = msg.get("toolCalls") if isinstance(msg, dict) else None
        if isinstance(tool_calls, list):
            for tc in tool_calls:
                if not isinstance(tc, dict):
                    continue
                fn = tc.get("function") or {}
                name = (fn.get("name") if isinstance(fn, dict) else None) or tc.get("name") or "tool"
                args = (fn.get("arguments") if isinstance(fn, dict) else None) or tc.get("arguments")
                args_json = args if isinstance(args, str) else (json.dumps(args, default=str) if args is not None else None)
                turns.append(IndexedTurn(
                    agent_id=agent_id, session_id=session_id, turn_index=len(turns),
                    role="tool",
                    content_text=f"{name} {args_json or ''}".strip(),
                    tool_name=name, tool_args_json=args_json, ts=0,
                ))

        tool_states = entry.get("toolCallStates")
        if isinstance(tool_states, list):
            for state in tool_states:
                if not isinstance(state, dict):
                    continue
                output = state.get("output")
                output_text = content_to_text(output) if output is not None else ""
                if output_text:
                    turns.append(IndexedTurn(
                        agent_id=agent_id, session_id=session_id, turn_index=len(turns),
                        role="tool", content_text=output_text, ts=0,
                    ))

    if not turns:
        return None
    if is_update and len(turns) == existing[0]:
        return None

    record = SessionRecord(
        agent_id=agent_id, session_id=session_id,
        cwd=data.get("workspaceDirectory") if isinstance(data.get("workspaceDirectory"), str) else None,
        title=data.get("title") if isinstance(data.get("title"), str) else None,
        started_at=None, last_turn_at=None,
        turn_count=len(turns),
    )
    raw_meta = json.dumps(
        {"source_path": str(path), "source_mtime": mtime, "title": data.get("title")},
        default=str,
    )
    return ScanResult(record=record, turns=turns, raw_meta=raw_meta, is_update=is_update)
