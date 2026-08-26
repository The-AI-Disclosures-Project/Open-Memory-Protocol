"""Convert ACP `SessionUpdate` variants into flat IndexedTurn rows."""

from __future__ import annotations

import json
import time
from typing import Any

from acp.schema import (
    AgentMessageChunk,
    AgentPlanUpdate,
    AgentThoughtChunk,
    AudioContentBlock,
    AvailableCommandsUpdate,
    ConfigOptionUpdate,
    CurrentModeUpdate,
    EmbeddedResourceContentBlock,
    ImageContentBlock,
    ResourceContentBlock,
    SessionInfoUpdate,
    TextContentBlock,
    ToolCallProgress,
    ToolCallStart,
    UsageUpdate,
    UserMessageChunk,
)

from acp_memory_server.models import IndexedTurn

UpdateUnion = (
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


def _content_to_text(content: Any) -> str:
    if isinstance(content, TextContentBlock):
        return content.text or ""
    if isinstance(content, ImageContentBlock):
        return "<image>"
    if isinstance(content, AudioContentBlock):
        return "<audio>"
    if isinstance(content, ResourceContentBlock):
        return getattr(content, "uri", None) or "<resource>"
    if isinstance(content, EmbeddedResourceContentBlock):
        return "<resource>"
    if isinstance(content, list):
        return "".join(_content_to_text(c) for c in content)
    if isinstance(content, str):
        return content
    return ""


def _safe_dump(model: Any) -> str:
    """Best-effort JSON dump of a Pydantic model or plain object."""
    try:
        if hasattr(model, "model_dump_json"):
            return model.model_dump_json(by_alias=True)
        if hasattr(model, "model_dump"):
            return json.dumps(model.model_dump(by_alias=True), default=str)
        return json.dumps(model, default=str)
    except Exception:  # noqa: BLE001
        return ""


def normalize_update(
    agent_id: str,
    session_id: str,
    turn_index: int,
    update: UpdateUnion,
) -> IndexedTurn | None:
    """Map a session/update payload to a single IndexedTurn, or None to skip.

    Only message/thought/tool-call updates carry transcript content worth indexing.
    Status/plan/mode updates are dropped (they're transient UI signals)."""
    now = int(time.time())
    raw = _safe_dump(update)

    if isinstance(update, UserMessageChunk):
        return IndexedTurn(
            agent_id=agent_id,
            session_id=session_id,
            turn_index=turn_index,
            role="user",
            content_text=_content_to_text(update.content),
            raw_blob=raw,
            ts=now,
        )

    if isinstance(update, AgentMessageChunk):
        return IndexedTurn(
            agent_id=agent_id,
            session_id=session_id,
            turn_index=turn_index,
            role="agent",
            content_text=_content_to_text(update.content),
            raw_blob=raw,
            ts=now,
        )

    if isinstance(update, AgentThoughtChunk):
        return IndexedTurn(
            agent_id=agent_id,
            session_id=session_id,
            turn_index=turn_index,
            role="thought",
            content_text=_content_to_text(update.content),
            raw_blob=raw,
            ts=now,
        )

    if isinstance(update, ToolCallStart):
        # ToolCallStart fields: tool_call_id, title, kind, status, content (list), raw_input, locations
        title = getattr(update, "title", None) or ""
        tool_kind = getattr(update, "kind", None) or ""
        raw_input = getattr(update, "raw_input", None)
        try:
            tool_args_json = (
                json.dumps(raw_input, default=str) if raw_input is not None else None
            )
        except Exception:  # noqa: BLE001
            tool_args_json = None
        content_chunks = getattr(update, "content", None) or []
        content_text = " ".join(
            _content_to_text(getattr(c, "content", c)) for c in content_chunks
        )
        return IndexedTurn(
            agent_id=agent_id,
            session_id=session_id,
            turn_index=turn_index,
            role="tool",
            content_text=f"{title} {content_text}".strip(),
            tool_name=str(tool_kind or title or "tool"),
            tool_args_json=tool_args_json,
            raw_blob=raw,
            ts=now,
        )

    if isinstance(update, ToolCallProgress):
        content_chunks = getattr(update, "content", None) or []
        content_text = " ".join(
            _content_to_text(getattr(c, "content", c)) for c in content_chunks
        )
        if not content_text:
            return None
        return IndexedTurn(
            agent_id=agent_id,
            session_id=session_id,
            turn_index=turn_index,
            role="tool",
            content_text=content_text,
            tool_name=getattr(update, "title", None) or "tool",
            raw_blob=raw,
            ts=now,
        )

    # Other updates (plan, available commands, mode, usage) carry no durable transcript content.
    return None
