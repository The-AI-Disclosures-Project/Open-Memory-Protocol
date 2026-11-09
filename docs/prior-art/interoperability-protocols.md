# Interoperability Protocols and the Memory Gap

Agent interoperability is addressed by several protocols and standards bodies.
This document maps the landscape and identifies where memory fits -- and where
it is absent.

## The emerging protocol stack

Three layers of agent interoperability have active protocol efforts:

| Layer | Protocol | Governs | Memory role |
|-------|----------|---------|-------------|
| Agent-to-tool | MCP (Anthropic, now AAIF) | How agents discover and call tools | Memory can be exposed as MCP tools, but MCP defines no memory semantics |
| Agent-to-agent | A2A (Google, Linux Foundation) | How agents delegate tasks to each other | Enforces opacity: agents never see each other's internal state or memory |
| Trust and provenance | PTC/GAL (LF Edge, AAIF) | How trust travels across agent and tool boundaries | Governs whether a memory crossing a boundary should be trusted, but defines no memory object model |

Memory sits in a gap between these layers. MCP provides the plumbing through
which memory operations can flow; A2A provides the coordination layer for
multi-agent systems; PTC provides the trust verification for data crossing
boundaries. None of them defines what a memory *is*, how memories are stored,
or how they become portable.

## Protocol details

### MCP (Model Context Protocol)

**Governed by:** Agentic AI Foundation (AAIF), Linux Foundation. Originally
developed by Anthropic, donated to AAIF.

**What it handles:** A standard for how AI agents discover, authenticate to,
and call external tools and data sources. The 2026-07-28 spec pushed further
toward statelessness for cloud-native scalability.

**Relationship to memory:** MCP is deliberately stateless at the protocol
level. Memory is an implementation concern. The official Memory MCP Server is
a reference implementation (local knowledge graph using a JSON file), and
community extensions add various backends (Neo4j, pgvector, hybrid stores).
Several memory systems (MemoryHub, Mem0, Letta) expose their memory operations
as MCP tools, making MCP the de facto transport for memory operations in
tool-calling agents.

**Implication for OMP:** MCP is a natural transport binding for memory
operations. An OMP "tool profile" would define standardized MCP tool names
and schemas for memory operations (write, read, search, delete), so that any
MCP-connected agent can interact with any OMP-conformant memory system.

### A2A (Agent-to-Agent Protocol)

**Governed by:** Linux Foundation Technical Steering Committee (AWS, Cisco,
Google, IBM, Microsoft, Salesforce, SAP, ServiceNow). v1.0 specification.

**What it handles:** How agents discover each other, negotiate capabilities,
and delegate tasks. Production deployments.

**Relationship to memory:** A2A enforces a strict opacity contract: agents
never see each other's internal state, memory, tools, or prompts. State is
grouped by `contextId` with three patterns (shared context store, per-agent
state, embedded context), but the protocol does not address how accumulated
knowledge transfers between agents. Teams needing shared state are expected
to "layer MCP-mounted memory tools on top of A2A."

**Implication for OMP:** A2A intentionally stays out of the memory space.
When agents need to share knowledge (not just delegate tasks), they need a
memory layer. OMP fills this gap without competing with A2A's coordination
model.

### PTC (Provenance and Trust Context)

**Governed by:** LF Edge + Agentic AI Foundation (AAIF). v0.2.3-draft.

**What it handles:** A connectivity-orthogonal trust layer for agentic systems.
Defines a signed trust-context object with an append-only provenance chain and
taint labels on a Biba integrity lattice. The object travels with data across
every agent and tool boundary and is consumed by a deterministic, model-free
gate at each boundary.

PTC rides existing transports (MCP `_meta` field, A2A extension, native
channel binding) rather than defining its own wire protocol.

**Key properties:**
- Provenance chains are append-only and non-strippable
- Taint propagation follows a Biba integrity lattice (low-integrity data
  cannot influence high-integrity actions without explicit, audited endorsement)
- Gates are deterministic and model-free (no LLM in the security decision path)
- Signing uses Ed25519 over DSSE-enveloped in-toto-style attestations
- Tool discovery is treated as untrusted input with two-key admission ceremonies

**Relationship to memory:** PTC governs whether a memory crossing a trust
boundary should be trusted, how provenance is verified, and whether the
receiving system should act on it. It does not define what a memory contains
or how memories are stored. When Agent A exports memories and Agent B imports
them, PTC handles the trust verification of the envelope; OMP handles the
content schema inside the envelope.

**Companion spec -- GAL (Grant and Autonomy Lifecycle):** Defines the autonomy
rungs that constrain what an agent can do at a given trust maturity. A
capability's autonomy rung is capped by what the mesh can prove about its
inputs. PTC supplies the proof, GAL moves the state.

**Implication for OMP:** PTC eliminates the need for OMP to define its own
provenance verification, signing, or trust model. OMP defines provenance
*metadata* on the memory object (who created it, from what source, with what
confidence). PTC handles provenance *verification* when memories cross
boundaries (is this envelope authentic, is the sender trusted, is the content
tainted).

### ANP (Agent Network Protocol)

**Status:** v1.1 spec, IETF Internet-Draft. Leads the W3C AI Agent Protocol
Community Group (~180 participants).

**What it handles:** Three-layer architecture covering internet infrastructure,
DID-based identity, and application protocols. Supports meta-protocol
negotiation, allowing agents to dynamically agree on communication protocols.
HTTP-native, uses JSON-LD and schema.org for semantic capability description.

**Relationship to memory:** Memory is an application-layer concern, not
specified by ANP.

**Origin:** Community-driven, with contributions from China Mobile, China
Telecom, and Huawei.

### AGNTCY

**Governed by:** Cisco, Linux Foundation. 49 repos, 65+ supporting
organizations including Dell, Google Cloud, Oracle, and Red Hat.

**What it handles:** Agent discovery, identity, messaging, and observability.
Their invocation protocol (ACP, originally from IBM) was archived in August
2025 when the team merged into A2A.

**Components:** Open Agent Schema Framework (OASF) for capability description,
W3C DID-based agent identity, quantum-safe pub/sub messaging (SLIM),
observability tooling.

**Relationship to memory:** Infrastructure layer with no memory-specific
components.

### AG-UI (Agent-User Interaction Protocol)

**Governed by:** CopilotKit. Adopted by Amazon Bedrock AgentCore, Oracle.

**What it handles:** Bidirectional event-driven protocol for agent-to-frontend
communication. Streams messages, tool calls, state deltas, and lifecycle events
over HTTP/SSE. Described as the "third pillar" alongside MCP (agent-to-tool)
and A2A (agent-to-agent).

**Relationship to memory:** AG-UI could be relevant for surfacing memory state
to users (displaying what memories exist, allowing edits), but the protocol
does not define memory semantics.

### Data Transfer Initiative (DTI)

Non-profit continuing the Data Transfer Project, funded by Apple, Google, Meta
and others. Focus is consumer-initiated portability between services rather than
agent memory specifically, but the governance model (a neutral body maintaining
adapters between proprietary formats) is the closest existing analogue to what
portable memory would need. [dtinit.org](https://dtinit.org). Noted in the first
OMP meeting as already in contact with the initiative.

### Agent Plugins

[agent-plugins.org/specification](https://agent-plugins.org/specification).
Plugin specification for agent capability distribution. Adjacent to memory rather
than about it, included because plugin and memory distribution face the same
scope and permission questions.

## Standards body activity

### AAIF (Agentic AI Foundation, Linux Foundation)

~290 member organizations. Governs MCP, A2A, Goose, AGENTS.md. Seven working
groups plus one cross-cutting workstream cover Identity/Trust,
Accuracy/Reliability, Workflows/Process, Agentic Commerce, Security/Privacy,
Observability/Traceability, and Governance/Risk/Regulatory.

There is no memory-specific working group. Memory falls into the gaps between
several working groups.

### CNCF (Cloud Native Computing Foundation)

Open initiative on "Cloud-Native Foundations for Distributed Agentic Systems"
(filed June 2025). Their gap analysis explicitly names **"AgentMemory API"**
as a needed project. A March 2026 blog discusses protecting "intermediate
memory states" using trusted execution environments and GPU-based confidential
computing.

### W3C

Two relevant community groups:

- **AI Agent Protocol Community Group** (founded May 2025, ~180 participants):
  producing a white paper and technical framework. Specs expected 2026-2027.
- **AI Agent Memory Interoperability Community Group** (founded June 2026):
  Charter v1.0 adopted June 19, 2026. Scope covers memory cell shape,
  post-quantum identity binding, encryption envelopes, sharing contracts with
  revocation, and cryptographic erasure. Very early stage.

### IETF

- **agentproto BoF** (IETF 126, Vienna, July 2026): exploring chartering a
  working group for agent protocols. 124 yes / 72 no on whether the problem
  is solvable. Any RFC would be 2027-2028 at earliest.
- **draft-rosenberg-ai-protocols**: surveys MCP, A2A, AGNTCY and describes
  how they fit a framework.
- **draft-daniel-ai-agent-internet-architecture**: architectural requirements
  covering naming, discovery, auth, delegation, async messaging, provenance,
  and auditability.
- **SAIHM (draft-saihm-memory-protocol-01)**: the only IETF draft specifically
  about agent memory. Defines encrypted memory cells with post-quantum identity
  binding, per-cell encryption, audit anchors, and cryptographic erasure. The
  ISE concluded consideration and released it from the queue without
  progression.

### NIST

AI Agent Standards Initiative launched February 2026. Three pillars:
industry-led standards, open-source protocol work (co-invested with NSF), and
fundamental research in agent identity/security. $55M in AI standards funding.
NCCoE identified six essential identity standards (OAuth 2.0/2.1, OIDC,
SPIFFE/SPIRE, SCIM, NGAC, MCP). An AI Agent Interoperability Profile is
planned for Q4 2026.

### OASIS/CoSAI (Coalition for Secure AI)

Co-chaired by Anthropic and IBM. Released "Agentic Identity and Access
Management" paper (April 2026). Addresses the trust and identity layer that
memory sharing requires, but does not address memory directly.

## The gap

The protocol stack has clear owners for tool access (MCP), agent coordination
(A2A), trust and provenance (PTC/GAL), and agent-to-frontend communication
(AG-UI). Memory is the unowned layer. Multiple bodies have identified this
gap (CNCF's gap analysis, the W3C Memory Interop CG's charter, A2A's own
documentation noting that shared state requires layering memory on top of
the protocol).

OMP occupies this gap. Its relationship to the rest of the stack is
complementary: it defines what a memory is and how agents interact with
memory systems, while relying on MCP for transport, A2A for coordination,
and PTC for trust verification.
