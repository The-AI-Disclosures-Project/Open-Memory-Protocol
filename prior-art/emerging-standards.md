# Emerging Standards and Formats

Specifications, exchange formats, and protocol proposals that address memory
portability and interoperability. These range from formal specifications to
practical format definitions to transcript normalization tools.

## Memory standards and protocols

### Portable Agent Memory (PAM)

**Author:** Santhosh Kumar Ravindran (Microsoft-affiliated). Published May 2026
on arXiv. Apache-2.0.

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
loop (agent-rated responses update edge weights) is distinctive.

**Adoption:** Cognee has $7.5M seed funding, 5M+ SDK runs/month, and 28K
GitHub stars. [PR #1](https://github.com/The-AI-Disclosures-Project/Open-Memory-Protocol/pull/1)
on the OMP repository (by Cognee founder Vasilije Stepanovic) proposes a
semantic core for portable agent memory based on COGX concepts.

### Engram

**Author:** Multiple independent projects use this name, creating namespace
confusion.

**What it defines:** One variant (engramspec.org, v0.1, CC-BY 4.0, June 2026)
describes itself as "the OAuth for AI Memory." Five-object JSON envelope
(IDENTITY, BELIEFS, CONSTRAINTS, CORRECTIONS, EVOLUTION). Seven-endpoint API
with Ed25519 signing.

**Current state:** Very early. The namespace confusion across multiple
unrelated "Engram" projects makes assessment difficult.

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
