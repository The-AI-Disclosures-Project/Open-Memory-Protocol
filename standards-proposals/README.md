# Standards Sketch

Early-stage sketches for the standards OMP should define. These are starting
points for discussion, not finished specifications.

## The landscape today

The agent ecosystem has clear protocol owners for tool access (MCP), agent
coordination (A2A), and trust/provenance
([PTC/GAL](https://github.com/wjatx/ptc-gal-standards/blob/main/PTC-SPEC.md)).
Memory is the unowned layer. CNCF's gap analysis names "AgentMemory API" as a
missing project. The W3C AI Agent Memory Interoperability CG is chartered but
very early. Multiple independent efforts (PAM, COGX, Engram, SAIHM) have
sketched partial solutions, but none has achieved cross-vendor adoption.

See [prior-art/emerging-standards.md](../prior-art/emerging-standards.md) for
the full survey.

## What we sketch here

Three concerns need to be addressed. Two are protocols (how things talk to
each other). One is a governance standard (what obligations implementations
must meet).

| Concern | Type | Document |
|---------|------|----------|
| The atomic unit of memory | Protocol | [Memory Object Format](memory-object-format.md) |
| Runtime accessibility and interoperability | Protocol | [Memory Access Protocol](memory-access-protocol.md) |
| User constraints and rights | Standard | [Memory Rights Standard](memory-rights-standard.md) |
| Protecting the agent from bad memories | Discussion | [Memory Security Considerations](memory-security-considerations.md) |

## What we deliberately leave out

**Provenance and trust.** [PTC](https://github.com/wjatx/ptc-gal-standards/blob/main/PTC-SPEC.md)
(Provenance and Trust Context) already covers signed provenance chains, taint
propagation, and trust verification when data crosses agent and tool
boundaries. It rides orthogonally to transport (MCP, A2A, or native bindings)
and is consumed by deterministic, model-free gates at each boundary. OMP
defines a few provenance metadata fields on the memory object (who created it,
from what source). PTC handles verifying those claims when memories move
between systems. Provenance is covered; we are not sketching it here.

**Storage.** Implementations may use markdown files, PostgreSQL, Neo4j, vector
databases, SQLite, or anything else. The protocol defines the object model and
exchange format, not the storage backend.

**Retrieval algorithms.** How an implementation decides which memories to
surface (embedding similarity, BM25, graph traversal, recency decay) is an
implementation choice. The protocol defines the search interface (what you can
query on), not the search engine.

**Memory extraction pipelines.** How an implementation derives memories from
conversations (LLM extraction, dreaming, consolidation) is internal. The
protocol defines what the output looks like, not how it was produced.
