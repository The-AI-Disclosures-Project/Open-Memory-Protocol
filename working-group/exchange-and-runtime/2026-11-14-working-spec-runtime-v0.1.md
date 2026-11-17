# Open Memory Protocol: Runtime Specification

**Editors' draft v0.1, draft for review.** Runtime sub-thread. Not an adopted OMP standard. Companions: [editors' draft v0.6](../../SPEC.md) of the Exchange and Runtime spec (the memory object, its interchange and runtime forms, and exchange semantics); [agreed decisions](2026-11-09-working-spec-v0.6-decisions.md) and [open questions and record](2026-11-09-working-spec-v0.6-notes.md).

This document defines the **runtime plug-in points** that let an agent harness consume memory at runtime and where a memory system plugs in. It builds on the memory object defined in the Exchange and Runtime spec: every runtime object is a projection of that object (Section 3.4 of v0.6), and every runtime write produces a new memory object that conforms to the interchange schema of v0.6.

## Part 1. Design principles

### 1.1 Scope

The protocol standardizes four runtime plug-in points and nothing more:

| Plug-in point | Direction | What it standardizes |
|---|---|---|
| **remember** | agent → memory system | The shape of the write call and the resulting memory object |
| **recall** | memory system → agent | The shape of the read response (memory objects in the runtime representation) |
| **passive-create** | memory system observes session | The interceptor signature that observes turns and may create a memory |
| **passive-decorate** | memory system decorates turns | The interceptor signature that decorates a turn with relevant memories before the agent sees it |

The protocol does **not** standardize:
- The recall function signature, ranking or retrieval algorithms (v0.6, 3.6.2). Implementations need room for different flavors of recall.
- Change notification during a session. Left to implementations (v0.6, I-11).
- Federation merge and ranking logic (v0.6, 2.2). Federation stays a separate binding.
- Memory-maintenance agents (forget, consolidation, "dream" agents) and their algorithms. Their writes still carry provenance (v0.6, 3.1.2).
- Storage, indexing, lookup, embeddings and internal mutation (v0.6, E).

### 1.2 Binding neutrality

The protocol is binding-neutral (v0.6, I-10): it fixes the object that crosses a runtime surface, the runtime representation, and no transport. A memory system may expose its runtime surface through:
- **MCP tools** — `remember` and `recall` as explicit tool calls; `passive-create` and `passive-decorate` as MCP interceptors
- **Harness hooks** — a supervisor callback that the harness invokes around each turn
- **CLI / HTTP** — command-line or REST endpoints the harness calls explicitly

A store that offers memories at runtime does so through one or more of these surfaces and SHOULD declare which in its capability declaration. A memory served through two surfaces MUST be the same memory: the same `identifier`, the same body, the same `origin`. Which optional runtime fields each surface shows is the implementation's (v0.6, 3.4).

### 1.3 Runtime representation

The runtime representation is the projection defined in v0.6, Section 3.4. The table below is normative where it says `no` and guidance elsewhere (v0.6, U-12):

| Field | Runtime |
|---|---|
| `identifier`, `media_type`, `body` | yes (required) |
| `stub` | yes, when true |
| `title`, `tags`, `valid_from` | yes |
| `version`, `valid_until` | yes if set |
| `weight` | yes with semantic description in tool definition |
| `path` | MAY be shown, for progressive disclosure |
| `provenance` | a summary MAY be shown (for example the author) |
| `evidence`, `links` | MAY be shown |
| `checksum` | no |
| `scope` | no |
| `status` | no |
| `protocol_version` | no |
| `created_at`, `updated_at` | no (prefer `valid_from` for semantic timestamp) |
| tombstones, audit records | no |
| `auditable` | MAY be shown (derived from provenance and evidence per v0.6, I-13) |

A memory system MAY add extension fields to the runtime projection under a dot-prefixed prefix, as v0.6, I-21 allows for interchange fields.

### 1.4 Provenance on write

Every write — whether active (`remember`) or passive (`passive-create`) — SHOULD (MUST in audit profile) record who wrote the memory. The contributor list follows v0.6, Section 3.1.1:

| Key | Meaning |
|---|---|
| `id` | An identifier for the contributor (a person, an agent, a system) |
| `kind` | `human`, `agent` or `system` |
| `contribution` | What the contributor did: `authored`, `instructed`, `approved`, `edited`, `imported`, `verified`, `corrected`, `contradicted`, `forgot`, `observed` |
| `name` | A name for the contributor |
| `at` | When this contributor acted |
| `accountable` | `true` only on a `human` entry, marking who is accountable (v0.6, I-3b) |

A passive-create interceptor that observes a session and extracts a memory MUST, when recording provenance, attribute the write to the agent that runs the interceptor, with `contribution: authored` and `kind: agent`. If a human explicitly confirms or edits the extracted memory, that human's `contribution: instructed` / `edited` / `approved` entries are added.

## Part 2. Active Memory Creation — the `remember` tool

### 2.1 Purpose

The `remember` tool lets an agent explicitly create a new memory from a piece of knowledge it has encountered: a user instruction, an agent-authored summary, an observation, or a derived fact. The agent supplies the content and minimal metadata; the memory system constructs the full memory object, computes `checksum`, assigns `identifier` if absent, and returns the runtime identifier of the stored memory.

### 2.2 The write contract

The `remember` call accepts a request object and returns a response object. The request is a superset of the memory object's writable fields (the body and the fields an agent is permitted to set); the response is the runtime representation of the stored memory.

```
POST /remember
Content-Type: application/json

{
  "body": string,                           // required: the memory content
  "media_type": string,                     // optional: MIME type of the body, text/plain if unset
  "title": string,                          // optional: human-readable label
  "tags": [string],                         // optional: semantic tags, system may exclude
                                            //           for systems with well-defined tag sets
  "path": string,                           // optional: where this sits in the origin store
  "valid_from": string,                     // optional: when the claim becomes true
  "valid_until": string,                    // optional: when the claim stops being true
  "links": [{ "target", "rel", ... }],      // optional: typed edges to other memories
  "evidence": [{ "ref", "relation", ... }], // optional: sources this memory rests on
  "identifier": string                      // optional: used to indicate an update, treated as an
                                            //           error otherwise
  "created_at": string,                     // NOT accepted: set by system
  "version": integer | string,              // NOT accepted: versioning managed by system
  "provenance": [...],                      // NOT accepted: set by the system
  "scope": [string],                        // NOT accepted: scope is set by the system (v0.6, U-11)
  "checksum": string,                       // NOT accepted: computed by the system
}
```

The `remember` tool is binding-neutral. In MCP it is a tool; in a harness hook it is a function; in CLI it is a subcommand. The shape of the request and response is the same across bindings.

In it's simplest form, `remember` may also simply take a `string`. This is inferred as the `"body"` field with `"media_type": "text/plain"` and all other fields unset.

#### 2.2.1 `scope` is system-set, not client-supplied

Per v0.6, U-11, a memory system MAY assign `scope` itself from the caller's identity and the write destination, and MUST ignore or reject a `scope` value supplied through a runtime surface. A `remember` request that carries `scope` is rejected or the field is dropped; the system sets its own scope tags.

#### 2.2.2 Update vs create

- **Create.** When a memory is supplied without an `identifier`, the system creates a new memory with a fresh `identifier`.
- **Update (revision).** When a client-supplied `identifier` collides with an existing memory, the system follows its versioning semantics to update the current one. If implementing immutable revisions (per v0.6, 3.3.3) the new revision is given an incremented `version` value following the system's comparitor semantics, and a `supersedes` link to the previous revision. The client may not supply a client-chosen `version`; versioning is the responsibility of the system, not the client.
- **Idempotent create.** When `origin` + `identifier` already exists with identical content, the system returns the existing revision without creating a duplicate (v0.6, U-14).

#### 2.2.3 `identifier` handling

- If the client supplies `identifier`, the system MUST check that it is present within the export/store for the given `origin` (v0.6, I-8). If occupied, the system treats it as an update. If unoccupied, the system treats this as a malformed request and returns an error. Identifier allocation belongs to the system, so unoccupied client-provided identifiers are not accepted.
- If the client does not supply `identifier`, the system generates one (RECOMMENDED: a UUID). The returned memory always carries the `identifier` the system settled on.

#### 2.2.4 `checksum` computation

The system computes `checksum` over the metadata fields plus the body per v0.6, U-1. The checksum MUST be deterministically computed by concatenating the values of all metadata fields in sorted order, followed by the raw body bytes. Fields MUST be separated by `0x0A` as a delimiter. All fields with a valid value MUST be included in the checksum. A field is valid if it is set to a value, including empty strings and lists. A field MUST NOT be included if its key is not present in the serialized representation of the memory.

The result is encoded as `algorithm:hex` (e.g. `sha256:...`).

#### 2.2.5 `valid_from` / `valid_until`

`valid_from` records when the claim became true in the world; `valid_until` records when it stops being true. A memory with `valid_until` in the past is still stored (it may be resurrected by forgetting) but a recall implementation SHOULD exclude it from current reads unless explicitly requested (v0.6, 3.3.4).

### 2.3 Response

The response to `remember` should carry all system-derived information that the client (agent) may have a legitimate semantic use for. The `body` MUST NOT be returned as this is likely to duplicate text in an agent's context. Full `body` content may be retrieved later using `recall`.

```
200 OK
Content-Type: application/json

{
  "memory": {
    // runtime representation per Section 1.3
    "identifier": string,
    "media_type": string,
    "tags": [string],
    "created_at": string,
    "version": integer | string,
    "provenance": [{ "id", "kind", "contribution", ... }],
    "evidence": [{ "ref", "relation", ... }],
    "links": [{ "target", "rel", ... }],
    "weight": number,
    "stub": boolean,
    "auditable": boolean
  },
  "receipt": {
    "action": "created" | "updated" | "transformed" | "rejected",
    "reason": string,        // human-readable when action is rejected
    "mapping": {              // present when origin-to-local mapping changed
      "origin": string,
      "local_id": string
    }
  }
}
```

The `receipt` echoes the write outcome per v0.6, 3.5.4. `action: created` means a brand-new memory; `updated` means a new revision was created; `transformed` means the system modified the client's input (for example, filling in missing provenance); `rejected` means the write was refused, with `reason` explaining why.

### 2.4 The `remember` tool binding (MCP)

In MCP, `remember` is a tool with the schema above. The tool name is `remember`. The tool's description states:

> Create a new memory or a new revision of an existing memory. The memory system owns `scope` assignment and `identifier` generation; client-supplied `scope` is ignored and client-supplied `identifier` is validated for uniqueness. Returns the runtime representation of the stored memory and a receipt describing the write outcome.

An MCP tool schema example (JSON Schema form):

```json
{
  "type": "object",
  "properties": {
    "body": { "type": "string", "description": "The memory content" },
    "media_type": { "type": "string", "description": "MIME type of the body" },
    "title": { "type": "string" },
    "tags": { "type": "array", "items": { "type": "string" } },
    "path": { "type": "string" },
    "created_at": { "type": "string", "format": "date-time" },
    "valid_from": { "type": "string", "format": "date-time" },
    "valid_until": { "type": "string", "format": "date-time" },
    "version": { "oneOf": [{ "type": "integer" }, { "type": "string" }] },
    "links": { "type": "array", "items": { "$ref": "#/definitions/link" } },
    "evidence": { "type": "array", "items": { "$ref": "#/definitions/evidence" } },
    "provenance": { "type": "array", "items": { "$ref": "#/definitions/contributor" } }
  },
  "required": ["body", "media_type"]
}
```

## Part 3. Active Memory Recall — the `recall` tool

### 3.1 Purpose

The `recall` tool lets an agent query the memory system for memories relevant to a given query. The protocol does NOT standardize the recall signature, ranking, or retrieval algorithm (v0.6, 3.6.2, I-15a). Each memory system provides its own recall surface; this spec only standardizes the shape of the request and the shape of the response — memory objects in the runtime representation.

### 3.2 Request

```
POST /recall
Content-Type: application/json

{
  "query": string,                         // required: free-text search query
  "tags": [string],                        // optional: all must match
  "path_prefix": string,                   // optional: memories under this path
  "created_after": string,                 // optional: ISO 8601
  "created_before": string,                // optional: ISO 8601
  "valid_at": string,                      // optional: ISO 8601; memories valid at this instant
  "limit": integer,                        // optional: max results to return
  "sort": "recency" | "relevance" | "random", // optional: ranking hint
  "cursor": string                         // optional: pagination cursor
}
```

All fields are optional except `query`, which is required. The `sort` field is a hint to the implementation; a system may ignore it or interpret it differently. `valid_at` filters to memories whose validity window contains the given instant (v0.6, 3.6.4).

### 3.3 Response

```
200 OK
Content-Type: application/json

{
  "results": [
    {
      "memory": {
        // runtime representation per Section 1.3
        "identifier": string,
        "media_type": string,
        "body": string,
        "title": string,
        "tags": [string],
        "path": string,
        "created_at": string,
        "version": integer | string,
        "provenance": [{ "id", "kind", "contribution", ... }],
        "evidence": [{ "ref", "relation", ... }],
        "links": [{ "target", "rel", ... }],
        "weight": number,
        "stub": boolean,
        "auditable": boolean
      },
      "score": number,                       // optional: implementation-specific relevance
      "highlight": string                    // optional: snippet around the match
    }
  ],
  "continuation": {
    "cursor": string,                        // present if more results available
    "estimated_total": integer               // optional: total matching count
  }
}
```

The `results` array holds memory objects in the runtime representation (v0.6, 3.4). Each result MAY carry an implementation-specific `score` and `highlight`; these are not standardized. `continuation` enables pagination per the `cursor` request field.

### 3.4 The `recall` tool binding (MCP)

In MCP, `recall` is a tool named `recall`. The tool's description states:

> Query the memory system for memories relevant to a free-text query. The protocol does not standardize the retrieval algorithm or ranking; the system returns memory objects in the runtime representation. Optional filters: tags (all must match), path_prefix, created_after / created_before, valid_at, limit, sort hint, cursor.

### 3.5 Recall returns only runtime fields

A recall response MUST NOT include `checksum`, `scope`, or tombstone/audit-record fields (v0.6, U-12). The agent receives only the runtime representation. If the agent needs provenance for audit purposes, it may read the memory again with a different surface, or the system may include a summary `provenance` field in the runtime projection.

## Part 4. Passive Memory Creation — `passive-create` interceptor

### 4.1 Purpose

Passive memory creation observes a session and autonomously creates memories from content the agent encounters. Unlike `remember` (which is agent-driven), `passive-create` is system-driven: an interceptor watches the conversation stream and, when it detects something worth remembering, creates a memory without the agent explicitly requesting it.

This is the runtime surface for what IBM v0.1 calls "observe" and what the September 28 common-ground notes call "memory lifecycle interceptor."

### 4.2 The interceptor contract

The interceptor is a function with this signature:

```
function passive-create(
  turn: Turn,
  session: SessionContext
) -> Maybe<MemoryRequest>
```

Where:
- `Turn` is the agent-facing unit of conversation: a user message, an agent action, or an observation. At minimum it contains:
  - `role`: `"user" | "assistant" | "system"`
  - `content`: string
  - `turn_number`: integer (monotonic within the session)
  - `timestamp`: ISO 8601
- `SessionContext` provides session-level state:
  - `session_id`: string
  - `user_id`: string (the account this session belongs to)
  - `agent_id`: string (which agent is running)
  - `project_id`: string or null (scope for the session)
  - `memory_scope`: string (derived from `project_id`/`user_id`; the system sets this per v0.6, U-11)
  - `origin`: string (the memory system's origin identifier, per v0.6, I-8)

The interceptor returns either:
- `null` / `None` — nothing to remember from this turn; or
- A `MemoryRequest` — a request to create a memory, defined below.

### 4.3 The `MemoryRequest`

A `MemoryRequest` is a subset of the `remember` request, containing only the fields an interceptor is permitted to set:

```json
{
  "body": string,                          // required: the extracted memory content
  "media_type": string,                    // required: usually "text/markdown" or "text/plain"
  "title": string,                         // recommended: a concise summary
  "tags": [string],                        // recommended: e.g. ["observation", "session"]
  "path": string,                          // optional: derived from session context
  "created_at": string,                    // defaults to turn timestamp
  "valid_from": string,                    // optional: when the observation became true
  "version": integer,                      // for update; absent for create
  "links": [{ "target", "rel" }],          // optional: links to source memories
  "evidence": [{ "ref", "relation" }],     // optional: what the observation is based on
  "provenance": [{ "id", "kind", "contribution", ... }] // REQUIRED: who/what contributed
}
```

The interceptor MUST set `provenance` with `kind: agent` and `contribution: authored` for the extraction itself. If the turn contains an explicit user instruction that prompted the observation, the interceptor SHOULD also include a `provenance` entry with `kind: human`, `contribution: instructed`, and the user's `id`.

### 4.4 The interceptor is a pure function (mostly)

The interceptor is conceptually a pure transformation: `Turn × SessionContext → Maybe<MemoryRequest>`. It does not directly write to the memory store. Instead:

1. The interceptor computes a `MemoryRequest` from the turn.
2. The harness or memory system then calls the `remember` write path with that request.
3. The `remember` path handles `identifier` assignment, `checksum` computation, `version` validation, and scope assignment per Sections 2.2–2.3.

This separation lets the same interceptor be reused across different memory systems and lets the write path enforce the system-set `scope` rule (v0.6, U-11) uniformly.

### 4.5 When the interceptor fires

The harness invokes the interceptor after each turn it receives (after a user message, after an agent action, after an observation). The interceptor decides whether the turn contains something worth remembering:

- A user instruction that establishes a preference or constraint: `"Remember, I prefer concise answers."`
- An observation the agent made that is worth retaining: `"The API returned a 429; back off for 30s."`
- A fact the user stated that is likely to recur: `"My timezone is UTC+2."`
- A correction the user made: `"Actually, the project is called 'northwind', not 'north-wind'."`

The interceptor should NOT fire for:
- Greetings and small talk
- Transient operational output (e.g., "File saved")
- Content already captured in a previous memory (deduplicated by the memory system's `checksum`/`body_checksum` per v0.6, U-1)

### 4.6 MCP interceptor binding

In MCP, interceptors are defined via the MCP specification's interceptor mechanism. The memory system declares an interceptor named `passive-create` (or a namespaced variant like `memory/passive-create`). The interceptor schema:

```json
{
  "type": "object",
  "properties": {
    "turn": {
      "type": "object",
      "properties": {
        "role": { "type": "string", "enum": ["user", "assistant", "system"] },
        "content": { "type": "string" },
        "turn_number": { "type": "integer" },
        "timestamp": { "type": "string", "format": "date-time" }
      },
      "required": ["role", "content", "turn_number", "timestamp"]
    },
    "session": {
      "type": "object",
      "properties": {
        "session_id": { "type": "string" },
        "user_id": { "type": "string" },
        "agent_id": { "type": "string" },
        "project_id": { "type": ["string", "null"] },
        "memory_scope": { "type": "string" },
        "origin": { "type": "string" }
      },
      "required": ["session_id", "user_id", "agent_id", "memory_scope", "origin"]
    }
  },
  "required": ["turn", "session"]
}
```

The interceptor returns either `null` or a `MemoryRequest` object matching the schema in Section 4.3.

The MCP interceptor is invoked by the harness after each turn. The harness then takes the returned `MemoryRequest` (if any) and calls the `remember` tool to persist it. The interceptor itself does not write; it only proposes.

### 4.7 De-duplication and idempotency

The interceptor may see the same content across multiple turns (e.g., a user repeating an instruction). The memory system's `remember` path handles deduplication via `checksum` (v0.6, U-1): if a memory with identical content already exists for the `origin`, the write is idempotent (v0.6, U-14). The interceptor does not need to maintain its own deduplication state, though it MAY for efficiency.

## Part 5. Passive Memory Decoration — `passive-decorate` interceptor

### 5.1 Purpose

Passive memory decoration filters user turns and decorates them with relevant memories before the agent sees them. This is distinct from passive creation: decoration is about *retrieval* (what context to inject), while creation is about *storage* (what to persist).

The September 28 common-ground notes list "decorate" as a runtime verb alongside "observe" (remember/recall/observe/decorate from IBM v0.1). This interceptor lets a memory system pre-compute relevant memories and attach them to a turn so the agent can use them without an explicit recall call.

### 5.2 The interceptor contract

The interceptor is a function with this signature:

```
function passive-decorate(
  turn: Turn,
  session: SessionContext
) -> DecoratedTurn
```

Where `Turn` and `SessionContext` are the same as in Section 4.2, and `DecoratedTurn` is:

```json
{
  "turn": Turn,                              // the original turn, unchanged
  "memories": [
    {
      "memory": {
        // runtime representation per Section 1.3
        "identifier": string,
        "media_type": string,
        "body": string,
        "title": string,
        "tags": [string],
        "path": string,
        "created_at": string,
        "version": integer | string,
        "provenance": [{ "id", "kind", "contribution", ... }],
        "evidence": [{ "ref", "relation", ... }],
        "links": [{ "target", "rel", ... }],
        "weight": number,
        "stub": boolean,
        "auditable": boolean
      },
      "reason": string,                      // why this memory is relevant
      "score": number                        // optional: relevance score
    }
  ],
  "mask": boolean                            // if true, suppress the original turn's content
}
```

The `memories` array holds memory objects most relevant to this turn, in the runtime representation. The `reason` field explains why each memory was selected (e.g., "matches project scope", "user mentioned this earlier", "tagged 'preference'"). The optional `score` is implementation-specific. The optional `mask` flag, if true, instructs the harness to suppress the original turn's content and replace it with the decorated memories — useful when the turn is a raw user utterance that should be rephrased through memory recall.

### 5.3 When the interceptor fires

The harness invokes the interceptor before it passes the turn to the agent model. For each turn:

1. The harness calls `passive-decorate(turn, session)`.
2. The interceptor returns a `DecoratedTurn` with zero or more relevant memories.
3. The harness injects the returned memories into the agent context (as hidden context blocks, tool context, or prompt injection) before invoking the agent.

The decorator may choose to return an empty `memories` array for turns where nothing is relevant (e.g., greetings). It should return memories for turns where the agent would otherwise lack needed context:
- User states a preference: decorate with any existing preference memories.
- User references a past decision: decorate with the decision memory.
- User mentions a project or file: decorate with project-scoped memories.

### 5.4 Decorator scope and filtering

The decorator uses `session.memory_scope` (set by the memory system per v0.6, U-11) to filter which memories are relevant. It MUST NOT return memories outside the session's scope. The decorator may also consider:
- `tags` on the turn or session context
- The `turn.role`: user turns are decorated for recall; assistant turns may be decorated for consistency
- Temporal recency: prefer recent memories unless `valid_until` is far in the future

### 5.5 MCP interceptor binding

In MCP, the decorator is an interceptor named `passive-decorate` (or `memory/passive-decorate`). The interceptor schema:

```json
{
  "type": "object",
  "properties": {
    "turn": {
      "type": "object",
      "properties": {
        "role": { "type": "string", "enum": ["user", "assistant", "system"] },
        "content": { "type": "string" },
        "turn_number": { "type": "integer" },
        "timestamp": { "type": "string", "format": "date-time" }
      },
      "required": ["role", "content", "turn_number", "timestamp"]
    },
    "session": {
      "type": "object",
      "properties": {
        "session_id": { "type": "string" },
        "user_id": { "type": "string" },
        "agent_id": { "type": "string" },
        "project_id": { "type": ["string", "null"] },
        "memory_scope": { "type": "string" },
        "origin": { "type": "string" }
      },
      "required": ["session_id", "user_id", "agent_id", "memory_scope", "origin"]
    }
  },
  "required": ["turn", "session"]
}
```

The interceptor returns a `DecoratedTurn` object matching the schema in Section 5.2.

### 5.6 Interaction with `passive-create`

`passive-decorate` and `passive-create` are orthogonal and may both be registered:

| Interceptor | Purpose | Returns |
|---|---|---|
| `passive-create` | Observe turn, propose a memory to store | `Maybe<MemoryRequest>` |
| `passive-decorate` | Observe turn, return relevant memories for context | `DecoratedTurn` |

A turn may trigger both:
1. `passive-decorate` runs first, returning relevant memories for the agent's context.
2. `passive-create` runs next, proposing a new memory from the turn's content.
3. The harness persists the proposed memory via `remember` (if any).

The order is an implementation detail; the spec only requires that both interceptors receive the same `Turn` and `SessionContext` and can make independent decisions.

## Part 6. Capability declaration

A memory system SHOULD declare which runtime surfaces it supports. The capability declaration follows the federation binding pattern (v0.6, 3.6.4): a JSON object with a `runtime` field:

```json
{
  "runtime": {
    "version": "0.6",
    "endpoints": {
      "remember": true,
      "recall": true,
      "passive-create": true,
      "passive-decorate": true
    },
    "bindings": ["mcp", "cli"],
    "scopes": {
      "user": {
        "description": "Memories scoped to a single user"
      },
      "project": {
        "description": "Memories scoped to a project/repository"
      }
    }
  },
  "memory_object": {
    "version": "0.6",
    "profiles": ["minimal", "audit"],
    "manifest": "required for export"
  }
}
```

The `endpoints` object declares which of the four runtime plug-in points are implemented. `bindings` lists the transports (MCP, CLI, HTTP). `scopes` describes the scope model the system uses internally (v0.6, U-11 leaves scope granularity to implementations; the system declares what it actually supports).

## Part 7. Next: management API (out of scope for this draft)

This draft intentionally does not cover the management API. The following are deferred to a subsequent document:

| Feature | Why deferred |
|---|---|
| Memory scope sharing | Requires defining how scopes are mapped across systems (v0.6, U-11 leaves this to implementations) |
| Auth / identity | v0.6, I-15b delegates auth to the binding (OAuth, MCP auth, transport equivalent); the management API would add scope-to-identity mapping |
| Forget / tombstone API | Covered by the `version` update path in Section 2.2, but a dedicated forget endpoint with reason codes (v0.6, U-10) is out of scope |
| Retention policies | v0.6, I-23b mentions `no_export`/`no_derive` constraints; retention is implementation policy |
| Consolidation / dreaming agents | Memory-maintenance agents are out of scope (v0.6, E); the management API would expose endpoints for external consolidation processes |
| Export / import management | v0.6, 3.5; the manifest proposal (D) owns this |

These build on the runtime plug-in points defined here: a management client would use `remember` to write forget markers, `recall` to query before forgetting, and the interceptors to observe what should be forgotten.

## Appendix A. Field mapping: runtime request → memory object

This table shows how the fields in the `remember` request (Section 2.2) map to the memory object fields (v0.6, Section 1.3). Fields not listed are computed by the system.

| Request field | Memory object field | Notes |
|---|---|---|
| `body` | `body` | Required; the memory content |
| `media_type` | `media_type` | Required; validated as a MIME type |
| `title` | `title` | Optional; human-readable label |
| `tags` | `tags` | Optional; semantic tags |
| `path` | `path` | Optional; hierarchy in origin store |
| `created_at` | `created_at` | Required; defaults to turn timestamp if omitted |
| `valid_from` | `valid_from` | Optional; when the claim becomes true |
| `valid_until` | `valid_until` | Optional; when the claim stops being true |
| `version` | `version` | Optional; for revision. System validates comparator (I-4) |
| `links` | `links` | Optional; typed edges `{target, rel, version, origin}` |
| `evidence` | `evidence` | Optional; references `{ref, relation, dangling, at, version, origin}` |
| `provenance` | `provenance` | Optional; contributor list. System may add/adjust entries |
| *client-supplied `identifier`* | `identifier` | Validated for uniqueness; system may override |
| *system-generated* | `identifier` | UUID if client did not supply |
| *system-computed* | `checksum` | `algorithm:hex` over metadata + body (U-1) |
| *system-computed* | `updated_at` | Set to `created_at` on create; updated on revision |
| *system-computed* | `protocol_version` | Set to spec version (I-26) |
| *system-assigned* | `scope` | Assigned from caller identity (U-11); client value ignored |
| *system-assigned* | `auditable` | Derived: true if provenance has accountable human and evidence present (I-13) |

## Appendix B. Example: full session with both active and passive paths

A session with user `u:alice`, agent `agent:notes-assistant`, project `proj:platform`:

```
Turn 1: user says "I prefer concise answers."
  passive-decorate returns: [] (no prior preferences)
  passive-create returns: MemoryRequest {
    body: "User prefers concise answers.",
    media_type: "text/plain",
    title: "User preference: concise answers",
    tags: ["preference"],
    provenance: [
      { id: "user:alice", kind: "human", contribution: "instructed", at: "..." },
      { id: "agent:notes-assistant", kind: "agent", contribution: "authored", at: "..." }
    ]
  }
  → remember creates memory M1 (identifier: mem:abc123)

Turn 2: user asks "What's the status update policy?"
  passive-decorate returns: [M1] with reason "matches user preference for concise answers"
  → harness injects M1's body as context before calling agent
  → agent calls recall? No — decoration provided context already
  passive-create returns: null (nothing new to remember)

Turn 3: agent outputs "Status updates are due Fridays."
  passive-decorate returns: [] (no relevant prior memories for this output)
  passive-create returns: MemoryRequest {
    body: "Status updates are due Fridays from Sep 15.",
    media_type: "text/markdown",
    title: "Status updates move to Friday",
    tags: ["preference", "team-process"],
    evidence: [{ ref: "transcripts/...", relation: "stated" }],
    provenance: [
      { id: "agent:notes-assistant", kind: "agent", contribution: "authored", at: "..." }
    ]
  }
  → remember creates memory M2 (identifier: mem:def456)
```

## Appendix C. Relationship to v0.6 sections

| This spec | v0.6 reference |
|---|---|
| Runtime representation (Section 1.3) | 3.4, U-12 |
| `identifier` + `origin` as global key | 1.3, I-8, 3.5.2 |
| `scope` is system-set, not client-supplied | U-11 |
| `checksum` computation | U-1 |
| `version` comparator and immutability | I-4, 3.3.2, 3.3.3 |
| `auditable` flag derivation | I-13 |
| Provenance keys (`contribution`, `accountable`) | 3.1.1, I-3a, I-3b |
| Evidence entry shape (`ref`, `relation`, `dangling`) | U-2 |
| Two representations (interchange vs runtime) | 3.4 |
| Bindings are separate from the spec | I-10 |
| Recall signature is not standardized | 3.6.2 |
