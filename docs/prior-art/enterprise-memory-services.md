# Enterprise Memory Services

Memory systems designed for production deployment, multi-tenant operation, and
integration with agent frameworks. These range from open-source libraries to
managed cloud services. They share the coding-agent harnesses' core problem
(agents need persistent knowledge) but operate at a different scale and with
different constraints: multi-user, multi-agent, API-driven, and often backed
by databases rather than files.

## Systems surveyed

### Letta / MemGPT

**Architecture:** OS-inspired virtual context management with an explicit
tool-call interface for memory operations. Three memory tiers:

- **Core memory**: always in the context window. Contains persona description
  and user information. Bounded in size. Modified via tool calls
  (`core_memory_append`, `core_memory_replace`).
- **Recall memory**: recent conversation history. Searchable via
  `conversation_search`.
- **Archival memory**: long-term storage. Accessed via
  `archival_memory_search` and `archival_memory_insert`.

**Data model:** Memory records with id, content, type, source, tags,
timestamps, and optional embeddings. The Packer draft of OMP (v0.2) reflects
this architecture directly.

**Storage:** PostgreSQL with pgvector for the hosted service. Configurable
backends for self-hosted.

**Scope model:** Agent-level (each agent has its own memory state).
Multi-agent orchestration supported but memories are per-agent.

**Lifecycle:** Agent-managed via tool calls. The agent decides when to write,
search, and modify its own memory. Background "sleep-time" consolidation
(dreaming) extracts and reorganizes memories from conversation history.

**Retrieval:** Hybrid search combining embedding similarity and keyword
matching. Core memory is always present; recall and archival memory are
searched on demand.

**User control:** Users can view and edit core memory blocks through the Letta
interface. Archival memory is searchable but less directly editable.

**Portability:** The Letta Trajectory library normalizes session transcripts
from 15 agent runtimes into a common format, but memory objects themselves
do not have a portable exchange format.

**Adoption:** $10M seed at $70M valuation (September 2024). The MemGPT paper
(UC Berkeley, 2023) introduced the tool-call memory management pattern that
influenced subsequent designs. The team authored the Packer draft of OMP.

### Mem0

**Architecture:** Multi-backend memory layer that combines three storage
systems simultaneously:

- **Vector store** (Qdrant, pgvector) for semantic search
- **Graph store** (Neo4j) for entity relationships
- **Key-value store** (Redis) for exact-match lookups

A routing layer selects the appropriate backend per query. LLM-based
extraction runs on the write path (every `add()` call invokes an LLM to
extract structured memories from the input).

**Data model:** Atomic facts with metadata. Scoped by `user_id`, `agent_id`,
or `run_id`. Each fact carries an extraction timestamp and source reference.

**Lifecycle:** Memories are created by LLM extraction during `add()`.
Updates, deletions, and history queries are supported. A 2026 algorithm
update added temporal reasoning (+29.6 points) and multi-hop reasoning
(+23.1 points).

**Retrieval:** Multi-signal: semantic similarity, BM25 keyword matching, and
entity linking run in parallel. Results are merged and ranked.

**User control:** Programmatic CRUD via the SDK. The hosted platform provides
a dashboard.

**Portability:** No defined export format or interchange protocol. Pluggable
backends in principle, but no portable memory representation.

**Adoption:** ~48K GitHub stars. $24M Series A. ~14M PyPI downloads. Broad
framework integrations (LangChain, CrewAI, AutoGen, Vercel AI SDK).

### Zep / Graphiti

**Architecture:** Two related products. Zep Cloud is a proprietary managed
service. Graphiti (Apache-2.0) is the open-source temporal knowledge graph
engine underneath.

**Data model:** A temporally-aware dynamic knowledge graph with three
hierarchical tiers:

- **Episode subgraph**: immutable raw input records
- **Semantic entity subgraph**: extracted entities and relationships
- **Community subgraph**: higher-order patterns and clusters

Bi-temporal model: every edge carries an event time (when the fact was true)
and an ingestion time (when the system learned it). This enables temporal
conflict resolution: old facts are invalidated, not deleted, preserving
history.

**Lifecycle:** Episodes are ingested and immutably stored. Entity extraction
runs asynchronously using LLMs, but only on the write path. Conflict
resolution handles contradictory facts using temporal ordering.

**Retrieval:** Hybrid retrieval combining semantic similarity, BM25, and
graph traversal. No LLM in the retrieval loop (P95 under 300ms).
Pre-formatted "Context Blocks" simplify prompt injection.

**User control:** API access to entities, relationships, and episodes.

**Portability:** Graph data tied to Neo4j/FalkorDB/Neptune. No defined
export format.

**Adoption:** ~30K GitHub stars for Graphiti. Benchmarks: 94.8% on DMR,
63.8% on LongMemEval (vs. Mem0's 49.0%).

### Cognee

**Architecture:** Open-source platform (Apache-2.0) with a knowledge graph
core and the COGX exchange format concept.

**Data model:** Strongly-typed `DataPoint` objects (Pydantic models) serving
as both node and edge schemas. Each DataPoint gets a UUID, version, and
timestamp. Nested DataPoints are recursively unpacked and deduplicated.

**Operations:** Four memory-native verbs in Cognee 1.0: `remember`, `recall`,
`forget`, `improve`. The ECL pipeline (Extract, Cognify, Load) handles
ingestion.

**Distinctive feature:** Feedback loops where agent-rated responses update
edge weights, causing the knowledge graph to improve with use.

**Portability:** COGX is a JSON-based archive format for exporting and
importing memory graphs, with claimed import from Mem0, Letta, Zep, and
Graphiti. However, no formal schema specification is publicly documented.

**Adoption:** $7.5M seed. 5M+ SDK runs/month. 28K GitHub stars.

### AWS AgentCore Memory

**Architecture:** Proprietary managed service (Amazon Bedrock).

**Data model:** Two tiers:

- **Short-term**: immutable events by actor and session (conversational or
  binary blobs)
- **Long-term**: three types extracted asynchronously:
  - *Episodic*: timestamped session records
  - *Semantic*: durable facts and preferences
  - *Procedural*: learned workflows and tool-use patterns (added at Build
    2026; showed 7-14% success rate gains on Tau bench)

**Lifecycle:** Extract, Consolidate (merge/deduplicate via LLMs), Retrieve
(hybrid search). Memory item CRUD with metadata (up to 10 indexed keys).
Store-level TTL. Lifecycle policies (September 2026) use Step Functions +
Bedrock for nightly score/consolidate/prune cycles.

**User control:** API-driven. Dashboard in the AWS console.

**Portability:** None. Fully AWS-locked.

### Google Vertex Memory Bank

**Architecture:** Proprietary managed service (GA since January 2026, $0.25
per 1K events).

**Data model:** Extracts facts, preferences, and context from conversation
history using Gemini models. Scoped per-user with data isolation.

**Operations:** Two pre-built tools: `PreloadMemoryTool` (auto-retrieval at
turn start) and `LoadMemoryTool` (on-demand). Two service implementations:
`InMemoryMemoryService` (prototyping) and `VertexAiMemoryBankService`
(production).

**Research basis:** Grounded in Google Research's topic-based memory approach
(ACL 2025). Memory poisoning mitigation via Model Armor integration.

**User control:** API access. Enterprise admin controls.

**Portability:** None. Tightly coupled to Google ADK and Agent Engine Sessions.

### Microsoft Foundry Agent Service Memory

**Architecture:** Proprietary managed service (preview since Ignite 2025).

**Data model:** Three types: user memory (preferences/facts), session memory,
procedural memory (added at Build 2026). Three phases: Extract, Consolidate,
Retrieve.

**Operations:** Memory item CRUD with TTL. Direct remember-or-forget
synchronous commands. Scoping via `scope` parameter for partitioning.

**Security integration:** Azure AI Content Safety and prompt injection
detection for memory validation.

**User control:** API-driven. Enterprise admin controls.

**Portability:** None. Azure-locked.

### ChatGPT Memory (OpenAI)

**Architecture:** Cloud-hosted, opaque memory system integrated into the
ChatGPT consumer product.

**Data model:** Atomic facts extracted by the model from conversations.
Each memory is a short natural-language statement. Scoped to the user account.

**Lifecycle:** The model decides when to create, update, or delete memories
based on conversation content. Users can also explicitly instruct the model
to remember or forget something. No TTL or expiration.

**Retrieval:** Relevant memories are automatically surfaced and injected into
the system prompt for each conversation. The selection mechanism is not
publicly documented.

**User control:** Users can view all memories, edit individual memories, and
delete specific memories or all memories at once. A toggle allows disabling
memory entirely.

**Portability:** No export mechanism. Memories are tied to the OpenAI account.

### Pi (Inflection)

**Architecture:** Cloud-hosted personalization system integrated into the Pi
conversational AI.

**Data model:** User preferences, personal context, and conversation history.
Designed for emotionally aware, relationship-oriented interactions.

**Lifecycle:** Extracted from conversations. Oriented toward personal
relationship building rather than task completion.

**User control:** Limited visibility into what is stored. Users can
instruct Pi to forget specific things.

**Portability:** None. Fully proprietary.

### LangMem (LangChain)

**Architecture:** Open-source Python SDK (pre-1.0, v0.0.30) for adding memory
to LangChain/LangGraph agents.

**Data model:** Three types modeled on human cognition:

- **Semantic**: facts and preferences extracted from conversations
- **Episodic**: records of past interactions
- **Procedural**: agents modifying their own prompts based on experience
  (the agent learns to improve its instructions)

**Storage:** Works with any LangGraph-compatible store backend.

**Lifecycle:** LLM-based extraction. Supports memory consolidation and
conflict resolution.

**Retrieval:** Search-based. Performance caveat: P95 search latency on LOCOMO
is 59.82 seconds vs Mem0's 0.200 seconds.

**Portability:** Coupled to the LangChain ecosystem. No portable exchange
format.

**Adoption:** ~746K monthly PyPI downloads.

## Convergent patterns

**LLM-based extraction is universal for service-based systems.** Every
enterprise memory service uses an LLM on the write path to extract structured
memories from unstructured conversation. The specific extraction approach
varies (single-pass in Mem0, reflection-based in Letta, ECL pipeline in
Cognee), but the pattern is consistent. Coding-agent harnesses generally
do not use LLM extraction; they rely on the agent itself to write memories
via tool calls or on users to maintain memory files manually.

**The three-type taxonomy is convergent.** AWS, Microsoft, and LangMem
independently arrived at the same three-type model: episodic, semantic,
and procedural. Google's Memory Bank uses semantic and episodic. Letta's
three tiers (core, recall, archival) map to a similar split. The CoALA
taxonomy (working, episodic, semantic, procedural) appears to be the
settled vocabulary.

**Hybrid retrieval combines multiple signals.** Mem0 (semantic + BM25 +
entity linking), Zep (semantic + BM25 + graph traversal), and AWS (hybrid
search) all combine multiple retrieval signals rather than relying on
embedding similarity alone. Pure vector search is increasingly recognized
as insufficient for memory retrieval.

**Cloud vendors converge on identical architectures.** AWS AgentCore, Google
Vertex Memory Bank, and Microsoft Foundry independently built nearly
identical systems: short-term session memory plus long-term extracted memory,
LLM-based extraction and consolidation, managed infrastructure, zero
interoperability. AWS and Microsoft both added procedural memory at their
respective 2026 conferences.

## Divergent choices

**Graph vs flat storage.** Zep/Graphiti and Cognee use knowledge graphs as
their primary structure. Mem0 uses a graph alongside vector and key-value
stores. Letta, AWS, Google, and Microsoft use flat or lightly structured
storage. The empirical evidence favors graphs for multi-hop reasoning and
temporal queries (see [Academic Foundations](academic-foundations.md)), but
graphs add operational complexity.

**Write-path vs read-path LLM usage.** Mem0 and Zep use LLMs on the write
path (extraction) but not the read path (retrieval is pure computation).
Some systems use LLMs on both paths, adding latency and cost to every query.
The write-path-only pattern achieves sub-second retrieval while still
producing structured memories.

**User visibility.** Coding-agent memories are fully visible (plain files
on disk). Enterprise service memories are API-accessible but often
lack user-facing dashboards. Consumer memories (ChatGPT, Pi) offer limited
visibility. The visibility spectrum correlates with the target audience:
developers expect to see and edit everything; consumers expect the system
to manage memory transparently.

**Portability stance.** Cognee (COGX format) and PAM are the only systems
with any portability story. Every cloud vendor and most open-source libraries
store memories in proprietary formats with no export mechanism. This is
the problem OMP exists to address.

## Implications for a standard

The convergence on three memory types (episodic, semantic, procedural), LLM-
based extraction, and hybrid retrieval suggests that a standard can be built
around shared concepts. The divergence on storage backends, graph vs flat
structure, and portability confirms that the standard should define the
object model and exchange format without prescribing storage or retrieval
implementation.

The cloud vendor lock-in pattern (identical architectures, zero
interoperability) is the strongest argument for an open standard. Users of
AWS, Google, and Microsoft memory services have no path to migrate their
agent's accumulated knowledge to another platform. A portable exchange
format would reduce switching costs and create competitive pressure toward
interoperability.
