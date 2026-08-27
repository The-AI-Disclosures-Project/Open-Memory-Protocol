<p align="center">
  <img src="media/ompi-logo.png" alt="Open Memory Protocol Initiative" width="640">
</p>

<p align="center">
  <a href="https://ai-disclosures.org/ompi"><strong>Site</strong></a> ·
  <a href="spec/draft-v0.1.md"><strong>Draft spec</strong></a> ·
  <a href="reference/"><strong>Experimental code</strong></a> ·
  <a href="prototypes/"><strong>Prototypes</strong></a> ·
  <a href="GOVERNANCE.md"><strong>Governance</strong></a> ·
  <a href="docs/contributing.md"><strong>Contribute</strong></a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/status-pre--1.0-orange" alt="Status: pre-1.0">
  <img src="https://img.shields.io/badge/spec-CC%20BY%204.0-lightgrey" alt="Spec license: CC BY 4.0">
  <img src="https://img.shields.io/badge/code-Apache%202.0-lightgrey" alt="Code license: Apache 2.0">
  <img src="https://img.shields.io/badge/python-3.10%2B-blue" alt="Python 3.10+">
</p>

---

> **Current stage.** OMPI is at the early-stage discussion phase. The protocol has not been built. The specification is a discussion draft, the Python code is an early experiment, and the working group holds its **first informal discussion on September 9, 2026** (online, co-hosted with Mozilla and IBM). Every artifact in this repository is a starting point for RFC review, not a finalized deliverable.

---

# Open Memory Protocol Initiative

This repository is the shared working space for the Open Memory Protocol Initiative (OMPI), undertaken with partners to advance portable, interoperable, and user-controlled memory across AI systems.

The **Open Memory Protocol (OMP)** is the technical work: an open, interoperable protocol for portable AI-agent memory. **OMPI** is the multi-stakeholder working group that develops it, hosted at the [AI Disclosures Project](https://ai-disclosures.org/) (a project of [Code for Science & Society](https://www.codeforsociety.org/)).

## Why OMP

Agent memory is persistent context that affects future model or agent behavior: user-provided facts, model- or agent-derived summaries, project instructions, prior decisions and actions, tool outputs, and references to underlying transcripts or artifacts. It is scoped to a user, project, organization, or shared group, and is distinct from a raw chat export. A memory system selects, transforms, organizes, retrieves, and expires information for future use.

Every major coding-agent harness (Claude Code, Codex, goose, OpenClaw, Letta Code) implements memory, but each uses a different convention — `AGENTS.md`, `MEMORY.md`, `USER.md`, `HUMAN.md`. Developers cannot move a stateful agent from one harness to another. Enterprises cannot switch memory providers without re-ingesting derived memory objects. Open-source memory projects duplicate one another because there is no shared object model, provenance format, or exchange protocol to converge on.

Fragmented memory has real engineering and security costs. Developers write bespoke adapters. Users and enterprises cannot reliably move accumulated context. Provenance is often lost when memory is copied. Permissions that were meaningful in one system may not survive export, and security review is harder when each integration defines its own exchange behavior. OMP specifies the smallest interoperable layer needed to address these costs while allowing implementations to keep their own storage backends, ownership models, and internal architectures.

## Shared practices we might build on

The working group's [scoping note](spec/scoping-note-2026-08.md) surveys memory implementations across coding harnesses, consumer assistants, and enterprise agent systems and identifies shared practices that are candidates for a minimal open protocol. These are the concrete issues the group will discuss — not commitments about what OMP will contain.

1. **Persistent memory across sessions.** Memory that survives across chat sessions rather than disappearing at conversation end. Present in Claude Code, OpenHands, Hermes, VS Code / Copilot, Deep Agents, ChatGPT, Gemini, AWS AgentCore, Vertex Memory Bank, and Microsoft Foundry.
2. **Scope and ownership.** Every memory tied to an owner or context — user, project, agent, team, or organization. Labels vary across systems, but each can answer "whose memory is this?"
3. **Lifecycle operations.** Memory treated as something with a lifecycle: create (remember), read (recall), update (correct or revise), delete (forget). Explicit in Hermes, Letta, Foundry, Copilot Studio, and various coding harnesses.
4. **Selective retrieval.** Agents request the memories relevant to the current task rather than loading the entire memory store.
5. **Controls and policy.** Rules for privacy, access, retention, provenance, and permission.

The [full scoping note](spec/scoping-note-2026-08.md) covers coding-harness patterns, consumer-assistant patterns, enterprise patterns, what is converging across vendors (background consolidation, progressive disclosure), and what remains implementation-specific (retrieval internals, human-approval workflow, MCP memory access).

## Repository layout

- [`spec/scoping-note-2026-08.md`](spec/scoping-note-2026-08.md) — working-group scoping note surveying current memory implementations and shared primitives an open protocol might build on (August 2026).
- [`spec/draft-v0.1.md`](spec/draft-v0.1.md) — Charles Packer's discussion draft of an Agent Memory Specification, circulating in the working group as a starting point for RFC review.
- [`reference/`](reference/) — an experimental Python sketch of the loader, validator, and harness contract from the discussion draft. Not a reference implementation; a first sketch for working-group discussion.
- [`prototypes/acp_memory_server/`](prototypes/acp_memory_server/) — ACP-based MCP memory-server prototype indexing sessions across twelve coding-agent harnesses (Claude Code, Codex, Goose, Cursor, Cline, Roo, Kilo, Zed, Gemini CLI, Qwen Code, Continue, Aider). Originated in [`SrulyRosenblat/agent_memory_mcp`](https://github.com/SrulyRosenblat/agent_memory_mcp) with first commits in **May 2026**; imported here at upstream commit `02b8d92`.
- [`references/`](references/) — research, source notes, and background reading relevant to the initiative.
- [`docs/contributing.md`](docs/contributing.md) — how to participate in the working group.
- [`GOVERNANCE.md`](GOVERNANCE.md) — steering committee, RFC process, licensing, long-term stewardship.
- [`media/`](media/) — logo and other visual assets.

## First vertical: coding agents

The working group's initial focus is the coding-agent vertical, where memory lock-in is most acute and developer users adopt standardized tooling fastest. Early experiments explore memory transfer across Claude Code, Codex, goose, and Letta Code as a first end-to-end benchmark.

Once the protocol has stable production adoption, the written specification will be submitted to the IETF for formal ratification.

## Working group

Partners: **Mozilla** and **IBM**. Direct implementation and specification collaborators: **Letta** (specification lead), **Block / goose** (open-source agent harness). Broader working group spans agent framework maintainers, memory-focused open-source projects, vector-database providers, and enterprise adopters.

- First informal working-group discussion: **September 9, 2026** (online, co-hosted with Mozilla and IBM).
- Optional gathering: **October 2026** at the O'Reilly open-source unconference (Berkeley).

## Project history

OMPI consolidates work that has been developing across the AI Disclosures Project for over a year. The initiative did not start with this repository; this repository is where the technical and governance work is now converging.

- **August 2025** — "Protocols and Power" (Moure, O'Reilly, Strauss) is published as an SSRC working paper. It sets out the intellectual case for open protocols in AI markets and the market-structure argument that underpins OMP. Available at [ai-disclosures.org](https://www.ai-disclosures.org/assets/papers/Protocols-and-Power-Moure-OReilly-Strauss_SSRC_08272025.pdf).
- **October 3, 2025** — ["The Memory Walled Garden"](https://asimovaddendum.substack.com/p/the-memory-walled-garden) publishes on *Asimov's Addendum* as the initiative's first public position on portable AI-agent memory.
- **April–May 2026** — Rockefeller Foundation Bellagio convening on *Human + AI Markets*. Twenty leaders across AI labs, memory-infrastructure providers, and civil-society organizations discuss agent-memory portability among other open-market questions.
- **May 2026** — First public commits on the ACP-based memory-server prototype ([`SrulyRosenblat/agent_memory_mcp`](https://github.com/SrulyRosenblat/agent_memory_mcp)), covering session indexing across twelve coding-agent harnesses. Now imported here as [`prototypes/acp_memory_server/`](prototypes/acp_memory_server/).
- **June 2026** — FOO Camp session (O'Reilly Media, Lighthaven Berkeley) advances the coding-agent memory-portability agenda with builders across the stack.
- **August 2026** — Charles Packer (Letta) circulates the draft Agent Memory Specification, reviewed by the AI Disclosures Project team; this is the working draft that has become [`spec/draft-v0.1.md`](spec/draft-v0.1.md). OMPI consolidates its work in this repository as the canonical technical and governance home.
- **September 9, 2026** — First informal working-group discussion, co-hosted with Mozilla and IBM.
- **October 2026** — In-person gathering at the O'Reilly open-source unconference (Berkeley).

## Working group recruitment network

As of August 2026, the OMPI outreach and technical-review pipeline contains **54 external individuals across 44 organizations or affiliations**, spanning the full agent-memory stack. Representative organizations tracked in the pipeline include Anthropic (Claude Code), OpenAI (Codex, ChatGPT Memory), Google (Gemini, ReasoningBank), AWS AgentCore Memory, Microsoft (AutoGen), LangChain / LangGraph, LlamaIndex, Letta, Mem0, Zep, Graphiti, Pinecone, Salesforce Agentforce, LinkedIn, W3C, the Agentic AI Foundation, and multiple coding-agent projects.

Thirteen external participants from ten affiliations are confirmed for the September 9, 2026 technical convening. Recruitment for the working group remains open beyond the founding network; contacts are counted as OMP users only when they actually implement or test the protocol, not on the basis of interest or attendance.

## Working principles

The initiative is focused on an open memory ecosystem in which people can retain meaningful control over their data, move context between compatible AI tools, and benefit from competition and innovation without rebuilding their history in every application.

This repository will evolve as the initiative and partner work progress.

## How to contribute

- Read the [current draft spec](spec/draft-v0.1.md) and open an issue with feedback.
- Try the experimental Python sketch ([`reference/`](reference/)) against your own memory workload.
- Explore the ACP-based memory-server prototype ([`prototypes/acp_memory_server/`](prototypes/acp_memory_server/)).
- Contact [ompi@aidisclosures.org](mailto:ompi@aidisclosures.org) to join the working group.

## License

- Specification and documentation: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)
- Code in this repository: [Apache 2.0](LICENSE)
