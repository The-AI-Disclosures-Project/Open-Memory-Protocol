from __future__ import annotations

import logging
import shutil
from typing import Any

from acp_memory_server.config import AgentOverride, Config
from acp_memory_server.models import AgentSpec

log = logging.getLogger(__name__)


def _flatten_distribution(dist: Any) -> dict[str, Any] | None:
    """ACP `distribution` blocks may be:
      - {"strategy": "binary"|"npx"|"uvx", "cmd": ..., "args": ..., "env": ...}
      - {"binary": {...}} or {"npx": {...}} (variant style)
      - {"platforms": {"darwin-aarch64": {"cmd": ..., ...}}, ...}
    Return a normalized dict {strategy, cmd, args, env} or None if unsupported.
    """
    if not isinstance(dist, dict):
        return None

    if "strategy" in dist and "cmd" in dist:
        return {
            "strategy": dist["strategy"],
            "cmd": dist["cmd"],
            "args": list(dist.get("args") or []),
            "env": dict(dist.get("env") or {}),
        }

    for strategy in ("npx", "uvx", "binary"):
        sub = dist.get(strategy)
        if isinstance(sub, dict):
            cmd = sub.get("cmd") or sub.get("package") or sub.get("module")
            if cmd is None and strategy == "npx":
                cmd = sub.get("name")
            if cmd is None:
                continue
            return {
                "strategy": strategy,
                "cmd": cmd,
                "args": list(sub.get("args") or []),
                "env": dict(sub.get("env") or {}),
            }

    return None


def _is_locally_runnable(strategy: str, cmd: str) -> bool:
    """Decide if we should *attempt* to launch this without auto-downloading anything."""
    if strategy == "binary":
        return shutil.which(cmd) is not None
    if strategy == "npx":
        return shutil.which("npx") is not None
    if strategy == "uvx":
        return shutil.which("uvx") is not None
    return False


def _build_launch(strategy: str, cmd: str, args: list[str]) -> tuple[str, list[str]]:
    """Translate (strategy, cmd, args) into the actual subprocess invocation."""
    if strategy == "binary":
        return cmd, args
    if strategy == "npx":
        # `npx -y <package> <args...>` runs without prompting; only succeeds locally if cached.
        return "npx", ["-y", cmd, *args]
    if strategy == "uvx":
        return "uvx", [cmd, *args]
    raise ValueError(f"Unknown strategy: {strategy}")


def _apply_override(spec: AgentSpec, override: AgentOverride) -> AgentSpec:
    return AgentSpec(
        id=spec.id,
        name=spec.name,
        launch_cmd=override.launch_cmd or spec.launch_cmd,
        launch_args=override.launch_args if override.launch_args is not None else spec.launch_args,
        launch_env={**spec.launch_env, **(override.launch_env or {})},
        cwd=override.cwd or spec.cwd,
        enabled=override.enabled,
    )


def detect_agents(registry_agents: list[dict[str, Any]], cfg: Config) -> list[AgentSpec]:
    """Return AgentSpecs for agents that are locally launchable, plus user-overridden ones."""
    detected: list[AgentSpec] = []
    seen_ids: set[str] = set()

    if cfg.auto_discover:
        for entry in registry_agents:
            agent_id = entry.get("id") or entry.get("name")
            if not agent_id:
                continue
            dist = entry.get("distribution") or entry.get("dist")
            normalized = _flatten_distribution(dist)
            if normalized is None:
                log.debug("agent %s: no usable distribution", agent_id)
                continue
            if not _is_locally_runnable(normalized["strategy"], normalized["cmd"]):
                log.debug(
                    "agent %s: %s %s not locally runnable",
                    agent_id,
                    normalized["strategy"],
                    normalized["cmd"],
                )
                continue
            launch_cmd, launch_args = _build_launch(
                normalized["strategy"], normalized["cmd"], normalized["args"]
            )
            spec = AgentSpec(
                id=agent_id,
                name=entry.get("name", agent_id),
                launch_cmd=launch_cmd,
                launch_args=launch_args,
                launch_env=dict(normalized["env"]),
            )
            override = cfg.agent_overrides.get(agent_id)
            if override is not None:
                spec = _apply_override(spec, override)
            if spec.enabled:
                detected.append(spec)
                seen_ids.add(spec.id)

    # Pull in user-defined agents not in the registry at all.
    for agent_id, override in cfg.agent_overrides.items():
        if agent_id in seen_ids or not override.launch_cmd or not override.enabled:
            continue
        detected.append(
            AgentSpec(
                id=agent_id,
                name=agent_id,
                launch_cmd=override.launch_cmd,
                launch_args=list(override.launch_args or []),
                launch_env=dict(override.launch_env or {}),
                cwd=override.cwd,
                enabled=True,
            )
        )

    return detected
