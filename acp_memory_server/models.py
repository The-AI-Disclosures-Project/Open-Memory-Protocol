from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AgentSpec:
    """An ACP agent the server knows how to launch."""

    id: str
    name: str
    launch_cmd: str
    launch_args: list[str] = field(default_factory=list)
    launch_env: dict[str, str] = field(default_factory=dict)
    cwd: str | None = None
    enabled: bool = True


@dataclass
class AgentStatus:
    id: str
    name: str
    status: str  # ok | needs_auth | unsupported | error | unknown
    last_polled_at: int | None = None
    session_count: int = 0
    last_error: str | None = None


@dataclass
class IndexedTurn:
    """A flattened ACP SessionUpdate ready for SQLite."""

    agent_id: str
    session_id: str
    turn_index: int
    role: str  # user | agent | tool | thought | system
    content_text: str
    tool_name: str | None = None
    tool_args_json: str | None = None
    raw_blob: str | None = None
    ts: int = 0


@dataclass
class SessionRecord:
    agent_id: str
    session_id: str
    cwd: str | None
    title: str | None
    started_at: int | None
    last_turn_at: int | None
    turn_count: int
