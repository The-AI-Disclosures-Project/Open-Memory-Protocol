"""Filesystem backends — read agents' on-disk session stores directly.

Each agent module exposes `scan(idx, agent_id)` (an iterator of ScanResult) and `available()`
(does the store exist?). This package wires them into the registry the poller consults via
`has_filesystem_backend()` and `scan()`.

The registry also drives `discover_filesystem_only_agents()`, which auto-registers agents
whose store exists but which aren't in the ACP registry (e.g. Cursor, Cline, Zed). Those
synthesize an `AgentSpec` with no launch command — the poller only ever uses them via the
filesystem path."""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field

from acp_memory_server.config import Config
from acp_memory_server.index import Index
from acp_memory_server.models import AgentSpec

from . import (
    aider,
    cline,
    claude_code,
    codex,
    continue_dev,
    cursor,
    gemini_cli,
    goose,
    zed,
)
from ._common import ScanResult

log = logging.getLogger(__name__)


__all__ = [
    "ScanResult",
    "has_filesystem_backend",
    "scan",
    "discover_filesystem_only_agents",
    "FILESYSTEM_AGENTS",
]


@dataclass(frozen=True)
class FilesystemAgent:
    """Built-in agent that ships with a filesystem parser.

    `id` is the canonical agent id — for agents that also appear in the ACP registry, use
    the registry id so both detection paths converge on one record.
    `aliases` are alternate ids the same store has been seen registered under; the dispatch
    table maps each alias back to this entry."""

    id: str
    name: str
    scanner: Callable[[Index, str], Iterator[ScanResult]]
    available: Callable[[], bool]
    aliases: tuple[str, ...] = field(default_factory=tuple)


# Canonical ids match the ACP registry where the agent is in it (claude-acp, codex-acp,
# goose, cline, qwen-code, gemini, kilo). Agents not in the registry get plain names.
FILESYSTEM_AGENTS: list[FilesystemAgent] = [
    FilesystemAgent(
        id="claude-acp", name="Claude Code",
        scanner=claude_code.scan, available=claude_code.available,
        aliases=("claude-code-acp",),
    ),
    FilesystemAgent(
        id="codex-acp", name="Codex CLI",
        scanner=codex.scan, available=codex.available,
    ),
    FilesystemAgent(
        id="goose", name="Goose",
        scanner=goose.scan, available=goose.available,
    ),
    FilesystemAgent(
        id="cursor", name="Cursor",
        scanner=cursor.scan, available=cursor.available,
    ),
    FilesystemAgent(
        id="cline", name="Cline",
        scanner=cline.scan_cline, available=cline.cline_available,
    ),
    FilesystemAgent(
        id="roo-code", name="Roo Code",
        scanner=cline.scan_roo, available=cline.roo_available,
    ),
    FilesystemAgent(
        id="kilo", name="Kilo Code",
        scanner=cline.scan_kilo, available=cline.kilo_available,
        aliases=("kilo-code",),
    ),
    FilesystemAgent(
        id="zed", name="Zed",
        scanner=zed.scan, available=zed.available,
    ),
    FilesystemAgent(
        id="gemini", name="Gemini CLI",
        scanner=gemini_cli.scan_gemini, available=gemini_cli.gemini_available,
        aliases=("gemini-cli",),
    ),
    FilesystemAgent(
        id="qwen-code", name="Qwen Code",
        scanner=gemini_cli.scan_qwen, available=gemini_cli.qwen_available,
    ),
    FilesystemAgent(
        id="continue", name="Continue",
        scanner=continue_dev.scan, available=continue_dev.available,
    ),
    FilesystemAgent(
        id="aider", name="Aider",
        scanner=aider.scan, available=aider.available,
    ),
]


# Build lookup table keyed by both canonical id and aliases.
_BY_ID: dict[str, FilesystemAgent] = {}
for _a in FILESYSTEM_AGENTS:
    _BY_ID[_a.id] = _a
    for _alias in _a.aliases:
        _BY_ID[_alias] = _a


def has_filesystem_backend(agent_id: str) -> bool:
    return agent_id in _BY_ID


def scan(idx: Index, agent_id: str) -> Iterator[ScanResult]:
    """Dispatch to the right per-agent scanner."""
    a = _BY_ID.get(agent_id)
    if a is None:
        raise ValueError(f"no filesystem backend for {agent_id}")
    yield from a.scanner(idx, agent_id)


def discover_filesystem_only_agents(cfg: Config, known_ids: set[str]) -> list[AgentSpec]:
    """Return synthetic AgentSpecs for agents whose on-disk store exists but the ACP
    registry didn't pick them up (e.g. Cursor, Cline-in-VS-Code, Zed, or any ACP-registry
    agent on a host without npx/uvx).

    Skips agents already in `known_ids` (registry detection got them) and any agent
    explicitly disabled in `cfg.agent_overrides`."""
    out: list[AgentSpec] = []
    for a in FILESYSTEM_AGENTS:
        if a.id in known_ids or any(alias in known_ids for alias in a.aliases):
            continue
        override = cfg.agent_overrides.get(a.id)
        if override is not None and not override.enabled:
            continue
        try:
            if not a.available():
                continue
        except Exception:  # noqa: BLE001
            log.exception("filesystem agent %s availability check failed", a.id)
            continue
        spec = AgentSpec(
            id=a.id,
            name=a.name,
            launch_cmd="",   # filesystem-only — never spawned
            launch_args=[],
            launch_env={},
            enabled=True,
        )
        out.append(spec)
    return out
