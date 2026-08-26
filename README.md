<p align="center">
  <img src="media/ompi-logo.png" alt="Open Memory Protocol Initiative" width="640">
</p>

<p align="center">
  <a href="https://ai-disclosures.org/omp"><strong>Site</strong></a> ·
  <a href="spec/draft-v0.1.md"><strong>Draft spec</strong></a> ·
  <a href="reference/"><strong>Reference implementation</strong></a> ·
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

# Open Memory Protocol Initiative

This repository is the shared working space for the Open Memory Protocol Initiative (OMPI), undertaken with partners to advance portable, interoperable, and user-controlled memory across AI systems.

The **Open Memory Protocol (OMP)** is the technical work: an open, interoperable protocol for portable AI-agent memory. **OMPI** is the multi-stakeholder working group that develops it, hosted at the [AI Disclosures Project](https://ai-disclosures.org/) (a project of [Code for Science & Society](https://www.codeforsociety.org/)).

## Why OMP

Every major coding-agent harness (Claude Code, Codex, goose, OpenClaw, Letta Code) implements memory, but each uses a different convention — `AGENTS.md`, `MEMORY.md`, `USER.md`, `HUMAN.md`. Developers cannot move a stateful agent from one harness to another. Enterprises cannot switch memory providers without re-ingesting derived memory objects. Open-source memory projects duplicate one another because there is no shared object model, provenance format, or exchange protocol to converge on.

OMP specifies the smallest interoperable layer needed to make agent memory portable across harnesses and memory-layer services. Backends, storage, ownership, synchronization, and internal architecture stay with implementers.

## Repository layout

- [`spec/draft-v0.1.md`](spec/draft-v0.1.md) — the current draft specification, authored by Charles Packer (Letta) with feedback from the AI Disclosures Project team.
- [`reference/`](reference/) — Python reference implementation of the loader, validator, and harness contract (runs against any spec-conformant memory directory).
- [`prototypes/acp_memory_server/`](prototypes/acp_memory_server/) — ACP-based MCP memory-server prototype (Sruly Rosenblat).
- [`references/`](references/) — research, source notes, and background reading relevant to the initiative.
- [`docs/contributing.md`](docs/contributing.md) — how to participate in the working group.
- [`GOVERNANCE.md`](GOVERNANCE.md) — steering committee, RFC process, licensing, long-term stewardship.
- [`media/`](media/) — logo and other visual assets.

## First vertical: coding agents

OMP's initial development focus is the coding-agent vertical, where memory lock-in is most acute and developer users adopt standardized tooling fastest. The reference implementation targets memory transfer across Claude Code, Codex, goose, and Letta Code as a first end-to-end benchmark.

Once the protocol has stable production adoption, the written specification will be submitted to the IETF for formal ratification.

## Working group

Formal in-kind partners: **Mozilla** and **IBM**. Direct implementation and specification collaborators: **Letta** (specification lead), **Block / goose** (open-source agent harness). Broader working group spans agent framework maintainers, memory-focused open-source projects, vector-database providers, and enterprise adopters.

- Kickoff technical convening: **September 9, 2026** (online, co-hosted with Mozilla and IBM).
- Second convening: **October 2026** at the O'Reilly open-source unconference (Berkeley).

## Working principles

The initiative is focused on an open memory ecosystem in which people can retain meaningful control over their data, move context between compatible AI tools, and benefit from competition and innovation without rebuilding their history in every application.

This repository will evolve as the initiative and partner work progress.

## How to contribute

- Read the [current draft spec](spec/draft-v0.1.md) and open an issue with feedback.
- Try the Python reference implementation ([`reference/`](reference/)) against your own memory workload.
- Explore the ACP-based memory-server prototype ([`prototypes/acp_memory_server/`](prototypes/acp_memory_server/)).
- Contact [ompi@ai-disclosures.org](mailto:ompi@ai-disclosures.org) to join the working group.

## License

- Specification and documentation: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)
- Reference implementation and other code in this repository: [Apache 2.0](LICENSE)
