from __future__ import annotations

import subprocess
from typing import ClassVar

from langchain.agents import create_agent
from langchain.messages import AIMessage, HumanMessage, ToolCall
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel

from contextnest_adapter import ContextNestMiddleware, CtxClient
from contextnest_adapter.cli import main as cli_main


class FakeModel(GenericFakeChatModel):
    calls: ClassVar[list] = []

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        type(self).calls.append(messages)
        return super()._generate(messages, stop=stop, run_manager=run_manager, **kwargs)


def _model(*responses):
    FakeModel.calls = []
    return FakeModel(messages=iter(list(responses)))


def _system_text(messages) -> str:
    sys_msg = next(m for m in messages if m.type == "system")
    return "\n".join(b["text"] for b in sys_msg.content_blocks if b.get("type") == "text")


# ------------------------------------------------------------- the engine does the work


def test_selectors_resolve_through_ctx(nest):
    c = CtxClient(nest)
    assert set(c.query("#project-omp").ids) == {
        "nodes/projects/omp",
        "nodes/projects/omp-areas",
        "nodes/notes/old-deadline",
    }
    assert set(c.query("#project-omp -#archive").ids) == {
        "nodes/projects/omp",
        "nodes/projects/omp-areas",
    }
    assert c.query("type:persona").ids == ["nodes/people/sruly"]
    assert set(c.query("pack:core").ids) == {"nodes/people/sruly", "nodes/projects/omp"}


def test_same_selector_same_set_every_time(nest):
    c = CtxClient(nest)
    sets = {tuple(c.query("#project-omp -#archive").ids) for _ in range(5)}
    assert len(sets) == 1


def test_resolution_is_identical_across_two_copies_of_a_nest(nest, tmp_path):
    # the same nest, moved: a different "backend" location, the same answer
    copy = tmp_path / "copy"
    subprocess.run(["cp", "-r", str(nest), str(copy)], check=True)
    sel = "(#core | #project-omp) -#archive"
    assert CtxClient(nest).query(sel).ids == CtxClient(copy).query(sel).ids
    assert cli_main(["resolve", sel, "--runs", "3", "--nests", str(nest), str(copy)]) == 0


def test_read_one_node_by_uri(nest):
    doc = CtxClient(nest).read("contextnest://nodes/people/sruly")
    assert doc is not None and "short answers" in doc.body
    assert CtxClient(nest).read("nodes/does/not-exist") is None


# ------------------------------------------------------------- governance at the plug


def test_proposed_memory_is_not_served_until_published(nest):
    c = CtxClient(nest)
    c.propose(
        "nodes/memory/moved",
        title="Sruly moved",
        body="Sruly moved to Brooklyn.",
        tags=["#person"],
    )
    assert "nodes/memory/moved" not in c.query("#person").ids
    c.run("update", "nodes/memory/moved", "--status", "published")
    assert "nodes/memory/moved" in c.query("#person").ids


# ------------------------------------------------------------- the middleware


def test_preload_is_labelled_loaded_in_full_and_traced(nest):
    mw = ContextNestMiddleware(CtxClient(nest), load="pack:core")
    agent = create_agent(model=_model(AIMessage(content="ok")), tools=[], middleware=[mw])
    agent.invoke({"messages": [HumanMessage(content="who am I talking to?")]})
    text = _system_text(FakeModel.calls[0])
    assert "<contextnest://nodes/people/sruly> (loaded in full)" in text
    assert "Prefers short answers." in text
    assert "not an index" in text
    assert mw.reads[-1]["via"] == "preload"
    assert set(mw.reads[-1]["ids"]) == {"nodes/people/sruly", "nodes/projects/omp"}
    assert mw.reads[-1]["checkpoint"] is not None


def test_agent_queries_by_selector(nest):
    mw = ContextNestMiddleware(CtxClient(nest))
    model = _model(
        AIMessage(
            content="",
            tool_calls=[
                ToolCall(name="nest_query", args={"selector": "#project-omp -#archive"}, id="1")
            ],
        ),
        AIMessage(content="Drafts are due October 2."),
    )
    agent = create_agent(model=model, tools=[], middleware=[mw])
    out = agent.invoke({"messages": [HumanMessage(content="when are OMP drafts due?")]})
    tool_msg = next(m for m in out["messages"] if m.type == "tool")
    assert "2026-10-02" in tool_msg.content
    assert "September 30" not in tool_msg.content  # the archived note stays out
    assert mw.reads[-1]["via"] == "tool"


def test_propose_tool_only_when_writable(nest):
    assert [t.name for t in ContextNestMiddleware(CtxClient(nest)).tools] == [
        "nest_query",
        "nest_search",
    ]
    mw = ContextNestMiddleware(CtxClient(nest), writable=True)
    model = _model(
        AIMessage(
            content="",
            tool_calls=[
                ToolCall(
                    name="nest_propose",
                    args={"title": "Prefers email", "body": "Sruly prefers email.", "tags": ["person"]},
                    id="1",
                )
            ],
        ),
        AIMessage(content="noted"),
    )
    agent = create_agent(model=model, tools=[], middleware=[mw])
    agent.invoke({"messages": [HumanMessage(content="remember I prefer email")]})
    assert mw.proposed == ["nodes/memory/prefers-email"]
    assert "nodes/memory/prefers-email" not in CtxClient(nest).query("#person").ids
