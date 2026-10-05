from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from langchain.agents import create_agent
from langchain.messages import AIMessage, HumanMessage, ToolCall, ToolMessage
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel

from ibm_memory import IBMMemoryMiddleware, MemoryStore, ScopePolicy
from ibm_memory.packer_bridge import memory_dir_from_records, records_from_memory_dir

PACKER_EXAMPLE = (
    Path(__file__).resolve().parents[2] / "packer-draft-langchain-harness" / "examples" / "memory"
)


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


# ------------------------------------------------------------- Packer <-> IBM


def test_packer_directory_round_trips_through_records(tmp_path: Path):
    store = MemoryStore("packer")
    recs = records_from_memory_dir(PACKER_EXAMPLE, store)
    assert len(recs) == 7
    by_path = {next(s for s in r.scope_tags if s.startswith("path:")): r for r in recs}
    assert "tier:core" in by_path["path:MEMORY.md"].scope_tags
    assert "tier:deferred" in by_path["path:projects/omp/MEMORY.md"].scope_tags
    assert any(t.startswith("description:") for t in by_path["path:human.md"].semantic_tags)
    assert by_path["path:human.md"].lifecycle.author == "user"
    assert not by_path["path:human.md"].lifecycle.provenance.ai_used

    out = tmp_path / "memory"
    written = memory_dir_from_records(store.as_of(), out)
    assert len(written) == 7
    for src in sorted(PACKER_EXAMPLE.rglob("*.md")):
        rel = src.relative_to(PACKER_EXAMPLE)
        assert (out / rel).read_text() == src.read_text(), rel

    # and the result still validates as a Packer memory
    from open_memory_protocol import validate_memory

    validate_memory(out)


def test_override_in_records_changes_the_file_on_export(tmp_path: Path):
    store = MemoryStore("packer")
    recs = records_from_memory_dir(PACKER_EXAMPLE, store)
    human = next(r for r in recs if "path:human.md" in r.scope_tags)
    store.override(human.id, "# Human\n\nSruly, now prefers long answers.\n", author="user")
    memory_dir_from_records(store.as_of(), tmp_path)
    assert "long answers" in (tmp_path / "human.md").read_text()
    assert (tmp_path / "human.md").read_text().startswith("---\ndescription: ")


# ------------------------------------------------------------- four verbs


def _agent(store, model, **kw):
    mw = IBMMemoryMiddleware(
        store,
        principal="sruly",
        write_scopes=["user:sruly"],
        agent_name="t",
        model_name="fake",
        **kw,
    )
    return mw, create_agent(model, tools=[], system_prompt="base", middleware=[mw])


def test_remember_stamps_scope_and_provenance():
    store = MemoryStore(
        "s", policy=ScopePolicy(read={"sruly": {"user:sruly"}}, write={"sruly": {"user:sruly"}})
    )
    _mw, agent = _agent(
        store,
        _model(
            AIMessage(
                content="",
                tool_calls=[
                    ToolCall(
                        name="remember",
                        args={"body": "Sruly uses uv", "semantic_tags": ["tooling"]},
                        id="c1",
                    )
                ],
            ),
            "noted",
        ),
        observe=False,
    )
    agent.invoke({"messages": [HumanMessage("I use uv for everything")]})
    recs = [r for r in store.all() if "observation" not in r.semantic_tags]
    assert len(recs) == 1
    r = recs[0]
    assert r.scope_tags == ["user:sruly"] and r.semantic_tags == ["tooling"]
    assert (
        r.lifecycle.provenance.ai_used
        and r.lifecycle.provenance.model == "fake"
        and r.lifecycle.author == "sruly"
    )


def test_recall_denies_forbidden_scope_and_supports_time():
    store = MemoryStore(
        "s", policy=ScopePolicy(read={"sruly": {"user:sruly"}}, write={"sruly": {"user:sruly"}})
    )
    store.write("finance secret", author="x", scope_tags=["team:finance"])
    store.write("Sruly likes tea", author="sruly", scope_tags=["user:sruly"])
    _mw, agent = _agent(
        store,
        _model(
            AIMessage(
                content="",
                tool_calls=[
                    ToolCall(
                        name="recall",
                        args={"query": "secret", "scope_tags": ["team:finance"]},
                        id="c1",
                    )
                ],
            ),
            AIMessage(
                content="", tool_calls=[ToolCall(name="recall", args={"query": "tea"}, id="c2")]
            ),
            "done",
        ),
        observe=False,
        decorate=False,
    )
    result = agent.invoke({"messages": [HumanMessage("x")]})
    tools = [m.content for m in result["messages"] if isinstance(m, ToolMessage)]
    assert tools[0].startswith("error: sruly may not read scopes ['team:finance']")
    assert "Sruly likes tea" in tools[1] and "finance" not in tools[1]


def test_observe_stores_user_turns_verbatim_and_decorate_injects_them():
    store = MemoryStore("s")
    mw, agent = _agent(store, _model("ok"))
    agent.invoke({"messages": [HumanMessage("My dog is called Pixel")]})
    obs = mw.last_observed
    assert len(obs) == 1 and obs[0].body == "My dog is called Pixel"
    assert not obs[0].lifecycle.provenance.ai_used and "observation" in obs[0].semantic_tags

    # second run: Decorate recalls the observation into the system prompt; Observe does not duplicate
    mw2, agent2 = _agent(store, _model("Pixel!"))
    agent2.invoke({"messages": [HumanMessage("what is my dog called?")]})
    sys_text = next(m for m in FakeModel.calls[0] if m.type == "system").text
    assert "## Recalled memories" in sys_text and "My dog is called Pixel" in sys_text
    assert [r.body for r in mw2.last_decorated] == ["My dog is called Pixel"]
    assert mw2.last_observed[0].body == "what is my dog called?"
    assert sum(1 for r in store.all() if r.body == "My dog is called Pixel") == 1


def test_remember_supersedes_via_tool():
    store = MemoryStore("s")
    old = store.write("Lives in Boston", author="sruly", scope_tags=["user:sruly"])
    _mw, agent = _agent(
        store,
        _model(
            AIMessage(
                content="",
                tool_calls=[
                    ToolCall(
                        name="remember",
                        args={"body": "Lives in Brooklyn", "supersedes": old.id},
                        id="c1",
                    )
                ],
            ),
            "updated",
        ),
        observe=False,
        decorate=False,
    )
    result = agent.invoke({"messages": [HumanMessage("I moved to Brooklyn")]})
    msg = next(m.content for m in result["messages"] if isinstance(m, ToolMessage))
    assert msg.startswith("stored") and "v2" in msg
    assert [r.body for r in store.as_of()] == ["Lives in Brooklyn"] and not store.get(
        old.id
    ).is_valid
