"""Aider (per-project `<repo>/.aider.chat.history.md`).

Aider has no central session index — chat history is written into each working tree.
We rely on a config-supplied list of project roots; without one, the scanner is a no-op.

File format (from `aider/io.py`):
  - Session boundary: a line `# aider chat started at <timestamp>`.
  - User turn: each user line is prefixed with `#### ` (four hashes + space).
  - Assistant turn: literal Markdown, no prefix.
  - Tool/system: `> ` blockquote prefix on each line.

We treat each `# aider chat started at` block as one session, keyed by `<file_path>#<offset>`.
Incremental scanning uses the file's mtime: if mtime hasn't moved, we skip."""

from __future__ import annotations

import hashlib
import json
import logging
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path

from acp_memory_server.index import Index
from acp_memory_server.models import IndexedTurn, SessionRecord

from ._common import ScanResult, existing_mtime

log = logging.getLogger(__name__)


def project_roots_from_config() -> list[Path]:
    """Read `agents.aider.project_roots` from the user's config.toml."""
    from acp_memory_server.config import load_config

    cfg = load_config()
    override = cfg.agent_overrides.get("aider")
    if override is None or not override.project_roots:
        return []
    return [Path(p).expanduser() for p in override.project_roots]


def available() -> bool:
    # Without configured roots Aider scanning is a no-op; we still register the agent so
    # users can see in `doctor` that they need to configure project_roots.
    return bool(project_roots_from_config())


def scan(idx: Index, agent_id: str) -> Iterator[ScanResult]:
    roots = project_roots_from_config()
    if not roots:
        log.info("aider: no project_roots configured; skipping. Add to ~/.config/acp-memory/config.toml.")
        return

    for root in roots:
        history = root / ".aider.chat.history.md"
        if not history.is_file():
            continue
        try:
            yield from _scan_file(idx, agent_id, history, root)
        except Exception:  # noqa: BLE001
            log.exception("aider parse failed: %s", history)


def _scan_file(idx: Index, agent_id: str, path: Path, project_root: Path) -> Iterator[ScanResult]:
    mtime = int(path.stat().st_mtime)
    text = path.read_text(errors="replace")

    # Slice into per-session chunks at `# aider chat started at` headers.
    sessions: list[tuple[str, str]] = []  # (started_at_str, body)
    cur_header = ""
    cur_body: list[str] = []
    for line in text.splitlines():
        if line.startswith("# aider chat started at "):
            if cur_header or cur_body:
                sessions.append((cur_header, "\n".join(cur_body)))
            cur_header = line[len("# aider chat started at "):].strip()
            cur_body = []
        else:
            cur_body.append(line)
    if cur_header or cur_body:
        sessions.append((cur_header, "\n".join(cur_body)))

    for started_str, body in sessions:
        # Stable session id: hash(path + started timestamp). Stays the same on re-scan
        # so INSERT OR IGNORE deduplicates.
        sid = hashlib.sha1(f"{path}|{started_str}".encode("utf-8")).hexdigest()[:32]

        existing = idx.session_watermark(agent_id, sid)
        is_update = existing is not None
        if is_update:
            prior_mtime = existing_mtime(idx, agent_id, sid)
            if prior_mtime is not None and prior_mtime >= mtime:
                continue

        started_at = _parse_aider_timestamp(started_str)
        turns = list(_parse_body(body, agent_id, sid, started_at))
        if not turns:
            continue
        if is_update and len(turns) == existing[0]:
            continue

        record = SessionRecord(
            agent_id=agent_id, session_id=sid,
            cwd=str(project_root), title=None,
            started_at=started_at, last_turn_at=started_at,
            turn_count=len(turns),
        )
        raw_meta = json.dumps(
            {"source_path": str(path), "source_mtime": mtime, "started_at": started_str},
            default=str,
        )
        yield ScanResult(record=record, turns=turns, raw_meta=raw_meta, is_update=is_update)


def _parse_body(body: str, agent_id: str, sid: str, ts: int | None) -> Iterator[IndexedTurn]:
    """Walk the body line-by-line, collecting user (`#### ` prefix) and assistant blocks."""
    role: str | None = None
    buf: list[str] = []
    next_idx = 0
    ts_eff = ts or 0

    def flush() -> Iterator[IndexedTurn]:
        nonlocal buf, role, next_idx
        if role and buf:
            text = "\n".join(buf).strip()
            if text:
                yield IndexedTurn(
                    agent_id=agent_id, session_id=sid, turn_index=next_idx,
                    role=role, content_text=text, ts=ts_eff,
                )
                next_idx += 1
        buf = []

    for line in body.splitlines():
        if line.startswith("#### "):
            if role != "user":
                yield from flush()
                role = "user"
            buf.append(line[5:])
        elif line.startswith("> "):
            # Tool / system blockquote: index separately.
            if role != "tool":
                yield from flush()
                role = "tool"
            buf.append(line[2:])
        else:
            if role not in ("agent", None):
                yield from flush()
            if role is None:
                role = "agent"
            buf.append(line)

    yield from flush()


def _parse_aider_timestamp(s: str) -> int | None:
    """Header timestamp format: `YYYY-MM-DD HH:MM:SS`."""
    if not s:
        return None
    try:
        dt = datetime.strptime(s, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        return int(dt.timestamp())
    except ValueError:
        return None
