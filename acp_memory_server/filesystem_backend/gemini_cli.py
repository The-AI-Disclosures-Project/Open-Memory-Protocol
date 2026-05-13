"""Gemini CLI and Qwen Code.

Layout under `~/.gemini/` (and `~/.qwen/` for the fork):
    projects.json                                — maps cwd → projectName slug
    tmp/<projectHash>/chats/session-*.{json,jsonl}
    tmp/<projectHash>/logs.json                  — flat per-user-message log

The `projectHash` directory is a SHA256 of the cwd; resolving hash → cwd requires either:
  (a) reading `projects.json` (cwd → slug, where slug becomes a `history/<slug>` symlink),
  (b) reading a session's body for an embedded path, or
  (c) walking `~/.gemini/history/<slug>/.project_root`, whose contents are the absolute cwd.

Two on-disk formats:
  - Older `.json`: one object with `{sessionId, projectHash, startTime, lastUpdated, messages: [...]}`.
  - Newer `.jsonl`: first line is the session metadata; subsequent lines (if any) are messages.

In both, a message looks like `{id, timestamp, type: "user"|"gemini"|"tool"|"info"|"error", content}`.
We treat `info`/`error` as system messages and drop them; `user` → user, `gemini` → agent."""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from acp_memory_server.index import Index
from acp_memory_server.models import IndexedTurn, SessionRecord

from ._common import ScanResult, content_to_text, existing_mtime, iso_to_epoch

log = logging.getLogger(__name__)


def gemini_root() -> Path:
    return Path.home() / ".gemini"


def qwen_root() -> Path:
    return Path.home() / ".qwen"


def gemini_available() -> bool:
    return (gemini_root() / "tmp").is_dir() or (gemini_root() / "history").is_dir()


def qwen_available() -> bool:
    return (qwen_root() / "tmp").is_dir() or (qwen_root() / "history").is_dir()


def scan_gemini(idx: Index, agent_id: str) -> Iterator[ScanResult]:
    yield from _scan_root(idx, agent_id, gemini_root())


def scan_qwen(idx: Index, agent_id: str) -> Iterator[ScanResult]:
    yield from _scan_root(idx, agent_id, qwen_root())


def _scan_root(idx: Index, agent_id: str, root: Path) -> Iterator[ScanResult]:
    """Walk one Gemini-shaped install tree."""
    tmp = root / "tmp"
    if not tmp.is_dir():
        return

    cwd_by_hash = _build_hash_to_cwd_map(root)

    for proj_dir in tmp.iterdir():
        if not proj_dir.is_dir():
            continue
        chats = proj_dir / "chats"
        if not chats.is_dir():
            continue
        cwd = cwd_by_hash.get(proj_dir.name)
        for session_file in chats.iterdir():
            if not session_file.is_file():
                continue
            try:
                result = _scan_session(idx, agent_id, session_file, cwd_hint=cwd)
            except Exception:  # noqa: BLE001
                log.exception("gemini parse failed: %s", session_file)
                continue
            if result is not None:
                yield result


def _build_hash_to_cwd_map(root: Path) -> dict[str, str]:
    """projects.json maps cwd → slug. history/<slug>/.project_root then holds the canonical
    cwd path. tmp/<projectHash>/ uses a SHA256 of the cwd as the directory name — but the
    hash isn't computed by us; we just need to reach cwd somehow.

    Heuristic: read every session file's body for an embedded cwd / projectHash combo.
    Cheaper fallback: check if any of the chats reference a known absolute path."""
    mapping: dict[str, str] = {}
    projects_json = root / "projects.json"
    if projects_json.is_file():
        try:
            data = json.loads(projects_json.read_text())
            slug_to_cwd: dict[str, str] = {}
            for cwd, slug in (data.get("projects") or {}).items():
                slug_to_cwd[str(slug)] = str(cwd)
            # No direct hash → cwd in projects.json; but a sibling history/<slug>/.project_root
            # has the cwd, and the tmp/<hash>/ matches by sessions inside. We probe.
            for slug, cwd in slug_to_cwd.items():
                # No reliable way to bridge slug → hash without hashing. Skip; rely on probe.
                pass
        except (OSError, json.JSONDecodeError):
            pass

    # Probe each tmp/<hash>/chats/*.json for an embedded path. Some Gemini versions write
    # the source path inside session metadata.
    tmp = root / "tmp"
    if tmp.is_dir():
        for proj_dir in tmp.iterdir():
            if not proj_dir.is_dir():
                continue
            chats = proj_dir / "chats"
            if not chats.is_dir():
                continue
            for f in chats.iterdir():
                if not f.is_file():
                    continue
                try:
                    with f.open() as fh:
                        line = fh.readline()
                    obj = json.loads(line)
                    for key in ("cwd", "workingDirectory", "projectRoot"):
                        v = obj.get(key)
                        if isinstance(v, str) and v:
                            mapping[proj_dir.name] = v
                            break
                except (OSError, json.JSONDecodeError):
                    pass
                if proj_dir.name in mapping:
                    break

    return mapping


def _scan_session(idx: Index, agent_id: str, path: Path, cwd_hint: str | None) -> ScanResult | None:
    mtime = int(path.stat().st_mtime)

    session_meta, messages = _read_session(path)
    if session_meta is None:
        return None
    session_id = session_meta.get("sessionId")
    if not isinstance(session_id, str):
        return None
    if not messages:
        return None

    existing = idx.session_watermark(agent_id, session_id)
    is_update = existing is not None
    if is_update:
        prior_mtime = existing_mtime(idx, agent_id, session_id)
        if prior_mtime is not None and prior_mtime >= mtime:
            return None

    started_at = iso_to_epoch(session_meta.get("startTime"))
    last_turn_at = iso_to_epoch(session_meta.get("lastUpdated")) or started_at

    turns: list[IndexedTurn] = []
    next_idx = 0
    for m in messages:
        if not isinstance(m, dict):
            continue
        ts = iso_to_epoch(m.get("timestamp")) or 0
        if ts:
            last_turn_at = ts
        mtype = m.get("type")
        content = m.get("content")
        text = content_to_text(content) if not isinstance(content, str) else content
        if not text:
            continue
        if mtype == "user":
            role = "user"
        elif mtype in ("gemini", "assistant", "model"):
            role = "agent"
        elif mtype in ("tool", "tool_call", "tool_result"):
            role = "tool"
        elif mtype in ("thought", "reasoning"):
            role = "thought"
        else:
            # info / error / system: skip — these are UI chrome, not transcript content.
            continue
        turns.append(IndexedTurn(
            agent_id=agent_id, session_id=session_id, turn_index=next_idx,
            role=role, content_text=text, ts=ts,
        ))
        next_idx += 1

    if not turns:
        return None
    if is_update and next_idx == existing[0]:
        return None

    record = SessionRecord(
        agent_id=agent_id, session_id=session_id,
        cwd=cwd_hint, title=None,
        started_at=started_at, last_turn_at=last_turn_at,
        turn_count=next_idx,
    )
    raw_meta = json.dumps(
        {"source_path": str(path), "source_mtime": mtime, "project_hash": session_meta.get("projectHash")},
        default=str,
    )
    return ScanResult(record=record, turns=turns, raw_meta=raw_meta, is_update=is_update)


def _read_session(path: Path) -> tuple[dict[str, Any] | None, list[Any]]:
    """Return `(session_meta, messages)`. Handles both .json and .jsonl shapes."""
    if path.suffix == ".json":
        try:
            data = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            return None, []
        if not isinstance(data, dict):
            return None, []
        return data, data.get("messages") or []

    # .jsonl: first line is metadata; remaining lines are messages.
    meta: dict[str, Any] | None = None
    messages: list[Any] = []
    try:
        with path.open() as fh:
            for i, line in enumerate(fh):
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if i == 0 and isinstance(obj, dict) and "sessionId" in obj and "messages" not in obj:
                    meta = obj
                else:
                    # A line could be a message OR a full-document fallback.
                    if isinstance(obj, dict) and "messages" in obj and meta is None:
                        meta = obj
                        messages = obj.get("messages") or []
                    else:
                        messages.append(obj)
    except OSError:
        return None, []
    return meta, messages
