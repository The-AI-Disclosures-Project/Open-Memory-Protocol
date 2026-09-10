# Academic Foundations

Research on agent memory architectures, taxonomies, benchmarks, and empirical
findings that inform protocol design. This document covers settled science,
active research frontiers, and empirical results with direct implications for
what a memory standard should require.

## Memory Taxonomy

### The four-type model (CoALA, Princeton, TMLR 2024)

The Cognitive Architectures for Language Agents (CoALA) framework established a
four-type memory taxonomy that has become the baseline across the field:

- **Working memory**: the active context window, including the current
  conversation, retrieved documents, and tool results. Volatile by nature.
- **Episodic memory**: timestamped records of experiences and interactions.
  "What happened" knowledge, anchored in time.
- **Semantic memory**: durable facts, preferences, and knowledge extracted
  from experience. "What is true" knowledge, independent of when it was learned.
- **Procedural memory**: skills, workflows, and learned behavioral patterns.
  "How to do things" knowledge, including self-modification of prompts and
  strategies.

Multiple independent surveys (December 2025 survey of memory in LLM agents,
AWS and Microsoft's 2026 product announcements, LangMem's design) converge on
this taxonomy, sometimes with different labels but consistent underlying
concepts. CoALA's framing maps directly to the cognitive science categories it
draws from: Tulving's episodic/semantic distinction (1972) and Anderson's ACT-R
procedural memory (1983).

### Extensions to the taxonomy

**Identity memory** (PAM, 2026): Portable Agent Memory adds a fifth category
for user preferences, persona, language, policies, and custom instructions.
This separates "who I am working with" from "what I know," a distinction
several implementations make in practice (Claude Code's user memories,
ChatGPT's personalization) without naming as a formal type.

## Foundational Architectures

### Generative Agents (Stanford/Google, UIST 2023)

The conceptual ancestor of structured agent memory. Introduced the
observation-reflection-planning triad, which maps to episodic-semantic-procedural
memory. Key design choices that influenced the field:

- Natural-language-first storage (memories as prose, not structured records)
- Retrieval by recency, importance, and relevance (a weighted combination)
- Reflection as a distinct operation (synthesizing higher-level insights from
  raw observations)

The ablation study demonstrated that all three components (observation,
reflection, planning) are independently critical. Removing any one produced
measurably degraded agent behavior. This result has been replicated in
subsequent work and supports the argument that a memory standard should
accommodate all three memory types rather than privileging one.

### MemGPT / Letta (UC Berkeley, 2023)

Introduced OS-inspired virtual context management with an explicit tool-call
interface for memory operations. Three tiers:

- **Core memory**: always in the context window (persona, user information)
- **Recall memory**: recent conversation history, searchable
- **Archival memory**: long-term storage, accessed via search

The tool-call interface for memory operations (`core_memory_append`,
`core_memory_replace`, `archival_memory_search`, `archival_memory_insert`)
became a widely adopted pattern. The insight that memory management operations
should be exposed as tools the agent calls, rather than handled transparently
by the runtime, influenced MCP-based memory servers and subsequent designs.

Renamed to Letta in September 2024. The Letta team authored the Packer draft
of OMP (v0.2), bringing this architectural perspective directly into the
standards conversation.

## Benchmarks

### LongMemEval (ICLR 2025)

500 questions testing five memory abilities across extended conversation
histories:

- Information extraction
- Multi-session reasoning
- Temporal reasoning
- Knowledge updates (handling contradictions and corrections)
- Abstention (knowing when a memory is absent or uncertain)

Key finding: accuracy drops 30-60% as conversation histories lengthen, across
all tested systems. This result motivates structured memory with explicit
lifecycle management over raw conversation logging. Systems that extract and
maintain discrete memories outperform those that search raw transcripts.

A V2 extension (LongMemEval-V2) adapts the benchmark for agentic contexts
where agents take actions based on recalled memories.

### MemoryAgentBench (ICLR 2026)

Tests incremental multi-turn interactions with a focus on retention, update,
and conflict resolution. Evaluates whether agents can maintain consistent
beliefs as new information arrives and old information is superseded.

### AgentMemBench (June 2026)

Systematic comparison of five memory strategies across three datasets and 491
turns. Provides controlled comparisons between retrieval approaches and memory
structures.

### Memory-R1 (August 2025)

An RL-trained memory manager with structured operations (ADD, UPDATE, DELETE,
NOOP). Achieved state-of-the-art on LoCoMo with +48% F1 and +69% BLEU-1 over
prior best. Demonstrates that learned memory management policies can
outperform hand-crafted heuristics, suggesting that a protocol should define
the operation vocabulary (what operations are available) without prescribing
the policy (when to use them).

## Empirical Findings Relevant to Protocol Design

### Structured schemas are more portable than free-form text

A controlled study (arXiv:2609.05339, September 2026) compared knowledge graph
representations against compressed text notes for cross-model memory transfer.
Results:

- Knowledge graphs transferred across model swaps with near-zero accuracy
  change (+0.0004 +/- 0.0020)
- Compressed text notes shifted +9.91 or -13.28 percentage points depending
  on the model pair

This provides direct empirical support for schema-based memory objects over
free-form text as the basis for a portability standard. A well-defined schema
survives model changes; prose does not.

### Graph structure outperforms flat storage for multi-hop reasoning

Multiple independent systems (HippoRAG, MAGMA, Zep/Graphiti, AriGraph, GAM)
demonstrate that graph-structured memory outperforms flat vector stores on
relationship traversal, temporal reasoning, and causal inference. The advantage
is most pronounced for queries that require connecting information across
multiple memories ("What did I decide about X after learning Y?").

This finding supports including relationship primitives (typed edges between
memories) in the protocol, even if not all implementations use them. The
protocol should be able to express "memory A supersedes memory B" or "memory C
was derived from memory D."

### Forgetting is as important as remembering

Multiple independent research threads converge on the finding that memory
systems without principled forgetting degrade over time:

- **MemoryBank** (Zhong et al.): applies Ebbinghaus forgetting curves to
  decay unreinforced memories
- **SCM** (Self-Controlled Memory): intentional forgetting of low-utility
  memories improves retrieval precision
- **Memory-R1**: the DELETE operation contributes measurably to performance;
  removing it degrades results
- **Sleep-consolidation research**: background reorganization during idle
  time strengthens important memories and prunes noise

A memory standard that defines only write and read operations, without
addressing lifecycle management (expiry, decay, supersession, deletion), will
produce systems that accumulate noise and degrade. The standard should define
lifecycle operations and the metadata needed to support them (timestamps,
relevance signals, expiry dates).

### Sleep-time consolidation is convergent

Multiple independent groups have arrived at background processing during idle
time to reorganize, compress, and strengthen memories:

- Letta's "dreaming" pipeline (background extraction and consolidation)
- SCM's self-controlled memory reorganization
- GAM's graph-based memory consolidation
- The "Language Models Need Sleep" research thread

This mirrors biological sleep consolidation and suggests that a memory standard
should accommodate asynchronous memory operations (extraction, consolidation,
decay) alongside synchronous ones (write, read, search).

### Memory security is a requirement, not an option

- **OWASP ASI06** recognizes memory poisoning as a top agentic security risk
- **MINJA** (Memory Injection Attacks) research demonstrates 95%+ injection
  success rates against production agent memory systems
- **SMSR** (Signed Memory with Source Recording) achieves 0% attack success
  for unsigned memory injection by applying HMAC-SHA256 provenance at write
  time

The implication for protocol design: provenance metadata on memories is not
optional. A memory without provenance information (who created it, how, from
what source) is vulnerable to injection. The standard should require minimum
provenance fields on every memory object.

## References

- CoALA: Sumers et al., "Cognitive Architectures for Language Agents," TMLR 2024
- Generative Agents: Park et al., "Generative Agents: Interactive Simulacra of Human Behavior," UIST 2023
- MemGPT: Packer et al., "MemGPT: Towards LLMs as Operating Systems," 2023
- LongMemEval: Wang et al., ICLR 2025
- Memory-R1: arXiv, August 2025
- Portability study: arXiv:2609.05339, September 2026
- MINJA: Zeng et al., "Practical LLM Agent Memory Injection Attacks," 2024
- MemoryBank: Zhong et al., 2024
