# OMP — IBM draft (v0.1) memory records, lifecycle and runtime verbs

A working implementation of the two protocol surfaces in
[`early-draft-specs/draft-v0.1-ibm.pdf`](../../early-draft-specs/draft-v0.1-ibm.pdf):

**1. Interoperability between memory systems (import/export).** `MemoryRecord` carries
every interface element the draft names: body, identifier, lifecycle (author, AI
provenance, created/invalidated timestamps, version, source material), semantic tags and
scope tags. Records are **immutable**: the store offers Write, Invalidate and Delete but no
Update. Logical mutation is `override`, which writes a new version and invalidates the old
at the same instant, so `as_of(timestamp)` gives time travel instead of data loss.
`export()` produces a versioned bundle; `import_bundle()` turns it into **new** memories in
the receiving system (new ids, `origin` recorded) with the tag mapping step the draft
anticipates for semantic and scope tags.

**2. Interoperability between memory systems and agents (runtime).** The four attachment
formats as LangChain `create_agent` middleware:

| Draft | Kind | Here |
|---|---|---|
| Remember | proactive tool-call | `remember(body, semantic_tags, supersedes)`. Scope tags are stamped by the harness, never chosen by the model. |
| Recall | proactive tool-call | `recall(query, at, semantic_tags, scope_tags)`. Requested scopes are validated against the `ScopePolicy`; a denied scope is an error. |
| Observe | conversation hook, read-only | `after_agent` stores each user turn verbatim (`ai_used=False`) as ground truth for later inferences to cite. |
| Decorate | conversation hook, mutating | `wrap_model_call` recalls memories relevant to the latest user message and injects them into the system prompt. |

**Cross-draft check.** [`packer_bridge.py`](ibm_memory/packer_bridge.py) converts a
Packer-draft memory directory to IBM records and back. The round trip is byte-identical
and the output still validates as a Packer memory. File layout travels as `path:` scope
tags, tier as `tier:core|deferred`, frontmatter as semantic tags.

## Install

```bash
uv sync --extra dev --extra packer
```

## CLI

```bash
# records from the Packer example, then look at them
uv run ibm-memory --store /tmp/m.json from-packer ../packer-draft-langchain-harness/examples/memory
uv run ibm-memory --store /tmp/m.json show

# immutable correction + time travel
ID=$(uv run ibm-memory --store /tmp/m.json write "Lives in Boston" --scope user:sruly)
uv run ibm-memory --store /tmp/m.json override $ID "Lives in Brooklyn"
uv run ibm-memory --store /tmp/m.json history <new id>
uv run ibm-memory --store /tmp/m.json show --as-of 2026-01-01T00:00:00+00:00

# move memories to another system with a scope/tag mapping
uv run ibm-memory --store /tmp/m.json export /tmp/a.json
uv run ibm-memory --store /tmp/n.json --system sysB import /tmp/a.json --map-scope user:sruly=acct:42

# agent with all four verbs (needs OPENROUTER_API_KEY, e.g. in prototypes/.env)
uv run ibm-memory --store /tmp/m.json agent --principal sruly "I moved to Brooklyn last month"
```

## Test

```bash
uv run pytest
```

Tests cover each interface element, immutability, override/invalidate time travel, scope
ACLs on read and write, export/import with mapping, the Packer round trip, and all four
runtime verbs with a fake model. No network or API key needed.

## License

Apache 2.0 (see [LICENSE](../../LICENSE)).
