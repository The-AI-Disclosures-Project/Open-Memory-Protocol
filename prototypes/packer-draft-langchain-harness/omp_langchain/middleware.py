"""OpenMemoryMiddleware: the OMP harness contract as LangChain `create_agent` middleware.

Spec: spec/draft-v0.2-packer.pdf §Harness contract. A conforming harness:

1. Keeps top-level .md files at least partially in context at all times.
2. Defers nested .md files (not auto-loaded).
3. Surfaces deferred memory one level down so the agent knows it exists.
4. Supports selective reads of deferred files through a tool.

Mapping onto create_agent middleware hooks:

- `wrap_model_call` re-reads the memory directory from disk before every model call and
  appends core memory (rule 1) plus the deferred index (rule 3) to the system message.
  Re-reading each call means edits made mid-conversation (by the agent or a human) are
  reflected on the next step, which the spec leaves to the harness.
- `tools` registers `read_memory` (rule 4) and, optionally, `write_memory`, which enforces
  the spec's size guidance at edit time (§Size guidance: "Harnesses can enforce size
  limitations at edit time").
- Rule 2 is satisfied by construction: nothing below the root is ever rendered by rule 1.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal

from langchain.agents import create_agent
from langchain.agents.middleware import AgentMiddleware, ModelRequest, ModelResponse
from langchain.messages import SystemMessage
from langchain.tools import tool
from open_memory_protocol import MemoryDirectory, load_memory
from open_memory_protocol.types import ROOT_INDEX_FILENAME

from omp_langchain.memory_index import (
    DEFAULT_MAX_FILE_CHARS,
    DEFAULT_MAX_TOTAL_TOKENS,
    deferred_entries,
    estimate_tokens,
    render_core_context,
    render_deferred_index,
    render_directory_listing,
)
from omp_langchain.models import DEFAULT_MODEL, resolve_model

logger = logging.getLogger(__name__)

DEFAULT_SYSTEM_PROMPT = (
    "You are an agent with persistent, file-based memory that follows the Open Memory "
    "Protocol. Memory comes in two tiers:\n"
    "1. CORE memory: every root-level file is reproduced IN FULL below. You already have "
    "their complete contents; never call `read_memory` on a root-level file.\n"
    "2. DEFERRED memory: files in subdirectories are NOT loaded. Only an index of them is "
    "shown. When a task touches something in that index, call `read_memory` on the path "
    "(a directory path returns its MEMORY.md plus a listing of what is inside).\n"
    "If asked what you can see without tool use, the answer is exactly the core files' "
    "full contents plus the deferred index, nothing more."
)

MEMORY_SECTION_HEADER = (
    "## Core memory (root-level files, FULL CONTENTS, already loaded; do not read_memory these)"
)
DEFERRED_SECTION_HEADER = (
    "## Deferred memory index (NOT loaded; only paths and descriptions are visible; "
    "call `read_memory` to load)"
)


class OpenMemoryMiddleware(AgentMiddleware):
    """Implements the OMP four-rule harness contract for a LangChain agent."""

    def __init__(
        self,
        memory_root: str | Path,
        *,
        max_file_chars: int | None = DEFAULT_MAX_FILE_CHARS,
        max_total_tokens: int | None = DEFAULT_MAX_TOTAL_TOKENS,
        writable: bool = False,
        enforce_size_on_write: bool = True,
    ) -> None:
        self.memory_root = Path(memory_root).resolve()
        self.max_file_chars = max_file_chars
        self.max_total_tokens = max_total_tokens
        self.writable = writable
        self.enforce_size_on_write = enforce_size_on_write
        self.last_stats: dict[str, Any] | None = None
        """Statistics from the most recent render (consumed by TraceMiddleware)."""

        # Validate eagerly so misconfiguration fails at construction, not first model call.
        load_memory(self.memory_root)

        # Tools are bound to this memory root, so they are built per instance rather than
        # declared as a class attribute. create_agent reads `middleware.tools` at compile time.
        self.tools = [self._build_read_tool()]
        if writable:
            self.tools.append(self._build_write_tool())

    # ----------------------------------------------------------------- helpers

    def _load(self) -> MemoryDirectory:
        return load_memory(self.memory_root)

    def _resolve(self, relative_path: str) -> Path:
        """Resolve a path the model supplied, refusing anything outside the memory root."""
        rel = relative_path.strip().lstrip("/")
        target = (self.memory_root / rel).resolve()
        if target != self.memory_root and self.memory_root not in target.parents:
            raise ValueError(f"Path escapes memory root: {relative_path!r}")
        return target

    def render_memory_block(self) -> str:
        """The exact text appended to the system prompt on every model call."""
        memory = self._load()
        core, warnings = render_core_context(memory, max_file_chars=self.max_file_chars)
        for w in warnings:
            logger.warning("OMP size guidance: %s", w)
        if self.max_total_tokens is not None:
            est = estimate_tokens(core)
            if est > self.max_total_tokens:
                logger.warning(
                    "OMP size guidance: core memory ~%d tokens exceeds recommended %d",
                    est,
                    self.max_total_tokens,
                )
        deferred = render_deferred_index(memory)
        block = (
            f"{MEMORY_SECTION_HEADER}\n\nMemory root: `{self.memory_root}`\n\n"
            f"{core}\n{DEFERRED_SECTION_HEADER}\n\n{deferred}\n"
        )
        entries = deferred_entries(memory)
        truncated_paths = {w.split(" ")[0] for w in warnings}
        self.last_stats = {
            "core_files": [
                {
                    "path": str(f.relative_path),
                    "chars": len(f.read()),
                    "truncated": str(f.relative_path) in truncated_paths,
                }
                for f in memory.core_files
            ],
            "core_tokens_est": estimate_tokens(core),
            "truncated": bool(warnings),
            "deferred_dirs": sum(1 for e in entries if e.is_dir),
            "deferred_files": sum(1 for e in entries if not e.is_dir),
            "external_files_total": len(memory.external_files),
            "block_chars": len(block),
            "block": block,
        }
        return block

    # ------------------------------------------------------------------- rule 4

    def _build_read_tool(self):
        middleware = self

        @tool("read_memory")
        def read_memory(path: str) -> str:
            """Read a deferred memory file or directory by path relative to the memory root.

            Pass a markdown file path (e.g. "notes/2026-08-12.md") to get its contents, or a
            directory path (e.g. "projects") to get that directory's MEMORY.md and a listing
            of what it contains, one level down. Use this whenever the deferred memory index
            in your system prompt lists something relevant to the current task.
            """
            try:
                target = middleware._resolve(path)
            except ValueError as e:
                return f"error: {e}"
            memory = middleware._load()
            if target.is_dir():
                return render_directory_listing(memory, target)
            if not target.exists():
                return f"error: no memory at {path!r}. Check the deferred index for valid paths."
            if target.suffix != ".md":
                return f"error: {path!r} is not a markdown memory file."
            text = target.read_text(encoding="utf-8")
            if target.parent == middleware.memory_root:
                return (
                    f"note: {path!r} is a root-level core file; it is already in your context "
                    f"in full unless marked truncated.\n\n{text}"
                )
            return text

        return read_memory

    # ---------------------------------------------------------- optional writes

    def _build_write_tool(self):
        middleware = self

        @tool("write_memory")
        def write_memory(
            path: str,
            content: str,
            mode: Literal["append", "replace"] = "append",
        ) -> str:
            """Append to or replace a markdown memory file, relative to the memory root.

            Keep root-level files small: they are always in context. Put detailed or
            historical material in a subdirectory (which must contain a MEMORY.md) so it is
            progressively disclosed instead. Creates parent directories and a placeholder
            MEMORY.md in new subdirectories so the memory stays spec-valid.
            """
            try:
                target = middleware._resolve(path)
            except ValueError as e:
                return f"error: {e}"
            if target.suffix != ".md":
                return "error: memory files must end in .md"

            existing = target.read_text(encoding="utf-8") if target.exists() else ""
            new_text = (
                (existing.rstrip("\n") + "\n\n" + content.strip() + "\n")
                if (mode == "append" and existing)
                else content.rstrip("\n") + "\n"
            )

            is_root_level = target.parent == middleware.memory_root
            if (
                is_root_level
                and middleware.enforce_size_on_write
                and middleware.max_file_chars is not None
                and len(new_text) > middleware.max_file_chars
            ):
                return (
                    f"error: write refused. {path!r} would be {len(new_text)} characters, over "
                    f"the {middleware.max_file_chars}-character limit for root-level (always "
                    "in-context) memory. Move detail into a subdirectory instead."
                )

            target.parent.mkdir(parents=True, exist_ok=True)
            # Keep every directory spec-valid (each must have a MEMORY.md).
            d = target.parent
            while d != middleware.memory_root:
                idx = d / ROOT_INDEX_FILENAME
                if not idx.exists():
                    idx.write_text(
                        f"# {d.name}\n\nIndex of memory in this directory.\n", encoding="utf-8"
                    )
                d = d.parent
            target.write_text(new_text, encoding="utf-8")
            return f"ok: wrote {len(new_text)} characters to {path}"

        return write_memory

    # --------------------------------------------------------------- rules 1+3

    def _inject(self, request: ModelRequest) -> ModelRequest:
        block = self.render_memory_block()
        if request.system_message is not None:
            blocks = list(request.system_message.content_blocks)
        else:
            blocks = []
        blocks.append({"type": "text", "text": "\n\n" + block})
        return request.override(system_message=SystemMessage(content=blocks))

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        return handler(self._inject(request))

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Any],
    ) -> ModelResponse:
        return await handler(self._inject(request))


def create_omp_agent(
    memory_root: str | Path,
    model: Any = DEFAULT_MODEL,
    *,
    tools: list | None = None,
    system_prompt: str = DEFAULT_SYSTEM_PROMPT,
    middleware: list | None = None,
    writable: bool = False,
    trace: list | Any | None = None,
    **kwargs: Any,
):
    """Build a `create_agent` harness whose memory follows the OMP contract.

    `model` may be a chat model instance or a string: "openrouter:<model>" (e.g. the default
    "openrouter:nvidia/nemotron-3-nano-30b-a3b", needs OPENROUTER_API_KEY) or any
    `init_chat_model` string like "anthropic:claude-sonnet-4-6".
    Extra middleware runs after OpenMemoryMiddleware, so it sees the injected memory block.
    `trace` is a sink or list of sinks (see omp_langchain.trace) that receive a live trace of
    model calls, tool calls, and memory statistics. The TraceMiddleware is exposed on the
    returned agent as `agent.omp_trace` (None if no trace was requested), and the memory
    middleware as `agent.omp_memory`.
    """
    from omp_langchain.trace import TraceMiddleware

    omp = OpenMemoryMiddleware(memory_root, writable=writable)
    stack: list = [omp]
    tracer = None
    if trace is not None:
        tracer = TraceMiddleware(trace, memory=omp)
        stack.append(tracer)
    stack.extend(middleware or [])
    agent = create_agent(
        resolve_model(model),
        tools=tools or [],
        system_prompt=system_prompt,
        middleware=stack,
        **kwargs,
    )
    agent.omp_trace = tracer
    agent.omp_memory = omp
    return agent
