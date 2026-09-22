"""Offline tests for the OMP LangChain harness.

Uses GenericFakeChatModel so no API key is needed. Each test maps to a rule of the
harness contract in spec/draft-v0.2-packer.pdf.
"""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

import pytest
from langchain.messages import AIMessage, HumanMessage, ToolCall, ToolMessage
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from open_memory_protocol import ValidationError

from omp_langchain import OpenMemoryMiddleware, create_omp_agent
from omp_langchain.memory_index import (
    deferred_entries,
    parse_frontmatter,
    render_core_context,
    render_deferred_index,
)

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "memory"


def _write(root: Path, rel: str, content: str = "test") -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


class RecordingFakeModel(GenericFakeChatModel):
    """GenericFakeChatModel that records every prompt it receives."""

    calls: ClassVar[list] = []

    def bind_tools(self, tools, **kwargs):
        # GenericFakeChatModel does not implement tool binding; create_agent needs it.
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        type(self).calls.append(messages)
        return super()._generate(messages, stop=stop, run_manager=run_manager, **kwargs)


@pytest.fixture(autouse=True)
def _reset_calls():
    RecordingFakeModel.calls = []
    yield


def _model(*responses):
    return RecordingFakeModel(messages=iter(list(responses)))


def _system_text(messages) -> str:
    sys_msgs = [m for m in messages if m.type == "system"]
    assert len(sys_msgs) == 1, "expected exactly one system message"
    return sys_msgs[0].text if hasattr(sys_msgs[0], "text") else str(sys_msgs[0].content)


# ----------------------------------------------------------------- rule 1


def test_rule1_root_files_always_in_context():
    agent = create_omp_agent(EXAMPLE, _model("hi"))
    agent.invoke({"messages": [HumanMessage("hello")]})
    sys_text = _system_text(RecordingFakeModel.calls[0])
    # Every root file appears, including its body.
    assert "### MEMORY.md" in sys_text
    assert "### persona.md" in sys_text and "Concise, direct" in sys_text
    assert "### human.md" in sys_text and "likes short answers" in sys_text
    # The base system prompt is preserved ahead of the memory block.
    assert sys_text.index("Open Memory Protocol") < sys_text.index("### MEMORY.md")


def test_rule1_truncation_is_visible(tmp_path: Path):
    _write(tmp_path, "MEMORY.md", "x" * 500)
    mw = OpenMemoryMiddleware(tmp_path, max_file_chars=100)
    block = mw.render_memory_block()
    assert "truncated by harness at 100 characters" in block
    assert "x" * 101 not in block


def test_rule1_edits_are_reflected_on_next_model_call(tmp_path: Path):
    _write(tmp_path, "MEMORY.md", "version one")
    model = _model(
        AIMessage(content="", tool_calls=[ToolCall(name="noop", args={}, id="c1")]),
        "done",
    )
    from langchain.tools import tool

    @tool
    def noop() -> str:
        """Simulate an out-of-band edit to memory mid-conversation."""
        (tmp_path / "MEMORY.md").write_text("version two")
        return "edited"

    agent = create_omp_agent(tmp_path, model, tools=[noop])
    agent.invoke({"messages": [HumanMessage("go")]})
    assert "version one" in _system_text(RecordingFakeModel.calls[0])
    assert "version two" in _system_text(RecordingFakeModel.calls[1])


# ----------------------------------------------------------------- rule 2


def test_rule2_nested_files_are_not_loaded():
    agent = create_omp_agent(EXAMPLE, _model("hi"))
    agent.invoke({"messages": [HumanMessage("hello")]})
    sys_text = _system_text(RecordingFakeModel.calls[0])
    # Body text that only exists in nested files must be absent.
    assert "secret handshake" not in sys_text
    assert "Reviewed the Packer draft" not in sys_text


# ----------------------------------------------------------------- rule 3


def test_rule3_deferred_index_surfaces_one_level_down():
    agent = create_omp_agent(EXAMPLE, _model("hi"))
    agent.invoke({"messages": [HumanMessage("hello")]})
    sys_text = _system_text(RecordingFakeModel.calls[0])
    assert "`projects/`" in sys_text and "Index of projects" in sys_text
    assert "`notes/`" in sys_text and "`notes/2026-08-12.md`" in sys_text
    # Two levels down is NOT surfaced at the root; the agent discovers it via projects/MEMORY.md.
    assert "projects/omp/MEMORY.md" not in sys_text


def test_rule3_index_is_deterministic_from_disk(tmp_path: Path):
    _write(tmp_path, "MEMORY.md", "root")
    _write(tmp_path, "a/MEMORY.md", "---\ndescription: about a\n---\n# a")
    _write(tmp_path, "a/deep/MEMORY.md", "deep")
    _write(tmp_path, "b/MEMORY.md", "b")
    _write(tmp_path, "b/thing.md", "thing")
    from open_memory_protocol import load_memory

    entries = deferred_entries(load_memory(tmp_path))
    paths = [str(e.relative_path) for e in entries]
    assert paths == ["a", "a/MEMORY.md", "b", "b/MEMORY.md", "b/thing.md"]
    a = entries[0]
    assert a.is_dir and a.description == "about a" and a.file_count == 2
    text = render_deferred_index(load_memory(tmp_path))
    assert "`a/` (2 files) — about a" in text


def test_rule3_no_deferred_memory_message(tmp_path: Path):
    _write(tmp_path, "MEMORY.md", "only")
    assert "No deferred memory" in OpenMemoryMiddleware(tmp_path).render_memory_block()


# ----------------------------------------------------------------- rule 4


def test_rule4_agent_can_selectively_read_deferred_file():
    model = _model(
        AIMessage(
            content="",
            tool_calls=[
                ToolCall(name="read_memory", args={"path": "projects/omp/MEMORY.md"}, id="c1")
            ],
        ),
        "The handshake is progressive disclosure.",
    )
    agent = create_omp_agent(EXAMPLE, model)
    result = agent.invoke({"messages": [HumanMessage("what's the handshake?")]})
    tool_msgs = [m for m in result["messages"] if isinstance(m, ToolMessage)]
    assert len(tool_msgs) == 1
    assert "secret handshake" in tool_msgs[0].content
    assert result["messages"][-1].content == "The handshake is progressive disclosure."


def test_rule4_reading_a_directory_gives_index_and_listing():
    mw = OpenMemoryMiddleware(EXAMPLE)
    read = mw.tools[0]
    out = read.invoke({"path": "projects"})
    assert "### projects/MEMORY.md" in out
    assert "`projects/omp/`" in out


def test_rule4_rejects_escape_and_non_markdown(tmp_path: Path):
    _write(tmp_path, "MEMORY.md", "root")
    _write(tmp_path, "sub/MEMORY.md", "s")
    _write(tmp_path, "sub/data.json", "{}")
    read = OpenMemoryMiddleware(tmp_path).tools[0]
    assert read.invoke({"path": "../../etc/passwd"}).startswith("error: Path escapes")
    assert read.invoke({"path": "sub/data.json"}).startswith("error:")
    assert read.invoke({"path": "sub/missing.md"}).startswith("error: no memory")


# ------------------------------------------------------- writes + size guidance


def test_write_tool_is_opt_in():
    assert [t.name for t in OpenMemoryMiddleware(EXAMPLE).tools] == ["read_memory"]
    assert [t.name for t in OpenMemoryMiddleware(EXAMPLE, writable=True).tools] == [
        "read_memory",
        "write_memory",
    ]


def test_write_enforces_root_size_limit_but_not_nested(tmp_path: Path):
    _write(tmp_path, "MEMORY.md", "root")
    mw = OpenMemoryMiddleware(tmp_path, writable=True, max_file_chars=50)
    write = mw.tools[1]
    big = "y" * 100
    assert write.invoke({"path": "MEMORY.md", "content": big}).startswith("error: write refused")
    assert (tmp_path / "MEMORY.md").read_text() == "root"
    assert write.invoke({"path": "logs/today.md", "content": big}).startswith("ok:")
    # New subdirectory was made spec-valid automatically.
    assert (tmp_path / "logs" / "MEMORY.md").exists()
    from open_memory_protocol import validate_memory

    validate_memory(tmp_path)


def test_write_append_and_replace(tmp_path: Path):
    _write(tmp_path, "MEMORY.md", "root")
    write = OpenMemoryMiddleware(tmp_path, writable=True).tools[1]
    write.invoke({"path": "MEMORY.md", "content": "more", "mode": "append"})
    assert (tmp_path / "MEMORY.md").read_text() == "root\n\nmore\n"
    write.invoke({"path": "MEMORY.md", "content": "fresh", "mode": "replace"})
    assert (tmp_path / "MEMORY.md").read_text() == "fresh\n"


# ---------------------------------------------------------------- misc


def test_invalid_memory_fails_at_construction(tmp_path: Path):
    _write(tmp_path, "project-1/MEMORY.md", "no root index")
    with pytest.raises(ValidationError):
        OpenMemoryMiddleware(tmp_path)


def test_frontmatter_description_is_shown_and_stripped(tmp_path: Path):
    _write(tmp_path, "MEMORY.md", "---\ndescription: root desc\n---\nbody here")
    from open_memory_protocol import load_memory

    text, _ = render_core_context(load_memory(tmp_path))
    assert "_root desc_" in text and "body here" in text
    assert "description: root desc" not in text
    assert parse_frontmatter("no frontmatter") == ({}, "no frontmatter")


# ---------------------------------------------------------------- models


def test_resolve_model_openrouter(monkeypatch):
    from omp_langchain.models import OPENROUTER_BASE_URL, resolve_model

    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="OPENROUTER_API_KEY"):
        resolve_model("openrouter:moonshotai/kimi-k3")

    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    m = resolve_model("openrouter:moonshotai/kimi-k3")
    assert m.model_name == "moonshotai/kimi-k3"
    assert m.openai_api_base == OPENROUTER_BASE_URL
    # Model instances pass through untouched.
    fake = _model("x")
    assert resolve_model(fake) is fake


# ---------------------------------------------------------------- trace


def test_trace_records_every_model_and_tool_event():
    from omp_langchain import ListSink

    sink = ListSink()
    model = _model(
        AIMessage(
            content="",
            tool_calls=[
                ToolCall(name="read_memory", args={"path": "notes/2026-08-12.md"}, id="c1")
            ],
        ),
        "Reviewed the draft.",
    )
    agent = create_omp_agent(EXAMPLE, model, trace=sink)
    agent.invoke({"messages": [HumanMessage("what happened on 2026-08-12?")]})

    kinds = [(e.step, e.kind) for e in sink.events]
    assert kinds == [
        (1, "model_call"),
        (1, "model_response"),
        (1, "tool_call"),
        (1, "tool_result"),
        (2, "model_call"),
        (2, "model_response"),
    ]
    first = sink.events[0].data
    assert first["memory"]["core_files"][0]["path"] == "MEMORY.md"
    assert first["memory"]["deferred_dirs"] == 2 and first["memory"]["truncated"] is False
    assert "### persona.md" in first["memory"]["block"]
    assert sink.events[1].data["tool_calls"] == [
        {"name": "read_memory", "args": {"path": "notes/2026-08-12.md"}}
    ]
    tool_result = sink.events[3].data
    assert tool_result["name"] == "read_memory" and not tool_result["is_error"]
    assert "Reviewed the Packer draft" in tool_result["result"]
    assert sink.events[-1].data["text"] == "Reviewed the draft."
    assert agent.omp_trace.summary["model_calls"] == 2
    assert agent.omp_trace.summary["tool_calls"] == 1


def test_trace_flags_tool_errors_and_writes_jsonl(tmp_path: Path):
    import json

    from omp_langchain import JsonlSink, ListSink

    sink, jsonl = ListSink(), JsonlSink(tmp_path / "trace.jsonl")
    model = _model(
        AIMessage(
            content="", tool_calls=[ToolCall(name="read_memory", args={"path": "nope.md"}, id="c1")]
        ),
        "sorry",
    )
    agent = create_omp_agent(EXAMPLE, model, trace=[sink, jsonl])
    agent.invoke({"messages": [HumanMessage("x")]})
    err = next(e for e in sink.events if e.kind == "tool_result")
    assert err.data["is_error"] is True
    lines = (tmp_path / "trace.jsonl").read_text().splitlines()
    assert len(lines) == len(sink.events)
    assert json.loads(lines[0])["kind"] == "model_call"


def test_console_sink_renders_without_crashing(capsys):
    import io

    from omp_langchain import ConsoleSink

    buf = io.StringIO()
    sink = ConsoleSink(buf, level=2, color=False)
    model = _model(
        AIMessage(
            content="",
            tool_calls=[ToolCall(name="read_memory", args={"path": "projects"}, id="c1")],
        ),
        "done",
    )
    create_omp_agent(EXAMPLE, model, trace=sink).invoke({"messages": [HumanMessage("x")]})
    out = buf.getvalue()
    assert (
        "→ model" in out and "⚙ tool read_memory" in out and "--- injected memory block ---" in out
    )
    assert "### projects/MEMORY.md" in out  # level 2 shows the tool result
