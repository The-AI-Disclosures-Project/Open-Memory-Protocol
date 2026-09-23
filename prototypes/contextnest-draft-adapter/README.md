# OMP: Context Nest draft (v0.1) as an agent plug

A LangChain `create_agent` middleware for
[`early-draft-specs/draft-v0.1-contextnest.md`](../../early-draft-specs/draft-v0.1-contextnest.md).

Unlike the other prototypes here, this one does **not** reimplement the draft. The memory
system is `ctx`, the draft's reference implementation, and this package is only the harness
side: it builds `ctx` calls, parses the JSON, and wires the results into the agent. That
means the same middleware plugs into a nest on disk or a hosted nest with no code change:

```bash
nest-agent --nest ./my-nest ...        # a local nest directory
nest-agent --nest team ...             # a hosted nest registered as an alias:
                                       #   ctx vault add team --url <nest MCP url> \
                                       #     --bearer-env CONTEXTNEST_API_KEY
```

| Draft section | Here |
|---|---|
| §3 eight-key Markdown, `contextnest://` URIs | every loaded document is labelled with its URI |
| §4.2 selectors and packs | `load="pack:core"` (or any selector) is loaded in full before each model call; `nest_query(selector)` lets the model load more |
| §5 / A.1 `status` | only `published` documents are served; `nest_propose` writes `pending_review`, which the resolver will not serve until a person publishes it |
| §5 checkpoints, CN §9.2 tracing | `middleware.reads` records selector, resolved ids, and checkpoint for every set the agent saw; `ctx` also logs each access itself |
| §6.3 forget | not here: it is proposed, not implemented in `ctx` yet |

## Install

Needs Node 20+ for `ctx`, and Python 3.10+.

```bash
npm install -g @promptowl/contextnest-cli
uv sync --extra dev
```

## CLI

```bash
# a small nest built with ctx
examples/seed-nest.sh /tmp/demo-nest

# what the harness injects, no model call
uv run nest-agent --nest /tmp/demo-nest context --load pack:core

# same selector, same set, same order: 5 runs, against the nest and a copy of it
cp -r /tmp/demo-nest /tmp/demo-copy
uv run nest-agent resolve "(#core | #project-omp) -#archive" --runs 5 \
  --nests /tmp/demo-nest /tmp/demo-copy

# the agent (needs OPENROUTER_API_KEY in prototypes/.env)
uv run nest-agent --nest /tmp/demo-nest ask --load pack:core --writable \
  "When are OMP drafts due? Also remember that I prefer email."
```

## Test

```bash
uv run pytest            # needs ctx on PATH; tests skip without it
# or, with nothing installed locally:
docker build -t nest-adapter . && docker run --rm nest-adapter
```

The tests seed a real nest with `ctx` and drive the middleware with a fake model:
selector and pack resolution, set and order stability across runs and across two copies
of a nest, URI reads, the propose-then-publish gate, the "loaded in full" labelling, and
the read trace. No network or API key needed. The same middleware was also run against a
hosted nest through a `ctx vault` alias (no code change); that run is not part of the
offline suite.

## What we found

- **A selector returns a set, not scores.** Two stores holding the same nest return the
  same ids in the same order, so combining results from several nests is set union, not
  merging scores that aren't comparable. This is the case the FMP prototype hit with BM25.
- **Order was not stable at first.** In graph mode, `ctx` returned the same set in a
  different order from run to run, and a hub document pulled in everything linking to it
  even at `--hops 0`. Both are fixed upstream in the reference implementation
  ([PromptOwl/ContextNest#119](https://github.com/PromptOwl/ContextNest/pull/119)). Until
  that ships, this adapter asks for exact sets with `ctx query --full`, which was already
  stable.
- **Agents propose; people publish.** Writing a memory as `pending_review` means a
  model-written memory cannot reach a later context window until someone approves it. The
  other drafts leave that step to the implementation.

## Where the draft was silent

- **What "load" means.** The draft names a set; it does not say whether the harness loads
  it every turn or once. Here it is resolved and injected on every model call, so a
  memory published mid-conversation is visible on the next turn.
- **Truncation.** A loaded document over 6,000 characters is cut, with a marker. The draft
  says nothing about budgets.
- **Where proposals go.** `nest_propose` writes to `nodes/memory/<slug-of-title>`. The draft
  does not reserve a folder for agent-written memory.
- **Hosted checkpoints.** `ctx` reports the checkpoint for local nests only, so
  `reads[].checkpoint` is `None` against a hosted nest.

## License

Apache 2.0 (see [LICENSE](../../LICENSE)) for this adapter. `ctx` is a separate program
under its own license, installed from npm and invoked as a subprocess.
