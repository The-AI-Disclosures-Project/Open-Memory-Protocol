"""Visibility into what the harness is doing.

`TraceMiddleware` sits inside `OpenMemoryMiddleware` in the middleware stack, so it sees the
system prompt *after* memory injection. It emits one `TraceEvent` per:

- model call     : step, message count, memory stats (which root files, sizes, truncation,
                   deferred entries), estimated prompt size
- model response : latency, token usage, text preview, requested tool calls
- tool call      : name, args
- tool result    : latency, result size, preview, error flag

Events go to one or more sinks. `ConsoleSink` prints a readable live trace to stderr;
`JsonlSink` appends machine-readable lines; `ListSink` collects for tests.
"""

from __future__ import annotations

import json
import sys
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, ClassVar, TextIO

from langchain.agents.middleware import AgentMiddleware, ModelRequest, ModelResponse
from langchain.tools.tool_node import ToolCallRequest

from omp_langchain.memory_index import estimate_tokens

Sink = Callable[["TraceEvent"], None]


@dataclass
class TraceEvent:
    kind: str  # model_call | model_response | tool_call | tool_result
    step: int
    data: dict[str, Any] = field(default_factory=dict)
    ts: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="milliseconds")
    )

    def to_json(self) -> str:
        return json.dumps(asdict(self), default=str)


def _arg_summary(args: dict[str, Any]) -> str:
    """The one argument a human wants to see: a path, a query, or the first string."""
    for key in ("path", "query", "content"):
        if key in args:
            return _preview(args[key], 60)
    for v in args.values():
        if isinstance(v, str):
            return _preview(v, 60)
    return ""


def _preview(text: Any, n: int) -> str:
    s = str(text).replace("\n", "⏎ ")
    return s if len(s) <= n else s[:n] + f"… (+{len(s) - n} chars)"


# --------------------------------------------------------------------------- sinks


class ListSink:
    """Collects events in memory (for tests and programmatic inspection)."""

    def __init__(self) -> None:
        self.events: list[TraceEvent] = []

    def __call__(self, event: TraceEvent) -> None:
        self.events.append(event)


class JsonlSink:
    """Appends one JSON object per event to a file."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def __call__(self, event: TraceEvent) -> None:
        with self.path.open("a", encoding="utf-8") as f:
            f.write(event.to_json() + "\n")


class ConsoleSink:
    """Human-readable live trace. `level` 1 = summary lines, 2 = full previews."""

    _C: ClassVar[dict[str, str]] = {
        "dim": "\033[2m",
        "bold": "\033[1m",
        "cyan": "\033[36m",
        "green": "\033[32m",
        "yellow": "\033[33m",
        "magenta": "\033[35m",
        "red": "\033[31m",
        "reset": "\033[0m",
    }

    def __init__(
        self, stream: TextIO | None = None, *, level: int = 1, color: bool | None = None
    ) -> None:
        self.stream = stream or sys.stderr
        self.level = level
        self.color = self.stream.isatty() if color is None else color
        self.preview_len = 2000 if level >= 2 else 160

    def _c(self, name: str, text: str) -> str:
        return f"{self._C[name]}{text}{self._C['reset']}" if self.color else text

    def _line(self, text: str = "") -> None:
        print(text, file=self.stream, flush=True)

    def __call__(self, e: TraceEvent) -> None:
        d = e.data
        tag = self._c("dim", f"[step {e.step}]")
        if e.kind == "model_call":
            self._line(
                f"{tag} {self._c('cyan', '→ model')} {d['model']}  "
                f"messages={d['message_count']}  ~prompt_tokens={d['prompt_tokens_est']}"
            )
            mem = d.get("memory")
            if mem:
                files = ", ".join(
                    f"{f['path']}({f['chars']}c{'*' if f['truncated'] else ''})"
                    for f in mem["core_files"]
                )
                self._line(
                    f"{'':9}{self._c('dim', 'memory:')} core=[{files}] "
                    f"~{mem['core_tokens_est']} tok; deferred={mem['deferred_dirs']} dirs / "
                    f"{mem['deferred_files']} files listed"
                    + (self._c("yellow", "  (* = truncated)") if mem["truncated"] else "")
                )
                if self.level >= 2:
                    self._line(self._c("dim", "         --- injected memory block ---"))
                    for ln in mem["block"].splitlines():
                        self._line(self._c("dim", "         │ ") + ln)
                    self._line(self._c("dim", "         --- end memory block ---"))
        elif e.kind == "model_response":
            usage = d.get("usage") or {}
            u = (
                f"  tokens in/out={usage.get('input_tokens', '?')}/{usage.get('output_tokens', '?')}"
                if usage
                else ""
            )
            self._line(f"{tag} {self._c('cyan', '← model')} {d['latency_ms']}ms{u}")
            for tc in d["tool_calls"]:
                self._line(
                    f"{'':9}{self._c('magenta', 'wants')} {tc['name']}({json.dumps(tc['args'])})"
                )
            if d["text"]:
                self._line(
                    f"{'':9}{self._c('dim', 'text:')} {_preview(d['text'], self.preview_len)}"
                )
        elif e.kind == "tool_call":
            self._line(f"{tag} {self._c('green', '⚙ tool')} {d['name']}({json.dumps(d['args'])})")
        elif e.kind == "tool_result":
            status = self._c("red", "ERROR") if d["is_error"] else self._c("green", "ok")
            self._line(
                f"{tag} {self._c('green', '⚙ done')} {d['name']} {status} {d['latency_ms']}ms  "
                f"{d['result_chars']} chars"
            )
            if self.level >= 2 or d["is_error"]:
                self._line(
                    f"{'':9}{self._c('dim', 'result:')} {_preview(d['result'], self.preview_len)}"
                )


class ActivitySink:
    """Compact, plain-language narration of what the agent is doing. On by default in the CLI.

    One line per action, prefixed with a bullet, so a user watching the terminal can follow
    the loop without reading a full trace:

        ● memory: 3 core files (~192 tok) in context · 2 deferred dirs indexed
        ● model thinking (nvidia/nemotron-3-nano-30b-a3b) … 2.4s → wants read_memory
        ● reading deferred memory: projects (192 chars)
        ● model thinking … 0.8s → answer
    """

    def __init__(self, stream: TextIO | None = None, *, color: bool | None = None) -> None:
        self.stream = stream or sys.stderr
        self.color = self.stream.isatty() if color is None else color
        self._memory_announced: str | None = None

    def _c(self, name: str, text: str) -> str:
        return f"{ConsoleSink._C[name]}{text}{ConsoleSink._C['reset']}" if self.color else text

    def _line(self, text: str) -> None:
        print(self._c("dim", "● ") + text, file=self.stream, flush=True)

    def __call__(self, e: TraceEvent) -> None:
        d = e.data
        if e.kind == "model_call":
            mem = d.get("memory")
            if mem:
                key = (
                    f"{[(f['path'], f['chars']) for f in mem['core_files']]}{mem['deferred_dirs']}"
                )
                if key != self._memory_announced:  # only re-announce when memory changed
                    self._memory_announced = key
                    names = ", ".join(f["path"] for f in mem["core_files"])
                    trunc = self._c("yellow", " (some truncated)") if mem["truncated"] else ""
                    self._line(
                        f"{self._c('bold', 'memory:')} {len(mem['core_files'])} core file(s) "
                        f"[{names}] ~{mem['core_tokens_est']} tok in context{trunc} · "
                        f"{mem['deferred_dirs']} deferred dir(s), {mem['external_files_total']} "
                        f"file(s) not loaded"
                    )
            self._line(f"{self._c('cyan', 'model thinking')} ({d['model']}) …")
        elif e.kind == "model_response":
            secs = d["latency_ms"] / 1000
            if d["tool_calls"]:
                wants = ", ".join(
                    f"{tc['name']}({_arg_summary(tc['args'])})" for tc in d["tool_calls"]
                )
                self._line(f"  {secs:.1f}s → {self._c('magenta', 'wants')} {wants}")
            else:
                self._line(f"  {secs:.1f}s → {self._c('green', 'final answer')}")
        elif e.kind == "tool_call":
            if d["name"] == "read_memory":
                self._line(
                    f"{self._c('green', 'reading deferred memory:')} {d['args'].get('path')}"
                )
            elif d["name"] == "write_memory":
                self._line(
                    f"{self._c('yellow', 'writing memory:')} {d['args'].get('path')} "
                    f"({d['args'].get('mode', 'append')})"
                )
            else:
                self._line(f"{self._c('green', 'tool:')} {d['name']}({json.dumps(d['args'])})")
        elif e.kind == "tool_result":
            if d["is_error"]:
                self._line(f"  {self._c('red', 'error:')} {_preview(d['result'], 200)}")
            else:
                self._line(self._c("dim", f"  ok, {d['result_chars']} chars"))


# ---------------------------------------------------------------------- middleware


class TraceMiddleware(AgentMiddleware):
    """Emit a TraceEvent for every model call, model response, tool call and tool result.

    Pass `memory=<OpenMemoryMiddleware>` to include per-call memory statistics (what was
    injected, sizes, truncation). Place this *after* OpenMemoryMiddleware in the stack.
    """

    def __init__(self, sinks: list[Sink] | Sink, *, memory: Any = None) -> None:
        self.sinks = list(sinks) if isinstance(sinks, (list, tuple)) else [sinks]
        self.memory = memory
        self.step = 0
        self.summary = {
            "model_calls": 0,
            "tool_calls": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "model_ms": 0,
            "tool_ms": 0,
        }

    def emit(self, kind: str, **data: Any) -> None:
        ev = TraceEvent(kind=kind, step=self.step, data=data)
        for s in self.sinks:
            s(ev)

    # --- model ---------------------------------------------------------------

    def _before_model(self, request: ModelRequest) -> float:
        self.step += 1
        self.summary["model_calls"] += 1
        sys_text = request.system_message.text if request.system_message is not None else ""
        prompt_chars = len(sys_text) + sum(len(str(m.content)) for m in request.messages)
        model = (
            getattr(request.model, "model_name", None)
            or getattr(request.model, "model", None)
            or type(request.model).__name__
        )
        mem = getattr(self.memory, "last_stats", None) if self.memory is not None else None
        self.emit(
            "model_call",
            model=str(model),
            message_count=len(request.messages),
            system_chars=len(sys_text),
            prompt_tokens_est=estimate_tokens(" " * prompt_chars),
            memory=dict(mem) if mem else None,
        )
        return time.perf_counter()

    def _after_model(self, response: ModelResponse, t0: float) -> None:
        ms = int((time.perf_counter() - t0) * 1000)
        self.summary["model_ms"] += ms
        msg = response.result[-1] if response.result else None
        usage = getattr(msg, "usage_metadata", None) or {}
        if usage:
            self.summary["input_tokens"] += usage.get("input_tokens", 0) or 0
            self.summary["output_tokens"] += usage.get("output_tokens", 0) or 0
        tool_calls = [
            {"name": tc["name"], "args": tc["args"]} for tc in getattr(msg, "tool_calls", []) or []
        ]
        text = (
            (msg.text if hasattr(msg, "text") else str(getattr(msg, "content", ""))) if msg else ""
        )
        self.emit(
            "model_response",
            latency_ms=ms,
            usage=dict(usage) if usage else None,
            tool_calls=tool_calls,
            text=text,
        )

    def wrap_model_call(
        self, request: ModelRequest, handler: Callable[[ModelRequest], ModelResponse]
    ) -> ModelResponse:
        t0 = self._before_model(request)
        response = handler(request)
        self._after_model(response, t0)
        return response

    async def awrap_model_call(
        self, request: ModelRequest, handler: Callable[[ModelRequest], Any]
    ) -> ModelResponse:
        t0 = self._before_model(request)
        response = await handler(request)
        self._after_model(response, t0)
        return response

    # --- tools ---------------------------------------------------------------

    def _before_tool(self, request: ToolCallRequest) -> float:
        self.summary["tool_calls"] += 1
        self.emit("tool_call", name=request.tool_call["name"], args=request.tool_call["args"])
        return time.perf_counter()

    def _after_tool(
        self, request: ToolCallRequest, result: Any, t0: float, exc: Exception | None = None
    ) -> None:
        ms = int((time.perf_counter() - t0) * 1000)
        self.summary["tool_ms"] += ms
        if exc is not None:
            content, is_error = f"{type(exc).__name__}: {exc}", True
        else:
            content = str(getattr(result, "content", result))
            is_error = getattr(result, "status", None) == "error" or content.startswith("error:")
        self.emit(
            "tool_result",
            name=request.tool_call["name"],
            latency_ms=ms,
            result_chars=len(content),
            result=content,
            is_error=is_error,
        )

    def wrap_tool_call(
        self, request: ToolCallRequest, handler: Callable[[ToolCallRequest], Any]
    ) -> Any:
        t0 = self._before_tool(request)
        try:
            result = handler(request)
        except Exception as e:
            self._after_tool(request, None, t0, e)
            raise
        self._after_tool(request, result, t0)
        return result

    async def awrap_tool_call(
        self, request: ToolCallRequest, handler: Callable[[ToolCallRequest], Any]
    ) -> Any:
        t0 = self._before_tool(request)
        try:
            result = await handler(request)
        except Exception as e:
            self._after_tool(request, None, t0, e)
            raise
        self._after_tool(request, result, t0)
        return result

    def format_summary(self) -> str:
        s = self.summary
        return (
            f"{s['model_calls']} model call(s) in {s['model_ms']}ms, "
            f"{s['tool_calls']} tool call(s) in {s['tool_ms']}ms, "
            f"tokens in/out={s['input_tokens']}/{s['output_tokens']}"
        )
