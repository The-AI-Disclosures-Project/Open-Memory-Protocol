"""Per-agent cwd discovery.

ACP `session/list` is sometimes silently filtered to sessions whose project
matches the calling cwd. To capture all of a user's history, we may need to
call `list_sessions(cwd=<project>)` once per known project root.

Discovery is best-effort and per-agent. For agents we don't know about, we
return an empty list — the poller falls back to a single unfiltered call.

Users can override discovery per agent via config.toml:

    [agents.claude-acp]
    cwds = ["/Users/me/code/foo", "/Users/me/code/bar"]

    [agents.codex-acp]
    cwds = []   # explicit empty -> single unfiltered call
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from pathlib import Path

log = logging.getLogger(__name__)


def _claude_code_cwds() -> list[str]:
    """Read ~/.claude/projects/*/ and pull each project's original cwd.
    Each project dir name is a `/`-to-`-` encoding of the cwd, but that's
    lossy when the path itself contains `-`. Prefer the embedded `cwd` field
    in any session JSONL inside the project dir."""
    root = Path.home() / ".claude" / "projects"
    if not root.is_dir():
        return []

    cwds: set[str] = set()
    for project_dir in root.iterdir():
        if not project_dir.is_dir():
            continue
        cwd = _peek_cwd_from_jsonls(project_dir)
        if cwd is None:
            cwd = _decode_dashed_dirname(project_dir.name)
        if cwd and Path(cwd).exists():
            cwds.add(cwd)
    return sorted(cwds)


def _peek_cwd_from_jsonls(project_dir: Path, max_files: int = 2, max_lines: int = 5) -> str | None:
    """Look in a project dir's JSONLs for an embedded `cwd` field."""
    files = []
    for p in project_dir.rglob("*.jsonl"):
        files.append(p)
        if len(files) >= max_files:
            break
    for f in files:
        try:
            with f.open() as fh:
                for i, line in enumerate(fh):
                    if i >= max_lines:
                        break
                    cwd = _find_cwd(json.loads(line))
                    if cwd:
                        return cwd
        except (OSError, json.JSONDecodeError):
            continue
    return None


def _find_cwd(obj: object) -> str | None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k.lower() == "cwd" and isinstance(v, str):
                return v
            found = _find_cwd(v)
            if found:
                return found
    elif isinstance(obj, list):
        for v in obj:
            found = _find_cwd(v)
            if found:
                return found
    return None


def _decode_dashed_dirname(name: str) -> str | None:
    """Best-effort decode of `-Users-foo-bar` -> `/Users/foo/bar`. Lossy on
    paths with literal dashes; only used as a fallback."""
    if not name.startswith("-"):
        return None
    return "/" + name.lstrip("-").replace("-", "/")


_DISCOVERERS: dict[str, Callable[[], list[str]]] = {
    "claude-acp": _claude_code_cwds,
    "claude-code-acp": _claude_code_cwds,
    # Codex's filesystem store is not project-scoped (~/.codex/sessions/<year>/),
    # so its ACP adapter probably accepts a single unscoped list_sessions call.
    # Add an entry here if that turns out to be wrong.
}


def discover_cwds(agent_id: str) -> list[str]:
    fn = _DISCOVERERS.get(agent_id)
    if fn is None:
        return []
    try:
        return fn()
    except Exception:  # noqa: BLE001
        log.exception("cwd discovery failed for %s", agent_id)
        return []
