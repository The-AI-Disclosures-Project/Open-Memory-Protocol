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
