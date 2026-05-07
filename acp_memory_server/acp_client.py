"""ACP Client implementation that the server uses to talk to spawned agents.

This is intentionally minimal — we never run an interactive turn, only `session/list`
and `session/load`, which means most Client callbacks are stubs. Permission requests
and filesystem callbacks raise `method_not_found`; session updates are funneled into
an asyncio Queue keyed by session_id so the poller can collect a transcript replay."""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import Any

from acp import Client, RequestError
from acp.schema import (
    AgentMessageChunk,
    AgentPlanUpdate,
    AgentThoughtChunk,
    AvailableCommandsUpdate,
    ConfigOptionUpdate,
    CurrentModeUpdate,
    CreateTerminalResponse,
    EnvVariable,
    KillTerminalResponse,
    PermissionOption,
    ReadTextFileResponse,
    ReleaseTerminalResponse,
    RequestPermissionResponse,
    SessionInfoUpdate,
    TerminalOutputResponse,
    ToolCallProgress,
    ToolCallStart,
    ToolCallUpdate,
    UsageUpdate,
    UserMessageChunk,
    WaitForTerminalExitResponse,
    WriteTextFileResponse,
)

log = logging.getLogger(__name__)

UpdatePayload = (
    UserMessageChunk
    | AgentMessageChunk
    | AgentThoughtChunk
    | ToolCallStart
    | ToolCallProgress
    | AgentPlanUpdate
    | AvailableCommandsUpdate
    | CurrentModeUpdate
    | ConfigOptionUpdate
    | SessionInfoUpdate
    | UsageUpdate
)


class CollectingClient(Client):
    """A passive ACP Client. Buffers session/update notifications per session_id."""

    def __init__(self) -> None:
        self._queues: dict[str, asyncio.Queue[UpdatePayload | None]] = defaultdict(asyncio.Queue)

    def queue_for(self, session_id: str) -> asyncio.Queue[UpdatePayload | None]:
        return self._queues[session_id]

    def reset(self, session_id: str) -> None:
        self._queues.pop(session_id, None)

    def end_of_stream(self, session_id: str) -> None:
        """Signal end-of-stream so the consumer can stop draining."""
        self._queues[session_id].put_nowait(None)

    # ----- ACP Client interface -----

    async def request_permission(
        self,
        options: list[PermissionOption],
        session_id: str,
        tool_call: ToolCallUpdate,
        **kwargs: Any,
    ) -> RequestPermissionResponse:
        # Headless poller — never grant tool permissions.
        raise RequestError.method_not_found("session/request_permission")

    async def write_text_file(
        self, content: str, path: str, session_id: str, **kwargs: Any
    ) -> WriteTextFileResponse | None:
        raise RequestError.method_not_found("fs/write_text_file")

    async def read_text_file(
        self,
        path: str,
        session_id: str,
        limit: int | None = None,
        line: int | None = None,
        **kwargs: Any,
    ) -> ReadTextFileResponse:
        raise RequestError.method_not_found("fs/read_text_file")

    async def create_terminal(
        self,
        command: str,
        session_id: str,
        args: list[str] | None = None,
        cwd: str | None = None,
        env: list[EnvVariable] | None = None,
        output_byte_limit: int | None = None,
        **kwargs: Any,
    ) -> CreateTerminalResponse:
        raise RequestError.method_not_found("terminal/create")

    async def terminal_output(
        self, session_id: str, terminal_id: str, **kwargs: Any
    ) -> TerminalOutputResponse:
        raise RequestError.method_not_found("terminal/output")

    async def release_terminal(
        self, session_id: str, terminal_id: str, **kwargs: Any
    ) -> ReleaseTerminalResponse | None:
        raise RequestError.method_not_found("terminal/release")

    async def wait_for_terminal_exit(
        self, session_id: str, terminal_id: str, **kwargs: Any
    ) -> WaitForTerminalExitResponse:
        raise RequestError.method_not_found("terminal/wait_for_exit")

    async def kill_terminal(
        self, session_id: str, terminal_id: str, **kwargs: Any
    ) -> KillTerminalResponse | None:
        raise RequestError.method_not_found("terminal/kill")

    async def session_update(
        self,
        session_id: str,
        update: UpdatePayload,
        **kwargs: Any,
    ) -> None:
        self._queues[session_id].put_nowait(update)

    async def ext_method(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        raise RequestError.method_not_found(method)

    async def ext_notification(self, method: str, params: dict[str, Any]) -> None:
        raise RequestError.method_not_found(method)
