# OMP — LangChain harness

A [LangChain `create_agent`](https://docs.langchain.com/oss/python/langchain/agents) harness
that implements the **harness contract** from the Packer draft spec v0.2
([`spec/draft-v0.2-packer.pdf`](../../spec/draft-v0.2-packer.pdf)). It builds on the
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

The default model is **Kimi K3 via OpenRouter** (`openrouter:moonshotai/kimi-k3`). Set
`OPENROUTER_API_KEY` in your environment or in a `.env` file in this directory. Any
`openrouter:<model>` string works, and so does any LangChain `init_chat_model` string such
as `anthropic:claude-sonnet-4-6` or `openai:gpt-5` (with that provider's key).

## Use

```python
from omp_langchain import create_omp_agent

agent = create_omp_agent("./memory")                      # Kimi K3 via OpenRouter
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

# One-shot against Kimi K3 (needs OPENROUTER_API_KEY)
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
