<p align="center">
  <img src="media/ompi-logo.png" alt="Open Memory Protocol Initiative" width="640">
</p>

<p align="center">
  <a href="https://openmemoryprotocol.org"><strong>Site</strong></a> ·
  <a href="working-group/exchange-and-runtime/2026-11-06-working-spec-v0.5.md"><strong>Working spec (v0.5)</strong></a> ·
  <a href="working-group/past-proposals/"><strong>Proposals</strong></a> ·
  <a href="prototypes/"><strong>Prototypes</strong></a> ·
  <a href="https://ompi.fly.dev"><strong>Live demo</strong></a> ·
  <a href="GOVERNANCE.md"><strong>Governance</strong></a> ·
  <a href="docs/contributing.md"><strong>Contribute</strong></a> ·
  <a href="https://discord.gg/B8Fhcech4"><strong>Discord</strong></a>
</p>

<p align="center">
  <sub><b>Hosted at</b></sub><br>
  <a href="https://ai-disclosures.org/"><img src="media/aidp-logo.png" alt="AI Disclosures Project" height="72"></a>
</p>

<p align="center">
  <sub><b>Co-convened with</b></sub><br>
  <a href="https://www.mozilla.org/"><img src="media/mozilla-logo.png" alt="Mozilla" height="40"></a>
  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
  <a href="https://www.ibm.com/"><img src="media/ibm-logo.png" alt="IBM" height="52"></a>
</p>

<p align="center">
  <sub><b>Participating organizations</b></sub><br>
  <sub>Letta · Block / goose · Cognee · PromptOwl · Sapience Labs · Mila · Pinecone · Agentic AI Foundation · Pi</sub>
</p>

---

# Open Memory Protocol Initiative

The [Open Memory Protocol Initiative (OMPI)](https://openmemoryprotocol.org) is building an open protocol for agent memory, so that memory can move between agent systems and be shared between them. It is hosted at the [AI Disclosures Project](https://ai-disclosures.org/) ([Code for Science & Society](https://www.codeforsociety.org/)) and co-convened with IBM and Mozilla. This repository holds the working specification, the contributed proposals, prototypes and the governance documents.

## Current work

- **Status.** Pre-1.0. No reference implementation exists yet. Current focus: the memory object and exchange semantics; next, the export/import manifest (a follow-up to v0.5). First implementation target: coding-agent harnesses (Claude Code, Codex, goose, Letta Code).
- **[Exchange-and-runtime working specification, editors' draft v0.5](working-group/exchange-and-runtime/2026-11-06-working-spec-v0.5.md)** (November 6, 2026). Defines the individual memory object, its interchange and runtime representations and the exchange semantics; the export/import manifest is deferred to a follow-up proposal. Merged in [PR #13](https://github.com/The-AI-Disclosures-Project/Open-Memory-Protocol/pull/13). Not an adopted protocol.
- **[PR #17: memory security and threat model](https://github.com/The-AI-Disclosures-Project/Open-Memory-Protocol/pull/17).** Open for review. Written against v0.1; read alongside v0.5.
- **[September 28 working notes](working-group/exchange-and-runtime/2026-09-28-common-ground.md).** Comparison matrix of the contributed proposals and the call notes the editors' draft grew out of.
- **December hackathon.** Online, early December, to align on the spec's goals and work on a draft implementation together. [Vote on the date](https://forms.gle/ditdHjo1trjm9X7YA). <!-- remove after the hackathon -->
- [All open proposals and contributions](https://github.com/The-AI-Disclosures-Project/Open-Memory-Protocol/pulls)

## Why an open protocol

Agent memory is persistent context that affects future model or agent behavior: user-provided facts, model- or agent-derived summaries, project instructions, prior decisions and actions, tool outputs, and references to underlying transcripts or artifacts. It is scoped to a user, project, organization, or shared group, and is distinct from a raw chat export. A memory system selects, transforms, organizes, retrieves, and expires information for future use.

The coding-agent harnesses surveyed (Claude Code, Codex, goose, OpenClaw, Letta Code, and others) all implement memory, but each uses a different convention: `AGENTS.md`, `MEMORY.md`, `USER.md`, `HUMAN.md`. Developers cannot move a stateful agent from one harness to another. Enterprises cannot switch memory providers without re-ingesting derived memory objects. Open-source memory projects duplicate one another because there is no shared object model, provenance format, or exchange format to converge on. Provenance is lost when memory is copied, and permissions that meant something in one system do not survive export. OMP aims to be the thinnest layer that addresses this while leaving storage backends, ownership models and internal architectures to implementers.

### What existing memory systems share

The [scoping note](working-group/past-proposals/scoping-note-2026-09.pdf) finds five practices a minimal protocol can standardize; the [prior-art survey](docs/prior-art/)'s convergence analysis reaches similar conclusions:

1. **Persistent memory across sessions.** Memory that survives the end of a conversation.
2. **Scope and ownership.** Every memory tied to a user, project, agent, team or organization.
3. **Lifecycle operations.** Create (remember), read (recall), update, delete (forget).
4. **Selective retrieval.** Agents request the memories relevant to the task, not the whole store.
5. **Controls and policy.** Privacy, access, retention, provenance, permission.

## Artifacts

### Contributed proposals

Inputs to the working specification. Only the latest revision of each is listed here; superseded revisions are in [`working-group/past-proposals/archive/`](working-group/past-proposals/archive/).

- **Letta draft v0.2** — Charles Packer (Letta). A `MEMORY.md` directory with progressive disclosure and a four-rule harness contract; ownership, versioning and sync are out of scope. [`working-group/past-proposals/draft-v0.2-packer.pdf`](working-group/past-proposals/draft-v0.2-packer.pdf)
- **IBM proposal v0.1** — An immutable memory record (body, id, author, AI provenance, created/invalidated, version comparator, source, semantic and scope tags) and the runtime verbs remember, recall, observe and decorate. [`working-group/past-proposals/draft-v0.1-ibm.pdf`](working-group/past-proposals/draft-v0.1-ibm.pdf)
- **AI Disclosures Project, Federated Memory Protocol draft v0.2** — Sruly Rosenblat (October 13, 2026). Many memory servers behind one plugin, over native, plugin + MCP, or plain MCP endpoints. Numbered v1.1 inside the document. [`working-group/past-proposals/draft-v0.2-aidp.pdf`](working-group/past-proposals/draft-v0.2-aidp.pdf)
- **Cognee proposal v0.1** — A semantic core for portable agent memory: identity, evidence, authority, lineage, lifecycle and exchange fidelity, with COGX as an implemented reference input. [`working-group/past-proposals/draft-v0.1-cognee.md`](working-group/past-proposals/draft-v0.1-cognee.md)
- **Context Nest proposal v0.1** — PromptOwl. A governed Markdown profile: front-matter keys and in-prose links as the atomic unit, `contextnest://` addressing, scoped selectors, append-only hash-chained history, and a forget protocol. [`working-group/past-proposals/draft-v0.1-contextnest.md`](working-group/past-proposals/draft-v0.1-contextnest.md)
- **Sapience knowledge-object proposal v0.2** — Sapience Labs. The knowledge object as a portable memory unit: confidence carried in provenance, two timestamps, supersession as a first-class relation; mapped onto editors' draft v0.2. [`working-group/past-proposals/draft-v0.2-sapience.md`](working-group/past-proposals/draft-v0.2-sapience.md)
- **`me.md`** — David Hamilton (Block / goose). A user-owned, plain-file protocol for what agents know about you; agents may only propose additions. Complementary discussion draft, maintained at [`block/me.md`](https://github.com/block/me.md).

### Surveys and documentation

- **Scoping note** (August 2026) — Strauss and Rosenblat. Surveys current memory implementations and the shared primitives a protocol can standardize. [`working-group/past-proposals/scoping-note-2026-09.pdf`](working-group/past-proposals/scoping-note-2026-09.pdf)
- **Prior-art survey** (September 2026) — Memory implementations, standards and research across the ecosystem, with a convergence analysis. [`docs/prior-art/`](docs/prior-art/)
- **Agent Memory System Card (AMS Card)** — A documentation format for agent memory systems, by [Mila](https://mila.quebec/) and [Mozilla](https://mozilla.org). Template, reference card and evaluation framework: [`mila-iqia/agent-memory-system-card`](https://github.com/mila-iqia/agent-memory-system-card/). Draft, open for comment. [`working-group/past-proposals/ams-card.md`](working-group/past-proposals/ams-card.md)
- **The Memory Walled Garden** (October 2025) — Essay on memory lock-in and the case for portability. Markdown archive with figures. [`docs/the-memory-walled-garden/`](docs/the-memory-walled-garden/the-memory-walled-garden.md)

### Code and prototypes

- **Live demo (omp-live)** — One set of memories kept in sync across a Markdown file tree, a knowledge graph, a full-text index and a coding agent through OMP interchange records; forgets leave tombstones, conflicts wait for a person. Built for FOO Camp. [ompi.fly.dev](https://ompi.fly.dev) · source [`SrulyRosenblat/ompi-foo-camp`](https://github.com/SrulyRosenblat/ompi-foo-camp/tree/main/omp-live)
- **Python loader / validator** — Sketch of a loader, validator and harness contract for the Letta v0.2 draft; not yet updated to v0.5. [`prototypes/python-loader-validator/`](prototypes/python-loader-validator/)
- **ACP memory server** — Earlier prototype that indexes session history across twelve coding-agent harnesses, imported from [`SrulyRosenblat/agent_memory_mcp`](https://github.com/SrulyRosenblat/agent_memory_mcp) at commit `02b8d92`. [`prototypes/acp_memory_server/`](prototypes/acp_memory_server/)

## Repository layout

```
working-group/exchange-and-runtime/   current editors' draft (v0.5) and working-group notes
working-group/past-proposals/         contributed proposals (latest revision of each; archive/ holds superseded ones), the scoping note, the AMS card
prototypes/                           experimental code
docs/                                 contributing guide, history, prior-art survey, the Memory Walled Garden essay
media/                                logos
GOVERNANCE.md · SECURITY.md · LICENSE · README.md
```

## How to contribute

- Issues and pull requests against the [v0.5 working spec](working-group/exchange-and-runtime/2026-11-06-working-spec-v0.5.md); proposals go in `working-group/past-proposals/`. Process, meetings and code conventions: [docs/contributing.md](docs/contributing.md).
- Discussion: [Discord](https://discord.gg/B8Fhcech4) (by application) or [ompi@aidisclosures.org](mailto:ompi@aidisclosures.org).

## Governance

Decisions go through a Technical Steering Group under the rules in [GOVERNANCE.md](GOVERNANCE.md): lazy consensus among maintainers, simple-majority TSG votes for unresolved questions, two-thirds for breaking changes. Contributions use a DCO sign-off. An external governance review in months 12–24 assesses the long-term home, with continued AI Disclosures Project / CS&S stewardship as the default. How the initiative got here: [docs/history.md](docs/history.md).

## License

- Specification documents: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)
- Code in this repository: [Apache 2.0](LICENSE)
