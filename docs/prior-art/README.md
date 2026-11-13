# Prior Art Survey

A survey of memory implementations, standards, and research relevant to the
Open Memory Protocol. This directory captures what exists across the ecosystem
as of September 2026, to inform protocol design decisions.

## Scope

This survey covers three layers of the memory landscape:

1. **Implementations** -- how shipping products and open-source projects handle
   agent memory today, from coding-agent harnesses to enterprise platforms.
2. **Standards and formats** -- emerging specifications, exchange formats, and
   protocol proposals that address memory portability and interoperability.
3. **Research** -- academic work on memory architectures, benchmarks, and
   empirical findings that inform what a standard should require.

## How to read these documents

Each survey document describes what systems do and the design choices they make.
Where systems share a design choice, the survey presents that as convergence.
Where they diverge, the survey describes the tradeoffs each approach optimizes
for. The [convergence analysis](convergence-analysis.md) synthesizes patterns
across all the surveyed systems and identifies what a minimum viable
interoperability standard needs to cover.

## Documents

| Document | Contents |
|----------|----------|
| [Agent Harness Memory Systems](agent-harness-memory-systems.md) | Claude Code, Codex, Goose, Cursor, Cline, Gemini CLI, Continue, Aider, OpenHands, Copilot, OpenClaw, Hermes, Pi |
| [Enterprise Memory Services](enterprise-memory-services.md) | Letta/MemGPT, Mem0, Zep/Graphiti, Cognee, AWS AgentCore, Google Vertex, Microsoft Foundry, ChatGPT, Pi |
| [Emerging Standards](emerging-standards.md) | PAM, COGX, Engram, SAIHM, Memoryfield, ATIF/Harbor, Letta Trajectory, me.md, Agent Memory System Card |
| [Interoperability Protocols](interoperability-protocols.md) | MCP, A2A, PTC/GAL, ANP, AGNTCY, AG-UI, and how memory fits the protocol landscape |
| [Convergence Analysis](convergence-analysis.md) | Shared patterns, divergent choices, and the design space for a minimum viable standard |
| [Academic Foundations](academic-foundations.md) | CoALA taxonomy, benchmarks, empirical findings on portability, forgetting, and graph structure |

## Methodology

Research was conducted through direct examination of source code, published
specifications, documentation, and academic papers. GitHub repositories were
cloned and read at the code level where possible. Published benchmarks and
empirical studies were consulted for claims about portability, retrieval quality,
and architectural tradeoffs.

Where a system's architecture is documented only through marketing material or
blog posts rather than code or specifications, that limitation is noted.

## Contributing

This survey is a living document. If you notice an inaccuracy, a missing system,
or a mischaracterization of your project's design choices, please open an issue
or submit a correction. We want this to be useful and fair to every project it
describes.
