# Open Memory Protocol: The Memory Object (Exchange and Runtime)

Editors' draft v0.5 (2026-11-06), restructured 2026-11-09. Same content, no normative change: the text is reordered into goals, the protocol, what is agreed, and everything else. Exchange and Runtime sub-thread, written with the Memory Model and Context (MM&C) overlap in mind. Not an adopted OMP standard.

## Part 0. Front matter and how to read this draft

The key words MUST, MUST NOT, SHOULD, SHOULD NOT, MAY and RECOMMENDED are to be read as in RFC 2119 and RFC 8174. Every normative statement in this draft is proposed: a MUST states what the editors propose the requirement should be once adopted, and does not claim the group has agreed to it.

Two marks appear in Parts 1 and 2, on sentences and table rows: everything is proposed by the editors unless marked [agreed], and a question the group has not settled is marked [open I-n] (or [open U-n] for a question raised without an issue number) and described in full once, in the register at 4.2 (the body carries the mark and at most one sentence stating the question). A mark at the end of a paragraph or list covers the whole paragraph or list; a mark inside a paragraph covers its sentence. Part 3 defines what [agreed] means and lists what carries it.

Part 1 states the goals; Part 2 is the specification; Part 3 is the floor the group stands on; Part 4 holds everything else (alternatives, open issues, deferred items, the discussion record with its attributions, sources and change history); the appendices are the examples. The map from v0.5 section numbers to this document is in 4.7.

## Part 1. Goals and scope

### 1.1 What the protocol standardizes

The protocol standardizes two things.

1. **An exchange format.** What metadata travels with a memory so that one system can export it and another can import it and represent it well. This serves portability and data ownership.
2. **Runtime plug-in points.** What an agent harness consumes at runtime, and where a memory system plugs in, so that memory systems and harnesses can be built and chosen independently.

Everything standardized MUST work down to a folder of memory files on one laptop and up to a multi-user, multi-scope deployment with access control.

### 1.2 Design goals

The design is judged against three goals.

1. **Adoption.** A folder of markdown memories, a database-backed store and a graph store can all conform with little work. Most metadata fields are optional, and the minimal profile (2.11) can be met by today's harnesses. Optional fields tend to go unimplemented, so the protocol SHOULD keep the number of optional fields that matter for interchange small.
2. **Auditability.** When a deployment needs it, every memory can be traced to one or more accountable humans (2.5.3) [agreed], its history can be verified, and its lifecycle events are recorded. These requirements sit in tiers (2.3) so that individual users are not forced to carry enterprise obligations. Full audit is a multi-user enterprise requirement, not a single-user one. [agreed]
3. **Room for innovation.** The protocol standardizes interfaces and the shape of data, not algorithms. What is left to implementations to compete on is listed in 4.4.

### 1.3 Non-goals

- This is a transfer format, not a storage format. The protocol says nothing about how a system stores, indexes or looks up memories.
- Markdown is neither required nor preferred, for storage or for the exported body; a folder of markdown memories conforms (2.11, minimal profile). [agreed]
- The size and semantic scope of a single memory (a fact, a document) are not fixed. [open I-2: the atomic unit]
- The recall function signature, ranking and retrieval algorithms are not standardized. [agreed]
- Federation merge and ranking logic is not standardized. [agreed]
- Change notification during a session is left to implementations (I-11, closed; 4.2.2).
- Third-party chains of trust for provenance are out of scope for now. [open I-22: trust and sanitization]

The full list of what is left to implementations is 4.4.

### 1.4 Scope of this document

This document specifies one memory as it is represented on export and import. The export/import manifest, used once per export or import, is a separate follow-up proposal. [agreed] The manifest fields Part 2 depends on are listed once, in 2.9.1; until the manifest proposal exists, 4.3 holds the working text.

## Part 2. The protocol

This part defines one memory as a system exports, imports and serves it: the object and its fields (2.1 to 2.4), what stands behind it (2.5, 2.6), how it changes (2.7), its two representations (2.8), how it travels between systems (2.9), how it reaches an agent (2.10) and what a deployment may claim (2.11).

### 2.1 The memory object

A memory is **metadata** plus a **body**. The metadata is a rigorous schema that can be rendered into any format that renders schemas (JSON, YAML front matter, a database row); it is for the system that manages the memory. The body is what is semantically relevant to the agent; its format is declared by `media_type` (2.4), and it is usually a string in a text format. This is a two-sided data contract: stable metadata that changes only through versioning or lifecycle events (2.7.3), and a free-form payload the protocol does not prescribe. The base object is the metadata plus a typed body, not a markdown file; 2.10.6 defines how a markdown-first loading profile relates to it. [agreed]

The body MAY be in any format with a valid MIME type; `media_type` declares which (2.4). Implementations need not process every format; non-text bodies such as image or audio are allowed but not required. [agreed] Whether a body can be a structured value rather than a string, and how a non-text body such as an image or audio is carried, is unsettled. [open I-17] Some sources need more than a media type: structured or relational sources and opaque documents such as PDFs are handled differently downstream, and whether an optional schema or source-type field is needed for them is unsettled. [open I-18]

The protocol does not fix the size or semantic scope of a memory. [open I-2]

A memory MAY be a **stub**: its body is a summary or pointer, and the full body has to be fetched before use. A stub carries `stub: true` so that an agent knows to fetch the full body if it needs it.

### 2.2 Profiles at a glance

Profiles let a deployment claim only what it implements. Two profiles set field requirements:

- **minimal**: the required fields, a body, and unknown fields preserved; reachable from a folder of markdown memories with no other metadata.
- **audit**: every memory traces to an accountable human (2.5.3), carries `checksum` and `version`, and keeps a verifiable history (2.7.3). Meant for multi-user deployments (1.2). Part 2 calls a system that claims it audit-grade.

Two further profiles set no field requirements: the markdown loading profile (2.10.6) and the federation binding (2.10.4). The checklists are 2.11. The profile construct itself is editors-added text the group has not discussed; 4.1 lists it.

### 2.3 Field tiers

Each field in 2.4 carries one tier:

| Tier | Meaning |
|---|---|
| **required** | Every conforming memory carries it |
| **audit-required** | Required in the audit profile (2.2, 2.11); optional otherwise |
| **ACL-required** | Required where access control applies; interchange only |
| **optional** | May be omitted in every profile |

Whether the tier assignments in 2.4 hold is unsettled. [open I-16] No profile names the ACL-required tier, so nothing in 2.11 checks it. [open U-7]

### 2.4 Field table

The table is the single definition of every standard field; a memory carries each field at the tier 2.3 defines, and 2.8 says which fields reach the agent.

| Field | Type | Tier | Definition |
|---|---|---|---|
| `identifier` | string | required | Identifies the memory within its origin system, and stays the same across all versions of that memory. Carries no required meaning. UUIDs are RECOMMENDED. MUST be unique among the memories in one export. Together with the manifest's `origin` (4.3), it is the memory's global key |
| `path` | string | optional | Where the memory sat in the origin store's hierarchy, for example a folder path. Kept separate from `identifier` because folder structure carries discovery and progressive-disclosure information. [open I-19: hierarchy beyond path] |
| `title` | string | optional | A human-readable label. May duplicate the body for fact-sized memories |
| `protocol_version` | string | optional | The version of this protocol the memory was written against. It lets a system bring memories at rest forward as the protocol changes, including when it exports from and imports to itself. Optional on the memory so a folder of markdown stays conformant; the manifest (4.3) is expected to require it. [agreed] An exporter MAY add it at export. [open I-26: name and format] |
| `media_type` | string | required | The media type of the body. MUST be a valid MIME type (for example `text/markdown`, `application/json`, `text/html`, `text/csv`, `application/xml`). A system SHOULD support `text/plain` and `text/markdown`, and MAY support any other valid MIME type. Not a semantic ontology. [agreed] |
| `stub` | boolean | optional | `true` when the body is a summary or pointer and the full body may be fetched for more details (2.1) |
| `tags` | list of strings | optional | Semantic tags. Free-form, or values drawn from a vocabulary declared elsewhere (for example a JSON-LD `@context` or schema.org). This is where a system records the kind of a memory (fact, preference, decision, observation) without the protocol requiring an ontology. Tags MAY cross into the runtime representation (2.8) |
| `scope` | list of strings | ACL-required | Scope tags that access policy attaches to. Set by the system, never by the agent. Interchange only (2.8). A scope tag is neither an access grant nor proof of ownership. Runtime access control is enforced by the serving system using interchange fields; the agent does not need to see them |
| `created_at` | ISO 8601 timestamp | required | When the system recorded the memory. Distinct from when the claim became true (`valid_from`) |
| `valid_from` | ISO 8601 timestamp | optional | When the claim became true in the world |
| `valid_until` | ISO 8601 timestamp | optional | When the claim stops being true. MAY be in the future, for example a temporary workaround to retry at a set time. [agreed] |
| `version` | opaque, with a declared comparator | audit-required | The revision of this memory. Its shape and comparator are in 2.7.2. [open I-4: form and comparator] |
| `updated_at` | ISO 8601 timestamp | optional | When this revision was written |
| `checksum` | string (`algorithm:hex`, for example `sha256:abcdefg...`) | audit-required | An integrity hash of the metadata-covered fields plus the body. [open U-1: body-only hash] |
| `provenance` | list of contributors (2.5.1) | optional; audit-required, with an accountable human | Everyone and everything that contributed. A missing `provenance` means the author is unknown (2.5.5) |
| `evidence` | list of references or strings | optional; audit-required when the memory is derived from other memories (2.5.4) | What the memory rests on, inside or outside the store (2.5.4). [open I-5] |
| `links` | list of edges | optional | References to other memories (2.6). [open I-5] |
| `weight` | float | optional | A relative ordering among memories from one `origin`. Not bounded, and with no prescribed mathematical meaning, so it is not a probability or a confidence. Values from different origins are not comparable. A memory MAY carry it; a receiving system MAY interpret `weight` however it wants. [agreed] |
| `body` | string | required | The content of the memory, in the format `media_type` declares. A string in this version. [open I-17: structured or non-text body] |

`status`, a lifecycle or visibility state inside a store, is parked and not a standard field; its description is in 4.3.2, and 2.8 shows where it would sit if kept. [open I-14]

Implementations MAY add fields. Unknown fields MUST be preserved on export and MUST NOT change the meaning of standard fields.

### 2.5 Provenance and evidence

#### 2.5.1 Contributor list

`provenance` is a list. Each entry names one contributor:

| Key | Tier | Meaning |
|---|---|---|
| `id` | required | An identifier for the contributor (a person, an agent, a system) |
| `kind` | required | `human`, `agent` or `system` |
| `contribution` | optional | What the contributor did, for example `authored`, `instructed`, `approved`, `edited`, `imported`, `verified`, `corrected`, `contradicted` |
| `ai_usage` | optional | How much AI was involved. Values to be aligned directly with EU AI Act terminology |
| `name` | optional | A name for the contributor, whether a human, an agent, a model or a system |
| `at` | optional | When this contributor acted |

Attribution is per revision: `provenance` records who contributed to a revision and in what sequence, not who wrote each line. An implementation that needs line-level attribution MAY derive it from the diffs between revisions. [agreed]

[open I-3: shape of provenance] [open I-25: line-level attribution field]

#### 2.5.2 Writers are contributors

Any process that writes a memory, including forget, consolidation and other maintenance agents, MUST appear in `provenance` like any other writer. What those agents do is not defined (4.4).

#### 2.5.3 Accountable human

A memory is auditable if it can be traced to one or more accountable humans. [agreed] In the audit profile (2.11) every memory MUST carry at least one `provenance` entry with `kind: human`, and SHOULD mark which human is accountable when several appear (for example the person who gave the instructions and the person who approved). Accountability is assigned, not a sign-off on each memory. For a consolidation or other maintenance agent the accountable human MAY be the operator who runs it. A store that cannot name one does not claim the audit profile. It is still a conforming store.

#### 2.5.4 Evidence

`evidence` records what a memory rests on: source material, transcript turns, other memories, or a person's statement. Each entry is a reference, or a plain string when the source is not addressable. A reference MAY point outside the store: a file, a URL, a record in a system of record, or a turn in a transcript. Implementations SHOULD distinguish how the memory relates to its evidence: observed, stated by a person, inferred by a model, or derived from other memories. Evidence records origin, not truth. A derived memory whose evidence is unavailable MUST say so rather than omit the field silently. Evidence that points outside the store MAY be excluded from an export; what happens then is 2.9.5. A memory SHOULD link to a system of record rather than copy from it.

[open I-5: exporting and linking transcripts] [open U-2: evidence entry shape]

#### 2.5.5 Unknown authorship

A store that does not know who wrote a memory (for example a folder of markdown files) MUST leave `provenance` out rather than fill it with guesses. A receiving system MUST read a missing `provenance` as "author unknown". In particular, it MUST NOT read it as the user's own words. Such memories conform to the minimal profile but cannot claim the audit profile.

#### 2.5.6 Accuracy and confidence

The protocol defines no portable accuracy or confidence score. Accuracy is conveyed through provenance and evidence, which already travel: who checked a memory appears as a contributor with `contribution: verified`, `corrected` or `contradicted` plus `at` (humans, agents and evaluators such as an LLM judge, each marked by `kind`); what the check rests on is evidence (the source, the transcript or the later memory that confirmed or contradicted it); receivers compute their own confidence from those records with their own algorithm (4.4). An implementation MAY carry its own score as an extension field. It SHOULD name the system that produced the score, so that a receiver does not mistake it for a portable value. Relative ordering within one `origin` travels as `weight` (2.4).

[open I-20: confidence per evidence entry] [open I-23: contradictions and consent]

### 2.6 Links and lineage

Evidence and lineage form a graph whose nodes are memories and sources. How the graph is built, stored and traversed is left to the implementation. An audit-grade system MUST be able to reconstruct the full chain behind a memory; other systems MAY leave nodes unconnected. [agreed] The protocol does not require full provenance on every object; the minimum lineage an audit-grade system keeps is unsettled [open I-6: minimum depth]. Consolidation SHOULD name all its inputs.

Memories MAY reference each other, by inline links in the body (for example wiki syntax `[[identifier]]`, which works in any format that carries text) or by typed edges in the metadata (`links: [{target, rel}]`, with `rel` values such as `derived_from`, `supersedes`, `relates_to`). The two are not exclusive. Links and evidence are separate fields: evidence answers why to believe a memory and may point outside the store; links answer how memories relate to each other. [open I-5: link target; typed edges in core] [open I-23: a contradicts rel] Unresolvable targets: 2.9.5.

### 2.7 Versioning and lifecycle

#### 2.7.1 Stores and snapshots

Both kinds of store are supported: those that change memories in place and those that never change a memory and write superseding revisions instead. Neither is required (2.7.3 states the audit profile's rule).

By default an export is a snapshot as of the manifest's `exported_at` (4.3). History travels only when the export declares it (audit profile, 2.11; federation, 2.10.4).

#### 2.7.2 Version

When present, the format of `version` is left to the implementation (a sequence number, a semantic version or other). The implementation MUST declare a comparator. The comparator MAY report two versions as **incomparable**, for example revisions on different branches where both are valid; versions need not be totally ordered. Wall-clock time SHOULD NOT be the comparator. `identifier` stays the same across versions (2.4). [open I-4: form and comparator] [open U-6: comparator location, history export]

#### 2.7.3 Immutable revisions

A change SHOULD create a new revision that supersedes the old one, rather than overwrite it in place, so history can be read as of a point in time. This is RECOMMENDED, not required. In the audit profile (2.11), immutable revisions and a verifiable history (for example a hash chain) are REQUIRED. [open U-5: audit REQUIRED status]

Even where the body never changes, a system MAY update lifecycle metadata such as `valid_until`, supersession links and forget markers.

#### 2.7.4 Invalidation and supersession

A memory stops applying at its `valid_until` without being deleted. A newer revision or another memory MAY supersede it with a `supersedes` link (2.6). Current reads SHOULD exclude memories past `valid_until` and superseded memories. Historical reads SHOULD be explicit.

#### 2.7.5 Delete

A conforming store MAY delete a memory. A delete SHOULD leave an audit record (who, when, why) with no content. A delete does not by itself stop the content from coming back on a later import (2.7.6). What a delete means for memories derived from the deleted one is not settled. [open I-7: core or audit]

#### 2.7.6 Forget, tombstones and anti-resurrection

A **forget** erases a memory's content on purpose, for example to honor an erasure request, while its history stays verifiable. A **tombstone** is the record a forget leaves behind. This section states the outcomes a conforming store delivers; how a store achieves them is left to implementations (4.4).

- After a forget, the content of every revision it covers MUST NOT be retrievable from the store or from its exports.
- A store that offers a verifiable history (2.7.3) MUST still verify after a forget.
- A forget MUST leave a tombstone that records when it happened, who did it and why. The tombstone MUST NOT contain the forgotten content.
- **Anti-resurrection.** A receiving system MUST NOT restore forgotten content from an older archive or a pre-forget copy.

Tombstones travel with exports (2.9) so that receivers can tell. Recognizing a re-imported memory needs `origin` plus `identifier`; showing that a copy predates the forget needs `exported_at` (both from the manifest, 4.3). [open I-7: core or audit] [open U-10: standard tombstone fields]

### 2.8 Representations: interchange and runtime

There are two representations of the same memory. [agreed]

- **Interchange** (export and import, migration): the full metadata, including operational fields a receiving system needs to integrate the memory.
- **Runtime** (what an agent sees): a projection of the interchange form. It omits fields that would add noise to the agent's context or reveal how the store is organized. Metadata the agent does not need can make it perform worse.

Which fields reach the agent is left to each memory system. The table below is guidance, not a requirement. [open U-12: table normativity]

| Field | Interchange | Runtime |
|---|---|---|
| `identifier`, `media_type`, `body` | yes | yes |
| `stub` | yes | yes, when true |
| `title`, `tags`, `created_at` | yes | yes |
| `path` | yes | MAY be shown, for progressive disclosure |
| `protocol_version`, `version`, `updated_at`, `valid_from`, `valid_until`, `weight` | yes | when the implementation needs them |
| `provenance` | yes | a summary MAY be shown (for example the author) |
| `evidence`, `links` | yes | MAY be shown |
| `checksum` | yes | no |
| `scope` | yes | no |
| `status` (parked, 4.3.2) | yes, if kept | no |
| tombstones, audit records | yes | no |

Runtime access control is enforced by the serving system using interchange fields (2.4, `scope` row).

### 2.9 Exchange

#### 2.9.1 Manifest dependency

Part 2 depends on these manifest fields (working text in 4.3): `origin`, which with `identifier` forms a memory's global key (2.4), identifies a re-imported memory (2.7.6) and is the party whose claims imported provenance and evidence are (2.9.7); `exported_at`, the time the export is as of (2.7.1), which shows whether a copy predates a forget (2.7.6); `protocol_version` and the profiles the export follows (2.11); the body formats present (2.4); whether the export is a complete snapshot, a selection or a full history (2.7.1); and the transfer intent (2.9.2). Where the version comparator is declared is [open U-6: comparator location, history export]. Absence from a partial export MUST NOT be read as deletion.

#### 2.9.2 Transfer intent

An export MUST declare its intent: **copy**, the source keeps its memories; **move**, the source deletes its memories only after a durable, conforming import on the receiving side; **federation**, no transfer, the memory is read where it resides (2.10.4). A receiving system that assigns its own identifiers MUST keep the origin-to-local mapping. Whether an imported memory keeps its origin `identifier` or receives a new one with a recorded mapping is [open I-8: keep or reassign identifier]. Whether intent is a core requirement, and where it lives once the manifest proposal exists, is [open U-3: intent as core requirement].

#### 2.9.3 Fidelity

The receiving side SHOULD be able to check that it received the same memory with the same history. In the audit profile, it MUST be able to, using `checksum` (2.4) and the verifiable history (2.7.3).

#### 2.9.4 Receipts

An import SHOULD produce a receipt that lists, per memory, whether it was accepted, transformed, omitted or rejected, with reasons and any identifier mappings (2.9.2). Retries MUST NOT duplicate memories.

#### 2.9.5 Dangling references

A reference (a link, 2.6, or an evidence entry, 2.5.4) is dangling when the receiver cannot resolve it: the target was left out of a partial export or deleted, lives outside the store (a session log, a file, a system of record), or is outside the reader's scope, so a reference that resolves for one person dangles for another. A system MUST be able to hold dangling references. It MUST keep them and mark them as dangling rather than drop them silently. An import MUST NOT fail because of a dangling reference. A system MAY try to resolve dangling references during import or later, including by asking a person.

#### 2.9.6 Credentials

Credentials (passwords, API keys, tokens) are not memory and MUST NOT be exported as memory.

#### 2.9.7 Trust on import

Receivers SHOULD treat imported provenance and evidence as claims made by the exporting `origin`, not as facts. `checksum` and a verifiable history (2.7.3) let a receiver check integrity, not truth. Receivers MAY review or sanitize imported memories before agents rely on them [open I-22: trust and sanitization].

### 2.10 Runtime binding

#### 2.10.1 What crosses the binding

At runtime, memory reaches an agent in three ways:

1. **File access**: the agent reads memory files with shell or file tools.
2. **Tools**: the agent calls explicit remember and recall tools exposed by a memory server.
3. **Hooks**: a supervisor observes or decorates the conversation without the agent knowing, deciding what to add to a session and what to store.

The protocol standardizes the shape of the memory objects that cross these surfaces, the runtime representation (2.8), not a new transport. Which binding hosts them, MCP, hooks, CLI, or several, is [open I-10: MCP, hooks or CLI].

#### 2.10.2 Recall

The protocol MUST NOT fix a signature for recall. Implementations provide their own recall and their own guidance on using it. The protocol defines what recall returns, memory objects in the runtime representation (2.8), not how it is called. [agreed]

Whether federation needs any standard recall is [open I-15: standard recall for federation].

#### 2.10.3 Writes

A write needs, at minimum, an author, a time, and whether it creates a memory or revises an existing one (2.7.2).

#### 2.10.4 Federation

When several memory servers are connected, a federation layer MAY sit between them and the agent and present one unified memory. How it merges results and combines scopes is left to the implementation. Identity MUST pass through the federation layer to each server. [agreed]

Identity and scope granularity for federation are [open I-15: identity and scope granularity].

The federation endpoint binding is an endpoint set of upload, search, read, delete and a required capability endpoint, carrying memory objects in the runtime representation (2.8); each server declares its capabilities. Whether a standard search endpoint is compatible with the recall rule of 2.10.2 is [open U-9: search endpoint vs recall].

#### 2.10.5 Multiple memories

Whether a server returns several memories compiled into one payload or as separate objects, and whether memories can nest, is [open I-12: compiled or separate, nesting]. If they are returned separately, each carries its own runtime metadata.

#### 2.10.6 Markdown loading profile

The markdown loading profile is the directory and loading contract of a root `MEMORY.md`: deeper files deferred, deferred memory surfaced one level down, and selective reads. Metadata is carried as front matter or in a sidecar, and `path` (2.4) records each file's place. When a projection to this profile drops fields, it MUST declare the loss. Hierarchy metadata beyond `path` is [open I-19: hierarchy beyond path].

### 2.11 Conformance profiles

Profiles are introduced in 2.2; this section lists what each one requires, each item pointing to the section that states the rule. An export's manifest declares the profiles it follows (4.3). Whether "markdown loading" and "federation binding" remain declarable profile names is handed to the manifest proposal (4.3).

**Minimal profile.** The required fields of 2.4 (`identifier`, `media_type`, `created_at`), a body, and an export that preserves unknown fields (2.4). Reachable from a folder of markdown memories with no other metadata. Provenance and versioning are not required (2.5.5, 2.7.2). Whether the exchange rules of 2.9 (transfer intent, dangling references) belong here or only to the audit profile is [open U-13: intent and dangling membership].

**Markdown loading profile.** The loading contract of 2.10.6: a root `MEMORY.md`, deferred deeper files surfaced one level down, selective reads, metadata in front matter or a sidecar, `path` on each file (2.4), and a declared loss for every field the projection drops.

**Federation binding.** The endpoint set of 2.10.4 with a capability endpoint, each server declaring its capabilities; memory objects cross it in the runtime representation (2.8); identity passes through to each server (2.10.4).

**Audit profile.** Everything in the minimal profile, plus:

- `provenance` on every memory, with an accountable human (2.5.3);
- `checksum` and `version` on every memory (2.4);
- immutable revisions with a verifiable history (2.7.3);
- evidence on derived memories (2.5.4);
- recorded lifecycle events, including deletes (2.7.5);
- dangling references kept and marked (2.9.5); when a system is evaluated against this profile, its dangling references are noted;
- forget, tombstones and anti-resurrection (2.7.6) [open I-7: core or audit].

## Part 3. What the group has agreed

In v0.5, "[agreed]" means "at least two participants explicitly agreed on a call and nobody objected." Agreed is not adopted: nothing here is an OMP standard, and every item stays open to the group's later decision. The list below states each agreed decision, the meeting it was agreed at, and the section of Part 2 (or Part 1) where it now sits as the floor under the editors' proposals. Where a decision left part of a question open, the last column names the remainder by issue id. Two labelled sub-lists hold items that v0.5 records as decided without an [agreed] tag in the body, so that nothing untagged is quietly upgraded.

| Topic | Decision | Meeting | Where | Open remainder |
|---|---|---|---|---|
| Goals and scope | Full audit is a multi-user enterprise requirement, not a single-user one; audit obligations sit in tiers so individual users do not carry them. | 2026-09-28 call (inferred; v0.5 cites no meeting) | 1.2, 2.3 | |
| Goals and scope | The base object is metadata plus a typed body, not a markdown file, and markdown is not preferred. Closes I-1. | 2026-10-14 | 1.3, 2.1 | |
| Goals and scope | This document is the individual memory spec; the export/import manifest is a follow-up proposal. | 2026-11-06 | 1.4, 2.9.1 | U-8 (who owns the manifest proposal); working text in 4.3 |
| Memory object | A memory is metadata plus a body: the metadata is a schema for the managing system, the body is what is semantically relevant to the agent. | 2026-09-28 call | 2.1 | |
| Memory object | The body MAY be in any format with a valid MIME type, and `media_type` declares which. | 2026-10-14 and 2026-11-06 | 2.1, 2.4 | I-17 (structured and non-text bodies) |
| Fields | `media_type` is required and MUST be a valid MIME type; a system SHOULD support `text/plain` and `text/markdown` and MAY support any other valid MIME type. | 2026-11-06 | 2.4 | |
| Fields | `protocol_version` is optional on the memory; the manifest proposal is expected to require it. | 2026-11-06 | 2.4 | I-26 (name and format) |
| Fields | `valid_until` replaces `invalidated_at` and MAY be a future date. | 2026-10-14 | 2.4, 2.7.4 | |
| Fields | `weight` is an optional, unbounded float with no prescribed mathematical meaning that orders memories from one `origin` relative to each other. | 2026-11-06 | 2.4, 2.5.6 | |
| Provenance | Attribution is per revision: `provenance` records who contributed to a revision and in what sequence; line-level attribution MAY be derived from diffs; `at` stays as written. | 2026-11-06 | 2.5.1 | I-25 (a field for line-level attribution) |
| Provenance | A memory is auditable if it can be traced to one or more accountable humans; in the audit profile every memory MUST carry a `provenance` entry with `kind: human`. | 2026-09-28 call (inferred; v0.5 cites no meeting) | 2.5.3, 1.2 | I-3 (several accountable humans); the SHOULD and MAY in 2.5.3 are editors' text (4.1.5) |
| Links | Evidence and lineage form a graph of memories and sources; an audit-grade system MUST be able to reconstruct the full chain behind a memory; other systems MAY leave nodes unconnected. | 2026-09-28 call | 2.6 | I-6 (minimum lineage depth) |
| Representations | Interchange and runtime are two representations of one memory; interchange carries the full metadata and runtime is a projection of it. | 2026-09-28 call | 2.8 | |
| Runtime | The protocol MUST NOT fix a signature for recall; it defines what recall returns (memory objects in the runtime representation), not how it is called. Recall signature, ranking and retrieval algorithms are out of scope. | 2026-09-28 call | 2.10.2, 1.3, 4.4 | I-15 (standard recall for federation) |
| Runtime | A federation layer MAY sit between several memory servers and the agent and present one unified memory; identity MUST pass through it to each server; merge and ranking logic is out of scope. | 2026-09-28 call | 2.10.4, 1.3, 4.4 | I-15 (identity and scope granularity) |

**Recorded as decided, group to confirm.** v0.5 records these in its changelogs, as read-backs, or in the issue list, while the body text that carries them is not tagged [agreed].

- `version` is audit-required, not required, and stores that change memories in place and stores that never change them are both supported (2026-10-14, changelog; the issue list calls I-4 "mostly settled" while the field row and the store sentence are tagged proposed). Remainder: the form of `version` and its comparator, including incomparable versions (I-4). Where: 2.4, 2.7.1, 2.7.2.
- `created_at` records when the system learned something; `valid_from` records when it became true (2026-10-14, changelog; the two field rows are tagged "no objection" and proposed). Where: 2.4, 2.7.4.
- The protocol defines no portable accuracy or confidence score; accuracy travels as provenance and evidence, plus the agreed `weight` (settled 2026-11-06 in the issue list, I-20, while the section heading still said proposed). Remainder: an optional confidence on each evidence entry (I-20 residual). Where: 2.5.6.
- Tier assignments: `version` (audit-required) and `updated_at` (optional) were read back on 2026-10-14; `protocol_version` and `weight` (both optional) were set on 2026-11-06; every other tier is the editors' (I-16). Where: 2.3, 2.4.
- "Header" is now "metadata" (2026-10-14, changelog). Where: 2.1.
- `type` is now `media_type`, provenance `role` is now `contribution`, and `model` is now `name` (closed in review of PR #13, not on a call). Where: 2.4, 2.5.1.

**Closed by review, not agreed on a call.**

- I-9: replaced by the unknown-authorship rule. Where: 2.5.5; 4.2.2.
- I-11: left to implementations unless reopened. Where: 1.3; 4.2.2.

## Part 4. Everything else to take into account

Part 4 holds what Parts 1 to 3 deliberately leave out: the proposals that did not make it into the text, the questions still open, the items set aside or handed to another document, and the list of what the protocol leaves to implementations.

### 4.1 Proposed, not agreed: alternatives and editors-added text

#### 4.1.1 A thin core with semantic conventions (I-21)

Ilan proposes in review (PR #13) to follow OpenTelemetry and keep the protocol core minimal. A memory would be:

```json
{ "identifier": "MEMORY.md", "media_type": "text/markdown", "body": "The user prefers concise answers.", "attributes": {} }
```

Every other field would become an attribute defined in **semantic conventions**. The conventions would be debated and versioned on their own schedule: the manifest declares `semantic_conventions_version` separately from `protocol_version` (4.3). Under this model the tiers of 2.3 and the profiles of 2.2 and 2.11 would become named sets of conventions. This was not reached on 2026-10-14 and is not adopted. The field table (2.4) stands until the group decides.

#### 4.1.2 Cognee's further fields (PR #16)

Cognee's PR #16 proposes `subject`, `kind`, `accuracy`, an `origin` qualifier, `invalidated_by` (a reverse pointer on the superseded memory, the counterpart of the `supersedes` link in 2.7.4), a list shape for `evidence`, and a second hash of the body alone for deduplication (U-1 in 4.2). They are reflected where they overlap (2.4 `checksum` row via U-1, 2.5.4, 2.5.6, 2.7.4, 4.3) and are otherwise left for review in PR #16.

#### 4.1.3 Alternatives to 2.5.6

- **Vouching** (Sruly, 10-14): instead of a carried accuracy score, a model or a person vouches for a memory.
- **Confidence per evidence entry** (review, 10-15): an optional confidence on each evidence entry instead of a record-level score, portable only together with who or what produced it, how and when. It would extend 2.5.4, not the field table. This is the open residual of I-20 (4.2).

#### 4.1.4 Editors' resolution for I-7

Forget, tombstones and anti-resurrection (2.7.6) belong to the audit profile (2.11), not the core. The group has not decided (I-7 in 4.2).

#### 4.1.5 Text the editors added without discussion, by section

Profiles as a construct (2.2, 2.11) and the names "minimal" and "audit" are editors-added, as are the "markdown loading profile" (2.10.6) and "federation binding" (2.10.4) as named profiles; the thin core (4.1.1) would replace them with convention sets. The following sentences have the same status:

- 2.3: every field tier in 2.4 except `version`, `updated_at`, `protocol_version` and `weight` (I-16 in 4.2).
- 2.4: the body row, which restates the body's place in the object and in the minimal profile; the key tiers of the contributor list in 2.5.1.
- 2.5.2: writers are contributors, maintenance agents included.
- 2.5.3: the accountable human for a maintenance agent MAY be the operator who runs it (from review).
- 2.5.4: a derived memory whose evidence is unavailable MUST say so (from Cognee §3.2).
- 2.7.3: immutable revisions with a verifiable history REQUIRED in the audit profile (U-5 in 4.2).
- 2.9.2: a receiving system that assigns its own identifiers MUST keep the origin-to-local mapping (from Cognee §3.1).
- 2.9.6: credentials are not memory and MUST NOT be exported as memory (from Cognee §3.3).
- 2.4 (`protocol_version` row): the clause "an exporter MAY add it at export" is the editors'; the agreed part of that row is the optional tier and the manifest's expected requirement.
- 2.11: the markdown loading profile and the federation binding listed as profiles with checklists.
- Deleted from the body, recorded here: the v0.5 opening sentence of the provenance chapter, "Provenance and evidence are the protocol's main tools for answering who stands behind a memory and why to believe it. Trust and accuracy build on them."

### 4.2 Open issues register

This register is the single owner of every issue's full description; the body carries the mark and at most a one-sentence statement of the question. U-numbers are provisional until the group assigns I-numbers.

#### 4.2.1 Open

| # | Issue | Where in Part 2 |
|---|---|---|
| I-2 | The atomic unit. Three views: a memory is the smallest semantic unit that carries meaning and can be evaluated true or false (Cognee, call); memories are documents with titles and authors, as in document stores (CN; Packer); a single claim is the unit, carrying its provenance, a confidence estimate, its versions and what it superseded (the knowledge object: arXiv 2601.15313, Appendix A; arXiv 2603.15994; arXiv 2603.17781; SSRN 10.2139/ssrn.5812343). The metadata of 2.4 is written to work for all three. Deferred 10-14 (4.3) | 1.3, 2.1 |
| I-3 | The shape of provenance: whether `contribution` and `ai_usage` are core, the EU AI Act terms for `ai_usage`, and how to record several accountable humans | 2.5.1, 2.5.3 |
| I-4 | Versioning: the form of `version` and its comparator, including incomparable versions. Mostly settled 10-14: audit-required, and in-place updates allowed (4.2.2); the form and the comparator remain. See U-6 for where the comparator is declared | 2.4, 2.7.2 |
| I-5 | Links: inline, metadata edges, or both; what a link targets (an identifier, or an identifier at a version); whether edges are typed in the core; how transcripts are exported or linked to. Appendix A pre-decides the edge shape (U-2) | 2.5.4, 2.6 |
| I-6 | Lineage depth required for audit: n hops back, or the full chain. The sentence in 2.6 marked agreed says an audit-grade system MUST be able to reconstruct the full chain, while the 2026-09-28 call left how the graph is built, stored and traversed to the implementation and v0.5 kept the minimum depth open | 2.6 |
| I-7 | Tombstones, anti-resurrection and delete of derived memories: core or audit profile, and what a delete means for memories derived from the deleted one. The editors propose audit (4.1.4) | 2.7.5, 2.7.6, 2.11 |
| I-8 | Identity on import: keep the origin `identifier`, or assign a new one with a recorded mapping. IBM's draft treats a memory as valid in one system at a time, with an import creating a new memory in the receiving system; Cognee's draft keeps the origin identity across copies. With `origin` in the manifest (4.3), the origin key survives either way. U-14 depends on this | 2.9.2 |
| I-10 | Runtime binding: MCP, hooks, CLI, or several. MCP was proposed as the home for the runtime binding: tools for remember and recall, interceptors for hooks, and file access as a tool (IBM; call). It is not agreed. Some implementers find hooks more controllable than MCP tools, and some find a CLI more reliable for retrieval isolation (call). SEP-2640 (Skills over MCP) was suggested as a way to get progressive disclosure over MCP without a file system (AIDP, thread) | 2.10.1 |
| I-12 | Compiled vs separate memories at runtime, and nesting | 2.10.5 |
| I-13 | An auditable flag on memories and retrievals: the protocol may define the flag, not the log | 4.4 |
| I-14 | `status` and visibility: standardize or leave to implementations. Parked, row in 4.3 | 4.3 |
| I-15 | Identity and scope granularity for federation, and whether federation needs any standard recall (review). See U-9 and U-11 | 2.10.2, 2.10.4 |
| I-16 | Whether the tier assignments in 2.4 hold | 2.3 |
| I-17 | Whether a body can be a structured value rather than a string (review), and how a non-text body such as image or audio is carried (11-06) | 2.1, 2.4 body row |
| I-18 | An optional schema or source-type field for structured or relational sources and opaque documents such as PDFs; whether a query-backed memory is the query output or its source data (10-14) | 2.1 |
| I-19 | Folder taxonomy and other hierarchy metadata beyond `path` (10-14) | 2.4 path row, 2.10.6 |
| I-20 (residual) | Confidence on evidence entries, the variant from review (10-15) described in 4.1.3; the main question is settled (4.2.2) | 2.5.6 |
| I-21 | A thin core with separately versioned semantic conventions (review). Full proposal in 4.1.1 | 4.1 |
| I-22 | Trust and sanitization of imported memories | 2.9.7 |
| I-23 | Use cases not yet covered (#use-cases list): contradictions kept and flagged rather than resolved (for example a `contradicts` link rel, or `contribution: contradicted` per 2.5.6), consent to hand a memory over, and consent to learn from a memory. Note: 2.5.6 uses `contribution: contradicted`, a value the `contribution` list in 2.5.1 does not name | 2.5.6, 2.6 |
| I-25 | Whether line-level attribution needs an optional field, or stays derived from diffs between revisions (11-06) | 2.5.1 |
| I-26 | The name of the version field, `protocol_version` or `omp_version`, and its format, for example date-based to match MCP's `MCP-Protocol-Version` (11-06) | 2.4 protocol_version row |

#### 4.2.2 Resolved

| # | Issue | Where in Part 2 |
|---|---|---|
| I-1 | ~~Markdown as the common body format vs the base object~~. Settled 10-14: the base object is metadata plus a typed body, and markdown is not preferred | 1.3 |
| I-4 (main) | ~~Whether `version` is required, and whether in-place updates are allowed~~. Mostly settled 10-14: audit-required, in-place allowed. The remainder stays open above; Part 3 lists the decision as recorded, not tagged | 2.4, 2.7.2 |
| I-9 | ~~How an export declares inferred provenance~~. Replaced by 2.5.5 (review): absent provenance means unknown | 2.5.5 |
| I-11 | ~~Change notification during a session~~: how a harness learns that a memory it already loaded has changed (for example through MCP resource subscriptions). Left to implementations (review); closed unless the group reopens it | 1.3 |
| I-20 (main) | ~~Accuracy and confidence as a standard field~~. Settled 11-06: provenance and evidence carry accuracy, plus an optional `weight` for relative ordering within one `origin`. Part 3 asks the group to confirm, since only `weight` carried an agreed tag in v0.5. The residual stays open above | 2.5.6 |

I-24: the number is not used in v0.5 (the sequence jumps from I-23 to I-25, and the changelog records "new open issues I-25 and I-26"); check the PR #13 and PR #16 history for a lost issue before assigning it.

#### 4.2.3 Untracked questions

| # | Question | Where in Part 2 |
|---|---|---|
| U-1 | A second hash of the body alone, for deduplication (Cognee, PR #16): tagged open in v0.5's checksum row with no issue number | 2.4 checksum row |
| U-2 | The shape of an evidence entry and of a link edge. `evidence` is "a list of references or strings" and the keys `ref`, `relation` and `dangling` that Appendix A uses are never defined; the link edge `{target, version, rel}` in Appendix A pre-decides what I-5 leaves open. Also undefined is how a derived memory "says so" when its evidence is unavailable (2.5.4), given that evidence pointing outside the store MAY be excluded from an export while the audit profile requires evidence on derived memories | 2.5.4, 2.6, Appendix A |
| U-3 | Whether an export MUST declare a transfer intent at all, and where the declaration lives once the manifest proposal exists (4.3); v0.5 tagged the section open but tracked only I-8 there | 2.9.2 |
| U-4 | The rename `role` to `contribution`: recorded as done in the changelog (review) but tagged open in v0.5's key table | 2.5.1 |
| U-5 | Immutable revisions and a verifiable history REQUIRED in the audit profile: editors-only text in a section v0.5 tagged open, and I-4 does not cover the audit requirement | 2.7.3, 2.11 |
| U-6 | Where the version comparator is declared: in the manifest (static per system version, 4.3), by "the implementation" (2.7.2), or on each memory as Appendix A does (`"version": { "value": 2, "comparator": "integer" }`, while Appendix B carries the scalar `version: 2`). Also how several revisions of one `identifier` are serialized in a full-history export against the rule that `identifier` MUST be unique among the memories in one export | 2.7.2, 2.4 identifier row, Appendix A, Appendix B |
| U-7 | The ACL-required tier maps to no profile: 2.11 defines minimal and audit, and no profile in which ACL-required fields are required | 2.3 |
| U-8 | The manifest proposal: its content, author and timeline are unassigned (4.3) | 4.3 |
| U-9 | The federation binding's endpoint set includes `search` while 2.10.2 says the protocol MUST NOT fix a signature for recall; I-15 brushes this without owning it | 2.10.4 |
| U-10 | Which tombstone fields are standard (a tombstone records when, who and why) and which belong to the implementation's format: 4.4 defers to "the fields named in 2.7.6", which names no field keys | 2.7.6, 4.4 |
| U-11 | How `scope` being "set by the system, never by the agent" is enforced (no keyword, no rule), and how scopes combine under federation when `scope` is interchange-only and federation carries the runtime representation | 2.4 scope row, 2.10.4 |
| U-12 | Whether the placement table in 2.8 is normative at all ("guidance, not a requirement") while Appendix B relies on it to drop the audit fields | 2.8, Appendix B |
| U-13 | Whether transfer intent (2.9.2) and the dangling-reference rules (2.9.5) belong to the minimal profile or only to the audit profile; 2.11 lists dangling references under audit and intent under neither | 2.11 |
| U-14 | "Retries MUST NOT duplicate memories" (2.9.4) needs `origin` plus `identifier` identity, which I-8 leaves open and the manifest text in 4.3 is being replaced | 2.9.4 |

### 4.3 Deferred, parked and handed off

#### 4.3.1 Handed to the manifest proposal (11-06)

This document is the individual memory spec; a follow-up proposal defines the manifest used once per export or import. That proposal covers attributes that are static for a given system version (for example supported MIME types, semantic tags and the version comparator), attributes that vary per transaction, and self-to-self migrations, when a system moves its own data between versions. It MUST declare the MIME types the exporting and importing systems support, it is expected to require `protocol_version`, and it MAY describe what a system's `weight` means. Until it exists, the v0.5 working text stands:

Every export SHOULD begin with a manifest that declares:

- `protocol_version`, and the profiles the export follows (2.11);
- `origin`: an identifier generated once per store. `origin` plus `identifier` is the global key of a memory (review; Cognee PR #16). Without it, two people who each export a `MEMORY.md` produce colliding identifiers;
- `exported_at`: the time the export is as of. It orders exports, and shows that a copy predates a forget (2.7.6) (review);
- the body formats present;
- whether it is a complete snapshot, a selection, or a full history (including memories no longer valid, for example for forensic review (10-14));
- any required extensions (Cognee §3.6).

The rule that absence from a partial export is not deletion stays in 2.9.1 and depends on the snapshot-or-selection declaration above. The thin-core proposal (4.1.1) would add `semantic_conventions_version` beside `protocol_version`. Appendix A of v0.5 illustrated the manifest as:

```json
{
  "protocol_version": "0.5",
  "profiles": ["minimal", "audit"],
  "origin": "store:6f1c2a9e-4b7d-4e2a-9c1f-3d8e5a7b0c42",
  "exported_at": "2026-10-14T18:00:00Z",
  "selection": "snapshot",
  "intent": "copy",
  "media_types": ["text/markdown"]
}
```

In v0.5 the "markdown loading profile" (2.10.6) and the "federation binding" (2.10.4) were declarable profile names, since an export's manifest declares its profiles; the manifest proposal must say whether they stay so. Author and timeline of the proposal are unassigned [open U-8].

#### 4.3.2 Parked

- The `status` field [open I-14]: string, optional; lifecycle or visibility state inside a store, for example draft, published; possibly implementation-specific; if kept, interchange only (call; CN). The placement table of v0.5 showed it as "yes, if kept" for interchange and "no" for runtime.

#### 4.3.3 Deferred (10-14)

- The atomic unit, the semantic scope of a single memory (I-2; the three views are in 4.2.1).

#### 4.3.4 Left for review in PR #16

- Cognee's fields that do not overlap the field table (list in 4.1.2).

#### 4.3.5 Out of scope for now (10-14)

- A third-party chain of trust for provenance. Sanitization of imported memories is I-22 (2.9.7).

#### 4.3.6 Raised, no issue number

- Immediate removal of wrongly stored content, whatever the retention rules, for example classified information stored by mistake: something the spec should make implementable, though not a requirement for every store (Wes, 10-14). The outcomes a forget delivers are in 2.7.6.

### 4.4 Out of scope: left to implementations

Left to implementations, so that they can compete and improve on them:

- Storage, indexing, lookup, embeddings and internal mutation (all drafts; 10-14). In particular, markdown is not required as a storage format.
- The semantic scope of a single memory, for now (10-14; I-2).
- The recall function signature, ranking and retrieval algorithms [agreed].
- Confidence, accuracy and decay scoring, and how they weigh recency (10-14; 2.5.6).
- Federation merge and ranking logic (2.10.4) [agreed].
- Memory-maintenance agents (forget, consolidation, "dream" agents) and their algorithms. Their writes still carry provenance (2.5.2).
- Forget mechanics: how content is erased, what a store keeps so its history still verifies, and the tombstone format beyond the fields named in 2.7.6 [open U-10].
- Retrieval isolation, such as limits on graph traversal depth.
- Audit-log storage and delivery. The protocol may define a flag saying whether a memory or a retrieval is auditable [open I-13], but not the log.
- Access-control systems. The protocol carries `scope` tags that access policy attaches to, but does not define the policy language (IBM; CN).
- Third-party chains of trust for provenance, and how imported memories are sanitized (2.9.7) [open I-22].

### 4.5 Discussion record: rationale and attributions by section

This section keeps every "who said what, when" and every source-draft citation that Parts 1 and 2 shed, grouped under the section the text now lives in, so that a participant can verify their position was recorded. Only the facts of the discussion are kept; the rules themselves are stated once, in the section named.

**Legend.** "call" = the 2026-09-28 exchange-and-runtime call. "10-14" and "11-06" = the 2026-10-14 and 2026-11-06 technical working meetings. "10-15" = a review comment of that date. "review" = a comment on PR #13. "PR #16" = Cognee's header proposals. "PR #12" = the round-trip field report. "thread" = the #exchange-and-runtime Discord thread. Source drafts, in `early-draft-specs/`: Packer (Letta, v0.2), IBM (v0.1), AIDP (AIDP / FMP), Cognee (v0.1; "Cognee §x" points into it), CN (Context Nest v0.1; "CN §x" points into it), AMS (the AMS Card, Mila / Mozilla). People are named as v0.5 names them: first name plus meeting code.

**Part 1 (1.1 to 1.4).**
- The two standardized things, the exchange format and the runtime plug-in points, and the design requirement that everything standardized work from a folder of files on one laptop up to a multi-user, multi-scope deployment with access control: 10-14. The goals-and-scope section was itself put forward on 10-14.
- Non-goals: a transfer format, not a storage format; markdown not required for storage or for the exported body; the semantic scope of one memory out of scope for now: 10-14.
- "Much agent memory today is markdown, and this design keeps it conformant without making it the standard": 10-14.
- Optional fields tend to go unimplemented, so the number of optional fields that matter for interchange is kept small: call.
- That this document is the individual memory spec and the manifest moves to a follow-up proposal: 11-06.

**2.1 The memory object.**
- "Header" became "metadata" because "metadata" avoids implying a file: 10-14.
- The two-sided data contract, stable metadata that changes only through versioning or lifecycle events and a free-form payload the protocol does not prescribe: Cognee, on the call.
- Whether a body can be a structured value rather than a string (I-17): raised in review; how a non-text body is carried added on 11-06.
- The body format list, markdown, plain text, JSON, DocLang, XML (for example PubMed), HTML, CSV and others: 10-14 and 11-06. The SHOULD for `text/plain` and `text/markdown` and the MAY for any other valid MIME type: 11-06.
- The base object is metadata plus a typed body, not a markdown file: call, confirmed 10-14. The markdown loading profile (2.10.6) relates to it through Packer's loading contract.
- An optional schema or source-type field for structured and opaque sources (I-18): 10-14.
- The atomic unit (I-2): "the smallest semantic unit that carries meaning and can be evaluated true or false" is Cognee's view from the call; "documents with titles and authors" is the CN and Packer view; the single claim carrying provenance, confidence, versions and what it superseded is the knowledge object of arXiv 2601.15313 (Appendix A), arXiv 2603.15994, arXiv 2603.17781 and SSRN 10.2139/ssrn.5812343. 10-14 kept the question out of scope for now; the metadata is written to work for all three views.
- Stubs, whose body is a summary or pointer fetched before use "much as skills sit in context as stubs": Wes, 10-14; put forward on 10-14.

**2.3 Field tiers.**
- The four tiers were proposed by Gabe on the call.
- Every tier assignment in the field table is the editors', except `version` and `updated_at`, read back on 10-14, and `protocol_version` and `weight`, set on 11-06.

**2.4 Field table.**
- `identifier` replaces `title` as the key: call; IBM's "memory identifier"; Cognee §3.1. Stability across versions and the RECOMMENDED UUIDs: 10-14. `identifier` plus `origin` as a global key: review; Cognee PR #16.
- `path` kept separate from `identifier` because folder structure carries discovery and progressive-disclosure information: Sruly, 10-14; put forward on 10-14. Hierarchy metadata beyond `path` (I-19): 10-14.
- `title` may duplicate the body for fact-sized memories: call.
- `protocol_version`: agreed on 11-06 as optional on the memory, the manifest expected to require it; its reason, bringing memories at rest forward as the protocol changes, including self-to-self export and import: 11-06. Name and format (I-26): 11-06.
- `media_type` renamed from `type` because agent harnesses already use `type` for the kind of a memory: review; CN; call. The MIME-type rule set on 11-06.
- `stub`: 10-14.
- `tags` as the place to record the kind of a memory without an ontology: IBM; CN; 10-14. The tag field had been marked "discussed" in the call notes.
- `scope`: IBM; Cognee §3.3; call. Runtime access control enforced by the serving system from interchange fields, so the agent need not see them: call.
- `created_at` as recording time distinct from `valid_from`: 10-14; the field had "no objection" in the call notes. `valid_from`: IBM; Cognee §3.5; 10-14.
- `valid_until` replaces `invalidated_at` and may be a future date: review; agreed 10-14.
- `version` audit-required: IBM; read back 10-14. `updated_at` allows stores that change memories in place: 10-14.
- `checksum` over the metadata-covered fields plus the body: CN; call ("no objection"). A second hash of the body alone for deduplication: Cognee PR #16.
- `provenance` replaces `author`; a missing `provenance` means the author is unknown: review.
- `evidence`: call; Cognee §3.2; Cognee PR #16; AIDP. `links`: Cognee §3.4; IBM override; CN.
- `weight`, agreed 11-06; the rationale, that a receiver which recomputes its own values loses the exporter's relative ordering, which usually comes from an algorithm the exporter does not share: review; 11-06.
- `status`, parked: call; CN.
- The extension rule (implementations MAY add fields, unknown fields preserved): Cognee §5.
- Cognee PR #16 proposes further fields (`subject`, `kind`, `accuracy`, an `origin` qualifier, `invalidated_by`, a list shape for evidence); they are reflected where they overlap (list in 4.1.2) and otherwise left for review there.
- The thin core with semantic conventions (I-21, full text in 4.1) was proposed by Ilan in review, following OpenTelemetry; not reached on 10-14.

**2.5 Provenance and evidence.**
- `contribution` renamed from `role`, which LLM APIs use for user / system / assistant: review. `ai_usage` to be aligned with EU AI Act terminology: review; IBM; call. `name` renamed from `model` so that every kind can be named: review. The tier column of the contributor table is the editors'.
- A plain list lets a memory record that a person asked an agent to save something and the agent rewrote it, without forcing a single grade on the result: Sruly, call.
- Attribution per revision, `at` kept as written, line-level attribution derivable from diffs: agreed 11-06. Whether that needs a field (I-25): 11-06.
- Writers are contributors (2.5.2): editors' text, not yet discussed.
- The accountable human: agreed on the call; the SHOULD to mark who is accountable when several humans appear is the editors'. The operator of a maintenance agent as its accountable human: review, carried by the editors.
- Evidence as a reference or a plain string when the source is not addressable: call. A reference that points outside the store: review. The relation kinds observed / stated / inferred / derived: Cognee §3.2; Cognee PR #16; AIDP's ground truth / transcripts / inferences. A derived memory whose evidence is unavailable says so: Cognee §3.2, carried by the editors. Exporting or linking transcripts (I-5): review.
- "Agent memory is often the wrong home for facts that belong in a system of record, such as a price list or a patient record": Wes, 10-14.
- Unknown authorship: a missing `provenance` MUST NOT be read as the user's own words: review. It replaces v0.1's heuristic provenance, which a receiver could not tell apart from real provenance; the change closed I-9.
- Accuracy: 10-14 asked whether a memory should carry its accuracy (Vasilije, 10-14; Cognee PR #16 `accuracy`). Two concerns from 10-14: a score cannot move between systems unless the algorithm that produced it is also standardized, and a system can become confidently wrong through self-reinforcing loops. Vouching, a model or a person vouching for a memory, was suggested instead: Sruly, 10-14. The provenance-and-evidence resolution is the editors' proposal, settled 11-06 together with `weight`.
- The variant that puts an optional confidence on each evidence entry, portable only together with who or what produced it, how and when: review, 10-15.

**2.6 Links and lineage.**
- The graph rule, audit-grade systems reconstruct the full chain and others may leave nodes unconnected: call.
- Consolidation names all its inputs: Cognee §3.4.
- Inline links in the body, `[[identifier]]`: CN. Typed edges in the metadata with `rel` values: Cognee §3.4; IBM override.
- Folding evidence into links as a `rel: evidence` edge was suggested in review; 10-14 leaned against it, because evidence answers why to believe a memory and may point outside the store, while links answer how memories relate. Keeping them separate was put forward on 10-14.

**2.7 Versioning and lifecycle.**
- Both kinds of store supported, neither required: 10-14. IBM originally proposed immutable memories with supersession for everything; most systems may work that way, but requiring it would rule out memory files edited in place on disk: 10-14.
- Whether versioning belongs in a point-in-time export at all: raised in review and again on 10-14.
- The declared comparator: IBM. Incomparable versions and versions that are not totally ordered: Mike, 10-14. Wall-clock time SHOULD NOT be the comparator: call. The version slot was put forward on 10-14.
- A change SHOULD create a superseding revision: IBM; Cognee §3.1; CN. That it is recommended and not required: call; 10-14. Immutable revisions and a verifiable history REQUIRED in the audit profile: the editors' proposal.
- Lifecycle metadata MAY change even where the body never does: 10-14.
- Recording time distinct from when a claim applies: Cognee §3.5; 10-14. A memory stops applying at `valid_until` without being deleted: IBM; 10-14. The reverse pointer `invalidated_by` on the superseded memory: Cognee PR #16. Historical reads explicit: Cognee §3.5.
- Delete: IBM; AIDP `/fmp/delete`; Cognee; CN. What a delete means for derived memories (I-7): review.
- Forget and tombstones: Cognee §3.5; CN §6.3. Immediate removal whatever the retention rules, for example classified information stored by mistake, as something the spec should make implementable though not a requirement for every store: Wes, 10-14.
- `origin` plus `identifier` to recognize a re-import and `exported_at` to show a copy predates the forget: review.
- Without tombstones, an interchange rule that turns every re-import into a new memory lets an invalidated or deleted memory come back from an old archive: Cognee §3.5. Cross-draft adapter fixtures reproduce this case. Placing the whole of forget, tombstones and anti-resurrection in the audit profile is the editors' resolution of I-7.

**2.8 Representations.**
- Two representations of one memory, interchange and runtime: call. Metadata the agent does not need can make it perform worse: 10-14.
- A markdown body the agent reads, with structured metadata stored separately: AIDP, thread.
- Each memory system takes the interchange form and uses whatever subset helps: review. Access control enforced by the serving system: call.

**2.9 Exchange.**
- The manifest text was marked for replacement by the follow-up proposal on 11-06.
- `origin` plus `identifier` as the global key, the way CloudEvents uses `source` plus `id`; "two people who each export a `MEMORY.md` produce colliding identifiers": review; Cognee PR #16. `exported_at` ordering exports and dating a copy against a forget: review.
- A full-history export, including memories no longer valid, for forensic review: 10-14. Required extensions, and absence from a partial export not read as deletion: Cognee §3.6.
- Transfer intent (copy, move, federation): Cognee §3.6; the federation intent: AIDP. IBM's draft treats a memory as valid in one system at a time, an import creating a new memory; Cognee's keeps the origin identity across copies; with `origin` in the manifest the origin key survives either way (the remainder is I-8). The MUST to keep an origin-to-local mapping: Cognee §3.1, carried by the editors.
- Fidelity: raised in the thread.
- Receipts: Cognee §3.6. "A round-trip field report found a store that applied 208 records and kept none, with no warning": PR #12.
- The dangling-reference rules were proposed by Gabe on 10-14; the causes, including a reader's scope that does not include the target: 10-14. "A dangling reference can still mean something in the audit chain even when nobody can follow it. Some dangling references point at things that should never have been stored as memory in the first place": Wes, 10-14.
- Credentials are not memory: Cognee §3.3, carried by the editors.
- "An imported provenance chain is a claim, and it can be laundered": Wes, 10-14. A third-party chain of trust for provenance out of scope for now: 10-14; the question was opened on 10-14 (I-22).

**2.10 Runtime binding.**
- The three surfaces, file access, tools and hooks: call. Observe / decorate: IBM. Plugins: AIDP.
- MCP as the home for the binding (I-10): IBM; call. Some implementers find hooks more controllable than MCP tools, and some find a CLI more reliable for retrieval isolation: call. SEP-2640 (Skills over MCP) for progressive disclosure without a file system: AIDP, thread.
- Recall not standardized, the protocol defining what recall returns and not how it is called: call. Whether federation needs some standard recall (I-15): review.
- The write minimum, an author, a time, and create-or-revise: call.
- Federation layer and its merge logic left to implementations: AIDP; call. Identity passes through to each server: call.
- Change notification left to implementations, closing I-11: review.
- The markdown loading contract (root `MEMORY.md`, deferred files, one level down, selective reads): Packer. Declaring loss on projection: Cognee §2.
- The federation endpoint set (upload, search, read, delete, a required capability endpoint): AIDP.
- Compiled versus separate memories at runtime (I-12) carries no attribution in v0.5.

**2.2 and 2.11 Profiles.**
- Profiles that let a deployment claim only what it implements: Cognee §5. The conformance section as a whole was editors' text. An exporter MAY add `protocol_version` at export: the editors.

**4.4 Out of scope.**
- Storage, indexing, lookup, embeddings and internal mutation: all drafts; 10-14. The semantic scope of one memory: 10-14. Confidence, accuracy and decay scoring: 10-14. `scope` tags without a policy language: IBM; CN.

**4.2 Open issues register, attributions carried on the rows.** I-1 settled 10-14. I-2 deferred 10-14. I-4 mostly settled 10-14. I-11 closed in review. I-15 raised in review. I-17 raised in review, extended 11-06. I-18 and I-19 raised 10-14. I-20 settled 11-06. I-21 raised in review. I-25 and I-26 raised 11-06.

**Papers.** The knowledge-object papers shared by lvrzhn on PR #13, arXiv 2601.15313, 2603.15994 and 2603.17781, and SSRN 10.2139/ssrn.5773922 (revised 10.2139/ssrn.5812343), informed the atomic-unit discussion (I-2, 4.2) and the accuracy discussion (2.5.6).

### 4.6 Sources

This draft distills the proposals in `early-draft-specs/` on `main`: the scoping note (Strauss and Rosenblat), Packer v0.2 (Letta), IBM v0.1, AIDP / FMP, Cognee v0.1, Context Nest v0.1 and the AMS Card (Mila / Mozilla). It also draws on the 2026-09-28 exchange-and-runtime call, the 2026-10-14 and 2026-11-06 technical working meetings, the review comments on PR #13, Cognee's header proposals in PR #16, and the #exchange-and-runtime thread. The date codes and source-draft abbreviations used in Part 4 are defined at the head of 4.5.

### 4.7 Change history

#### Restructured 2026-11-09

- The v0.5 text is reordered into four parts: goals (Part 1), the protocol (Part 2), what the group has agreed (Part 3), and everything else (Part 4). No normative change: no MUST, SHOULD or MAY is added, removed, strengthened or weakened, and no field, profile, default or encoding is introduced.
- Editorial changes to tables and examples: a body row is added to the field table (2.4), restating the existing text on what a body is and that the minimal profile carries one; the parked `status` row moves from the field table to 4.3.2; the manifest JSON moves from Appendix A to 4.3; `protocol_version` is removed from the Appendix C example, since the minimal profile does not require it; and the Appendix B caption now says what the example shows.
- The eight-tag status scheme ([agreed], [proposed], [open], [discussed], [no objection], [parked], [deferred], [editors]) is replaced by two marks in the body, [agreed] and [open I-n] / [open U-n]. Unmarked text is proposed by the editors. Who agreed what and when is in Part 3; who proposed what and when is in 4.5; editors-added text is listed in 4.1; parked and deferred items are listed in 4.3.
- Every attribution, meeting code, PR number and source-draft citation moves out of Parts 1 and 2 into 4.5.
- Fourteen questions the v0.5 text raised without an issue number are registered as U-1 to U-14 in 4.2.

The § references in the two verbatim entries below are v0.5 section numbers. This map translates them.

| v0.5 | This draft |
|---|---|
| Title block | 0 |
| Sources | 4.6 (text); 4.5 (date-code legend) |
| Changes since v0.2, Changes since v0.1 | 4.7 |
| §0.1 Status | 0; the definition of [agreed] is quoted in 3 |
| §0.2 Goals, non-goals and scope | 1.1, 1.3, 1.4; manifest description → 4.3 |
| §0.3 Conventions | 0 |
| §1 Goals | 1.2; the left-to-implementations list → 4.4 |
| §2.1 Metadata plus body | 2.1 |
| §2.2 Body formats | 2.1; 2.4 (`media_type` row); 1.3 |
| §2.3 Atomic unit | 1.3; 2.1; 4.2 (I-2); 4.3 |
| §2.4 Stubs | 2.1; 2.4 (`stub` row) |
| §3.1 Tiers | 2.3 |
| §3.2 Field table | 2.4; `status` row → 4.3 |
| §3.3 A thin core with semantic conventions | 4.1; 4.2 (I-21) |
| §4 intro | 4.1 |
| §4.1 Contributor list | 2.5.1 |
| §4.2 Writers are contributors | 2.5.2 |
| §4.3 Accountable human | 2.5.3; 2.2 |
| §4.4 Evidence | 2.5.4 |
| §4.5 Unknown authorship | 2.5.5 |
| §4.6 Accuracy, confidence and weight | 2.5.6; 2.4 (`weight` row); 4.2 (I-20) |
| §5.1 A graph | 2.6 |
| §5.2 Depth | 2.6; 4.2 (I-6) |
| §5.3 Links between memories | 2.6 |
| §6 intro | 2.7.1 |
| §6.1 Version slot | 2.7.2 |
| §6.2 Immutable revisions | 2.7.3 |
| §6.3 Invalidation and supersession | 2.7.4 |
| §6.4 Delete | 2.7.5 |
| §6.5 Forget, tombstones and anti-resurrection | 2.7.6 |
| §7.1 Interchange is a superset of runtime | 2.8 |
| §7.2 Field placement | 2.8 (table); last sentence → 2.4 (`scope` row) |
| §8.1 Manifest | 4.3 (working text); 2.9.1; 1.4 |
| §8.2 Transfer intent | 2.9.2; 4.2 (I-8) |
| §8.3 Fidelity | 2.9.3; 2.11 |
| §8.4 Receipts | 2.9.4 |
| §8.5 Dangling references | 2.9.5; fourth bullet → 2.11 |
| §8.6 Credentials | 2.9.6 |
| §8.7 Trust on import | 2.9.7; 1.3; 4.4 |
| §9.1 What crosses the binding | 2.10.1 |
| §9.2 Candidate binding: MCP | 4.2 (I-10); one line in 2.10.1 |
| §9.3 Recall is not standardized | 2.10.2; 2.10.3 |
| §9.4 Federation | 2.10.4 |
| §9.5 Change notification | 1.3; 4.2 (I-11); 4.3 |
| §9.6 Multiple memories | 2.10.5 |
| §10 intro | 2.2 |
| §10.1 Minimal profile | 2.11 |
| §10.2 Markdown loading profile | 2.10.6 |
| §10.3 Federation binding | 2.10.4 |
| §10.4 Audit profile | 2.11 |
| §11 Out of scope | 4.4; 1.3 (short form) |
| §12 Open issues | 4.2 |
| Appendix A (manifest) | 4.3 |
| Appendix A (memory) | Appendix A |
| Appendix B | Appendix B |
| Appendix C | Appendix C |
| Acknowledgements | 4.8 |

#### Changes since v0.2

- `media_type` MUST be a valid MIME type. A system SHOULD support `text/plain` and `text/markdown` and MAY support any other valid MIME type, so bodies are no longer limited to text (11-06, §2.2, §3.2).
- New optional field: `protocol_version`, the protocol version a memory was written against. The manifest proposal is expected to require it. The name is still open (11-06, §3.2).
- New optional field: `weight`, a relative ordering among memories from one `origin` (11-06, §3.2, §4.6).
- `at` in `provenance` stays as written. Attribution is per revision, and line-level attribution MAY be derived from diffs (11-06, §4.1).
- This document is now the individual memory spec. The export/import manifest moves to a follow-up proposal (11-06, §0.2, §8.1).
- New open issues I-25 and I-26.

#### Changes since v0.1

- "Header" is now **metadata** (10-14), and `type` is now **`media_type`** (review).
- The draft now states its goals and non-goals up front (§0.2): it is a transfer format, not a storage format. Markdown is neither required nor preferred (10-14).
- `version` is **audit-required**, not required. Stores that change memories in place and stores that never change them are both supported (10-14, §6).
- **`valid_until`** replaces `invalidated_at` and may be a future date (10-14). `created_at` records when the system learned something; `valid_from` records when it became true (10-14).
- `provenance` is optional outside the audit profile. An exporter that doesn't know who wrote a memory leaves it out rather than inventing it (review, §4.5).
- New open issues I-17 to I-23.
- New: a `stub` flag (§2.4), `path` kept separate from `identifier` (§3.2), `origin` and `exported_at` in the manifest (§8.1), a rule for dangling references (§8.5), and a note on trust when importing (§8.7).
- Accuracy and confidence are handled through provenance and evidence, as an editors' proposal (§4.6).
- The thin core with semantic conventions is listed as an open proposal (§3.3).
- Provenance `role` is now `contribution`, and `model` is now `name` (review).

### 4.8 Acknowledgements

Built from the proposals by Charles Packer (Letta), Gabe Goodhart and colleagues (IBM), Sruly Rosenblat and Ilan Strauss (AI Disclosures Project), Vasilije Markovic (Cognee), Misha Sulpovar (Context Nest), and Mila and Mozilla (AMS Card). It also draws on the 2026-09-28 call with Gabe Goodhart, Sruly Rosenblat, Vasilije Markovic, Alex Hancock and Misha Sulpovar, and on the review comments on PR #13 by Gabe Goodhart (with Rynne and Anna Lisa), Sruly Rosenblat and Ilan Strauss. v0.2 also reflects the 2026-10-14 technical working meeting and its participants, including Wes Jackson. v0.5 reflects the 2026-11-06 technical working meeting and its participants. The knowledge object papers shared by lvrzhn on PR #13 (arXiv 2601.15313, 2603.15994, 2603.17781; SSRN 10.2139/ssrn.5773922, revised 10.2139/ssrn.5812343) informed the atomic-unit discussion (4.2, I-2) and 2.5.6.

## Appendix A. A memory in interchange form (JSON)

This is one memory in the interchange representation (2.8); it carries every field the audit profile requires (2.11). Key names inside `version`, `evidence` and `links` (`value`/`comparator`; `ref`/`relation`/`dangling`; `target`/`version`/`rel`) are illustrative: their shapes are open (I-4, I-5, U-2, U-6) and the evidence relation vocabulary is 2.5.4.

```json
{
  "identifier": "9b2e7c14-3f6a-4d1e-8a5b-2c7f9e0d4b31",
  "protocol_version": "0.5",
  "path": "team/preferences/status-update-day.md",
  "title": "Status updates move to Friday",
  "media_type": "text/markdown",
  "tags": ["preference", "team-process"],
  "scope": ["team:platform"],
  "created_at": "2026-09-15T09:30:00Z",
  "valid_from": "2026-09-15T00:00:00Z",
  "version": { "value": 2, "comparator": "integer" },
  "checksum": "sha256:9f2c1e0b6d4a8f3e2b1c7d5a9e0f4b3c8d2a6e1f7b9c3d5e8a0f2b4c6d1e3a5",
  "provenance": [
    { "id": "user:jordan", "kind": "human", "contribution": "instructed", "at": "2026-09-15T09:28:00Z" },
    { "id": "agent:notes-assistant", "kind": "agent", "contribution": "authored", "name": "example-model-1" },
    { "id": "user:sam", "kind": "human", "contribution": "approved", "at": "2026-09-15T09:30:00Z" },
    { "id": "agent:review-judge", "kind": "agent", "contribution": "verified", "name": "example-judge-1", "at": "2026-10-01T12:00:00Z" }
  ],
  "evidence": [
    { "ref": "transcripts/2026-09-15-standup#turn-14", "relation": "stated" },
    { "ref": "https://wiki.example.com/team/process", "relation": "observed", "dangling": true }
  ],
  "links": [
    { "target": "9b2e7c14-3f6a-4d1e-8a5b-2c7f9e0d4b31", "version": 1, "rel": "supersedes" }
  ],
  "weight": 1.7,
  "body": "Status updates are due Fridays from Sep 15. They were due Tuesdays before that."
}
```

## Appendix B. The same memory in runtime form (markdown with front matter)

```markdown
---
identifier: 9b2e7c14-3f6a-4d1e-8a5b-2c7f9e0d4b31
protocol_version: "0.5"
path: team/preferences/status-update-day.md
title: Status updates move to Friday
media_type: text/markdown
tags: [preference, team-process]
created_at: 2026-09-15T09:30:00Z
version: 2
provenance:
  - { id: user:jordan, kind: human, contribution: instructed }
  - { id: agent:notes-assistant, kind: agent, contribution: authored }
---

Status updates are due Fridays from Sep 15. They were due Tuesdays
before that.
```

This is one possible projection (2.8): `scope`, `checksum` and the `approved` and `verified` provenance entries are omitted, the two provenance entries shown are a summary, and `version` is kept as a field the implementation needs. All remain in the interchange form.

## Appendix C. The smallest conforming memory (minimal profile)

```markdown
---
identifier: MEMORY.md
media_type: text/markdown
created_at: 2026-10-14T00:00:00Z
---

The user prefers concise answers.
```

No `provenance`, so the author is unknown (2.5.5). No `version`, so it cannot claim the audit profile (2.11). No `protocol_version`: the minimal profile does not require it on the memory (2.4); the manifest carries it for the export as a whole (4.3).
