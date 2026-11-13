# Convergence Analysis

What the surveyed systems share, where they diverge, and what those patterns
imply for a minimum viable interoperability standard.

## What everyone does the same

These patterns appear independently in enough implementations to be considered
settled. A standard that contradicts any of them will face adoption friction.

### Memory persists across sessions

Every surveyed system, from a single CLAUDE.md file to AWS AgentCore, persists
memory beyond a single conversation. The mechanisms vary (files, databases,
APIs), but the concept is universal. There is no agent memory system that is
purely ephemeral by design.

### Every memory has an owner and a scope

Every system ties memories to an owner or context. Labels vary (user, project,
agent, team, workspace, organization), but the question "whose memory is this?"
is always answered. The minimum scope set that appears across both agent harnesses
and enterprise services is **personal** (one user's knowledge) and **project**
(knowledge scoped to a codebase, workspace, or task domain).

### CRUD plus search is the operation set

Create, read, update, delete, and search appear in every system that offers
programmatic access. Some systems add archive, expire, or version operations,
but CRUD+search is the floor. No system omits any of the five.

### Selective retrieval, not full loading

No system designed for scale loads all memories into every context. All use
some form of selection: keyword matching, semantic search, scope filtering,
recency weighting, or priority/salience scoring. The exception is some coding
agents (Goose, Codex) that load all memories at startup, but this works only
because their memory stores are small enough to fit in the context window.

### Provenance matters for trust

Systems that handle memory from multiple sources (agent-extracted, user-stated,
imported) track where memories came from. The depth varies (a simple "source:
agent" tag vs a full provenance chain with confidence scores and lineage), but
the concept that a receiving system needs to know how a memory was created
appears in every specification-level proposal (OMP drafts, PAM, PTC) and in
several implementations (MemoryHub, Mem0's history, Zep's bi-temporal model).

### Markdown is the lingua franca for agent harnesses

Every agent-harness harness uses markdown for persistent memory. CLAUDE.md,
AGENTS.md, GEMINI.md, .cursor/rules, .clinerules, me.md: the format is always
markdown, often with YAML frontmatter for metadata. This convergence is
organic, not coordinated.

### LLM-based extraction is standard for service-based systems

Every enterprise memory service (Letta, Mem0, Zep, AWS, Google, Microsoft)
uses an LLM on the write path to extract structured memories from unstructured
input. The extraction approach varies, but the pattern of "LLM transforms
conversation into discrete memories" is universal for systems that operate
at scale.

## Where implementations diverge

These are the design decisions where reasonable implementations make different
choices. A standard should acknowledge these decisions and support the range
of valid approaches rather than mandating one.

### Memory type taxonomy

| Approach | Used by |
|----------|---------|
| No formal types (unstructured prose) | Codex, Cursor, Aider, Gemini CLI |
| Practical labels (fact, preference, instruction) | Claude Code, OMP Packer draft |
| Cognitive science types (episodic, semantic, procedural) | AWS, Microsoft, LangMem, PAM, CoALA |
| Three-tier architecture (core, recall, archival) | Letta/MemGPT |
| Behavioral types (experiential, knowledge, behavioral) | MemoryHub |

The CoALA four-type taxonomy (working, episodic, semantic, procedural) has the
broadest adoption in academic and enterprise contexts. The practical-label
approach has broader adoption in developer-facing tools.

**Implication:** A standard should define a recommended vocabulary that
implementations use for interoperability, with explicit guidance on how the
vocabularies map to each other. A closed enum would be premature; a recommended
set with extension points balances interoperability and flexibility.

### Storage backend

| Approach | Used by |
|----------|---------|
| Plain files (markdown) | Claude Code, Codex, Goose, Cursor, Cline, Gemini CLI |
| Relational database (PostgreSQL) | MemoryHub, Letta |
| Vector database (Qdrant, pgvector) | Mem0, Letta, AWS |
| Knowledge graph (Neo4j, FalkorDB) | Zep/Graphiti, Cognee |
| Multi-backend (vector + graph + KV) | Mem0 |
| Managed cloud service | AWS AgentCore, Google Vertex, Microsoft Foundry |

**Implication:** A standard must not prescribe a storage backend. The object
model and exchange format are what get standardized, not the storage. This is
explicitly acknowledged by the OMP scoping note and by every specification-
level proposal.

### Graph structure vs flat records

Some systems (Zep/Graphiti, Cognee, MemoryHub) maintain typed relationships
between memories (derived_from, supersedes, conflicts_with, related_to).
Others store memories as independent records with no explicit relationships.

Empirical evidence favors graphs for multi-hop reasoning and temporal queries.
Flat storage is simpler to implement and sufficient for single-lookup retrieval.

**Implication:** The standard should be able to express relationships between
memories (as optional metadata on the memory object or as a separate
relationship object), without requiring implementations to maintain a graph.
Systems that do not support graphs can ignore relationship fields; systems
that do can use them for richer retrieval.

### Retrieval strategy

| Approach | Used by |
|----------|---------|
| Load everything at startup | Goose, Codex, Cline |
| Keyword/full-text search | Claude Code (MEMORY.md index) |
| Embedding similarity | Mem0, Letta, AWS, Google |
| Hybrid (semantic + BM25 + graph) | Mem0, Zep, MemoryHub |
| Relevance ranking (recency + importance + similarity) | Generative Agents model |

**Implication:** Retrieval strategy is entirely implementation-specific. The
standard defines a search interface (what you can query on) without prescribing
how the search is executed. The minimum search interface should support text
queries, scope filtering, and result limits.

### User visibility and control

| Approach | Used by |
|----------|---------|
| Full (plain files, human-editable) | All agent harnesses |
| API-accessible with dashboard | Enterprise services |
| View and delete, limited edit | ChatGPT |
| Minimal or opaque | Pi |

**Implication:** User control over memories is a governance concern, not a
protocol concern. The standard should require that conforming implementations
support export and deletion (as operations in the access protocol), but the UI
and UX for user control is implementation-specific. A governance standard can
separately define user rights obligations.

### Agent-authored vs user-authored memory

Coding agents span a spectrum: some (Codex, Cursor, Gemini CLI) treat memory
as user-authored documentation; others (Claude Code, Goose) have the agent
create memories autonomously; enterprise services have LLMs extract memories
from conversations without explicit user instruction.

**Implication:** The standard should track authorship in provenance metadata
(who created this memory: the user, the agent, a system process, an import).
This is a field on the memory object, not a protocol-level distinction.

### Memory lifecycle

| Approach | Used by |
|----------|---------|
| No lifecycle (memories persist until manually deleted) | Most agent harnesses, ChatGPT |
| TTL-based expiration | AWS (store-level), OMP Packer draft |
| Semantic expiry (content becomes stale at a date) | MemoryHub (relevant_until) |
| Decay policies (time-based, access-based, relevance-based) | AIDP draft, MemoryBank |
| Soft delete with retention | MemoryHub, IBM draft |
| Versioning with supersession | MemoryHub, IBM draft |
| Contradiction detection | MemoryHub |

**Implication:** Lifecycle management is where simple systems and sophisticated
systems diverge most. The standard should define lifecycle-related fields on
the memory object (timestamps, expiration, version, status) and lifecycle
operations (update, delete, archive) without mandating implementation of
advanced features like decay policies or contradiction detection.

### Portability

| Approach | Used by |
|----------|---------|
| Plain files (inherently portable) | All agent harnesses |
| COGX JSON archive | Cognee |
| PAM JSON/CBOR with Merkle-DAG | PAM |
| Export/import API with conflict resolution | OMP Packer draft, IBM draft |
| No portability | AWS, Google, Microsoft, Mem0, Zep, ChatGPT, Pi |

The majority of service-based memory systems have no portability mechanism.
This is the central problem OMP exists to solve.

## The minimum viable standard

Based on the convergence analysis, a minimum viable interoperability standard
needs to cover:

### 1. A memory object schema (required fields)

The fields that every memory must carry for interoperability:

| Field | Rationale |
|-------|-----------|
| Unique identifier | Universally present |
| Content (the memory text) | Universally present |
| Scope (personal, project, or extended) | Universally present |
| Scope qualifier (which project, which user) | Needed but absent from most proposals |
| Owner identifier | Universally present |
| Timestamps (created, modified) | Universally present |
| Provenance origin (user, agent, system, import) | Needed for trust |

### 2. A memory object schema (recommended fields)

Fields that implementations should support for richer interoperability:

| Field | Rationale |
|-------|-----------|
| Memory type (from a recommended vocabulary) | Convergent across enterprise systems |
| Importance/salience/weight | Present in several systems |
| Tags/labels/domains | Present in most systems |
| Version number | Present in versioning systems |
| Expiration or TTL | Present in lifecycle-aware systems |
| Extensible metadata | Universally present as an escape hatch |

### 3. An exchange format

A portable serialization for moving memories between systems. Based on the
convergence patterns, this should have two forms:

- **Markdown with YAML frontmatter** for file-based systems (agent harnesses).
  The required and recommended fields from the object schema appear as
  frontmatter; the content is the markdown body.
- **JSON** for API-based systems (enterprise services). The same schema
  expressed as a JSON object.

Both serializations must be lossless representations of the same logical
object, round-trippable between formats.

A bundle format (a collection of memories for export/import) with a manifest
(source system, export time, schema version) and conflict-resolution semantics
(skip, overwrite, merge) enables bulk portability.

### 4. An operations interface

The minimum operations for interoperability:

| Operation | What it does |
|-----------|-------------|
| Write | Create a new memory |
| Read | Retrieve a memory by ID |
| Search | Find memories by query, scope, and filters |
| Update | Modify an existing memory (with versioning) |
| Delete | Remove a memory (hard delete for user rights compliance) |
| Export | Produce a portable bundle of memories |
| Import | Ingest a portable bundle with conflict resolution |

These operations should have concrete bindings for at least two profiles:

- **File profile**: directory layout, file naming, index file conventions
- **Tool profile**: MCP tool names, input schemas, output schemas

A REST/HTTP profile is valuable for service-to-service integration but may
be a later addition.

### 5. A consent signal

A queryable, settable `memory_enabled` state per scope. When memory is
disabled at a scope, conforming implementations must not write new memories
at that scope.

### 6. Provenance requirements

Every memory must carry minimum provenance: who created it and how (origin
type). Full provenance (lineage chain, confidence, model identity,
attestation) is recommended but not required at the minimum viable level.

When memories cross trust boundaries, provenance verification and trust
evaluation are handled by the trust layer (PTC or equivalent), not by the
memory protocol itself.

## The adoption journey

Getting harness makers to converge on a standard is a social and technical
challenge. The technical path:

1. **Define the file format first.** Coding agents are the easiest adoption
   target because they already use markdown files with similar conventions.
   A standard file format with frontmatter that any harness can read alongside
   its native format allows incremental adoption with no breaking changes.

2. **Bridge, don't replace.** Harnesses should read both their native format
   (CLAUDE.md, AGENTS.md, GEMINI.md) and the standard format. A user who
   maintains an OMP-compliant memory directory gets portability across any
   conforming harness; a user who prefers the native format loses nothing.

3. **Define MCP tool schemas second.** For service-based systems, standardized
   MCP tool names and schemas for memory operations allow any MCP-connected
   agent to interact with any conforming memory service. This is the API
   equivalent of the file format: a common interface that bridges
   implementations.

4. **Portability is the carrot.** The value proposition for harness authors
   is not "replace your memory system" but "let your users bring their
   memories from other tools." Users who switch between Claude Code, Cursor,
   and Codex are the ones who feel the pain of fragmented memory. A standard
   that lets them carry their context across tools makes each individual tool
   more valuable.

5. **Start with agent harnesses, then expand.** The agent-harness vertical has
   acute developer pain, open-source harnesses with accessible maintainers,
   and a culture of interoperability (git, LSP, Language Servers). Enterprise
   memory services and consumer AI platforms are harder targets with
   commercial incentives toward lock-in. Establishing the standard in the
   agent-harness space first creates the gravity that pulls enterprise and
   consumer systems toward conformance.

The social path: the OMP working group includes contributors from many of
the systems surveyed here. The first convening (September 2026) brings
together spec authors, harness maintainers, and memory service builders.
Convergence requires demonstrating that the standard serves everyone's
interests: portability for users, reduced integration burden for developers,
and a larger addressable market for memory services.
