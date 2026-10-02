# Open Memory Protocol: Memory Object, Exchange and Runtime

**Editors' draft v0.1, 2026-10-02**, building on the 2026-09-28 call. Exchange and Runtime sub-thread, written with the Memory Model and Context (MM&C) overlap in mind. Not an adopted OMP standard.

**Sources.** This draft distills the proposals in `early-draft-specs/` on `main` (commit 7beb260): the scoping note (Strauss and Rosenblat), Packer v0.2 (Letta), IBM v0.1, AIDP / FMP v0.1, Cognee v0.1, Context Nest v0.1 and the AMS Card (Mila / Mozilla). It also draws on the 2026-09-28 exchange-and-runtime call and the #exchange-and-runtime thread. Section references in parentheses point to the source draft, for example (IBM), (Cognee §3.5), (CN §6.3).

---

## 0. Status, scope and conventions

### 0.1 Status

This is a working draft for discussion. Every section carries a status:

- **[agreed]**: at least two participants explicitly agreed on the 2026-09-28 call and nobody objected.
- **[proposed]**: put forward on the call or in a source draft and not contested, but nobody explicitly signed on.
- **[open]**: raised and not resolved.
- **[discussed]**, **[no objection]**, **[parked]**: used for header fields, as in the call notes.
- **[editors]**: text the editors added to make the draft complete. It has not been discussed yet.

### 0.2 Scope

In scope: the memory object (its header and body), the fields it carries, how memories link to each other and to evidence, versioning and lifecycle, the export/import (interchange) representation, the runtime representation, and the shape of what crosses a runtime binding.

Out of scope for this draft: user scope and candidate implementations (set aside on the call), and everything listed in §11.

### 0.3 Conventions

The key words MUST, MUST NOT, SHOULD, SHOULD NOT, MAY and RECOMMENDED are to be read as in RFC 2119 and RFC 8174. **In this draft, every normative statement is proposed.** A MUST states what the editors propose the requirement should be once adopted. It does not claim the group has agreed to it.

---

## 1. Goals

The design is judged against three goals.

1. **Adoption.** A folder of markdown memories, a server-backed store and a graph store can all conform with little work. Most header fields are optional, and the smallest profile (§10.1) can be met by today's harnesses.
2. **Auditability.** When a deployment needs it, every memory can be traced to one or more accountable humans (§4.3) [agreed], its history can be verified, and its lifecycle events are recorded. These requirements sit in tiers (§3.1) so that individual users are not forced to carry enterprise obligations. Full audit is a multi-user enterprise requirement, not a single-user one [agreed].
3. **Room for innovation.** The protocol standardizes interfaces and the shape of data, not algorithms. Recall, ranking, federation merge logic, memory-maintenance agents, retrieval isolation and audit-log delivery are left to implementations to compete on (§11).

---

## 2. The memory object

### 2.1 Header plus body [agreed]

A memory is a **header** plus a **body**.

- The **header** is a rigorous schema that can be rendered into any format that renders schemas (JSON, YAML front matter, a database row).
- The **body** is a string in any format, and its format is declared by the header's `type` field (§3).

This is a two-sided data contract: a stable header that changes only through versioning, and a free-form payload the protocol does not prescribe (Cognee, from the call).

### 2.2 Body formats [agreed]

Markdown is the common body format and is RECOMMENDED for bodies meant to be read by agents. Plain text is equally acceptable. The protocol MUST allow other formats, including DocLang, CSV, XML (for example PubMed) and HTML, without requiring every implementation to process every format.

The group is leaning toward markdown as the **common body format**, not the **base object** [open, leaning]. The base object is the header plus a typed body. Section 10.2 defines how a markdown-first loading profile relates to that (Packer).

### 2.3 Atomic unit [open]

The protocol does not yet fix the size of a memory. One view: a memory is the smallest semantic unit that carries meaning and can be evaluated true or false (Cognee, from the call). Another: memories are documents with titles and authors, as in document stores (CN, Packer). The header in §3 is written to work for both. See issue I-2.

---

## 3. Header fields

### 3.1 Tiers [proposed]

Each field carries one tier (proposed by Gabe on the call):

| Tier | Meaning |
|---|---|
| **required** | Every conforming memory carries it |
| **audit-required** | Required in the audit profile (§10.4); optional otherwise |
| **ACL-required** | Required where access control applies; interchange only |
| **optional** | May be omitted in every profile |

Optional fields tend to go unimplemented, so the protocol SHOULD keep the number of optional fields that matter for interchange small (from the call).

**Every tier assignment in §3.2 is proposed by the editors.** The call did not assign fields to tiers.

### 3.2 Field table

| Field | Type | Tier [editors] | Status | Definition |
|---|---|---|---|---|
| `identifier` | string | required | [proposed] | Identifies the memory within its origin system. May be a readable title, a UUID or a path, and carries no required meaning. MUST be unique among the memories in one export. Replaces `title` as the key (call; IBM "memory identifier"; Cognee §3.1) |
| `title` | string | optional | [proposed] | A human-readable label. May duplicate the body for fact-sized memories (call) |
| `type` | string | required | [discussed] | The content or media type of the body (for example `text/markdown`, `text/html`, `text/csv`, `application/xml`, a skill, structured data). Not a semantic ontology (CN; call) |
| `tags` | list of strings | optional | [discussed] | Semantic tags. Free-form, or values drawn from an ontology declared elsewhere (for example a JSON-LD `@context`). The protocol defines the shape of a tag set, not the values (IBM; CN) |
| `scope` | list of strings | ACL-required | [proposed] | Scope tags that access policy attaches to. Set by the system, never by the agent. Interchange only (§7). A scope tag is neither an access grant nor proof of ownership (IBM; Cognee §3.3; call) |
| `created_at` | ISO 8601 timestamp | required | [no objection] | When the memory was first created |
| `version` | opaque, with a declared comparator | required | [open] | The revision of this memory. See §6.1 |
| `updated_at` | ISO 8601 timestamp | optional | [open] | When this revision was written. Whether it belongs in the header at all is open (issue I-4) |
| `checksum` | string (`algorithm:hex`) | audit-required | [no objection] | An integrity hash of the header-covered fields plus the body (CN; call) |
| `provenance` | list of contributors | required, with an accountable human audit-required | [proposed] | Everyone and everything that contributed. Replaces `author`. See §4 |
| `evidence` | list of references or strings | optional, audit-required when the memory is derived | [open] | Where the memory came from. See §4.4 |
| `links` | list of edges | optional | [open] | References to other memories. See §5 |
| `valid_from` / `invalidated_at` | ISO 8601 timestamp | optional | [proposed] | When the claim applies and when it stopped applying, distinct from when it was recorded (IBM; Cognee §3.5) |
| `status` | string | optional | [parked] | Lifecycle or visibility state inside a store (for example draft, published). Possibly implementation-specific. If kept, interchange only (call; CN) |

Implementations MAY add fields. Unknown fields MUST be preserved on export and MUST NOT change the meaning of standard fields (Cognee §5).

---

## 4. Provenance and evidence

### 4.1 Contributor list [proposed]

`provenance` is a list. Each entry names one contributor:

| Key | Tier [editors] | Meaning |
|---|---|---|
| `id` | required | An identifier for the contributor (a person, an agent, a system) |
| `kind` | required | `human`, `agent` or `system` |
| `role` | optional | For example `author`, `instructed`, `approved`, `edited`, `imported` [open] |
| `ai_usage` | optional | `none`, `draft` or `full`, mirroring the human / mixed / AI split in the EU AI Act (IBM; call) [open] |
| `model` | optional | The model or agent that acted, when `kind` is `agent` |
| `at` | optional | When this contributor acted |

A plain list lets a memory record, for example, that a person asked an agent to save something and the agent rewrote it, without forcing a single grade on the result (Sruly, call). Whether `role` and `ai_usage` are part of the core is open (issue I-3).

### 4.2 Writers are contributors [editors]

Any process that writes a memory, including forget, consolidation and other maintenance agents, MUST appear in `provenance` like any other writer. The protocol does not define what those agents do (§11).

### 4.3 Accountable human [agreed]

A memory is **auditable** if it can be traced to one or more accountable humans. In the audit profile (§10.4), every memory MUST carry at least one `provenance` entry with `kind: human`, and SHOULD mark who is accountable when several humans appear (for example the person who gave the instructions and the person who approved) [proposed].

### 4.4 Evidence [open]

`evidence` links a memory back to what it was derived from: source material, transcript turns, or other memories. Each entry is either a reference to another memory's `identifier` (optionally at a version) or a plain string when the source is not addressable (call). Implementations SHOULD distinguish source material, transcripts, human assertions and machine-derived memories (Cognee §3.2; AIDP ground truth / transcripts / inferences). Evidence records origin, not truth.

A derived memory whose evidence is unavailable MUST say so rather than omit the field silently (Cognee §3.2) [editors].

### 4.5 Legacy stores [open]

Stores without metadata (for example a folder of markdown memories) MAY fill `provenance` heuristically, for instance treating the harness as the agent and the local user as the human. An export built this way MUST declare that its provenance is inferred and that the memories are not auditable (call). How to declare it is issue I-9.

---

## 5. Links, lineage and edges

### 5.1 A graph [agreed]

Evidence and lineage form a graph whose nodes are memories and sources. How the graph is built, stored and traversed is left to the implementation. An audit-grade system MUST be able to reconstruct the full chain behind a memory. Other systems MAY leave nodes unconnected (call).

### 5.2 Depth [open]

The protocol does not require full provenance on every object. The minimum lineage an audit-grade system must keep (n hops back, or the full chain) is open (issue I-6). Consolidation SHOULD name all its inputs (Cognee §3.4).

### 5.3 Links between memories [open]

Memories MAY reference each other. Two carriers are under discussion, and they are not exclusive:

- **Inline links in the body**, for example wiki syntax `[[identifier]]` (CN). These work in any format that can carry text.
- **Typed edges in the header**, for example `links: [{target, rel}]`, with `rel` values such as `derived_from`, `supersedes`, `relates_to` (Cognee §3.4; IBM override).

Open: what a link targets (identifier, or identifier at a version), whether edges are typed in the core, and what happens when a target is missing from an export (§8.5). See issue I-5.

---

## 6. Versioning and lifecycle

### 6.1 Version slot [open]

Every memory carries a `version` field. Its format is left to the implementation (a sequence number, semantic version or other), but the implementation MUST declare a comparator that orders the versions of one memory (IBM). Wall-clock time SHOULD NOT be the comparator (call). Whatever the group decides in issue I-4, the `version` slot stays, so implementations with richer history have a place to expose it [editors].

### 6.2 Immutable revisions [open]

A change SHOULD create a new revision that supersedes the old one, rather than overwrite it in place, so history can be read "as of" a point in time (IBM; Cognee §3.1; CN). This is RECOMMENDED, not required, because a hard rule breaks markdown-on-disk stores (call). **Proposed by the editors:** in the audit profile (§10.4), immutable revisions and a verifiable history (for example a hash chain) are REQUIRED.

### 6.3 Invalidation and supersession [proposed]

Recording time is distinct from when a claim applies (Cognee §3.5). A memory MAY be invalidated (`invalidated_at`) without being deleted (IBM). A newer revision or another memory MAY supersede it. Current reads SHOULD exclude invalidated memories, and historical reads SHOULD be explicit (Cognee §3.5).

### 6.4 Delete [proposed]

A conforming store MAY delete a memory (IBM; AIDP `/fmp/delete`; Cognee; CN). A delete SHOULD leave an audit record (who, when, why) with no content. A delete does not by itself stop the content from coming back on a later import.

### 6.5 Forget, tombstones and anti-resurrection [proposed, not discussed on the call]

A **forget** erases a memory's content while keeping its history verifiable (CN §6.3). A **tombstone** records that a revision was erased (Cognee §3.5).

**Implementation status.** A released implementation exists (Context Nest, `ctx` 3.0.0; PromptOwl/ContextNest#130), so this section is implementable as written. The need is observable as well: in cross-draft adapter fixtures, a store whose import rule gives every re-import a new identity revives an invalidated memory from an older archive, which is the resurrection case above.

- A forget MUST remove the content of every revision it covers and MUST keep whatever hashes the history's verification depends on, so verification still passes.
- A forget MUST leave a tombstone per erased revision with the time, the actor and a reason code from a closed set. It MUST NOT keep the content in the tombstone or in any audit record.
- **Anti-resurrection.** A receiving system MUST honor tombstones carried by an import, and MUST refuse to restore a tombstoned revision from an older archive or a pre-forget copy (Cognee §6; CN §6.3).
- Tombstones travel with exports (§8).

Without tombstones, an interchange rule that turns every re-import into a new memory lets an invalidated or deleted memory come back from an old archive (Cognee §3.5). Whether tombstones belong in the core or in the audit profile is issue I-7.

---

## 7. Representations

### 7.1 Interchange is a superset of runtime [agreed]

There are two representations of the same memory (call):

- **Interchange** (export and import, migration): the full header, including operational fields a receiving system needs to integrate the memory.
- **Runtime** (what an agent sees): a projection of the interchange form. It omits fields that would add noise to the agent's context or reveal how the store is organized.

This lines up with keeping metadata out of the agent's view, for example a markdown body the agent reads with structured metadata stored separately (AIDP, thread).

### 7.2 Field placement [proposed]

| Field | Interchange | Runtime |
|---|---|---|
| `identifier`, `type`, `body` | yes | yes |
| `title`, `tags`, `created_at` | yes | yes |
| `version`, `updated_at`, `valid_from`, `invalidated_at` | yes | when the implementation needs them |
| `provenance` | yes | a summary MAY be shown (for example the author) |
| `evidence`, `links` | yes | MAY be shown |
| `checksum` | yes | no |
| `scope` | yes | no |
| `status` | yes, if kept | no |
| tombstones, audit records | yes | no |

Runtime access control is enforced by the serving system using interchange fields. The agent does not need to see them (call).

---

## 8. Exchange

### 8.1 Manifest [proposed]

Every export SHOULD begin with a manifest that declares the protocol version, the profiles it follows (§10), the body formats present, whether it is a complete snapshot or a selection, and any required extensions (Cognee §3.6). Absence from a partial export MUST NOT be read as deletion (Cognee §3.6).

### 8.2 Transfer intent [open]

An export MUST declare its intent (Cognee §3.6):

- **copy**: the source keeps its memories.
- **move**: the source deletes its memories only after a durable, conforming import on the receiving side.
- **federation**: no transfer. The memory is read where it resides (AIDP).

IBM's draft treats a memory as valid in one system at a time, with an import creating a new memory in the receiving system. Cognee's draft keeps the origin identity across copies. Whether an imported memory keeps its origin `identifier` or receives a new one with a recorded mapping is issue I-8. A receiving system that assigns its own identifiers MUST keep the origin-to-local mapping (Cognee §3.1) [editors].

### 8.3 Fidelity [proposed, raised in the thread, not discussed on the call]

The receiving side SHOULD be able to check that it received the same memory with the same history. In the audit profile, it MUST be able to, using `checksum` and the verifiable history (§6.2).

### 8.4 Receipts [proposed, not discussed on the call]

An import SHOULD produce a receipt that lists, per memory, whether it was accepted, transformed, omitted or rejected, with reasons and any identifier mappings (Cognee §3.6). Retries MUST NOT duplicate memories.

### 8.5 Dangling links [open, not discussed on the call]

In a partial export, a link or evidence reference may point to a memory that was not included or was deleted. The receiving system MUST NOT fail the import for this reason. Whether it keeps the reference as unresolved, drops it, or reports it in the receipt is issue I-5.

### 8.6 Credentials [editors]

Credentials (passwords, API keys, tokens) are not memory and MUST NOT be exported as memory (Cognee §3.3).

---

## 9. Runtime binding

### 9.1 What crosses the binding [proposed]

At runtime, memory reaches an agent in three ways (call):

1. **File access**: the agent reads memory files with shell or file tools.
2. **Tools**: the agent calls explicit remember and recall tools exposed by a memory server.
3. **Hooks**: a supervisor observes or decorates the conversation without the agent knowing, deciding what to add to a session and what to store (IBM observe / decorate; AIDP plugins).

The protocol standardizes the **shape of the memory objects** that cross these surfaces, meaning the runtime representation of §7, not a new transport.

### 9.2 Candidate binding: MCP [proposed, not agreed]

MCP was proposed as the home for the runtime binding: tools for remember and recall, interceptors for hooks, and file access as a tool (IBM; call). It is **not agreed**. Some implementers find hooks more controllable than MCP tools, and some find a CLI more reliable for retrieval isolation (call). SEP-2640 (Skills over MCP) was suggested as a way to get progressive disclosure over MCP without a file system (AIDP, thread). See issue I-10.

### 9.3 Recall is not standardized [agreed]

The protocol MUST NOT fix a signature for recall. Implementations provide their own recall and their own guidance on using it. The protocol defines what recall returns (memory objects in the runtime representation), not how it is called (call).

A write needs, at minimum, an author, a time, and whether it creates a memory or revises an existing one (call) [proposed].

### 9.4 Federation [agreed]

When several memory servers are connected, a federation layer MAY sit between them and the agent and present one unified memory. How it merges results and combines scopes is left to the implementation (AIDP; call). Identity MUST pass through the federation layer to each server (call).

### 9.5 Change notification [open, raised in the thread]

Memory can change during a session. How a harness learns that a memory it already loaded has changed (for example through MCP resource subscriptions) is issue I-11.

### 9.6 Multiple memories [open]

Whether a server returns several memories compiled into one payload or as separate objects, and whether memories can nest, is issue I-12. If they are returned separately, each carries its own runtime header.

---

## 10. Conformance levels [editors]

Profiles let a deployment claim only what it implements (Cognee §5). An export's manifest declares its profiles.

### 10.1 Minimal profile

The required fields of §3.2, a body with a declared `type`, and an export that preserves unknown fields. Meant to be reachable from a folder of markdown memories.

### 10.2 Markdown loading profile

The directory and loading contract of Packer: a root `MEMORY.md`, deeper files deferred, deferred memory surfaced one level down, and selective reads (Packer). Header fields are carried as front matter or in a sidecar. When a projection to this profile drops fields, it MUST declare the loss (Cognee §2).

### 10.3 Federation binding

The endpoint set of AIDP / FMP (upload, search, read, delete, and a required capability endpoint), carrying memory objects in the runtime representation (AIDP). Each server declares its capabilities.

### 10.4 Audit profile

Everything in the minimal profile, plus: an accountable human in every memory's `provenance` (§4.3), `checksum` on every memory, immutable revisions with a verifiable history (§6.2), evidence on derived memories (§4.4), recorded lifecycle events including deletes, and, if adopted (issue I-7), tombstones and anti-resurrection (§6.5).

---

## 11. Out of scope

Left to implementations, so that they can compete and improve on them:

- The recall function signature, ranking and retrieval algorithms [agreed].
- Federation merge and ranking logic (§9.4) [agreed].
- Memory-maintenance agents (forget, consolidation, "dream" agents) and their algorithms. Their writes still carry provenance (§4.2).
- Retrieval isolation, such as limits on graph traversal depth.
- Audit-log storage and delivery. The protocol may define a flag saying whether a memory or a retrieval is auditable (issue I-13), but not the log.
- Storage, indexing, embeddings and internal mutation (all drafts).
- Access-control systems. The protocol carries `scope` tags that access policy attaches to, but does not define the policy language (IBM; CN).

---

## 12. Open issues

| # | Issue | Where |
|---|---|---|
| I-1 | What it means for a markdown-first profile that markdown is the common body format rather than the base object | §2.2, §10.2 |
| I-2 | The atomic unit: the smallest meaningful claim, or a document | §2.3 |
| I-3 | The shape of provenance: whether `role` and `ai_usage` are core, and how to record several accountable humans | §4.1, §4.3 |
| I-4 | Versioning: whether `version` form is constrained, whether in-place updates are allowed, and whether `updated_at` belongs | §6.1, §6.2 |
| I-5 | Links: inline, header edges, or both; what a link targets; handling of dangling links | §5.3, §8.5 |
| I-6 | Lineage depth required for audit | §5.2 |
| I-7 | Tombstones and anti-resurrection: core or audit profile | §6.5 |
| I-8 | Identity on import: keep the origin identifier, or assign a new one with a mapping | §8.2 |
| I-9 | How an export declares inferred, non-auditable provenance | §4.5 |
| I-10 | Runtime binding: MCP, hooks, CLI, or several | §9.2 |
| I-11 | Change notification during a session | §9.5 |
| I-12 | Compiled vs separate memories at runtime, and nesting | §9.6 |
| I-13 | An auditable flag on memories and retrievals | §11 |
| I-14 | Status and visibility: standardize or leave to implementations (parked) | §3.2 |
| I-15 | Identity and scope granularity for federation | §9.4 |
| I-16 | Whether the tier assignments in §3.2 hold | §3 |

---

## Appendix A. Example header in JSON (interchange)

```json
{
  "identifier": "team/preferences/status-update-day",
  "title": "Status updates move to Friday",
  "type": "text/markdown",
  "tags": ["preference", "team-process"],
  "scope": ["team:platform"],
  "created_at": "2026-09-01T14:02:00Z",
  "version": { "value": 2, "comparator": "integer" },
  "updated_at": "2026-09-15T09:30:00Z",
  "valid_from": "2026-09-15T00:00:00Z",
  "checksum": "sha256:9f2c1e0b6d4a8f3e2b1c7d5a9e0f4b3c8d2a6e1f7b9c3d5e8a0f2b4c6d1e3a5",
  "provenance": [
    { "id": "user:jordan", "kind": "human", "role": "instructed", "at": "2026-09-15T09:28:00Z" },
    { "id": "agent:notes-assistant", "kind": "agent", "role": "author", "ai_usage": "full", "model": "example-model-1" },
    { "id": "user:sam", "kind": "human", "role": "approved", "at": "2026-09-15T09:30:00Z" }
  ],
  "evidence": [
    { "ref": "transcripts/2026-09-15-standup#turn-14" },
    { "ref": "team/preferences/status-update-day", "version": 1 }
  ],
  "links": [
    { "target": "team/preferences/status-update-day", "version": 1, "rel": "supersedes" }
  ],
  "body": "Status updates are due Fridays from Sep 15. They were due Tuesdays before that."
}
```

## Appendix B. The same memory as markdown with front matter (runtime projection)

```markdown
---
identifier: team/preferences/status-update-day
title: Status updates move to Friday
type: text/markdown
tags: [preference, team-process]
created_at: 2026-09-01T14:02:00Z
version: 2
provenance:
  - { id: user:jordan, kind: human, role: instructed }
  - { id: agent:notes-assistant, kind: agent, role: author }
---

Status updates are due Fridays from Sep 15. They were due Tuesdays
before that. Supersedes [[team/preferences/status-update-day@1]].
```

`scope`, `checksum`, `approved` provenance entries and the audit fields are omitted from the runtime projection (§7.2). They remain in the interchange form.

---

## Acknowledgements

Built from the proposals by Charles Packer (Letta), Gabe Goodhart and colleagues (IBM), Sruly Rosenblat and Ilan Strauss (AI Disclosures Project), Vasilije Markovic (Cognee), Misha Sulpovar (Context Nest), and Mila and Mozilla (AMS Card), and from the 2026-09-28 call with Gabe Goodhart, Sruly Rosenblat, Vasilije Markovic, Alex Hancock and Misha Sulpovar.

