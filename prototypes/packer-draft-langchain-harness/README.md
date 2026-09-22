# OMP — Packer draft (v0.2) LangChain harness

A [LangChain `create_agent`](https://docs.langchain.com/oss/python/langchain/agents) harness
that implements the **harness contract** from the Packer draft spec v0.2
([`early-draft-specs/draft-v0.2-packer.pdf`](../../early-draft-specs/draft-v0.2-packer.pdf)). It builds on the
[`python-loader-validator`](../python-loader-validator/) package for directory validation
and adds the part that package deliberately leaves out: an actual agent loop.

The whole contract is one piece of middleware, `OpenMemoryMiddleware`:

| Spec rule | Where it lives |
|---|---|
| 1. Top-level `.md` always (at least partially) in context | `wrap_model_call` appends every root file to the system message on **every** model call, re-reading from disk so edits show up on the next step. Files over `max_file_chars` are truncated with a visible marker. |
| 2. Defer nested `.md` | Nothing below the root is rendered by rule 1. |
| 3. Surface deferred memory one level down | A deterministic index of immediate subdirectories (with their `MEMORY.md` `description` frontmatter and file counts) and the files directly inside them is appended after the core memory. |
| 4. Selective reads | The `read_memory` tool reads a deferred file, or a directory's `MEMORY.md` plus a one-level listing, so disclosure stays progressive at every depth. Paths are confined to the memory root. |
| Size guidance (recommendation) | Warnings are logged when core memory exceeds the limits. With `writable=True`, a `write_memory` tool refuses root-level writes that would exceed `max_file_chars` ("enforce at edit time"). |
| Optional metadata | `description:` frontmatter is parsed and shown in the index; it is stripped from the rendered body. |

## Install

Requires Python 3.10+. From this directory:

```bash
uv sync --extra dev
```

(`uv` resolves the sibling loader package from `../python-loader-validator` as an editable
path dependency. With plain pip: `pip install -e ../python-loader-validator -e '.[dev]'`.)

## Models

The default model is **NVIDIA Nemotron 3 Nano via OpenRouter** (`openrouter:nvidia/nemotron-3-nano-30b-a3b`). Set
`OPENROUTER_API_KEY` in your environment or in a `.env` file in this directory. Any
`openrouter:<model>` string works, and so does any LangChain `init_chat_model` string such
as `anthropic:claude-sonnet-4-6` or `openai:gpt-5` (with that provider's key).

## Use

```python
from omp_langchain import create_omp_agent

agent = create_omp_agent("./memory")  # Kimi K3 via OpenRouter
# agent = create_omp_agent("./memory", "anthropic:claude-sonnet-4-6")
result = agent.invoke({"messages": [{"role": "user", "content": "what do you know about me?"}]})
print(result["messages"][-1].content)
```

Or compose the middleware into your own `create_agent` stack:

```python
from langchain.agents import create_agent
from omp_langchain import OpenMemoryMiddleware

agent = create_agent(
    "anthropic:claude-sonnet-4-6",
    tools=[...],
    system_prompt="...",
    middleware=[OpenMemoryMiddleware("./memory", writable=True), ...],
)
```

### CLI

```bash
# See exactly what the harness injects, without calling a model
uv run omp-agent --memory examples/memory --show-context

# One-shot against the default OpenRouter model (needs OPENROUTER_API_KEY)
uv run omp-agent --memory examples/memory "What is the OMP project's secret handshake?"

# Another provider
uv run omp-agent --memory examples/memory --model anthropic:claude-sonnet-4-6 "..."

# Interactive, with the write_memory tool enabled
uv run omp-agent --memory examples/memory --writable
```

The example memory under [`examples/memory/`](examples/memory/) is the spec's "expanded"
layout. In the one-shot example above the handshake is not in core memory, so a conforming
run has to disclose progressively. A live run with Kimi K3 did exactly that:

```
AI tool_calls: [('read_memory', {'path': 'projects/MEMORY.md'})]
AI tool_calls: [('read_memory', {'path': 'projects/omp'})]
FINAL: Secret handshake: "progressive disclosure" (per projects/omp/MEMORY.md) ...
```

## Seeing what the harness does

By default the CLI narrates each step on stderr, so the answer on stdout stays clean:

```
$ uv run omp-agent --memory examples/memory "What is the OMP project's secret handshake?"
omp-agent · model openrouter:nvidia/nemotron-3-nano-30b-a3b · memory .../examples/memory
           3 core file(s) always in context, 4 deferred file(s) readable via read_memory

● memory: 3 core file(s) [MEMORY.md, human.md, persona.md] ~192 tok in context · 2 deferred dir(s), 4 file(s) not loaded
● model thinking (nvidia/nemotron-3-nano-30b-a3b) …
●   1.9s → wants read_memory(projects)
● reading deferred memory: projects
●   ok, 192 chars
● model thinking (nvidia/nemotron-3-nano-30b-a3b) …
●   1.0s → wants read_memory(projects/omp)
● reading deferred memory: projects/omp
●   ok, 344 chars
● model thinking (nvidia/nemotron-3-nano-30b-a3b) …
●   0.8s → final answer

The OMP project's secret handshake is "progressive disclosure." (see projects/omp/MEMORY.md)

--- 3 model call(s) in 3717ms, 2 tool call(s) in 4ms, tokens in/out=2982/575
```

`-q` prints only the answer. `-v` switches to a detailed per-step trace (`-vv` also dumps
the full injected memory block and full tool results), and `--trace FILE.jsonl` writes a
machine-readable log of the same events:

```bash
uv run omp-agent --memory examples/memory -v --trace run.jsonl "What is the secret handshake?"
```

```
[step 1] → model nvidia/nemotron-3-nano-30b-a3b  messages=1  ~prompt_tokens=412
         memory: core=[MEMORY.md(404c), human.md(172c), persona.md(153c)] ~179 tok; deferred=2 dirs / 3 files listed
[step 1] ← model 2702ms  tokens in/out=782/600
         wants read_memory({"path": "projects"})
[step 1] ⚙ tool read_memory({"path": "projects"})
[step 1] ⚙ done read_memory ok 1ms  192 chars
...
--- 4 model call(s) in 5025ms, 3 tool call(s) in 5ms, tokens in/out=3692/970
```

Each model call line shows exactly which root files were injected (with sizes, and `*` if
truncated) and how much deferred memory was surfaced, so you can check the four rules are
being honoured on every step. Programmatically, pass `trace=` to `create_omp_agent`:

```python
from omp_langchain import ActivitySink, ConsoleSink, JsonlSink, ListSink, create_omp_agent

sink = ListSink()
agent = create_omp_agent("./memory", trace=[sink, ActivitySink(), JsonlSink("run.jsonl")])
agent.invoke(...)
sink.events  # list[TraceEvent]: model_call / model_response / tool_call / tool_result
agent.omp_trace.summary  # totals: calls, latency, tokens
```

The trace is also a cheap way to compare models. In the run above, Nemotron 3 Nano spent a
tool call re-reading `human.md` even though it was already in context as core memory;
Kimi K3 on the same prompt went straight to `projects/MEMORY.md` then `projects/omp`.

## Test

```bash
uv run pytest
```

Tests run fully offline against LangChain's `GenericFakeChatModel`; each test is named for
the rule it checks.

## Notes on the draft

- The draft's per-file size guidance reads "500 tokens (~20,000 characters)", which is
  inconsistent (20k characters is roughly 5k tokens). This harness exposes both
  `max_file_chars` (default 20,000) and `max_total_tokens` (default 20,000, estimated at
  4 chars/token) so either reading can be enforced.
- The draft says rule-3 metadata "can be learned by the agent or deterministically generated
  by the harness". This harness generates it; the root `MEMORY.md` can additionally describe
  subdirectories in prose, and both will appear.
- Refreshing the prefix after an edit is explicitly out of scope for the spec. This harness
  refreshes on every model call, which is the simplest conforming choice.

## License

Apache 2.0 (see [LICENSE](../../LICENSE)).
