# Contributed proposals

The proposals the working group distilled into the [exchange-and-runtime editors' draft](../exchange-and-runtime/2026-11-09-working-spec-v0.6.md), plus the scoping note and the AMS card. This folder keeps the latest revision of each; earlier revisions are in [`archive/`](archive/). The [September 28 common-ground notes](../exchange-and-runtime/2026-09-28-common-ground.md) compare them primitive by primitive.

## Latest revisions

- **Letta draft v0.2** — Charles Packer (Letta), August 2026. A `MEMORY.md` directory with progressive disclosure and a four-rule harness contract; ownership, versioning and sync are out of scope. [`draft-v0.2-packer.pdf`](draft-v0.2-packer.pdf)
- **IBM proposal v0.1** — An immutable memory record (body, id, author, AI provenance, created/invalidated, version comparator, source, semantic and scope tags) and the runtime verbs remember, recall, observe and decorate. [`draft-v0.1-ibm.pdf`](draft-v0.1-ibm.pdf)
- **Federated Memory Protocol draft v0.2** — Sruly Rosenblat (AI Disclosures Project), October 13, 2026. Many memory servers behind one plugin, over native, plugin + MCP, or plain MCP endpoints. [`draft-v0.2-aidp.pdf`](draft-v0.2-aidp.pdf)
- **Cognee proposal v0.1** — Cognee, September 9, 2026. A semantic core for portable agent memory: identity, evidence, authority, lineage, lifecycle and exchange fidelity, with COGX as an implemented reference input. [`draft-v0.1-cognee.md`](draft-v0.1-cognee.md)
- **Context Nest proposal v0.1** — PromptOwl, September 22, 2026. A governed Markdown profile: front-matter keys and in-prose links as the atomic unit, `contextnest://` addressing, scoped selectors, append-only hash-chained history, and a forget protocol. [`draft-v0.1-contextnest.md`](draft-v0.1-contextnest.md)
- **Knowledge object v0.2** — Sapience Labs, October 15, 2026. The knowledge object as a portable memory unit: confidence carried in provenance, two timestamps, supersession as a first-class relation; mapped onto editors' draft v0.2. [`draft-v0.2-sapience.md`](draft-v0.2-sapience.md)
- **me.md** — David Hamilton (Block / goose). A user-owned, plain-file protocol for what agents know about you; agents may only propose additions. Maintained outside this repository at [`block/me.md`](https://github.com/block/me.md).

## Background documents

- **Scoping note** — Strauss and Rosenblat, August 2026. Surveys memory implementations across coding harnesses, consumer assistants and enterprise systems, and names the shared primitives a minimal protocol can standardize. [`scoping-note-2026-09.pdf`](scoping-note-2026-09.pdf)
- **Agent Memory System Card** — Mila and Mozilla. A documentation format for memory systems; template, reference card and evaluation framework at [`mila-iqia/agent-memory-system-card`](https://github.com/mila-iqia/agent-memory-system-card/). [`ams-card.md`](ams-card.md)

## Superseded revisions

| Revision | Superseded by | When |
|---|---|---|
| [`archive/draft-v0.1-sapience.md`](archive/draft-v0.1-sapience.md) (mapped onto editors' draft v0.1) | [`draft-v0.2-sapience.md`](draft-v0.2-sapience.md) | October 15, 2026 |

The editors' drafts themselves (v0.1 of October 2, v0.2 of October 14) were revised in place; their change logs are in the change history of the [v0.6 draft](../exchange-and-runtime/2026-11-09-working-spec-v0.6.md).

## Adding or revising a proposal

1. Name the file `draft-vX.Y-<org>.md` (Markdown preferred; a PDF only when there is no source). Start it with a status line that says it is proposed for discussion and which editors' draft it was written against.
2. When revising, `git mv` the previous revision to `archive/` and add a row to the table above. Only the latest revision stays in this folder.
3. Update the row in the root [README](../../README.md#proposals) and the entry above.
4. Do not edit another author's draft beyond fixing links.
