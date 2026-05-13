from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path


def _xdg(env_var: str, default_subdir: str) -> Path:
    val = os.environ.get(env_var)
    if val:
        return Path(val).expanduser()
    return Path.home() / default_subdir


def config_dir() -> Path:
    return _xdg("XDG_CONFIG_HOME", ".config") / "acp-memory"


def data_dir() -> Path:
    return _xdg("XDG_DATA_HOME", ".local/share") / "acp-memory"


def cache_dir() -> Path:
    return _xdg("XDG_CACHE_HOME", ".cache") / "acp-memory"


def db_path() -> Path:
    return data_dir() / "db.sqlite"


def config_path() -> Path:
    return config_dir() / "config.toml"


@dataclass
class AgentOverride:
    id: str
    enabled: bool = True
    launch_cmd: str | None = None
    launch_args: list[str] | None = None
    launch_env: dict[str, str] | None = None
    cwd: str | None = None
    # cwds is a tri-state:
    #   None  -> use auto-discovery (or single unscoped call if no discoverer)
    #   []    -> force a single unscoped list_sessions() call
    #   [...] -> use exactly this list (no auto-discovery)
    cwds: list[str] | None = None
    # backend = "acp" | "filesystem" | "auto" (default; uses filesystem if available, else acp)
    backend: str | None = None
    # Per-project roots for agents whose history lives next to the working tree (Aider, Crush, ...).
    project_roots: list[str] | None = None


@dataclass
class Config:
    poll_interval_seconds: int = 300
    registry_url: str = "https://cdn.agentclientprotocol.com/registry/v1/latest/registry.json"
    registry_cache_ttl_seconds: int = 24 * 3600
    auto_discover: bool = True
    agent_overrides: dict[str, AgentOverride] = field(default_factory=dict)


def load_config() -> Config:
    path = config_path()
    if not path.exists():
        return Config()

    with path.open("rb") as f:
        raw = tomllib.load(f)

    cfg = Config(
        poll_interval_seconds=int(raw.get("poll_interval_seconds", 300)),
        registry_url=str(raw.get("registry_url", Config.registry_url)),
        registry_cache_ttl_seconds=int(raw.get("registry_cache_ttl_seconds", 24 * 3600)),
        auto_discover=bool(raw.get("auto_discover", True)),
    )

    for agent_id, section in (raw.get("agents") or {}).items():
        cfg.agent_overrides[agent_id] = AgentOverride(
            id=agent_id,
            enabled=bool(section.get("enabled", True)),
            launch_cmd=section.get("launch_cmd"),
            launch_args=list(section["launch_args"]) if "launch_args" in section else None,
            launch_env=dict(section["launch_env"]) if "launch_env" in section else None,
            cwd=section.get("cwd"),
            cwds=list(section["cwds"]) if "cwds" in section else None,
            backend=section.get("backend"),
            project_roots=list(section["project_roots"]) if "project_roots" in section else None,
        )
    return cfg


def ensure_dirs() -> None:
    for p in (config_dir(), data_dir(), cache_dir()):
        p.mkdir(parents=True, exist_ok=True)
