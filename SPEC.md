# Open Memory Protocol: The Memory Object

**Editors' draft v0.6, 2026-11-09.**

Proposals the group has not yet adopted are kept in [Notes J](2026-11-09-working-spec-v0.6-notes.md#j-proposals-not-yet-in-the-text) until they are accepted or rejected.

## Part 1. The memory object

### 1.1 What is a memory object
Memory in the Open Memory Protocol is defined as a **body** plus **metadata**. The body is the part of the memory that is relevant to an agent. The metadata is there to help transfer additional information alongside the body to other memory stores that the agent interacts with. It also helps the memory systems keep track of provenance and versioning, linking memories to each other, and controlling who can access them.

We do not enforce the size of a memory. Different systems may have more granular information, such as making memories consist of a single fact only, others may include entire essays as a single memory, we aim to support both. A memory server can process memories to better fit their particular memory format once they receive it, our goal for the memory object is only to transfer it over.

**Body Format**

The body MUST be a string. Non-text content, such as images or audio, MAY be carried as a base64-encoded string with `body_encoding: base64`. Implementations are not required to interpret every media type.

In cases where a memory is stored as a structured object such as JSON or XML the metadata SHOULD include a `media_type` field with a value such as `application/json` or `application/xml`.

The body of a memory also does not need to include full documents inline. It can instead indicate that a memory is a stub with the `stub` field and optionally tell the memory system elsewhere with a `body_uri` field.

### 1.2 Field table

The table defines every standardized field within the Open Memory Protocol. Unstandardized metadata fields may be added by implementations if a field they need is not covered by the fields below. Future versions of the protocol will aim to officially adopt fields that are missed below but commonly used.

| Field | Type | Tier | Definition |
|---|---|---|---|
| `identifier` | string | required | Identifies the memory within its origin system. UUIDs are RECOMMENDED. MUST be unique among the memories in one export. |
| `path` | string | optional | Where the memory sits in the origin store, as a relative path with `/` separators, for example `team/preferences/status.md`. A receiver MAY rebuild folder structure from it. |
| `title` | string | optional | A human-readable label. May duplicate the body for fact-sized memories |
| `protocol_version` | string | optional | The version of this protocol the memory was written in. A receiver MUST import a memory whose `protocol_version` it does not recognise, and preserve the field. |
| `media_type` | string | required | The media type of the body. MUST be a valid MIME type. |
| `stub` | boolean | optional | `true` when the body is a summary or pointer and the full body may be fetched |
| `body_uri` | string (URI) | optional | Where the full body can be fetched when `stub` is `true` |
| `body_encoding` | string | optional | How the body string is encoded. `base64` for non-text content; absent for text |
| `tags` | list of strings | optional | Semantic tags, free-form or from a vocabulary declared elsewhere.|
| `scope` | list of strings | ACL-required | A list of scopes the user or agent needs to access memory. |
| `created_at` | ISO 8601 timestamp | required | When the system recorded the memory. |
| `valid_from` | ISO 8601 timestamp | optional | When the claim became true in the world |
| `valid_until` | ISO 8601 timestamp | optional | When the claim stops being true. MAY be in the future. |
| `version` | opaque, with a declared comparator | audit-required | The current version of this memory |
| `updated_at` | ISO 8601 timestamp | optional | When this revision was written |
| `checksum` | string | audit-required | An integrity hash of the metadata-covered fields plus the body |
| `provenance` | list of contributors | optional; audit-required, with an accountable human | Everyone and everything that contributed to a memory. |
| `evidence` | list of references or strings | optional; audit-required | A list of items the memory is based on. |
| `links` | list of edges | optional | References to other memories. |
| `weight` | float | optional | An opaque weight score describing how "useful" the memory is. A receiving system MAY interpret `weight` however it wants. |
| `body` | string | required | The content of the memory, in the format `media_type` declares. A string (1.1) |

`checksum` is computed over the UTF-8 bytes of `identifier`, `version` (if present), `created_at`, `updated_at` (if present) and `media_type`, each followed by a newline (`0x0A`), then the body bytes, decoded first if `body_encoding` is set. Its value is `algorithm:hex`; implementations MUST support `sha256`.

`status`, a lifecycle or visibility state inside a store, is parked and not a standard field; its description is in Notes D.2, and 3.4 shows where it would sit if kept.

Implementations MAY add fields. Unknown fields MUST be preserved on export and MUST NOT change the meaning of standard fields.

### 1.3 Example memory object

```json
{
  "identifier": "9b2e7c14-3f6a-4d1e-8a5b-2c7f9e0d4b31",
  "protocol_version": "0.6",
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

### 1.4 Profiles at a glance

A deployment claims only what it implements. **Minimal**: the required fields, a body, and unknown fields preserved; a folder of markdown memories with no other metadata meets it. **Audit**: every memory traces to an accountable human (3.1.3), carries `checksum` and `version`, and keeps a verifiable history (3.3.3); meant for multi-user deployments. A system that claims it is audit-grade. Two more profiles set no field requirements: the markdown loading profile (3.6.6) and the federation binding (3.6.4). The checklists are 3.7.

Each field in 1.2 carries one tier:

| Tier | Meaning |
|---|---|
| **required** | Every conforming memory carries it |
| **audit-required** | Required in the audit profile (1.4, 3.7); optional otherwise |
| **ACL-required** | Required where access control applies; interchange only |
| **optional** | May be omitted in every profile |

## Part 2. Goals and scope

### 2.1 Goals

The protocol standardizes two things: an **exchange format**, the metadata that travels with a memory so one system can export it and another import and represent it, for portability and data ownership; and **runtime plug-in points**, what an agent harness consumes at runtime and where a memory system plugs in, so harnesses and memory systems can be built and chosen independently. Everything standardized MUST work down to a folder of memory files on one laptop and up to a multi-user, multi-scope deployment with access control.

Three goals judge the design.

1. **Adoption.** A folder of markdown memories, a database-backed store and a graph store can all conform with little work; most fields are optional and today's harnesses can meet the minimal profile (3.7). Optional fields go unimplemented, so the protocol SHOULD keep the number of optional fields that matter for interchange small.
2. **Auditability.** When a deployment needs it, every memory can be traced to one or more accountable humans (3.1.3) [agreed], its history verified and its lifecycle events recorded, in tiers (1.4) so individual users do not carry enterprise obligations. Full audit is a multi-user enterprise requirement, not a single-user one. [agreed]
3. **Room for innovation.** The protocol standardizes interfaces and the shape of data, not algorithms; Notes E lists what is left to implementations.

### 2.2 Non-goals and scope

- A transfer format, not a storage format: nothing about how a system stores, indexes or looks up memories.
- Markdown is neither required nor preferred, for storage or for the exported body; a folder of markdown memories conforms (3.7). [agreed]
- The size and semantic scope of a single memory (a fact, a document) are not fixed (I-2a).
- The recall function signature, ranking and retrieval algorithms are not standardized. [agreed]
- Federation merge and ranking logic is not standardized. [agreed]
- Change notification during a session is left to implementations (I-11, closed; Notes C.2).
- Third-party chains of trust for provenance are out of scope for now (I-22).

This document specifies one memory as represented on export and import. The export/import manifest, used once per export or import, is a separate follow-up proposal. [agreed] The manifest fields this draft depends on are listed in 3.5.1; until that proposal exists, Notes D holds the working text.

> **Proposed (U-8).** The Exchange and Runtime sub-thread owns the export/import manifest proposal, with Notes D as its working text and the editors of this draft as its editors until the group names others; the fields this draft depends on (3.5.1) are its minimum scope, and `version_comparator` (I-4) and `intent` (U-3) join them. It is adopted separately from this document, so a change to the manifest never requires a new revision of the memory object.

## Part 3. Rules

How a memory is attributed, linked, changed, represented, exchanged, served, and what a deployment may claim.

### 3.1 Provenance and evidence

#### 3.1.1 Contributor list

`provenance` is a list of contributors, one entry each:

| Key | Tier | Meaning |
|---|---|---|
| `id` | required | An identifier for the contributor (a person, an agent, a system) |
| `kind` | required | `human`, `agent` or `system` |
| `contribution` | optional | What the contributor did, for example `authored`, `instructed`, `approved`, `edited`, `imported`, `verified`, `corrected`, `contradicted` |
| `ai_usage` | optional | How much AI was involved. Values to be aligned directly with EU AI Act terminology |
| `name` | optional | A name for the contributor, whether a human, an agent, a model or a system |
| `at` | optional | When this contributor acted |

> **Proposed (U-4).** The key is `contribution`; `role` is not a standard key of a `provenance` entry and MUST NOT be written. A receiver that reads `role` in a memory written against protocol version 0.1 MUST rewrite it as `contribution` on export; `role` is the one key exempt from preservation (I-21).

> **Proposed (I-3a).** `contribution` is an optional key in every profile, RECOMMENDED on each entry, with the open vocabulary `authored`, `instructed`, `approved`, `edited`, `imported`, `verified`, `corrected`, `contradicted`, `forgot`; a receiver MUST preserve a value it does not know, and an entry without `contribution` counts as `authored`. `ai_usage` is not a standard key: how much AI was involved is read from the list, so a revision with no `kind: agent` contributor is **human-authored**, one an agent `authored` or `edited` with a human who `authored`, `edited`, `instructed` or `approved` it is **AI-assisted**, and one an agent `authored` or `edited` with no such human is **AI-generated** (the EU AI Act's human / mixed / artificially generated split). A receiver MAY carry that class as an extension field but MUST NOT require it on import.

Attribution is per revision: `provenance` records who contributed to a revision and in what sequence, not who wrote each line. An implementation that needs line-level attribution MAY derive it from the diffs between revisions. [agreed]

> **Proposed (I-25).** No field for line-level attribution is defined; an implementation that needs it derives it from the diffs between the retained revisions (3.3.3), and a deleted revision (3.3.5) cannot be attributed line by line. An extension field carrying precomputed line attribution MUST name the revisions it was computed between and MUST NOT change the meaning of `provenance`.

#### 3.1.2 Writers are contributors

Any process that writes a memory, including forget, consolidation and other maintenance agents, MUST appear in `provenance` like any other writer. A delete writes no memory; who performed it MAY be recorded on the tombstone (3.3.5). What those agents do is not defined (Notes E).

#### 3.1.3 Accountable human

A memory is auditable if it can be traced to one or more accountable humans. [agreed] In the audit profile (3.7) every memory MUST carry at least one `provenance` entry with `kind: human`, and SHOULD mark which human is accountable when several appear (for example the person who gave the instructions and the person who approved).

> **Proposed (I-3b).** A `provenance` entry MAY carry `accountable: true`, meaningful only on an entry with `kind: human`. This replaces the SHOULD of 3.1.3 with a MUST: in the audit profile a memory with more than one human entry MUST mark at least one of them `accountable: true`, a memory with exactly one human entry treats that entry as accountable, and several entries MAY carry it. A `kind: system` or `kind: agent` entry MUST NOT carry it; the operator who runs a maintenance agent appears as a human entry (3.1.2).

Accountability is assigned, not a sign-off on each memory. For a consolidation or other maintenance agent the accountable human MAY be the operator who runs it. A store that cannot name one does not claim the audit profile; it is still a conforming store.

#### 3.1.4 Evidence

`evidence` records what a memory rests on: source material, transcript turns, other memories, or a person's statement. Each entry is a reference, or a plain string when the source is not addressable. A reference MAY point outside the store: a file, a URL, a record in a system of record, or a turn in a transcript. Implementations SHOULD distinguish how the memory relates to its evidence: observed, stated by a person, inferred by a model, or derived from other memories. Evidence records origin, not truth. A derived memory whose evidence is unavailable MUST say so rather than omit the field silently. Evidence that points outside the store MAY be excluded from an export; what happens then is 3.5.5.

> **Proposed (U-2).** An evidence entry is a plain string or an object with `ref` (a memory `identifier`, a URI or a path), `relation` (`observed`, `stated`, `inferred` or `derived`), `dangling` (boolean), `at` (ISO 8601, when the evidence was recorded) and, when `ref` is a memory, the optional `version` and `origin` keys with the meaning they have on a link edge (3.2); `ref` MAY be omitted only when `dangling` is true. A memory is derived when it carries a `derived_from` link or an evidence entry with `relation: derived` or `inferred`. A derived memory whose evidence is unavailable, or was excluded from the export, MUST keep one entry per missing source with `dangling: true`, so the audit requirement is met by a marked gap and never by an absent field. Unknown keys on an entry are extension keys and MUST be preserved (1.2).

> **Proposed (I-20).** An evidence entry MAY carry `confidence`, a number from 0 to 1 stating how strongly the entry supports the memory, but only together with `assessed_by` (a contributor `id`, 3.1.1) and `assessed_at` (ISO 8601); an entry MUST NOT carry `confidence` without both. The value is the assessor's estimate within one `origin`, not a portable score: a receiver MUST NOT compare it across origins and MAY ignore it. The memory itself carries no confidence field (3.1.6).

A memory SHOULD link to a system of record rather than copy from it.

> **Proposed (I-5a).** A transcript is exported as a memory only when the store chooses to; it is then an ordinary memory with its own `identifier`, a `media_type` for its format and the tag `transcript`, and a memory derived from it links to it with `rel: derived_from` (3.2). Otherwise the transcript stays outside the store and a memory cites it from `evidence`, not `links`, by a reference with a turn anchor (`ref#turn-N`, as the example shows) and `relation: stated`; a receiver that cannot resolve it MUST keep it and mark it dangling (3.5.5). An exporter SHOULD link to a transcript rather than copy its text into `evidence`.

#### 3.1.5 Unknown authorship

A store that does not know who wrote a memory (for example a folder of markdown files) MUST leave `provenance` out rather than fill it with guesses. A receiving system MUST read a missing `provenance` as "author unknown". In particular, it MUST NOT read it as the user's own words. Such memories conform to the minimal profile but cannot claim the audit profile.

#### 3.1.6 Accuracy and confidence

The protocol defines no portable accuracy or confidence score. Accuracy travels as provenance and evidence:

- who checked a memory is a contributor with `contribution: verified`, `corrected` or `contradicted` plus `at`; humans, agents and evaluators such as an LLM judge are each marked by `kind`;
- what the check rests on is evidence: the source, the transcript or the later memory that confirmed or contradicted it;
- receivers compute their own confidence from those records, with their own algorithm (Notes E).

An implementation MAY carry its own score as an extension field. It SHOULD name the system that produced the score, so that a receiver does not mistake it for a portable value. Relative ordering within one `origin` travels as `weight` (1.2).

### 3.2 Links and lineage

Evidence and lineage form a graph whose nodes are memories and sources. How the graph is built, stored and traversed is left to the implementation. An audit-grade system MUST be able to reconstruct the full chain behind a memory; other systems MAY leave nodes unconnected. [agreed] The protocol does not require full provenance on every object. Consolidation SHOULD name all its inputs.

> **Proposed (I-6).** The minimum lineage an audit-grade system keeps is one hop per memory: every derived memory MUST name its direct inputs, as `evidence` entries (3.1.4) or `derived_from` links (3.2), at the revision that was processed where the input is versioned; the full chain is reconstructed by following those hops, so no fixed depth is standardized. Consolidation MUST name all its inputs in the audit profile and SHOULD elsewhere, except re-graining at import (I-2b), which MUST name them in every profile. An input that was deleted (3.3.5) or left out of an export is still part of the chain as a tombstone or a dangling reference (3.5.5); reconstruction reaches it and stops there.

Memories MAY reference each other, by inline links in the body (for example wiki syntax `[[identifier]]`, which works in any format that carries text) or by typed edges in the metadata (`links: [{target, rel}]`, with `rel` values such as `derived_from`, `supersedes`, `relates_to`). The two are not exclusive.

> **Proposed (I-5b).** Links are typed edges in the metadata, `links: [{target, rel, version, origin}]`: `target` is an `identifier` in the exporting `origin` unless the edge's optional `origin` names another store, the optional `version` pins one revision and is omitted to mean the current one, and `rel` is `supersedes`, `derived_from`, `relates_to`, `contradicts` (I-23a) or an implementation's own dot-prefixed value, which a receiver MUST preserve. Inline links in the body MAY stay; the protocol does not parse bodies, so an inline link that must survive import MUST also be stated as an edge, and a receiver MAY derive edges from inline links it understands. `links` stays optional in every profile.

Links and evidence are separate fields: evidence answers why to believe a memory and may point outside the store; links answer how memories relate to each other. Unresolvable targets: 3.5.5.

> **Proposed (I-23a).** `contradicts` is a standard `rel` value: a memory that disagrees with another MUST link to it with `rel: contradicts`, and the contradiction MUST NOT by itself supersede, invalidate or delete either memory; both stay current until one is superseded (3.3.4) or passes `valid_until`. A store that revises the contradicted memory to record the dispute SHOULD add a `provenance` entry with `contribution: contradicted` and `at`, whose `evidence` SHOULD name the contradicting memory. Current reads SHOULD surface both sides of an unresolved contradiction rather than pick one.

### 3.3 Versioning and lifecycle

#### 3.3.1 Stores and snapshots

Stores that change memories in place and stores that only write superseding revisions are both supported; neither is required (3.3.3 states the audit profile's rule).

By default an export is a snapshot as of the manifest's `exported_at` (Notes D). History travels only when the export declares it (audit profile, 3.7; federation, 3.6.4).

> **Proposed (U-6).** In a full-history export each revision is serialized as its own memory object; every revision of one memory carries the same `identifier` and its own `version`, `updated_at`, `checksum` and `provenance`, and the pair `identifier` plus `version` MUST be unique among the objects of the export. This refines the uniqueness rule of the `identifier` row (1.2), which stands for snapshots and selections: there one object per memory is exported and `identifier` alone MUST be unique. Tombstones are not memory objects and fall outside both rules; which exports carry them is 3.3.5. A receiver MUST read objects sharing an `identifier` as revisions of one memory, ordered by the declared comparator, never as duplicates.

#### 3.3.2 Version

When present, the format of `version` is left to the implementation (a sequence number, a semantic version or other). The implementation MUST declare a comparator. The comparator MAY report two versions as **incomparable**, for example revisions on different branches where both are valid; versions need not be totally ordered. Wall-clock time SHOULD NOT be the comparator. `identifier` stays the same across versions (1.2).

> **Proposed (I-4).** `version` MUST be a scalar, an integer or a string. The comparator MUST be one of `integer` (numeric order, the default), `semver` (Semantic Versioning 2.0.0 precedence), `opaque` (equality only; distinct values are incomparable) or a name an implementation registers under its own dot prefix (`contextnest.checkpoint`); a receiver that does not know a comparator MUST treat the versions as incomparable and MUST NOT fall back to `updated_at` or any wall-clock time. The exporting implementation declares the comparator once per export, in the manifest (3.5.1) as `version_comparator`; when the manifest omits it, or there is no manifest, the comparator is `integer`, and a memory MUST NOT carry a comparator of its own. The `{value, comparator}` object form is withdrawn in favour of the scalar `version: 2`.

#### 3.3.3 Immutable revisions

A change SHOULD create a new revision that supersedes the old one, rather than overwrite it in place, so history can be read as of a point in time. This is RECOMMENDED, not required. In the audit profile (3.7), immutable revisions and a verifiable history (for example a hash chain) are REQUIRED. A store that offers a verifiable history MUST still verify after a delete (3.3.5); a tombstone MAY carry the deleted revision's `checksum` for that purpose.

> **Proposed (U-5).** In the audit profile a store MUST keep every revision it has exported, and every revision a current revision supersedes, as a stored revision or a tombstone (3.3.5), and MUST be able to export them as a full history (3.3.1); a delete of a retained revision leaves a tombstone. A revision, once written, MUST NOT later appear under the same `identifier` and `version` with a different `checksum`; how a store achieves that (append-only files, a database log, retained copies) is left to the implementation. The history SHOULD be verifiable by a hash chain: each revision MAY carry `previous_checksum` (string), the `checksum` of the revision it supersedes, which a receiver checks under 3.5.3. This is the audit-profile item of 3.7.

Even where the body never changes, a system MAY update lifecycle metadata such as `valid_until` and supersession links.

#### 3.3.4 Invalidation and supersession

A memory stops applying at its `valid_until` without being deleted. A newer revision or another memory MAY supersede it with a `supersedes` link (3.2). Current reads SHOULD exclude memories past `valid_until` and superseded memories. Historical reads SHOULD be explicit.

#### 3.3.5 Removing and deleting memories

Because OMP transfers memories between systems, removing a memory from one store does not guarantee its deletion elsewhere. A store MAY remove a memory without retaining a record, but this is not a true delete as an older copy may later be imported and resurrect it. Preventing this requires a tombstone.

Tombstones are separate records, not memory objects, and are not subject to the required memory fields in 1.2. They are exported in a separate `tombstones` list alongside memories and MUST NOT be served to agents at runtime.

Tombstones are defined as follows:

| Field | Required | Description |
|---|---|---|
| `identifier` | Required | Identifier of the forgotten memory |
| `version` | Optional | Identifies a forgotten revision. If absent, the entire identifier is retired |
| `origin` | Optional | Identifies the originating system if different from the export manifest's `origin` |
| `checksum` | Optional | Checksum of the forgotten revision for history verification (3.3.3). Only permitted with `version` |
| `forgotten_at` | Optional | ISO 8601 timestamp of the delete |
| `reason` | Optional | One of `user_request`, `legal`, `retention_expiry`, or `error` |
| `provenance` | Optional | Identifies who performed the delete, using `contribution: forgot` and `at` (3.1.1) |

Apart from the optional `checksum`, a tombstone MUST NOT include the forgotten memory's body, title, tags, evidence or other fields derived from its content. Additional implementation-specific fields MAY be included as extensions, subject to the same restriction.

For example:

```json
{
  "tombstones": [
    {
      "identifier": "9b2e7c14-...",
      "version": 3
    },
    {
      "identifier": "4f1a0d22-..."
    }
  ]
}
```

When deleting a memory a store SHOULD leave a tombstone to prevent it from being restored by a later import. A receiver MUST NOT import or restore a revision covered by a tombstone it has received, including from older archives or copies made before the delete.

A tombstone with a `version` applies only to that revision. Other revisions MAY remain available, and new revisions MAY be created under the same identifier.

A tombstone without a `version` retires the entire identifier, covering all existing and future revisions. A store MUST NOT create new revisions under a retired identifier, and receivers MUST NOT accept them. Unversioned memories MUST use this form of tombstone.

A snapshot or full-history export SHOULD carry every tombstone the store holds. If the current revision of a memory is deleted and earlier revisions remain, a snapshot SHOULD export the latest remaining revision alongside the tombstone.

A conforming store MUST meet the following requirements:

- After a delete, the content of every covered revision MUST NOT be retrievable from the store or its exports.
- In the audit profile (3.7), the store MUST record when the delete occurred, who performed it and why. Exporting this information is optional.

Deleting a memory SHOULD NOT automatically delete memories derived from it. References to deleted memories or revisions become dangling references (3.5.5) and MUST be preserved and marked as such. Derived memories remain until the implementation's policy deletes them, invalidates them using `valid_until` (3.3.4), or re-derives them.

Receivers identify forgotten memories by their `origin` and `identifier`, and by `version` where provided. A tombstone applies to every copy of the covered revision, regardless of when that copy was exported. The `forgotten_at` timestamp is not required for anti-resurrection.

### 3.4 Representations: interchange and runtime

There are two representations of the same memory. [agreed]

- **Interchange** (export and import, migration): the full metadata, including the operational fields a receiving system needs to integrate the memory.
- **Runtime** (what an agent sees): a projection of the interchange form that omits fields that would add noise to the agent's context or reveal how the store is organized. Metadata the agent does not need can make it perform worse.

Which fields reach the agent is left to each memory system. The table below is guidance, not a requirement.

> **Proposed (U-12).** The placement table is normative where it says `no` and guidance elsewhere: `checksum`, `scope`, tombstones and audit records MUST NOT reach the agent through a runtime surface, and `identifier`, `media_type` and `body` MUST reach it with every memory object. A runtime projection MAY drop any other field and SHOULD drop a field that adds noise to the agent's context. The `status` row is removed (I-14) and the derived `auditable` row is I-13. Appendix A is therefore one conforming projection, not the only one.

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
| `status` (parked, Notes D.2) | yes, if kept | no |
| tombstones, audit records | yes | no |

> **Proposed (I-13).** `auditable` is an optional boolean of the runtime representation, computed by the serving system and never set by the agent or stored in interchange: `true` when the memory meets 3.1.3 (an accountable human) and, if derived, carries `evidence` (3.1.4); `false` otherwise, including when `provenance` is missing (3.1.5). A retrieval response MAY carry one `auditable` for the whole result, which MUST be `true` only when every memory returned is auditable. The flag is derived from fields 1.2 already defines and adds no field or tier to the memory; the audit log that records retrievals stays out of scope. The 3.4 table gains the row `auditable` (derived): interchange no, runtime MAY be shown.

Runtime access control is enforced by the serving system using interchange fields (1.2, `scope` row).

### 3.5 Exchange

#### 3.5.1 Manifest dependency

This draft depends on these manifest fields (working text in Notes D):

- `origin`: with `identifier`, the memory's global key (1.2); matches a tombstone to the memory it covers (3.3.5); the party whose claims imported provenance and evidence are (3.5.7).
- `exported_at`: the time the export is as of (3.3.1).
- `protocol_version`, and the profiles the export follows (3.7).
- The body formats present (1.2).
- Whether the export is a complete snapshot, a selection or a full history (3.3.1).
- The transfer intent (3.5.2).
- Where the `tombstones` list sits in an export (3.3.5).

The version comparator is declared in the manifest (I-4). Absence from a partial export MUST NOT be read as deletion.

#### 3.5.2 Transfer intent

An export MUST declare its intent: **copy**, the source keeps its memories; **move**, the source removes its memories only after a durable, conforming import on the receiving side, and leaves no tombstones for them (3.3.5); **federation**, no transfer, the memory is read where it resides (3.6.4). A receiving system that assigns its own identifiers MUST keep the origin-to-local mapping.

> **Proposed (I-8).** An imported memory MUST keep its `identifier`; `origin` plus `identifier` (1.2) names the same memory in every store it passes through, and a receiver MUST NOT mint a new `identifier` for a memory it preserves. A receiver MAY address the memory by a local identifier of its own, in which case it MUST keep the origin-to-local mapping and report it in the receipt (3.5.4), and on re-export it MUST emit the origin pair, carrying an optional per-memory `origin` field (string) wherever the memory's origin is not the manifest's. A receiver that re-derives rather than preserves MUST give the new memory its own `identifier` under its own `origin` and a `derived_from` link (3.2) to the origin pair.

> **Proposed (U-3).** Transfer intent is a requirement of the exchange, not of the memory, and this replaces the MUST of 3.5.2: it lives in the manifest as `intent`, one of `copy`, `move` or `federation` with the meanings in 3.5.2; an export with a manifest declares it there, and an export without a manifest or without the field is a `copy`, since copy obliges the source to nothing. No intent field is placed on the memory. This draft keeps what each intent means and the receiver's duties under it (the mapping in 3.5.2, the receipt in 3.5.4); the manifest proposal owns the field.

#### 3.5.3 Fidelity

The receiving side SHOULD be able to check that it received the same memory with the same history. In the audit profile, it MUST be able to, using `checksum` (1.2) and the verifiable history (3.3.3).

#### 3.5.4 Receipts

An import SHOULD produce a receipt that lists, per memory, whether it was accepted, transformed, omitted or rejected, with reasons and any identifier mappings (3.5.2). Retries MUST NOT duplicate memories.

> **Proposed (U-14).** The identity a retry is checked against is `origin` plus `identifier` (I-8) plus `version` where the memory carries one, and `checksum` where it does not. A receiver that already holds a memory with that identity MUST NOT create a second one; it MUST treat the re-import as the same memory and report it in the receipt as accepted without change. The same identity with different content is a conflict, which the receiver MUST report in the receipt rather than resolve silently, except a memory that carries neither `version` nor `checksum`, where the copy with the later `exported_at` replaces the earlier and the receipt lists it as transformed; `conflict` joins the receipt outcomes of 3.5.4.

> **Proposed (I-2b).** A receiving system MAY re-grain imported memories, splitting a document into claims or compiling claims into one memory, but only as new memories of its own: each MUST carry a `derived_from` link (3.2) to every imported memory it came from and a `provenance` entry with `contribution: imported` (3.1.1). The imported memories themselves MUST be kept as they arrived, or the receipt (3.5.4) MUST list each one as transformed. Whether a kept memory retains its origin `identifier` follows I-8.

#### 3.5.5 Dangling references

A reference (a link, 3.2, or an evidence entry, 3.1.4) is dangling when the receiver cannot resolve it: the target was left out of a partial export or deleted, lives outside the store (a session log, a file, a system of record), or is outside the reader's scope, so a reference that resolves for one person dangles for another. A system MUST be able to hold dangling references. It MUST keep them and mark them as dangling rather than drop them silently. An import MUST NOT fail because of a dangling reference. A system MAY try to resolve dangling references during import or later, including by asking a person.

#### 3.5.6 Credentials

Credentials (passwords, API keys, tokens) are not memory and MUST NOT be exported as memory.

#### 3.5.7 Trust on import

Receivers SHOULD treat imported provenance and evidence as claims made by the exporting `origin`, not as facts. `checksum` and a verifiable history (3.3.3) let a receiver check integrity, not truth. Receivers MAY review or sanitize imported memories before agents rely on them.

> **Proposed (I-22).** An imported body is data, not instruction; a receiver MUST NOT give it instruction authority because it becomes prompt-visible, and imported provenance and evidence remain the exporting `origin`'s claims. A receiver MAY hold imported memories in a staging state that its recall does not return until a person or a policy releases them; whether it stages is its own choice, and the state is an implementation field under an extension key (I-14). The import and any release MUST appear in `provenance` as contributors (`contribution: imported`, and `verified` or `corrected` for a review, 3.1.1), so a later reader can tell a reviewed import from an unreviewed one. Third-party chains of trust, signatures and a portable trust score stay out of scope (2.2).

### 3.6 Runtime binding

#### 3.6.1 What crosses the binding

At runtime, memory reaches an agent in three ways:

1. **File access**: the agent reads memory files with shell or file tools.
2. **Tools**: the agent calls explicit remember and recall tools exposed by a memory server.
3. **Hooks**: a supervisor observes or decorates the conversation without the agent knowing, deciding what to add to a session and what to store.

The protocol standardizes the shape of the memory objects that cross these surfaces, the runtime representation (3.4), not a new transport.

> **Proposed (I-10).** The protocol is binding-neutral: it fixes the object that crosses a runtime surface, the runtime representation (3.4), and no transport. A system that serves memories at runtime does so through one or more of the three surfaces of 3.6.1 and SHOULD declare which, in its capability declaration where it has one (3.6.4) and otherwise in its documentation; a store that only exports and imports needs no runtime surface. A memory served through two surfaces MUST be the same memory, the same `identifier` and the same body; which optional runtime fields each surface shows is the implementation's (3.4). Concrete bindings (MCP tools and interceptors, harness hooks, a CLI) are separate binding documents, like the federation binding, and none is required.

#### 3.6.2 Recall

The protocol MUST NOT fix a signature for recall. Implementations provide their own recall and their own guidance on using it. The protocol defines what recall returns, memory objects in the runtime representation (3.4), not how it is called. [agreed]

> **Proposed (I-15a).** Federation needs no standard recall: a server joins a federation through the federation binding's endpoint set (3.6.4), whose `search` call is defined only inside that binding (U-9), and on every other surface the recall rule of 3.6.2 stands. A federation layer MUST NOT require a server to expose any recall interface beyond the endpoints that server declares in its capability endpoint.

#### 3.6.3 Writes

A write needs, at minimum, an author, a time, and whether it creates a memory or revises an existing one (3.3.2).

#### 3.6.4 Federation

When several memory servers are connected, a federation layer MAY sit between them and the agent and present one unified memory. How it merges results and combines scopes is left to the implementation. Identity MUST pass through the federation layer to each server. [agreed]

> **Proposed (I-15b).** Identity passes through the federation layer as the caller's principal identifier carried by the binding's own authentication (OAuth, MCP auth, or the transport's equivalent); the protocol defines no identity scheme and no identity field on the memory. Scope granularity is not fixed: a `scope` tag is an opaque string and a system MAY tag a memory at any granularity (user, agent, session, project, team, organization, or finer). A `scope` tag SHOULD use the qualified form `kind:value` (`team:platform`, `user:jordan`, as the example does), so a receiver can read the granularity of a tag without a shared vocabulary. A federation layer MUST present each server with the caller's identity unchanged.

> **Proposed (U-11).** A serving system MUST assign `scope` itself, from the caller's identity and the write destination, and MUST ignore or reject a `scope` value supplied through a runtime surface (a write, 3.6.3, or a tool argument); on import, `scope` values from the exporting origin are claims (3.5.7) that the importer MUST map to its own scopes or reject, never adopt as grants. Under federation each server enforces its own access control from its own interchange fields before an object crosses the layer, so `scope` never crosses it: the unified memory is the union of what each server served to the pass-through identity. A federation layer MUST NOT widen access: it MUST NOT serve a caller a memory that no member server served for that caller's identity.

The federation endpoint binding is an endpoint set of upload, search, read, delete and a required capability endpoint, carrying memory objects in the runtime representation (3.4); each server declares its capabilities.

> **Proposed (U-9).** The federation `search` endpoint is a binding call, not the recall of 3.6.2: it is required only of servers that claim the federation binding (3.7), and a binding MAY fix the wire shape of its own query call. A `search` request MUST carry a free-text `query` string and MAY carry `tags` (list, all must match), `path_prefix` (string), `created_after` / `created_before` (ISO 8601) and `valid_at` (ISO 8601: memories valid at that instant); any further parameter is server-defined and declared in the capability endpoint. A `search` response MUST be a list of memory objects in the runtime representation (3.4), in the order the server chose. Ranking, the retrieval algorithm and how the federation layer merges lists stay out of scope (2.2).

#### 3.6.5 Multiple memories

Whether a server returns several memories compiled into one payload or as separate objects, and whether memories can nest, is unsettled. If they are returned separately, each carries its own runtime metadata.

> **Proposed (I-12).** A server MAY return several memories as separate objects, each in the runtime representation (3.4), or compiled into one payload; separate is the default where a binding does not say otherwise. A compiled payload is itself a memory object in the runtime representation, with its own `identifier` (or none when it is not stored) and a `links` list of `derived_from` edges to every compiled memory, so an agent's trace and the lineage chain (3.2) reach the sources. Memories MUST NOT nest: a body carries no memory objects, and a memory that contains or summarizes others relates to them through `links` or `stub` (1.1).

#### 3.6.6 Markdown loading profile

The markdown loading profile is the directory and loading contract of a root `MEMORY.md`: deeper files deferred, deferred memory surfaced one level down, and selective reads. Metadata is carried as front matter or in a sidecar, and `path` (1.2) records each file's place. When a projection to this profile drops fields, it MUST declare the loss. Hierarchy metadata beyond `path`: I-19 (1.2).

> **Proposed (U-15).** A file without front matter or sidecar derives its required fields: `identifier` and `path` are the file's relative path, `media_type` follows the extension (`.md` is `text/markdown`, otherwise `text/plain`), and `created_at` is the file's creation time or, where unavailable, its modification time. Front matter is YAML between `---` lines at the top of the file; a sidecar is `<file>.meta.yaml` beside the file with the same keys; front matter wins where both exist.

### 3.7 Conformance profiles

What each profile of 1.4 requires, each item pointing to the section that states the rule. An export's manifest declares the profiles it follows (Notes D). Whether "markdown loading" and "federation binding" remain declarable profile names is handed to the manifest proposal (Notes D).

**Minimal profile.** The required fields of 1.2 (`identifier`, `media_type`, `created_at`), a body, and an export that preserves unknown fields (1.2). Reachable from a folder of markdown memories with no other metadata. Provenance and versioning are not required (3.1.5, 3.3.2). A store that deletes a memory meets the requirements of 3.3.5, and a receiver honours the tombstones it receives (3.3.5).

> **Proposed (U-13).** The dangling-reference rules of 3.5.5 belong to the minimal profile: every conforming import MUST keep a reference it cannot resolve and MUST NOT fail because of it, and a kept reference whose target the receiver cannot resolve counts as marked; the explicit `dangling` marker on the entry (U-2) and the evaluation note stay audit-profile items. Transfer intent is a rule on the export, not a field requirement of any profile (U-3), so a bare folder of markdown stays conformant.

**Markdown loading profile.** The loading contract of 3.6.6: a root `MEMORY.md`, deferred deeper files surfaced one level down, selective reads, metadata in front matter or a sidecar, `path` on each file (1.2), and a declared loss for every field the projection drops.

**Federation binding.** The endpoint set of 3.6.4 with a capability endpoint, each server declaring its capabilities; memory objects cross it in the runtime representation (3.4); identity passes through to each server (3.6.4).

**Audit profile.** Everything in the minimal profile, plus:

- `provenance` on every memory, with an accountable human (3.1.3);
- `checksum` and `version` on every memory (1.2);
- immutable revisions with a verifiable history (3.3.3);
- evidence on derived memories (3.1.4);
- recorded lifecycle events, including when each delete occurred, who performed it and why (3.3.5);
- dangling references kept and marked (3.5.5); when a system is evaluated against this profile, its dangling references are noted.

## Appendix A. The example memory in runtime form (markdown with front matter)

```markdown
---
identifier: 9b2e7c14-3f6a-4d1e-8a5b-2c7f9e0d4b31
protocol_version: "0.6"
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

This is one possible projection (3.4): `scope`, `checksum` and the `approved` and `verified` provenance entries are omitted, the two provenance entries shown are a summary, and `version` is kept as a field the implementation needs. All remain in the interchange form.

## Appendix B. The smallest conforming memory (minimal profile)

```markdown
---
identifier: MEMORY.md
media_type: text/markdown
created_at: 2026-10-14T00:00:00Z
---

The user prefers concise answers.
```

No `provenance`, so the author is unknown (3.1.5). No `version`, so it cannot claim the audit profile (3.7). No `protocol_version`: the minimal profile does not require it on the memory (1.2); the manifest carries it for the export as a whole (Notes D).
