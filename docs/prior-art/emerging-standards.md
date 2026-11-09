# Emerging Standards and Formats

Specifications, exchange formats, and protocol proposals that address memory
portability and interoperability. These range from formal specifications to
practical format definitions to transcript normalization tools.

## Memory standards and protocols

### Portable Agent Memory (PAM)

**Author:** Santhosh Kumar Ravindran (Microsoft-affiliated). Published May 2026
on arXiv ([2605.11032](https://arxiv.org/abs/2605.11032)). Apache-2.0.
Repository: [santhoshravindran7/portable-agent-memory](https://github.com/santhoshravindran7/portable-agent-memory).

**What it defines:** A file-centric protocol and Python SDK for exporting,
transporting, verifying, and re-importing AI agent memory across models,
frameworks, and runtimes.

**Data model:** Five-component structured memory, drawing from cognitive science:

| Component | Contents | Example |
|-----------|----------|---------|
| Episodic | Timestamped observations with salience scores | "User prefers dark mode (salience: 0.8)" |
| Semantic | Subject-predicate-object triples with confidence | "(React, preferred_over, Angular, 0.9)" |
| Procedural | Named procedures with parameters and preconditions | "deploy_to_staging: requires clean tests" |
| Working | Goals, subgoals, scratchpad, pending actions | Current task state |
| Identity | Preferences, persona, language, policies | User profile and custom instructions |

All entries share a common base: BLAKE3 content-addressable ID, parent
references forming a Merkle-DAG, creation timestamp, tags, and schema version.

**Exchange format:** `.pam` files (pretty-printed JSON). CBOR binary alternative
for bandwidth-sensitive transport. MIME types: `application/pam+json`,
`application/pam+cbor`.

**Integrity model:** Content-addressable identity via BLAKE3 hashing. Root hash
computed over sorted entry IDs. Ed25519 signing for tamper evidence.
Capability-based access tokens with scoped, time-bounded permissions.

**Re-hydration pipeline:** A six-step process (verify, filter, rank, compress,
frame, render) converts a PAM artifact into a context string for injection into
any LLM. Includes injection-resistant framing with Unicode normalization, role
elevation pattern escaping, and per-session random nonces.

**Portability results:** Cross-model transfer demonstrated between GPT-4,
Claude, Gemini, and Llama with Transfer Continuity Scores of 0.83-0.92, a 2.4x
improvement over no-memory baselines.

**Integrations:** Claude Code (MCP server), GitHub Copilot (marketplace
extension), OpenAI Codex (AGENTS.md instruction), VS Code extension, browser
extension.

**Current state:** v0.1.0 Alpha. 19 GitHub stars. The specification is thorough
and the security design (injection framing, atomic writes, symlink protection)
is genuine engineering. The gap between the spec and the SDK implementation is
significant: the spec describes summarization-aware compression and
embedding-based relevance scoring that the SDK does not yet implement.

### COGX (Cognee)

**Author:** Cognee / Topoteretes. Apache-2.0.

**What it defines:** A JSON-based archive format for exporting and importing
memory graphs. Claims import capabilities from Mem0, Letta, Zep, and Graphiti.

**Data model:** Strongly-typed `DataPoint` objects (Pydantic models) serving as
both node and edge schemas. Each gets a UUID, version, and timestamp. Nested
DataPoints are recursively unpacked and deduplicated.

**Current state:** No formal COGX schema specification is publicly documented.
The format appears to be a practical export mechanism rather than a rigorously
specified interchange standard. Cognee's four memory verbs (`remember`,
`recall`, `forget`, `improve`) reflect a thoughtful design, and the feedback
loop (agent-rated responses update edge weights) is distinctive. Related:
[node sets](https://docs.cognee.ai/core-concepts/further-concepts/node-sets),
named subgraphs that bound what a given query can reach.

**Adoption:** Cognee has $7.5M seed funding, 5M+ SDK runs/month, and 28K
GitHub stars. [PR #1](https://github.com/The-AI-Disclosures-Project/Open-Memory-Protocol/pull/1)
on the OMP repository (by Cognee founder Vasilije Stepanovic) proposes a
semantic core for portable agent memory based on COGX concepts.

### Context Nest

**Author:** PromptOwl. Specification
[Apache-2.0](https://github.com/PromptOwl/context-nest-spec); reference
implementation (engine, MCP server) AGPL-3.0. Paper:
[arXiv:2607.02116](https://arxiv.org/abs/2607.02116), with IBM Research and
Emory University.

**What it defines:** A governance layer beneath retrieval rather than a
retrieval system. The stated scope is determining which artifacts are approved,
current, attributable, and integrity-verified *before* a retrieval system
operates over them. Nine areas: document format, selector grammar, context
packs, addressable context via URI, indexing, version history, checkpoints,
context injection, and validation, with defined extension points.

**Data model:** Typed Markdown with YAML frontmatter (`title`, `type`, `tags`,
`status`, `version`, `author`, `checksum`). Node types include document,
snippet, glossary, persona, prompt, source, tool, and skill. Edges come from
wikilink syntax in the prose and from a `contextnest://path[#anchor][@checkpoint]`
URI scheme, both indexed into a generated `context.yaml` that distinguishes
`reference` edges from `depends_on` edges.

**Lifecycle:** Five states (`draft`, `pending_review`, `approved`, `published`,
`rejected`). Only `published` is visible to an agent; drafts are invisible by
default. Promotion is a separate, attributed act rather than a side effect of
writing.

**Integrity model:** SHA-256 hash chains across both document versions and
graph-level checkpoints. Versioning uses keyframes plus diffs, so any prior
state can be rebuilt rather than inferred. Selectors are deterministic set
algebra, which is what makes a past retrieval replayable.

**Reported results:** Two controlled experiments in the paper. In a
stale-version scenario, governed selection outperformed BM25 sparse retrieval on
answer quality (97% versus 93-90%) at roughly one third the input-token cost. In
a determinism test over a 1,060-document corpus, deterministic selectors and
BM25 returned stable document sets across repeated identical queries (Jaccard
1.0) while a dense + HNSW baseline was non-deterministic on 80% of queries (mean
Jaccard 0.611, worst case 0.210).

**Current state:** The determinism result is close to definitional for a
set-algebraic selector and is better read as a cost of dense retrieval than a
feature of this one. Semantic retrieval is specified but gated off, so the
shipped path is deterministic-only and paraphrase queries that a tag would miss
are currently unserved. Adoption is small relative to others in this survey. The
specification exists in two public locations whose license headers have drifted;
the Apache-2.0 repository above is canonical.

### EngramSpec

**Author:** Ashish Verma (8mem), maintained by Engram Steering Group. RFC Draft
v0.1, June 2026, CC-BY 4.0.
[engramspec.org](https://engramspec.org).
Repository: [engramspec/spec](https://github.com/engramspec/spec).

**What it defines:** An HTTP-based protocol for portable, governed AI memory.
One required endpoint (`GET /v1/context`) returns an Ed25519-signed JSON
envelope with four objects: IDENTITY (stable facts), BELIEFS (dynamic
preferences with confidence scores), CORRECTIONS (explicit user overrides with
audit trail), and EVOLUTION (append-only history of belief changes). Six
optional endpoints cover corrections submission, discovery, incremental sync,
and key distribution. Three conformance tiers: Reader, Writer, Full.

**Current state:** Three documented implementations (8mem reference
implementation, OpenClaw, Hermes), all associated with the spec's creator.
Academic paper on SSRN (ID 6878038). Official SDKs listed as "coming soon."
Repository has 2 stars.

**Namespace collision:** The term "engram" (from neuroscience: Semon's 1904
hypothesis about memory traces) has been independently adopted by at least
eight unrelated AI memory projects on PyPI and GitHub (engram-core,
piia-engram, engramma-memory, Gentleman-Programming/engram, and others), none
implementing EngramSpec. The reference implementation ecosystem (PLUR,
plur.ai) uses a different data model (Engram and Episode objects with
activation-weighted decay) than the published spec, adding to the confusion.

### SAIHM (Secure Agent Interoperable Hybrid Memory)

**Author:** Russell Jackson. IETF Internet-Draft (draft-saihm-memory-protocol-01).

**What it defines:** Encrypted memory cells with post-quantum identity binding,
per-cell encryption envelopes, audit anchors on public chains, and
cryptographic erasure for GDPR Article 17 compliance.

**Current state:** The ISE concluded consideration and released the draft from
the queue without progression. The W3C AI Agent Memory Interoperability
Community Group (also founded by Russell Jackson, June 2026) normatively
references this draft. The CG charter covers memory cell shape, post-quantum
identity binding, encryption envelopes, sharing contracts with revocation, and
cryptographic erasure. Very early: five public mailing list messages as of
July 2026.

### Memoryfield

**Published:** September 2026.

**What it defines:** A simple portable memory file format. Zip archive
containing Markdown files plus a SQLite3 embedding database. Not a protocol,
just a file format.

**Design choice:** Optimizes for simplicity and human readability. The Markdown
files are inspectable without any tooling. The SQLite database provides
retrieval without requiring a running service.

### Mesh Memory Protocol (MMP)

**Author:** Academic specification (arXiv, April 2026). v0.2.3.

**What it defines:** An eight-layer architecture for multi-agent memory systems.
Four layers constitute "Mesh Cognition" (Coupling, Synthetic Memory, xMesh,
Application).

**Key concept:** Write-time filtering as a "cognitive invariant": role-indexed
per-field admission ensures stored graphs are meaningful to each receiving
agent. This addresses the problem of shared memory becoming noisy when
multiple agents with different roles write to the same store.

### MEMORY.md (Cromus.ai)

**What it defines:** An open spec (v0.2.0) for agent-written persistent memory
files. Defines a convention for how agents create and maintain a markdown file
that persists across sessions.

**Relationship to OMP:** The file-based memory pattern (a markdown file that
the agent reads at session start and updates during the session) is the
simplest form of agent memory. Several coding agents (Claude Code, Goose)
use this pattern independently. A standard that formalizes the markdown format
with structured frontmatter could unify these implementations.

## Trajectory and transcript formats

These are not memory standards per se, but they capture the raw material from
which memories are extracted. They sit upstream of memory formation.

### ATIF (Agent Trajectory Interchange Format)

**Author:** Harbor Framework.

**What it defines:** A JSON-based specification for logging the complete
interaction history of autonomous LLM agents. Captures user messages, agent
responses, tool executions, environment feedback, LLM metrics (token usage,
costs, logprobs), and multi-agent delegation.

**Data model:** A `Trajectory` object containing an `Agent` descriptor and an
ordered array of `Step` objects. Each step has a source (user, agent, system,
environment), a message, optional tool calls with observations, and optional
metrics.

**Supported agents:** Converters exist for OpenHands, Claude Code, Codex,
Gemini CLI, and others. ATIF serves as a common format for agent benchmarking
and evaluation.

**Design choice:** ATIF captures what happened, not what was learned. It is
a transcript format, not a memory format. The gap between "what happened in
a session" and "what should be remembered from a session" is where memory
extraction (dreaming, consolidation) operates.

### Letta Trajectory Library

**Author:** Letta.

**What it defines:** A normalization library (TypeScript primary, Python
wrapper) that converts native agent transcript formats from 15 coding-agent
runtimes into a validated data model. Two output schemas: Trajectory v1
(portable, normalized) and Canonical v1 (optimized for Letta's Cloud
ingestion pipeline).

**Supported sources:** Claude Code, Codex, Goose (OMP/Pi), Cursor,
OpenHands, Gemini CLI, Hermes, and others.

**Provenance model:** Four identity derivation levels: `native` (source
provides a UUID), `location` (byte offset), `content` (SHA-256 hash), and
`synthetic` (generated for metadata records). Content versioning via
content-hash comparison enables deduplication and conflict detection.

**Design choice:** Explicitly not a memory format. The library produces
normalized transcripts that feed into Letta's "Dream pipeline" for memory
formation. The separation between transcript normalization and memory
extraction is architecturally clean and reflects the distinction between
episodic recording and semantic extraction.

### Agent Memory System Card

**Author:** Mila (Quebec AI Institute) and Mozilla.

**What it defines:** A structured documentation format for agent memory
systems, analogous to model cards (Mitchell et al., 2019) and dataset cards
(Gebru et al., 2021). A template for describing what a memory system does,
how it works, and what its properties are.

**Purpose:** Transparency and comparability, not interchange. A system card
helps users understand what a memory system stores, how it retrieves, what
controls it offers, and what risks it poses. This serves the governance and
disclosure layer rather than the technical interoperability layer.

**Canonical repository:** `mila-iqia/agent-memory-system-card`.

## me.md

**Author:** David Hamilton (Block/Goose).

**What it defines:** A user-owned, plain-file personal-sovereignty memory
format. The user maintains a markdown file (`me.md`) that describes their
preferences, context, and instructions. Any agent that supports the format
reads the file and incorporates it into its context.

**Design philosophy:** User sovereignty over agent memory. The user is the
author, not the agent. The file lives on the user's machine, not in a service.
The format is human-readable and human-editable.

**Relationship to OMP:** me.md represents one end of the memory authorship
spectrum (user-authored) while agent-extracted memory (dreaming, consolidation)
represents the other (system-authored). A memory standard likely needs to
accommodate both patterns and track the distinction in provenance metadata.

## Design decisions surfaced by this survey

**Specification maturity varies widely.** PAM has a detailed specification
(with gaps between spec and implementation). COGX has working code but no
formal schema documentation. SAIHM has an IETF draft that did not progress.
ATIF has Pydantic models and a validator. The field would benefit from
specifications that are both formally documented and backed by working code.

**The transcript-to-memory boundary is real.** ATIF and Letta Trajectory
capture what happened. Memory systems store what was learned. The extraction
step between them (variously called dreaming, consolidation, or reflection)
is where intelligence lives, and it is implementation-specific. A memory
standard should define the output format (the memory object) without
prescribing the extraction process.

**Content-addressable identity is convergent.** PAM uses BLAKE3 hashing.
SAIHM uses cryptographic envelopes. Letta Trajectory uses SHA-256 for
content versioning. PTC uses SHA-256 for payload digests. The concept of
deriving a memory's identity from its content (rather than assigning an
arbitrary ID) appears independently in multiple systems. The specific hash
algorithm varies; the pattern is consistent.

**Signing and integrity verification appear in multiple proposals.** PAM,
SAIHM, and PTC all include signing mechanisms for tamper evidence. The
approaches differ (Ed25519 in PAM and PTC, post-quantum in SAIHM), but the
requirement is convergent: memories crossing trust boundaries need
verifiable integrity.
