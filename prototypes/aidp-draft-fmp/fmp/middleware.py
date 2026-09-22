"""FMP as LangChain `create_agent` middleware (draft tier 2: plugin with hooks + tools).

- `search_memory` tool  : fan-out search across every connected server (Recall).
- `remember` tool       : store an inference, routed to one named server or all that accept.
- `after_agent` hook    : upload the run's transcript to every server configured to receive it
                          (the draft's "hooks to capture full transcripts automatically").
- system prompt addendum: lists the connected servers and their policies so the model knows
                          where memory lives and where it will be sent.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Any

from langchain.agents.middleware import AgentMiddleware, ModelRequest, ModelResponse
from langchain.messages import SystemMessage
from langchain.tools import tool

from fmp.client import FederatedMemory, FMPError
from fmp.schema import CreatedBy, InferenceUpload, MemoryType, Message, TranscriptUpload, now_iso

FMP_SECTION_HEADER = "## Federated memory (FMP)"


def _lc_to_messages(messages: list[Any]) -> list[Message]:
    out = []
    for m in messages:
        t = getattr(m, "type", "")
        role = {"human": "user", "ai": "assistant", "tool": "tool", "system": "system"}.get(t)
        if role is None:
            continue
        text = m.text if hasattr(m, "text") else str(m.content)
        meta: dict[str, Any] = {}
        if t == "ai" and getattr(m, "tool_calls", None):
            meta["tool_calls"] = [{"name": tc["name"], "args": tc["args"]} for tc in m.tool_calls]
        out.append(
            Message(
                role=role,
                content=text,
                ts=now_iso(),
                tool_name=getattr(m, "name", None) if t == "tool" else None,
                metadata=meta,
            )
        )
    return out


class FMPMiddleware(AgentMiddleware):
    def __init__(
        self,
        memory: FederatedMemory,
        *,
        agent_name: str = "langchain",
        model_name: str | None = None,
        upload_transcripts: bool = True,
        session_id: str | None = None,
    ) -> None:
        self.memory = memory
        self.agent_name = agent_name
        self.model_name = model_name
        self.upload_transcripts = upload_transcripts
        self.session_id = session_id or uuid.uuid4().hex
        self.last_upload: dict[str, str] = {}
        self.tools = [self._search_tool(), self._remember_tool()]

    # --- tools -----------------------------------------------------------------

    def _search_tool(self):
        fm = self.memory

        @tool("search_memory")
        def search_memory(query: str, types: list[str] | None = None, limit: int = 8) -> str:
            """Search the user's memory across every connected memory server.

            Returns the best-matching snippets with the server they came from and a `ref`
            you can cite in `remember(based_on=[...])`. `types` may restrict to
            "file", "transcript" and/or "inference".
            """
            mts = [MemoryType(t) for t in types] if types else None
            try:
                hits = fm.search(query, types=mts, limit=limit)
            except (FMPError, ValueError) as e:
                return f"error: {e}"
            if not hits:
                return "no matches" + (
                    f" (errors: {'; '.join(fm.last_errors)})" if fm.last_errors else ""
                )
            lines = [
                f"[{h.server}] {h.type.value} {h.ts or ''} ref={h.ref}\n    {h.snippet}"
                for h in hits
            ]
            if fm.last_errors:
                lines.append(f"(some servers failed: {'; '.join(fm.last_errors)})")
            return "\n".join(lines)

        return search_memory

    def _remember_tool(self):
        mw = self

        @tool("remember")
        def remember(
            content: str, based_on: list[str] | None = None, server: str | None = None
        ) -> str:
            """Save an inference about the user or their work to memory.

            `content` should be a single durable fact in plain language. `based_on` lists
            refs from search results or "transcript:<session>#<turn>". `server` routes to one
            named memory server; omit to store on every server that accepts inferences.
            """
            inf = InferenceUpload(
                content=content,
                based_on=based_on or [f"transcript:{mw.session_id}"],
                created_by=CreatedBy(kind="agent", name=mw.agent_name, model=mw.model_name),
            )
            try:
                ids = mw.memory.remember(inf, server=server)
            except FMPError as e:
                return f"error: {e}"
            if not ids:
                return "error: no connected server accepts inferences"
            return "stored on " + ", ".join(f"{k} (id {v[:8]})" for k, v in ids.items())

        return remember

    # --- hooks -----------------------------------------------------------------

    def _inject(self, request: ModelRequest) -> ModelRequest:
        block = (
            f"{FMP_SECTION_HEADER}\n\nYou are connected to these memory servers. Use "
            f"`search_memory` before answering questions about the user's history or past work, "
            f"and `remember` to save durable facts.\n{self.memory.describe()}\n"
        )
        blocks = list(request.system_message.content_blocks) if request.system_message else []
        blocks.append({"type": "text", "text": "\n\n" + block})
        return request.override(system_message=SystemMessage(content=blocks))

    def wrap_model_call(
        self, request: ModelRequest, handler: Callable[[ModelRequest], ModelResponse]
    ) -> ModelResponse:
        return handler(self._inject(request))

    async def awrap_model_call(
        self, request: ModelRequest, handler: Callable[[ModelRequest], Any]
    ) -> ModelResponse:
        return await handler(self._inject(request))

    def _upload(self, state: Any) -> None:
        if not self.upload_transcripts:
            return
        msgs = _lc_to_messages(state.get("messages", []))
        if not msgs:
            return
        t = TranscriptUpload(
            id=self.session_id,
            source=self.agent_name,
            messages=msgs,
            title=next((m.content[:80] for m in msgs if m.role == "user"), None),
            metadata={"model": self.model_name},
        )
        try:
            self.last_upload = self.memory.upload_transcript(t)
        except Exception as e:  # noqa: BLE001 - never fail the run because memory is down
            self.last_upload = {"error": str(e)}

    def after_agent(self, state: Any, runtime: Any) -> None:
        self._upload(state)

    async def aafter_agent(self, state: Any, runtime: Any) -> None:
        self._upload(state)
