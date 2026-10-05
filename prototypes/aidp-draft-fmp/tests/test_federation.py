"""Federated client + LangChain middleware tests (offline, fake model)."""

from __future__ import annotations

from typing import ClassVar

from langchain.agents import create_agent
from langchain.messages import AIMessage, HumanMessage, ToolCall, ToolMessage
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel

from fmp.client import FMPError
from fmp.middleware import FMPMiddleware
from fmp.schema import InferenceUpload, Message, TranscriptUpload


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


def test_search_fans_out_and_tags_server(federation):
    federation.clients["personal"].upload_inferences([InferenceUpload(content="likes espresso")])
    federation.clients["work"].upload_inferences(
        [InferenceUpload(content="espresso machine in office 3B")]
    )
    hits = federation.search("espresso")
    assert {h.server for h in hits} == {"personal", "work"}


def test_transcripts_only_go_to_servers_that_receive_them(federation):
    out = federation.upload_transcript(
        TranscriptUpload(source="t", messages=[Message(role="user", content="hi")])
    )
    assert list(out) == ["personal"]
    assert federation.clients["work"].read_transcripts()[2] == 0


def test_remember_routes(federation):
    assert set(federation.remember(InferenceUpload(content="both"))) == {"personal", "work"}
    assert list(federation.remember(InferenceUpload(content="only work"), server="work")) == [
        "work"
    ]
    try:
        federation.remember(InferenceUpload(content="x"), server="nope")
        raise AssertionError("expected FMPError")
    except FMPError:
        pass


def test_describe_shows_policy(federation):
    d = federation.describe()
    assert "- personal:" in d and "transcripts sent" in d
    assert "- work:" in d and "transcripts NOT sent" in d


def test_middleware_tools_hook_and_prompt(federation):
    federation.clients["work"].upload_inferences([InferenceUpload(content="standup is at 9:30")])
    model = _model(
        AIMessage(
            content="",
            tool_calls=[ToolCall(name="search_memory", args={"query": "standup"}, id="c1")],
        ),
        AIMessage(
            content="",
            tool_calls=[
                ToolCall(
                    name="remember",
                    args={"content": "User asked about standup time", "server": "personal"},
                    id="c2",
                )
            ],
        ),
        "Standup is at 9:30.",
    )
    mw = FMPMiddleware(federation, agent_name="test-agent", model_name="fake")
    agent = create_agent(model, tools=[], system_prompt="base", middleware=[mw])
    result = agent.invoke({"messages": [HumanMessage("when is standup?")]})

    # prompt addendum lists servers + policy
    sys_text = next(m for m in FakeModel.calls[0] if m.type == "system").text
    assert "## Federated memory (FMP)" in sys_text and "- work:" in sys_text

    tool_msgs = [m for m in result["messages"] if isinstance(m, ToolMessage)]
    assert "[work] inference" in tool_msgs[0].content and "9:30" in tool_msgs[0].content
    assert tool_msgs[1].content.startswith("stored on personal")
    assert result["messages"][-1].content == "Standup is at 9:30."

    # after_agent uploaded the transcript to 'personal' only, with the session id
    assert list(mw.last_upload) == ["personal"] and mw.last_upload["personal"] == mw.session_id
    ts, _, _ = federation.clients["personal"].read_transcripts(include_messages=True)
    assert ts[0].source == "test-agent" and ts[0].metadata["model"] == "fake"
    roles = [m.role for m in ts[0].messages]
    assert roles[0] == "user" and "tool" in roles and roles[-1] == "assistant"
    assert ts[0].messages[1].metadata["tool_calls"][0]["name"] == "search_memory"
    # the remembered inference recorded provenance
    infs, _, _ = federation.clients["personal"].read_inferences()
    assert infs[0].created_by.name == "test-agent" and infs[0].based_on == [
        f"transcript:{mw.session_id}"
    ]


def test_middleware_survives_unreachable_server(personal):
    import httpx

    from fmp.client import FederatedMemory, ServerConfig

    _, _, pc = personal
    fm = FederatedMemory(
        [
            ServerConfig(name="personal", url="http://personal", http=pc),
            ServerConfig(name="down", url="http://127.0.0.1:1", http=httpx.Client(timeout=0.2)),
        ]
    )
    assert fm.search("anything") == [] and fm.last_errors  # personal empty, down errored
    assert "unreachable" in fm.describe()
    mw = FMPMiddleware(fm)
    agent = create_agent(_model("ok"), tools=[], system_prompt="s", middleware=[mw])
    agent.invoke({"messages": [HumanMessage("hi")]})
    assert list(mw.last_upload) == ["personal"]


def test_search_dedup_unlimited_by_default(federation):
    federation.clients["personal"].upload_inferences(
        [InferenceUpload(content="standup is at 9:30")]
    )
    calls = [
        AIMessage(
            content="",
            tool_calls=[ToolCall(name="search_memory", args={"query": "standup"}, id=f"c{i}")],
        )
        for i in range(3)
    ]
    mw = FMPMiddleware(federation)
    agent = create_agent(_model(*calls, "done"), tools=[], system_prompt="s", middleware=[mw])
    result = agent.invoke({"messages": [HumanMessage("when is standup?")]})
    tools = [m.content for m in result["messages"] if isinstance(m, ToolMessage)]
    assert "9:30" in tools[0] and "left in this run" not in tools[0]
    assert (
        tools[1].startswith("no new matches (1 result(s) already shown")
        and "budget" not in tools[2]
    )


def test_search_budget_when_configured(federation):
    federation.clients["personal"].upload_inferences(
        [InferenceUpload(content="standup is at 9:30")]
    )
    calls = [
        AIMessage(
            content="",
            tool_calls=[ToolCall(name="search_memory", args={"query": "standup"}, id=f"c{i}")],
        )
        for i in range(4)
    ]
    model = _model(*calls, "done")
    mw = FMPMiddleware(federation, max_searches_per_run=2)
    agent = create_agent(model, tools=[], system_prompt="s", middleware=[mw])
    result = agent.invoke({"messages": [HumanMessage("when is standup?")]})
    tools = [m.content for m in result["messages"] if isinstance(m, ToolMessage)]
    assert "9:30" in tools[0] and "(1 search(es) left in this run)" in tools[0]
    assert tools[1].startswith("no new matches (1 result(s) already shown")
    assert tools[2].startswith("search budget for this run is exhausted") and tools[3].startswith(
        "search budget"
    )
    # a new run resets the budget
    mw2_model = _model(calls[0], "ok")
    agent2 = create_agent(mw2_model, tools=[], system_prompt="s", middleware=[mw])
    r2 = agent2.invoke({"messages": [HumanMessage("again")]})
    assert "9:30" in next(m.content for m in r2["messages"] if isinstance(m, ToolMessage))


def test_tool_turns_are_not_searchable(personal):
    _, _, http = personal
    from fmp.client import FMPClient
    from fmp.schema import Message, SearchRequest, TranscriptUpload

    c = FMPClient("http://personal", http=http)
    c.upload_transcript(
        TranscriptUpload(
            source="t",
            messages=[
                Message(role="user", content="deploy the widget"),
                Message(
                    role="tool", content="Edit widget.py: widget widget widget", tool_name="Edit"
                ),
                Message(role="assistant", content="deployed the widget"),
            ],
        )
    )
    hits = c.search(SearchRequest(query="widget"))
    assert {h.snippet.split(":")[0] for h in hits} == {"user", "assistant"}
