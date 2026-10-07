# Memory Object Format (MOF)

A sketch of the canonical schema for a single memory and the serializations
that make it portable.

## The problem

Every memory system defines its own object model. Letta has MemoryRecord, Mem0
has atomic facts, Claude Code has markdown files with YAML frontmatter, OpenClaw
has provenance-annotated entries, Hermes has section-delimited blocks. A memory
created in one system cannot be consumed by another because there is no shared
definition of what a memory *is*.

## The sketch

Define a logical schema for a memory object: required fields, recommended
fields, and extensible metadata. Then define two lossless serializations of
that schema, so the same memory can live as a file on disk or as a JSON object
in an API response.

### Required fields

Every memory must carry these for interoperability:

| Field | What it answers |
|-------|-----------------|
| id | Which memory is this? |
| logical_id | Which logical memory is this a version of? (Distinct from id when versioning is supported.) |
| content | What does the memory say? |
| scope | Who can see this? (Minimum: `personal`, `project`. Extensible for platform deployments: `organizational`, `enterprise`, `role`, and others.) |
| scope_qualifier | Which project, which user? (The scope enum alone is not enough.) |
| owner | Who owns this memory? |
| origin_type | Was this user-stated, agent-inferred, system-generated, or imported? |
| created_at | When was it created? |

The scope vocabulary has a required minimum (`personal`, `project`) and is
open for extension. Platform deployments that need organizational, enterprise,
role, or team scopes add them without breaking interoperability with simpler
systems. A single-user file-based system uses `personal`. A multi-tenant
enterprise system adds whatever scopes its deployment requires. The fields are
the same; the enforcement is implementation.

### Recommended fields

Implementations should support these for richer interoperability:

| Field | What it answers |
|-------|-----------------|
| memory_type | What kind of knowledge is this? (Recommended vocabulary: fact, preference, instruction, decision, event, summary. Extensible.) |
| weight / salience | How important is this relative to other memories? |
| tags / domains | What topics does this relate to? |
| version | Which version of this memory is this? |
| status | Is this active, deprecated, or retracted? |
| expires_at | When should this memory be garbage-collected? |
| relevant_until | When does the content become stale? (Distinct from storage expiry.) |
| confidence | How confident is the creator in this memory's accuracy? |
| generating_model | Which model produced this, if agent-inferred? |
| actor_id | Who performed the write operation? |
| driver_id | On whose behalf? (Distinct from actor when delegation is involved.) |
| lineage | What other memory IDs was this derived from? |
| metadata | Extensible key-value bag for anything else. |

### Relationships

Memories can reference other memories via typed edges. Implementations that
support relationships should use a controlled vocabulary:

- `derived_from`: this memory was extracted or synthesized from another
- `supersedes`: this memory replaces an older one
- `conflicts_with`: this memory contradicts another
- `related_to`: general association

Implementations that do not support relationships can ignore these. The
relationship vocabulary is recommended, not required.

### Serializations

**Markdown with frontmatter** (for file-based systems):

```markdown
---
id: 550e8400-e29b-41d4-a716-446655440000
scope: project
scope_qualifier: github.com/org/repo
owner: wes
origin_type: agent
memory_type: decision
weight: 0.9
created_at: 2026-09-09T14:30:00Z
---

We chose FastAPI over Flask for the API layer because we need async
support and automatic OpenAPI documentation.
```

**JSON** (for API-based systems):

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "content": "We chose FastAPI over Flask for the API layer because we need async support and automatic OpenAPI documentation.",
  "scope": "project",
  "scope_qualifier": "github.com/org/repo",
  "owner": "wes",
  "origin_type": "agent",
  "memory_type": "decision",
  "weight": 0.9,
  "created_at": "2026-09-09T14:30:00Z"
}
```

Both serializations represent the same logical object. Round-tripping between
them must be lossless for all required and recommended fields.

### Exchange bundles

A collection of memories for export/import is a bundle: a manifest (source
system, export time, schema version) plus an array of memory objects.
Conflict resolution during import uses one of: skip (keep existing), overwrite
(replace with incoming), or merge-by-timestamp (keep the newer version).

## What this does not define

- The specific hash algorithm for content-addressable identity (implementation)
- The embedding vector or search index (implementation)
- The storage layout on disk or in a database (implementation)
- The extraction pipeline that produces memories (implementation)
- Trust verification of provenance claims ([PTC](https://github.com/wjatx/ptc-gal-standards/blob/main/PTC-SPEC.md))

## Open questions

- Is `logical_id` worth the complexity, or can versioning be handled by
  relationships (`supersedes`) alone?
- Should the memory type vocabulary draw from cognitive science (episodic,
  semantic, procedural) or practical labels (fact, preference, instruction)?
  The prior art survey shows both in wide use.
- Multi-tenant implementations enforce scope and tenant isolation as part of
  their access control. Should the spec say anything about enforcement, or
  just define the fields and leave enforcement to MAP and the implementation?
