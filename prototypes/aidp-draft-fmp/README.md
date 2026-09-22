# OMP — Federated Memory Protocol (AIDP draft v0.1) reference implementation

A working implementation of the Federated Memory Protocol from
[`early-draft-specs/draft-v0.1-aidp.pdf`](../../early-draft-specs/draft-v0.1-aidp.pdf): a **memory server** exposing
the `/fmp/*` endpoints, a **federated client** that treats many servers as one view, and a
**LangChain `create_agent` middleware** (the draft's tier 2: plugin with hooks + tools).

The draft says "TBD exact fields". This package is a concrete proposal for them; see
[`fmp/schema.py`](fmp/schema.py). Everything carries a nested `metadata` object.

| Draft item | Where |
|---|---|
| `/fmp/info` (always required), `upload/files`, `upload/transcript`, `upload/inferences`, `search`, `read_transcripts`, `read_inferences`, `delete` | [`fmp/server.py`](fmp/server.py). Any endpoint may be disabled; it then returns 501 and shows `false` in `info.capabilities`. |
| Three memory types: ground truth, transcripts, inferences | `FileUpload`, `TranscriptUpload`, `InferenceUpload` in the schema. Inferences carry `created_by` and `based_on` refs like `transcript:<id>#<turn>`. |
| Reference backend | `SQLiteStore`: one file, FTS5 search across all three types. |
| Real data with no new indexing | `ACPIndexStore`: a **read-only FMP view over the `acp_memory_server` index**, so every locally installed coding agent's history is served through FMP. |
| One plugin, many servers | `FederatedMemory` fans search out to every server and merges by score; routing policy is per server (`send_transcripts`, `accept_inferences`). |
| Hooks capture transcripts; tools search and upload | `FMPMiddleware`: `search_memory` + `remember` tools, `after_agent` uploads the transcript, and a system-prompt block tells the model where memory lives and where it will be sent. |

## Install

```bash
uv sync --extra dev            # + `--extra packer` to compose with the Packer-draft harness
```

## Run the federated demo

Three terminals (or background them):

```bash
uv run fmp-server --name personal --port 8801
uv run fmp-server --name work     --port 8802 --disable delete
uv run fmp-server --name history  --port 8803 --acp-index ~/.local/share/acp-memory/db.sqlite
```

Then, with `OPENROUTER_API_KEY` set (or in `.env`):

```bash
uv run fmp-agent --config examples/fmp.toml "what have I been working on in claude code lately?"
```

[`examples/fmp.toml`](examples/fmp.toml) is the federation policy: transcripts go only to
`personal`, inferences may go to `personal` or `work`, and `history` is read-only. The agent
prints which servers it is connected to, what it searched, and where the transcript was sent.

Add `--packer-memory ../packer-draft-langchain-harness/examples/memory` to mount a Packer-draft
memory directory in the same agent: core memory in the prompt, FMP servers for history.

## Use in code

```python
from fastapi.testclient import TestClient
from fmp import FMPMiddleware, FederatedMemory, ServerConfig, SQLiteStore, create_app
from langchain.agents import create_agent

fm = FederatedMemory(
    [
        ServerConfig(name="personal", url="http://127.0.0.1:8801"),
        ServerConfig(name="work", url="http://127.0.0.1:8802", send_transcripts=False),
    ]
)
agent = create_agent(
    "openrouter:nvidia/nemotron-3-nano-30b-a3b",
    tools=[],
    middleware=[FMPMiddleware(fm, agent_name="my-agent")],
)
```

## Answers to the draft's open questions (as implemented)

- **How are memories combined across servers?** The client merges search hits by score and
  tags each with its server; the model sees `[server] type ts ref= …` per hit.
- **How does the model route where a memory is stored?** `remember(server=...)` names one
  server; omitted, it goes to every server whose policy accepts inferences.
- **Are transcripts sent to every server?** No. Only servers with `send_transcripts = true`,
  and only if their `info` reports `upload_transcript`. Uploads carry the session id, so
  partial uploads of one session merge server-side.

## Test

```bash
uv run pytest
```

Server tests use FastAPI's `TestClient`; federation and middleware tests run the servers
in-process with a fake model, so no network or API key is needed.

## License

Apache 2.0 (see [LICENSE](../../LICENSE)).
