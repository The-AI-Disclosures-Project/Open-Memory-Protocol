"""Cline-family scanners (Cline, Roo Code, Kilo Code).

All three are VS Code extensions that share the same Anthropic-format storage layout. Each
task lives under `{globalStorage}/{publisherId}/tasks/<taskId>/` with the canonical files:

    api_conversation_history.json  — `Array<{role: "user"|"assistant", content: str|Block[]}>`
    ui_messages.json (or cline_messages.json / uiMessages.json on forks)  — UI-layer events

We prefer `api_conversation_history.json` for fidelity (tool I/O is preserved as Anthropic
content blocks); fall back to the UI file if the API file is missing.

The session id is the directory name. CWD is *not* stored in the task files — it lives in
`{globalStorage}/{publisherId}/state/taskHistory.json` (or `tasks/<id>/task_metadata.json`).

This is shared across:
    Cline  → saoudrizwan.claude-dev
    Roo    → rooveterinaryinc.roo-cline
    Kilo   → kilocode.kilo-code
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from acp_memory_server.index import Index
from acp_memory_server.models import IndexedTurn, SessionRecord

from ._common import ScanResult, content_to_text, existing_mtime

log = logging.getLogger(__name__)


# (id, publisher dir name, human-readable name)
FAMILY = {
    "cline": ("saoudrizwan.claude-dev", "Cline"),
    "roo-code": ("rooveterinaryinc.roo-cline", "Roo Code"),
    "kilo-code": ("kilocode.kilo-code", "Kilo Code"),
}


def _vscode_storage_roots() -> list[Path]:
    """Every VS Code-flavored installation we should check for globalStorage."""
    base = Path.home() / "Library" / "Application Support"
    candidates = [
        base / "Code" / "User" / "globalStorage",
        base / "Code - Insiders" / "User" / "globalStorage",
        base / "Cursor" / "User" / "globalStorage",
        base / "VSCodium" / "User" / "globalStorage",
        base / "Windsurf" / "User" / "globalStorage",
        Path.home() / ".vscode-server" / "data" / "User" / "globalStorage",
    ]
    return [p for p in candidates if p.is_dir()]


def publisher_dirs(publisher_id: str) -> list[Path]:
    return [r / publisher_id for r in _vscode_storage_roots() if (r / publisher_id).is_dir()]


def available_for(publisher_id: str) -> bool:
    return any((p / "tasks").is_dir() for p in publisher_dirs(publisher_id))


def cline_available() -> bool:
    return available_for(FAMILY["cline"][0])


def roo_available() -> bool:
    return available_for(FAMILY["roo-code"][0])


def kilo_available() -> bool:
    return available_for(FAMILY["kilo-code"][0])


def scan_cline(idx: Index, agent_id: str) -> Iterator[ScanResult]:
    yield from _scan_family(idx, agent_id, FAMILY["cline"][0])


def scan_roo(idx: Index, agent_id: str) -> Iterator[ScanResult]:
    yield from _scan_family(idx, agent_id, FAMILY["roo-code"][0])


def scan_kilo(idx: Index, agent_id: str) -> Iterator[ScanResult]:
    yield from _scan_family(idx, agent_id, FAMILY["kilo-code"][0])


def _scan_family(idx: Index, agent_id: str, publisher_id: str) -> Iterator[ScanResult]:
    for pub_dir in publisher_dirs(publisher_id):
        cwd_by_task = _load_task_cwds(pub_dir)
        tasks_dir = pub_dir / "tasks"
        if not tasks_dir.is_dir():
            continue
        for task_dir in tasks_dir.iterdir():
            if not task_dir.is_dir():
                continue
            try:
                result = _scan_task(idx, agent_id, task_dir, cwd_by_task)
            except Exception:  # noqa: BLE001
                log.exception("cline-family parse failed: %s", task_dir)
                continue
            if result is not None:
                yield result


def _scan_task(
    idx: Index, agent_id: str, task_dir: Path, cwd_by_task: dict[str, dict[str, Any]]
) -> ScanResult | None:
    api_file = task_dir / "api_conversation_history.json"
    ui_candidates = [
        task_dir / "ui_messages.json",
        task_dir / "uiMessages.json",
        task_dir / "cline_messages.json",
    ]
    ui_file = next((p for p in ui_candidates if p.is_file()), None)

    primary = api_file if api_file.is_file() else ui_file
    if primary is None:
        return None

    mtime = int(primary.stat().st_mtime)
    session_id = task_dir.name
    existing = idx.session_watermark(agent_id, session_id)
    is_update = existing is not None
    if is_update:
        prior_mtime = existing_mtime(idx, agent_id, session_id)
        if prior_mtime is not None and prior_mtime >= mtime:
            return None

    turns: list[IndexedTurn] = []
    started_at: int | None = None
    last_turn_at: int | None = None

    if primary == api_file:
        turns, started_at, last_turn_at = _parse_api(api_file, agent_id, session_id)
        # Mine the UI file for any user_feedback turns the API file dropped
        # (Cline rewrites context; user typings sometimes only survive in the UI file).
        if ui_file is not None and ui_file.is_file():
            extra = _parse_ui_user_feedback(ui_file, agent_id, session_id, start_index=len(turns))
            turns.extend(extra)
    else:
        turns, started_at, last_turn_at = _parse_ui_all(ui_file, agent_id, session_id)

    if not turns:
        return None
    if is_update and len(turns) == existing[0]:
        return None

    meta = cwd_by_task.get(session_id, {})
    cwd = meta.get("workspace") or meta.get("workspacePath") or _read_task_metadata_cwd(task_dir)
    title = meta.get("task") or meta.get("title") or None

    record = SessionRecord(
        agent_id=agent_id, session_id=session_id,
        cwd=cwd, title=title,
        started_at=started_at, last_turn_at=last_turn_at,
        turn_count=len(turns),
    )
    raw_meta = json.dumps(
        {"source_path": str(primary), "source_mtime": mtime, "title": title},
        default=str,
    )
    return ScanResult(record=record, turns=turns, raw_meta=raw_meta, is_update=is_update)


def _parse_api(
    path: Path, agent_id: str, session_id: str
) -> tuple[list[IndexedTurn], int | None, int | None]:
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return [], None, None
    if not isinstance(data, list):
        return [], None, None

    turns: list[IndexedTurn] = []
    for entry in data:
        if not isinstance(entry, dict):
            continue
        role_raw = entry.get("role")
        if role_raw == "user":
            role = "user"
        elif role_raw == "assistant":
            role = "agent"
        else:
            continue
        content = entry.get("content")
        if isinstance(content, str):
            if content:
                turns.append(IndexedTurn(
                    agent_id=agent_id, session_id=session_id, turn_index=len(turns),
                    role=role, content_text=content, ts=0,
                ))
            continue
        if isinstance(content, list):
            # Top-level text/assistant content
            text = content_to_text(content)
            if text:
                turns.append(IndexedTurn(
                    agent_id=agent_id, session_id=session_id, turn_index=len(turns),
                    role=role, content_text=text, ts=0,
                ))
            # Pull out tool_use / tool_result blocks for separate indexing
            for item in content:
                if not isinstance(item, dict):
                    continue
                t = item.get("type")
                if t == "tool_use":
                    name = item.get("name") or "tool"
                    args = item.get("input")
                    try:
                        args_json = json.dumps(args, default=str) if args is not None else None
                    except Exception:  # noqa: BLE001
                        args_json = None
                    turns.append(IndexedTurn(
                        agent_id=agent_id, session_id=session_id, turn_index=len(turns),
                        role="tool",
                        content_text=f"{name} {args_json or ''}".strip(),
                        tool_name=name, tool_args_json=args_json, ts=0,
                    ))
                elif t == "tool_result":
                    result_text = content_to_text(item.get("content"))
                    if result_text:
                        turns.append(IndexedTurn(
                            agent_id=agent_id, session_id=session_id, turn_index=len(turns),
                            role="tool", content_text=result_text, ts=0,
                        ))

    return turns, None, None


def _parse_ui_all(
    path: Path | None, agent_id: str, session_id: str
) -> tuple[list[IndexedTurn], int | None, int | None]:
    """Fallback: parse the UI-layer JSON when the API file is absent."""
    if path is None:
        return [], None, None
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return [], None, None
    if not isinstance(data, list):
        return [], None, None

    turns: list[IndexedTurn] = []
    started_at: int | None = None
    last_turn_at: int | None = None

    for ev in data:
        if not isinstance(ev, dict):
            continue
        ts_ms = ev.get("ts")
        ts = int(ts_ms) // 1000 if isinstance(ts_ms, (int, float)) else 0
        if ts:
            started_at = started_at if started_at is not None else ts
            last_turn_at = ts

        etype = ev.get("type")
        say = ev.get("say")
        ask = ev.get("ask")
        text = ev.get("text") or ev.get("reasoning") or ""
        if not text:
            continue

        if etype == "say" and say == "user_feedback":
            role = "user"
        elif etype == "say" and say == "task":
            role = "user"  # initial task statement counts as user
        elif etype == "say" and say in ("text", "completion_result"):
            role = "agent"
        elif etype == "say" and say == "reasoning":
            role = "thought"
        elif etype == "say" and say in ("tool", "command_output", "command", "browser_action_result"):
            role = "tool"
        elif etype == "ask" and ask in ("tool", "command", "browser_action_launch"):
            role = "tool"
        else:
            continue

        turns.append(IndexedTurn(
            agent_id=agent_id, session_id=session_id, turn_index=len(turns),
            role=role, content_text=text, ts=ts,
        ))

    return turns, started_at, last_turn_at


def _parse_ui_user_feedback(
    path: Path, agent_id: str, session_id: str, start_index: int
) -> list[IndexedTurn]:
    """Pull just user_feedback events from the UI file — used to top up API-file scans."""
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(data, list):
        return []

    extras: list[IndexedTurn] = []
    for ev in data:
        if not isinstance(ev, dict):
            continue
        if ev.get("type") != "say" or ev.get("say") != "user_feedback":
            continue
        text = ev.get("text") or ""
        if not text:
            continue
        ts_ms = ev.get("ts")
        ts = int(ts_ms) // 1000 if isinstance(ts_ms, (int, float)) else 0
        extras.append(IndexedTurn(
            agent_id=agent_id, session_id=session_id, turn_index=start_index + len(extras),
            role="user", content_text=text, ts=ts,
        ))
    return extras


def _load_task_cwds(pub_dir: Path) -> dict[str, dict[str, Any]]:
    """Read `state/taskHistory.json` if present. Cline writes `[{id, task, workspace, ts, ...}]`."""
    out: dict[str, dict[str, Any]] = {}
    for candidate in (pub_dir / "state" / "taskHistory.json", pub_dir / "taskHistory.json"):
        if not candidate.is_file():
            continue
        try:
            data = json.loads(candidate.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        items = data if isinstance(data, list) else data.get("taskHistory") if isinstance(data, dict) else None
        if not isinstance(items, list):
            continue
        for it in items:
            if isinstance(it, dict) and isinstance(it.get("id"), str):
                out[it["id"]] = it
        break
    return out


def _read_task_metadata_cwd(task_dir: Path) -> str | None:
    md = task_dir / "task_metadata.json"
    if not md.is_file():
        return None
    try:
        data = json.loads(md.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    for key in ("workspace", "workspacePath", "cwd", "workingDirectory"):
        v = data.get(key) if isinstance(data, dict) else None
        if isinstance(v, str) and v:
            return v
    return None
