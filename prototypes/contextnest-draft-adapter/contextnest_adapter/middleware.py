"""Context Nest as LangChain create_agent middleware.

The harness side of the proposal, and nothing more:

- `wrap_model_call` loads a named set of memories (a selector or `pack:<id>`, CN §2-§3) into
  the system prompt before every model call. The set is resolved by `ctx`, so only
  `published` documents can reach the model (CN §1.5.1). Each loaded document is labelled
  with its `contextnest://` URI and marked as loaded in full.
- `nest_query` lets the model name a further set by selector; `nest_search` is full-text.
- `nest_propose` (only when `writable=True`) writes a new memory as `pending_review`. An
  agent can propose; a person publishes. Until then the resolver will not serve it.
- `reads` records every set the agent saw: selector, resolved ids, and the nest checkpoint
  when `ctx` can report it, so "what did the agent know" has an answer after the fact.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

from langchain.agents.middleware import AgentMiddleware, ModelRequest, ModelResponse
from langchain.messages import SystemMessage
from langchain.tools import tool

from contextnest_adapter.ctx import CtxClient, CtxError, QueryResult

SELECTOR_HELP = (
    "Selector grammar: atoms `#tag`, `type:X`, `status:X`, `pack:<id>`, `nodes/<id>`; "
    "combine with `+` or a space (AND), `|` (OR), `-` (NOT), and parentheses. "
    'Example: "#project-omp -#archive".'
)
MAX_DOC_CHARS = 6000


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60] or "memory"


def _render(res: QueryResult, *, full: bool) -> str:
    if not res.documents:
        return f"(selector `{res.selector}` resolved to no published documents)"
    parts = []
    for d in res.documents:
        if full:
            body = d.body.strip()
            if len(body) > MAX_DOC_CHARS:
                body = body[:MAX_DOC_CHARS] + "\n[... truncated by harness]"
            parts.append(f"### {d.title}\n<{d.uri}> (loaded in full)\n\n{body}")
        else:
            parts.append(f"- {d.title} <{d.uri}>")
    return "\n\n".join(parts) if full else "\n".join(parts)


class ContextNestMiddleware(AgentMiddleware):
    def __init__(
        self,
        client: CtxClient,
        *,
        load: str | None = None,
        hops: int = 0,
        writable: bool = False,
        propose_folder: str = "nodes/memory",
    ) -> None:
        self.client = client
        self.load = load
        self.hops = hops
        self.writable = writable
        self.propose_folder = propose_folder.rstrip("/")
        self.reads: list[dict[str, Any]] = []
        self.proposed: list[str] = []
        self._checkpoint = client.latest_checkpoint()
        self.tools = [self._query_tool(), self._search_tool()]
        if writable:
            self.tools.append(self._propose_tool())

    # ------------------------------------------------------------------ trace
    def _record(self, res: QueryResult, via: str) -> None:
        self.reads.append(
            {
                "via": via,
                "selector": res.selector,
                "ids": res.ids,
                "checkpoint": (self._checkpoint or {}).get("checkpoint"),
                "nest": self.client.location,
            }
        )

    # ------------------------------------------------------------------ tools
    def _query_tool(self):
        mw = self

        @tool("nest_query")
        def nest_query(selector: str, hops: int = 0) -> str:
            """Load published memories named by a selector, with their full text.

            Use this to pull in a specific set, e.g. "#project-omp", "type:persona",
            "nodes/people/sruly", or "pack:<id>". `hops` follows links out from the set.
            """
            try:
                res = mw.client.query(selector, hops=hops)
            except CtxError as e:
                return f"error: {e}"
            mw._record(res, "tool")
            return _render(res, full=True)

        nest_query.description += "\n\n" + SELECTOR_HELP
        return nest_query

    def _search_tool(self):
        mw = self

        @tool("nest_search")
        def nest_search(text: str, limit: int = 8) -> str:
            """Full-text search. Returns titles and ids; load the ones you need with nest_query."""
            try:
                hits = mw.client.search(text, limit=limit)
            except CtxError as e:
                return f"error: {e}"
            if not hits:
                return "no matches"
            return "\n".join(
                f"- {h.get('title', h.get('id'))} <contextnest://{h.get('id')}>" for h in hits
            )

        return nest_search

    def _propose_tool(self):
        mw = self

        @tool("nest_propose")
        def nest_propose(title: str, body: str, tags: list[str] | None = None) -> str:
            """Propose a new durable memory. It is saved for human review, not served yet.

            Give it a short title, the memory in Markdown, and `#`-prefixed tags.
            """
            node_id = f"{mw.propose_folder}/{_slug(title)}"
            tags = [t if t.startswith("#") else f"#{t}" for t in (tags or [])]
            try:
                mw.client.propose(node_id, title=title, body=body, tags=tags)
            except CtxError as e:
                return f"error: {e}"
            mw.proposed.append(node_id)
            return f"proposed <contextnest://{node_id}> as pending_review; a person must publish it"

        return nest_propose

    # ------------------------------------------------------------------ context injection
    def render_context_block(self) -> str:
        text = (
            "## Memory (Context Nest)\n"
            f"Your memory is a Context Nest at {self.client.location}. Only published, "
            "approved memories are served to you. Load more with `nest_query`; find things "
            "with `nest_search`."
        )
        if self.writable:
            text += " Propose new memories with `nest_propose`; they wait for human review."
        if self.load:
            res = self.client.query(self.load, hops=self.hops)
            self._record(res, "preload")
            text += (
                f"\n\nThe documents below were resolved from `{self.load}` and are loaded in "
                "full. They are the content, not an index.\n\n" + _render(res, full=True)
            )
        return text

    def _inject(self, request: ModelRequest) -> ModelRequest:
        blocks = list(request.system_message.content_blocks) if request.system_message else []
        blocks.append({"type": "text", "text": self.render_context_block()})
        return request.override(system_message=SystemMessage(content=blocks))

    def wrap_model_call(
        self, request: ModelRequest, handler: Callable[[ModelRequest], ModelResponse]
    ) -> ModelResponse:
        return handler(self._inject(request))

    async def awrap_model_call(
        self, request: ModelRequest, handler: Callable[[ModelRequest], Any]
    ) -> ModelResponse:
        return await handler(self._inject(request))
