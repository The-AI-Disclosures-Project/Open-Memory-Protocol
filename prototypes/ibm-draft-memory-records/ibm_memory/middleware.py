"""The IBM draft's four runtime attachment formats as LangChain create_agent middleware.

    Write:  Remember  proactive tool-call
            Observe   conversation hook (read-only)
    Read:   Recall    proactive tool-call
            Decorate  conversation hook (mutating)

- Remember -> `remember` tool. Scope tags are "added systematically (no agent-defined
  scope tags)": the middleware stamps its configured write scope; the model only supplies
  body and semantic tags.
- Recall   -> `recall` tool with query seed, optional timestamp, semantic and scope tags.
  Scopes are validated against the ScopePolicy; a denied scope is an error the model sees.
- Observe  -> `after_agent`: reads the conversation (does not change it) and stores the
  user's turns verbatim as records with ai_used=False, so later inferences have ground truth
  to cite.
- Decorate -> `wrap_model_call`: recalls records relevant to the latest user message and
  injects them into the system prompt (this *does* change the conversation the model sees).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from langchain.agents.middleware import AgentMiddleware, ModelRequest, ModelResponse
from langchain.messages import SystemMessage
from langchain.tools import tool

from ibm_memory.schema import MemoryRecord, Provenance
from ibm_memory.store import MemoryStore, ScopeDenied

DECORATE_HEADER = "## Recalled memories (IBM draft: Decorate hook)"


def _fmt(r: MemoryRecord) -> str:
    lc = r.lifecycle
    prov = "AI" if lc.provenance.ai_used else "human"
    tags = " ".join(f"#{t}" for t in r.semantic_tags if not t.startswith("description:"))
    return f"- [{r.id[:8]} v{lc.version} {lc.created_at[:10]} by {lc.author}/{prov} scope={','.join(r.scope_tags)}] {r.body.strip()} {tags}".rstrip()


class IBMMemoryMiddleware(AgentMiddleware):
    def __init__(
        self,
        store: MemoryStore,
        *,
        principal: str,
        write_scopes: list[str],
        author: str | None = None,
        agent_name: str = "langchain",
        model_name: str | None = None,
        observe: bool = True,
        decorate: bool = True,
        decorate_limit: int = 5,
    ) -> None:
        self.store = store
        self.principal = principal
        self.write_scopes = list(write_scopes)
        self.author = author or principal
        self.agent_name = agent_name
        self.model_name = model_name
        self.observe = observe
        self.decorate = decorate
        self.decorate_limit = decorate_limit
        self.last_decorated: list[MemoryRecord] = []
        self.last_observed: list[MemoryRecord] = []
        self.tools = [self._remember_tool(), self._recall_tool()]

    # ------------------------------------------------------------ Remember
    def _remember_tool(self):
        mw = self

        @tool("remember")
        def remember(
            body: str,
            semantic_tags: list[str] | None = None,
            source_material: list[str] | None = None,
            supersedes: str | None = None,
        ) -> str:
            """Store a durable memory. Provide the body and optional semantic tags.

            Scope is assigned by the harness, not by you. To correct an existing memory pass
            its id in `supersedes`; the old one is invalidated, never edited. Cite what the
            memory is based on in `source_material` (ids from recall, or "conversation").
            """
            prov = Provenance(
                ai_used=True,
                model=mw.model_name,
                agent=mw.agent_name,
                how="inferred by agent during conversation",
            )
            try:
                if supersedes:
                    rec = mw.store.override(
                        supersedes,
                        body,
                        author=mw.author,
                        provenance=prov,
                        semantic_tags=semantic_tags,
                        source_material=source_material or [],
                        principal=mw.principal,
                    )
                else:
                    rec = mw.store.write(
                        body,
                        author=mw.author,
                        provenance=prov,
                        semantic_tags=semantic_tags or [],
                        scope_tags=mw.write_scopes,
                        source_material=source_material or ["conversation"],
                        principal=mw.principal,
                    )
            except ScopeDenied as e:
                return f"error: {e}"
            except KeyError as e:
                return f"error: {e.args[0]}"
            return f"stored {rec.id[:8]} v{rec.lifecycle.version} scope={','.join(rec.scope_tags)}"

        return remember

    # ------------------------------------------------------------ Recall
    def _recall_tool(self):
        mw = self

        @tool("recall")
        def recall(
            query: str,
            at: str | None = None,
            semantic_tags: list[str] | None = None,
            scope_tags: list[str] | None = None,
            limit: int = 10,
        ) -> str:
            """Search memory. `at` (ISO-8601) answers "what was true then" instead of now.

            `scope_tags` narrows to specific scopes; you may only read scopes you are
            allowed, and asking for another is an error. Omit it to search everything you
            may read. Results include ids for use in `remember(supersedes=...)`.
            """
            try:
                recs = mw.store.recall(
                    query,
                    principal=mw.principal,
                    at=at,
                    semantic_tags=semantic_tags or [],
                    scope_tags=scope_tags,
                    limit=limit,
                )
            except ScopeDenied as e:
                return f"error: {e}"
            return "\n".join(_fmt(r) for r in recs) if recs else "no matching memories"

        return recall

    # ------------------------------------------------------------ Decorate
    def _inject(self, request: ModelRequest) -> ModelRequest:
        blocks = list(request.system_message.content_blocks) if request.system_message else []
        text = (
            "\n\n## Memory (IBM draft)\nYou have `recall` and `remember` tools. Scope assigned to "
            f"anything you remember: {', '.join(self.write_scopes)}. Memories are immutable: "
            "correct one with remember(supersedes=<id>), never by re-stating it."
        )
        self.last_decorated = []
        if self.decorate:
            last_user = next((m for m in reversed(request.messages) if m.type == "human"), None)
            if last_user is not None:
                q = last_user.text if hasattr(last_user, "text") else str(last_user.content)
                self.last_decorated = self.store.recall(
                    q, principal=self.principal, limit=self.decorate_limit
                )
                if self.last_decorated:
                    text += f"\n\n{DECORATE_HEADER}\n" + "\n".join(
                        _fmt(r) for r in self.last_decorated
                    )
        blocks.append({"type": "text", "text": text})
        return request.override(system_message=SystemMessage(content=blocks))

    def wrap_model_call(
        self, request: ModelRequest, handler: Callable[[ModelRequest], ModelResponse]
    ) -> ModelResponse:
        return handler(self._inject(request))

    async def awrap_model_call(
        self, request: ModelRequest, handler: Callable[[ModelRequest], Any]
    ) -> ModelResponse:
        return await handler(self._inject(request))

    # ------------------------------------------------------------ Observe
    def _observe(self, state: Any) -> None:
        self.last_observed = []
        if not self.observe:
            return
        msgs = state.get("messages", [])
        # store only user turns not yet observed (by body match within this store)
        seen = {r.body.strip() for r in self.store.all() if "observation" in r.semantic_tags}
        for m in msgs:
            if m.type != "human":
                continue
            text = (m.text if hasattr(m, "text") else str(m.content)).strip()
            if not text or text in seen:
                continue
            rec = self.store.write(
                text,
                author=self.author,
                provenance=Provenance(
                    ai_used=False,
                    agent=self.agent_name,
                    how="verbatim user turn captured by Observe hook",
                ),
                semantic_tags=["observation"],
                scope_tags=self.write_scopes,
                source_material=["conversation"],
                principal=self.principal,
            )
            self.last_observed.append(rec)

    def after_agent(self, state: Any, runtime: Any) -> None:
        self._observe(state)

    async def aafter_agent(self, state: Any, runtime: Any) -> None:
        self._observe(state)
