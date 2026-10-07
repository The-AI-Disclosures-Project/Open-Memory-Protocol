# Memory Access Protocol (MAP)

A sketch of how agent harnesses discover, query, and write to memory systems.

## The problem

An agent harness author who wants to integrate with a memory system has no
standard to implement against. Claude Code reads markdown files from disk.
Codex reads a single AGENTS.md. Letta exposes MCP tools. Mem0 has a Python
SDK. AWS AgentCore has a REST API. Each integration is bespoke.

A harness author who wants to support portable memory needs to know: where do
I look for the memory system, what operations does it support, and what are
the function signatures?

## The ergonomics imperative

The memory standard has to work the way harness authors already work. If
adopting the standard requires more effort than building a bespoke integration,
nobody will adopt it. Three principles:

**Meet the harness author where they are.** A coding agent that works with
markdown files should not need an HTTP client. An enterprise platform team
building MCP integrations should not need to parse YAML frontmatter. The
protocol defines multiple access patterns (profiles), and each one should feel
like a natural extension of what the harness already does, not a new system to
learn.

**Be invisible to the user.** The user does not care about MOF or MAP. They
care that their memories follow them when they switch from Claude Code to
Cursor, or when they move from a local coding agent to a cloud-hosted
platform. The protocol succeeds when users never think about it.

**Design for the agent, not the API consumer.** Tool names, schemas, and file
conventions have to be designed for how agents actually reason. An LLM calling
`memory_search` with `{query: "what did we decide about auth"}` should just
work. The tool schemas need to match how agents form tool calls, not how API
designers structure REST resources.

Hermes and Pi already read AGENTS.md and CLAUDE.md. OpenClaw already imports
memory from Codex and Claude Code. Cross-harness compatibility is emerging
organically. A standard that formalizes and extends what is already happening
has a shorter path to adoption than one that asks everyone to start over.

## The sketch

Define the operations interface for memory systems, with concrete bindings
for multiple access patterns. A conforming implementation declares which
binding(s) it supports.

### Operations

The minimum operation set, based on what every surveyed system supports:

| Operation | What it does |
|-----------|-------------|
| write | Create a new memory |
| read | Retrieve a memory by ID |
| search | Find memories by query, scope, and filters |
| update | Modify an existing memory |
| delete | Remove a memory |
| export | Produce a portable bundle of memories |
| import | Ingest a portable bundle with conflict resolution |

### Discovery

Before a harness can use a memory system, it needs to find it and learn what
it supports. A discovery mechanism should answer:

- Is a memory system available?
- Which profile(s) does it support (file, tool, API)?
- Which optional capabilities does it support (versioning, relationships,
  search, consent signals)?
- How does the harness authenticate?

### Conformance profiles

Three profiles cover the range of implementations in the ecosystem. Each one
maps to the way a class of harnesses already works.

**File profile.** The memory system is a directory on disk. The harness reads
and writes memory files in a defined structure. This is the natural fit for
Claude Code, Codex, Goose, Cursor, Pi, and any harness that works with a
local repo.

A harness that already reads CLAUDE.md or AGENTS.md at startup can read an
OMP memory directory the same way. Adding support should be an afternoon of
work, not a sprint.

The spec would define:
- The directory layout (where to look)
- The index file convention (how to discover what memories exist)
- The file format (MOF markdown serialization)
- How to express consent signals (memory enabled/disabled per scope)

**Tool profile.** The memory system is accessed via callable tools (MCP tools,
function calls, or equivalent). This is the natural fit for agents that use
tool-calling to interact with services: Letta, OpenClaw, Hermes, and any
agent connected to memory via MCP.

The spec would define:
- Tool names: `memory_write`, `memory_read`, `memory_search`,
  `memory_update`, `memory_delete`, `memory_export`, `memory_import`
- Input schemas for each tool
- Output schemas for each tool
- A capability discovery tool: `memory_info`

Standardized tool names and schemas mean any MCP-connected agent can interact
with any conforming memory service without custom integration. The tool
schemas should be designed for how agents reason about tool calls: clear
parameter names, minimal required arguments, sensible defaults.

**API profile.** The memory system is accessed via HTTP endpoints. This covers
enterprise memory services and multi-tenant deployments.

The spec would define:
- REST endpoints for each operation
- Request and response schemas (MOF JSON serialization)
- Authentication requirements
- Pagination and filtering conventions

### Consent signals

A queryable, settable `memory_enabled` state per scope. When memory is
disabled at a scope, conforming implementations must not write new memories
at that scope. The signal is part of the protocol (it needs to be
interoperable across harnesses). The UI for the toggle is a product decision.

### Contradiction signaling

An operation for agents to report that a stored memory contradicts observed
behavior. Not a correction (the agent does not overwrite the memory), but a
signal that the memory may be stale. The memory system decides how to handle
the signal (flag for review, track contradiction count, trigger
re-evaluation).

## What this does not define

- The retrieval algorithm (how search results are ranked)
- The extraction pipeline (how memories are created from conversations)
- The storage backend (how memories are persisted)
- Trust verification ([PTC](https://github.com/wjatx/ptc-gal-standards/blob/main/PTC-SPEC.md))

## Open questions

- Should the file profile define a new directory convention (`.omp/`) or
  adopt an existing one (`MEMORY.md` at project root)?
- Should the tool profile mandate MCP specifically, or be transport-agnostic
  (defining tool semantics that could be bound to MCP, function calling, or
  future protocols)?
- Is the API profile needed in v1, or can it wait? The file and tool profiles
  cover the immediate use cases. REST endpoints may be a later addition.
- How should capability discovery work for the file profile? A manifest file
  in the directory? A well-known filename?
