# Open Memory Protocol: The Memory Object (Exchange and Runtime)

**Editors' draft v0.6, 2026-11-09.** Exchange and Runtime sub-thread. Not an adopted OMP standard. v0.6 reorders v0.5 (2026-11-06) without normative change and adds a proposed resolution for every open question. Companions: [agreed decisions](2026-11-09-working-spec-v0.6-decisions.md) and [open questions, proposals and record](2026-11-09-working-spec-v0.6-notes.md), which holds the issue register, the discussion record and the change history with the v0.5 section map.

**How to read.** MUST, SHOULD and MAY are RFC 2119 keywords; all of them are editors' proposals until adopted. Unmarked text was carried from v0.5. **[agreed]** marks what the group agreed on a call. **Proposed (I-n)** blocks are new in v0.6 and resolve the question with that id; the group accepts or rejects each one. A mark at the end of a paragraph covers it.

## Example

One memory in interchange form, meeting the audit profile (3.7). The shapes of `version`, `evidence` and `links` are the v0.5 shapes; proposals I-4, U-2 and I-5b would change them.

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

## Part 1. The memory object

### 1.1 Metadata plus body

A memory is **metadata** plus a **body**. The metadata is a rigorous schema that can be rendered into any format that renders schemas (JSON, YAML front matter, a database row), for the system that manages the memory. The body is what is semantically relevant to the agent; `media_type` (1.3) declares its format, and it is usually a string in a text format. The contract is two-sided: stable metadata that changes only through versioning or lifecycle events (3.3.3), and a free-form payload the protocol does not prescribe. The object is not a markdown file; a markdown folder is one way to carry it (3.6.6). [agreed]

The body MAY be in any format with a valid MIME type; `media_type` declares which (1.3). Implementations need not process every format; non-text bodies such as image or audio are allowed but not required. [agreed]

> **Proposed (I-17).** `body` MUST be a string. A structured value is carried as its serialization in the declared `media_type` (a JSON document as text under `application/json`), never as a nested object. A body whose bytes are not UTF-8 text MUST be carried inline, base64-encoded, with the optional field `body_encoding: base64`, or by reference: `stub: true`, `media_type` the content's own type, and the optional field `body_uri` (string, a URI) naming where the content is, the body then empty or a summary. `checksum` and `body_checksum` (U-1) hash the decoded inline bytes, or for a by-reference stub the body string as carried.

> **Proposed (I-18).** One optional field is added, `body_schema` (string): a URI or name identifying the schema a structured body conforms to (a JSON Schema URL, a CSV header contract, an ontology IRI); absent when the body has none. No source-type field is added: the kind of memory travels in `tags`, since `media_type` is agreed not to be a semantic ontology. An opaque document such as a PDF is carried under its MIME type (I-17); text extracted from it is a separate memory linked `derived_from` with the document as evidence. A query-backed memory is the query output; the query and the system of record are its evidence with `relation: observed`.

> **Proposed (I-2a).** A memory is one addressable object, whatever grain the origin system gives its own `identifier`, `created_at`, `media_type` and body: a single claim (a knowledge object), a fact with its evidence, or a whole document. The protocol fixes no grain; every field of 1.3 MUST be usable at every grain, and a receiving system MUST accept a memory at the grain it arrives in. A system MAY name its grain in `tags` (`claim`, `document`); the manifest proposal MAY declare the grains an export contains.

A memory MAY be a **stub**: its body is a summary or pointer, and the full body has to be fetched before use. It carries `stub: true` so an agent knows to fetch the full body if it needs it.

### 1.2 Field tiers

Each field in 1.3 carries one tier:

| Tier | Meaning |
|---|---|
| **required** | Every conforming memory carries it |
| **audit-required** | Required in the audit profile (1.4, 3.7); optional otherwise |
| **ACL-required** | Required where access control applies; interchange only |
| **optional** | May be omitted in every profile |

> **Proposed (I-16).** The tier assignments of 1.3 hold as the v0.6 baseline: `identifier`, `media_type`, `created_at` and `body` required; `version`, `checksum` and `provenance` (with an accountable human) audit-required; `evidence` audit-required when the memory is derived (U-2 says when a memory is derived); `scope` required in the access-controlled profile (U-7); every other field optional. A validator MUST apply the tiers exactly as the table states them and MUST NOT infer a requirement the table does not state. A tier changes only by a recorded group decision.

> **Proposed (U-7).** A third profile, **access-controlled**, joins 1.4 and 3.7: a deployment that enforces access control on memories claims it, and in it every memory MUST carry `scope` (1.3), set by the system, and the export's manifest MUST declare the profile. The ACL-required tier of 1.2 then reads "required in the access-controlled profile; optional otherwise". The profile sets no other field requirement, says nothing about the policy language or how scopes combine (U-11), and MAY be claimed with or without the audit profile.

### 1.3 Field table

The table defines every standard field; a memory carries each at the tier 1.2 defines, and 3.4 says which reach the agent.

| Field | Type | Tier | Definition |
|---|---|---|---|
| `identifier` | string | required | Identifies the memory within its origin system and stays the same across its versions. Carries no required meaning. UUIDs are RECOMMENDED. MUST be unique among the memories in one export. With the manifest's `origin` (Notes D), the memory's global key |
| `path` | string | optional | Where the memory sat in the origin store's hierarchy, for example a folder path. Separate from `identifier` because folder structure carries discovery and progressive-disclosure information |
| `title` | string | optional | A human-readable label. May duplicate the body for fact-sized memories |
| `protocol_version` | string | optional | The version of this protocol the memory was written against, so a system can bring memories at rest forward as the protocol changes, including self-to-self export and import. Optional on the memory so a folder of markdown stays conformant; the manifest (Notes D) is expected to require it. [agreed] An exporter MAY add it at export |
| `media_type` | string | required | The media type of the body. MUST be a valid MIME type (for example `text/markdown`, `application/json`, `text/html`, `text/csv`, `application/xml`). A system SHOULD support `text/plain` and `text/markdown`, and MAY support any other valid MIME type. Not a semantic ontology. [agreed] |
| `stub` | boolean | optional | `true` when the body is a summary or pointer and the full body may be fetched (1.1) |
| `tags` | list of strings | optional | Semantic tags, free-form or from a vocabulary declared elsewhere (for example a JSON-LD `@context` or schema.org). Where a system records the kind of a memory (fact, preference, decision, observation) without the protocol requiring an ontology. Tags MAY cross into the runtime representation (3.4) |
| `scope` | list of strings | ACL-required | Scope tags that access policy attaches to. Set by the system, never by the agent. Interchange only (3.4). Neither an access grant nor proof of ownership. Runtime access control is enforced by the serving system using interchange fields; the agent does not need to see them |
| `created_at` | ISO 8601 timestamp | required | When the system recorded the memory. Distinct from when the claim became true (`valid_from`) |
| `valid_from` | ISO 8601 timestamp | optional | When the claim became true in the world |
| `valid_until` | ISO 8601 timestamp | optional | When the claim stops being true. MAY be in the future, for example a temporary workaround to retry at a set time. [agreed] |
| `version` | opaque, with a declared comparator | audit-required | The revision of this memory. Shape and comparator: 3.3.2 (I-4) |
| `updated_at` | ISO 8601 timestamp | optional | When this revision was written |
| `checksum` | string (`algorithm:hex`, for example `sha256:abcdefg...`) | audit-required | An integrity hash of the metadata-covered fields plus the body |
| `provenance` | list of contributors (3.1.1) | optional; audit-required, with an accountable human | Everyone and everything that contributed. A missing `provenance` means the author is unknown (3.1.5) |
| `evidence` | list of references or strings | optional; audit-required when the memory is derived from other memories (3.1.4) | What the memory rests on, inside or outside the store (3.1.4) |
| `links` | list of edges | optional | References to other memories (3.2) |
| `weight` | float | optional | A relative ordering among memories from one `origin`. Not bounded, with no prescribed mathematical meaning, so not a probability or a confidence. Values from different origins are not comparable. A memory MAY carry it; a receiving system MAY interpret `weight` however it wants. [agreed] |
| `body` | string | required | The content of the memory, in the format `media_type` declares. A string (1.1) |

> **Proposed (I-19).** Hierarchy is carried by `path` alone: a `/`-separated relative path with no leading or trailing slash, no empty segment and no `.` or `..` segment; a receiver derives folder structure from its segments. No folder, taxonomy or parent field is added; a folder's own description (a root `MEMORY.md`, an index file) is itself a memory whose `path` is that file's path and which names its children in its body or links to them (3.2). A projection that cannot keep `path` MUST declare the loss (3.6.6).

> **Proposed (I-26).** The field is named `protocol_version`, on the memory and in the manifest, matching the thin core's `semantic_conventions_version`. Its value is a string: once the protocol is adopted, the date `YYYY-MM-DD` of the adopted revision, the form MCP's `MCP-Protocol-Version` uses, so revisions order without a registry; editors' drafts use their draft number (`"0.6"`) until then. A receiver MUST treat a value it does not know as a revision it does not implement and import the memory anyway, preserving the field.

> **Proposed (U-1).** `checksum` covers, in this order, the UTF-8 bytes of `identifier`, `version` where present, `created_at`, `updated_at` where present and `media_type`, each followed by `0x0A`, then the decoded body bytes (I-17), so two systems compute the same value. An optional `body_checksum` (string, `algorithm:hex`, same algorithms) hashes the decoded body bytes alone; a receiver MAY use it to detect identical content across memories or exports but MUST NOT merge memories or revisions on that basis alone, because identity is `origin` plus `identifier`.

> **Proposed (I-23b).** A memory MAY carry `use_constraints`, an optional, interchange-only list of strings naming constraints the origin attaches to it, with the RECOMMENDED values `no_export` (consent to hand the memory to another system was not given), `no_derive` (it MUST NOT be consolidated into or used to derive other memories) and `no_train` (it MUST NOT be used as training data); an unknown value MUST be preserved. An exporter MUST NOT include a memory carrying `no_export` in a copy or move export to another `origin`; an export whose receiver is the same origin (migration, backup) carries it with the constraint. A receiver that cannot honour a constraint MUST reject or restrict the memory at import and say so in the receipt (3.5.4). Withdrawal of consent after a hand-over travels as a forget and tombstone (3.3.6).

`status`, a lifecycle or visibility state inside a store, is parked and not a standard field; its description is in Notes D.2, and 3.4 shows where it would sit if kept.

> **Proposed (I-14).** `status` is not a standard field. The lifecycle states the protocol needs are carried by `valid_until`, `supersedes` links and tombstones (3.3.4, 3.3.6); an approval or visibility state inside a store (draft, published, rejected) is an implementation field under an extension key, interchange only, preserved on export like any unknown field (1.3). A snapshot export SHOULD contain every memory the store holds except those in a non-served store state (draft, rejected); superseded and expired memories are included. 3.4 drops its `status` row.

Implementations MAY add fields. Unknown fields MUST be preserved on export and MUST NOT change the meaning of standard fields.

> **Proposed (I-21).** An extension field MUST be named with a dot-separated prefix that identifies the system defining it (`cognee.accuracy`, `contextnest.type`); names without a dot are reserved for standard fields, and the same prefix form names an implementation's own values where a rule allows them (a comparator, 3.3.2; a `rel`, 3.2). Unknown fields, whether extension fields or standard fields the receiver does not implement, MUST be preserved on export and MUST NOT change the meaning of a standard field; a receiving system MAY ignore their values. Fields proposed for the table but not yet adopted SHOULD travel this way.

> **Proposed (fields).** Fields the proposals introduce, all optional and joining the table only when their proposal is accepted: `body_encoding`, `body_uri` (I-17), `body_schema` (I-18), `body_checksum` (U-1), `previous_checksum` (U-5), `use_constraints` (I-23b), `origin` (I-8), `tombstone`, `forgotten_at`, `reason` (U-10); the provenance key `accountable` (I-3b); the evidence keys `version`, `origin` (U-2), `confidence`, `assessed_by`, `assessed_at` (I-20); and the runtime-only `auditable` (I-13).

### 1.4 Profiles at a glance

A deployment claims only what it implements. **Minimal**: the required fields, a body, and unknown fields preserved; a folder of markdown memories with no other metadata meets it. **Audit**: every memory traces to an accountable human (3.1.3), carries `checksum` and `version`, and keeps a verifiable history (3.3.3); meant for multi-user deployments. A system that claims it is audit-grade. Two more profiles set no field requirements: the markdown loading profile (3.6.6) and the federation binding (3.6.4). The checklists are 3.7.

## Part 2. Goals and scope

### 2.1 Goals

The protocol standardizes two things: an **exchange format**, the metadata that travels with a memory so one system can export it and another import and represent it, for portability and data ownership; and **runtime plug-in points**, what an agent harness consumes at runtime and where a memory system plugs in, so harnesses and memory systems can be built and chosen independently. Everything standardized MUST work down to a folder of memory files on one laptop and up to a multi-user, multi-scope deployment with access control.

Three goals judge the design.

1. **Adoption.** A folder of markdown memories, a database-backed store and a graph store can all conform with little work; most fields are optional and today's harnesses can meet the minimal profile (3.7). Optional fields go unimplemented, so the protocol SHOULD keep the number of optional fields that matter for interchange small.
2. **Auditability.** When a deployment needs it, every memory can be traced to one or more accountable humans (3.1.3) [agreed], its history verified and its lifecycle events recorded, in tiers (1.2) so individual users do not carry enterprise obligations. Full audit is a multi-user enterprise requirement, not a single-user one. [agreed]
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

> **Proposed (I-25).** No field for line-level attribution is defined; an implementation that needs it derives it from the diffs between the retained revisions (3.3.3), and a revision a forget has emptied (3.3.6) cannot be attributed line by line. An extension field carrying precomputed line attribution MUST name the revisions it was computed between and MUST NOT change the meaning of `provenance`.

#### 3.1.2 Writers are contributors

Any process that writes a memory, including forget, consolidation and other maintenance agents, MUST appear in `provenance` like any other writer. What those agents do is not defined (Notes E).

#### 3.1.3 Accountable human

A memory is auditable if it can be traced to one or more accountable humans. [agreed] In the audit profile (3.7) every memory MUST carry at least one `provenance` entry with `kind: human`, and SHOULD mark which human is accountable when several appear (for example the person who gave the instructions and the person who approved).

> **Proposed (I-3b).** A `provenance` entry MAY carry `accountable: true`, meaningful only on an entry with `kind: human`. This replaces the SHOULD of 3.1.3 with a MUST: in the audit profile a memory with more than one human entry MUST mark at least one of them `accountable: true`, a memory with exactly one human entry treats that entry as accountable, and several entries MAY carry it. A `kind: system` or `kind: agent` entry MUST NOT carry it; the operator who runs a maintenance agent appears as a human entry (3.1.2).

Accountability is assigned, not a sign-off on each memory. For a consolidation or other maintenance agent the accountable human MAY be the operator who runs it. A store that cannot name one does not claim the audit profile; it is still a conforming store.

#### 3.1.4 Evidence

`evidence` records what a memory rests on: source material, transcript turns, other memories, or a person's statement. Each entry is a reference, or a plain string when the source is not addressable. A reference MAY point outside the store: a file, a URL, a record in a system of record, or a turn in a transcript. Implementations SHOULD distinguish how the memory relates to its evidence: observed, stated by a person, inferred by a model, or derived from other memories. Evidence records origin, not truth. A derived memory whose evidence is unavailable MUST say so rather than omit the field silently. Evidence that points outside the store MAY be excluded from an export; what happens then is 3.5.5.

> **Proposed (U-2).** An evidence entry is a plain string or an object with `ref` (a memory `identifier`, a URI or a path), `relation` (`observed`, `stated`, `inferred` or `derived`), `dangling` (boolean), `at` (ISO 8601, when the evidence was recorded) and, when `ref` is a memory, the optional `version` and `origin` keys with the meaning they have on a link edge (3.2); `ref` MAY be omitted only when `dangling` is true. A memory is derived when it carries a `derived_from` link or an evidence entry with `relation: derived` or `inferred`. A derived memory whose evidence is unavailable, or was excluded from the export, MUST keep one entry per missing source with `dangling: true`, so the audit requirement is met by a marked gap and never by an absent field. Unknown keys on an entry are extension keys and MUST be preserved (1.3).

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

An implementation MAY carry its own score as an extension field. It SHOULD name the system that produced the score, so that a receiver does not mistake it for a portable value. Relative ordering within one `origin` travels as `weight` (1.3).

### 3.2 Links and lineage

Evidence and lineage form a graph whose nodes are memories and sources. How the graph is built, stored and traversed is left to the implementation. An audit-grade system MUST be able to reconstruct the full chain behind a memory; other systems MAY leave nodes unconnected. [agreed] The protocol does not require full provenance on every object. Consolidation SHOULD name all its inputs.

> **Proposed (I-6).** The minimum lineage an audit-grade system keeps is one hop per memory: every derived memory MUST name its direct inputs, as `evidence` entries (3.1.4) or `derived_from` links (3.2), at the revision that was processed where the input is versioned; the full chain is reconstructed by following those hops, so no fixed depth is standardized. Consolidation MUST name all its inputs in the audit profile and SHOULD elsewhere, except re-graining at import (I-2b), which MUST name them in every profile. An input that was forgotten (3.3.6) or left out of an export is still part of the chain as a tombstone or a dangling reference (3.5.5); reconstruction reaches it and stops there.

Memories MAY reference each other, by inline links in the body (for example wiki syntax `[[identifier]]`, which works in any format that carries text) or by typed edges in the metadata (`links: [{target, rel}]`, with `rel` values such as `derived_from`, `supersedes`, `relates_to`). The two are not exclusive.

> **Proposed (I-5b).** Links are typed edges in the metadata, `links: [{target, rel, version, origin}]`: `target` is an `identifier` in the exporting `origin` unless the edge's optional `origin` names another store, the optional `version` pins one revision and is omitted to mean the current one, and `rel` is `supersedes`, `derived_from`, `relates_to`, `contradicts` (I-23a) or an implementation's own dot-prefixed value, which a receiver MUST preserve. Inline links in the body MAY stay; the protocol does not parse bodies, so an inline link that must survive import MUST also be stated as an edge, and a receiver MAY derive edges from inline links it understands. `links` stays optional in every profile.

Links and evidence are separate fields: evidence answers why to believe a memory and may point outside the store; links answer how memories relate to each other. Unresolvable targets: 3.5.5.

> **Proposed (I-23a).** `contradicts` is a standard `rel` value: a memory that disagrees with another MUST link to it with `rel: contradicts`, and the contradiction MUST NOT by itself supersede, invalidate or delete either memory; both stay current until one is superseded (3.3.4) or passes `valid_until`. A store that revises the contradicted memory to record the dispute SHOULD add a `provenance` entry with `contribution: contradicted` and `at`, whose `evidence` SHOULD name the contradicting memory. Current reads SHOULD surface both sides of an unresolved contradiction rather than pick one.

### 3.3 Versioning and lifecycle

#### 3.3.1 Stores and snapshots

Stores that change memories in place and stores that only write superseding revisions are both supported; neither is required (3.3.3 states the audit profile's rule).

By default an export is a snapshot as of the manifest's `exported_at` (Notes D). History travels only when the export declares it (audit profile, 3.7; federation, 3.6.4).

> **Proposed (U-6).** In a full-history export each revision is serialized as its own memory object; every revision of one memory carries the same `identifier` and its own `version`, `updated_at`, `checksum` and `provenance`, and the pair `identifier` plus `version` MUST be unique among the objects of the export. This refines the uniqueness rule of the `identifier` row (1.3), which stands for snapshots and selections: there one object per memory is exported and `identifier` alone MUST be unique; a tombstone (U-10) counts as a revision, and a snapshot carries a tombstone only for a memory whose every revision is forgotten. A receiver MUST read objects sharing an `identifier` as revisions of one memory, ordered by the declared comparator, never as duplicates.

#### 3.3.2 Version

When present, the format of `version` is left to the implementation (a sequence number, a semantic version or other). The implementation MUST declare a comparator. The comparator MAY report two versions as **incomparable**, for example revisions on different branches where both are valid; versions need not be totally ordered. Wall-clock time SHOULD NOT be the comparator. `identifier` stays the same across versions (1.3).

> **Proposed (I-4).** `version` MUST be a scalar, an integer or a string. The comparator MUST be one of `integer` (numeric order, the default), `semver` (Semantic Versioning 2.0.0 precedence), `opaque` (equality only; distinct values are incomparable) or a name an implementation registers under its own dot prefix (`contextnest.checkpoint`); a receiver that does not know a comparator MUST treat the versions as incomparable and MUST NOT fall back to `updated_at` or any wall-clock time. The exporting implementation declares the comparator once per export, in the manifest (3.5.1) as `version_comparator`; when the manifest omits it, or there is no manifest, the comparator is `integer`, and a memory MUST NOT carry a comparator of its own. The `{value, comparator}` object form is withdrawn in favour of the scalar `version: 2`.

#### 3.3.3 Immutable revisions

A change SHOULD create a new revision that supersedes the old one, rather than overwrite it in place, so history can be read as of a point in time. This is RECOMMENDED, not required. In the audit profile (3.7), immutable revisions and a verifiable history (for example a hash chain) are REQUIRED.

> **Proposed (U-5).** In the audit profile a store MUST keep every revision it has exported, and every revision a current revision supersedes, as a stored revision or a tombstone (3.3.6), and MUST be able to export them as a full history (3.3.1); a delete of a retained revision is a forget and leaves a tombstone. A revision, once written, MUST NOT later appear under the same `identifier` and `version` with a different `checksum`; how a store achieves that (append-only files, a database log, retained copies) is left to the implementation. The history SHOULD be verifiable by a hash chain: each revision MAY carry `previous_checksum` (string), the `checksum` of the revision it supersedes, which a receiver checks under 3.5.3. This is the audit-profile item of 3.7.

Even where the body never changes, a system MAY update lifecycle metadata such as `valid_until`, supersession links and forget markers.

#### 3.3.4 Invalidation and supersession

A memory stops applying at its `valid_until` without being deleted. A newer revision or another memory MAY supersede it with a `supersedes` link (3.2). Current reads SHOULD exclude memories past `valid_until` and superseded memories. Historical reads SHOULD be explicit.

#### 3.3.5 Delete

A conforming store MAY delete a memory. A delete SHOULD leave an audit record (who, when, why) with no content. A delete does not by itself stop the content from coming back on a later import (3.3.6).

> **Proposed (I-7a).** A delete or forget MUST NOT by itself delete memories derived from its target. Every `evidence` entry or link that pointed at the deleted memory becomes a dangling reference (3.5.5), kept and marked, so each derived memory stays until the deployment's policy deletes it, invalidates it with `valid_until` (3.3.4) or re-derives it; which policy applies is left to implementations. A reviewer finds the affected memories by those marks; neither the audit record nor the tombstone lists them. The rule applies in every profile.

#### 3.3.6 Forget, tombstones and anti-resurrection

A **forget** erases a memory's content on purpose, for example to honor an erasure request, while its history stays verifiable. A **tombstone** is the record a forget leaves behind. This section states the outcomes a conforming store delivers; how it achieves them is left to implementations (Notes E).

- After a forget, the content of every revision it covers MUST NOT be retrievable from the store or from its exports.
- A store that offers a verifiable history (3.3.3) MUST still verify after a forget.
- A forget MUST leave a tombstone that records when it happened, who did it and why. The tombstone MUST NOT contain the forgotten content.
- **Anti-resurrection.** A receiving system MUST NOT restore forgotten content from an older archive or a pre-forget copy.

Tombstones travel with exports (3.5) so that receivers can tell. Recognizing a re-imported memory needs `origin` plus `identifier`; showing that a copy predates the forget needs `exported_at` (both from the manifest, Notes D).

> **Proposed (U-10).** A tombstone is serialized as a memory object that carries the required fields of 1.3 with the covered memory's `created_at`, an empty `body` under `media_type: text/plain`, `tombstone: true`, `forgotten_at` (ISO 8601), `reason` (one of `user_request`, `legal`, `retention_expiry`, `error`; no free text) and a `provenance` list naming who forgot it with `contribution: forgot` and `at`, since a forget is a writer (3.1.2); in the audit profile that list names the operator as the accountable human (3.1.3). It keeps the `identifier` and, where versioning is in use, the `version` of the revision it covers (one tombstone per covered revision in a full-history export, U-6), and MAY keep that revision's `checksum`, so a hash chain (U-5) still verifies. It MUST NOT carry `title`, `tags`, `evidence` or any other field that restates the forgotten content; a store MAY add its own tombstone fields as extension keys. Anti-resurrection (3.3.6) binds a receiver for the covered revisions only.

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

> **Proposed (I-13).** `auditable` is an optional boolean of the runtime representation, computed by the serving system and never set by the agent or stored in interchange: `true` when the memory meets 3.1.3 (an accountable human) and, if derived, carries `evidence` (3.1.4); `false` otherwise, including when `provenance` is missing (3.1.5). A retrieval response MAY carry one `auditable` for the whole result, which MUST be `true` only when every memory returned is auditable. The flag is derived from fields 1.3 already defines and adds no field or tier to the memory; the audit log that records retrievals stays out of scope. The 3.4 table gains the row `auditable` (derived): interchange no, runtime MAY be shown.

Runtime access control is enforced by the serving system using interchange fields (1.3, `scope` row).

### 3.5 Exchange

#### 3.5.1 Manifest dependency

This draft depends on these manifest fields (working text in Notes D):

- `origin`: with `identifier`, the memory's global key (1.3); identifies a re-imported memory (3.3.6); the party whose claims imported provenance and evidence are (3.5.7).
- `exported_at`: the time the export is as of (3.3.1); shows whether a copy predates a forget (3.3.6).
- `protocol_version`, and the profiles the export follows (3.7).
- The body formats present (1.3).
- Whether the export is a complete snapshot, a selection or a full history (3.3.1).
- The transfer intent (3.5.2).

The version comparator is declared in the manifest (I-4). Absence from a partial export MUST NOT be read as deletion.

#### 3.5.2 Transfer intent

An export MUST declare its intent: **copy**, the source keeps its memories; **move**, the source deletes its memories only after a durable, conforming import on the receiving side; **federation**, no transfer, the memory is read where it resides (3.6.4). A receiving system that assigns its own identifiers MUST keep the origin-to-local mapping.

> **Proposed (I-8).** An imported memory MUST keep its `identifier`; `origin` plus `identifier` (1.3) names the same memory in every store it passes through, and a receiver MUST NOT mint a new `identifier` for a memory it preserves. A receiver MAY address the memory by a local identifier of its own, in which case it MUST keep the origin-to-local mapping and report it in the receipt (3.5.4), and on re-export it MUST emit the origin pair, carrying an optional per-memory `origin` field (string) wherever the memory's origin is not the manifest's. A receiver that re-derives rather than preserves MUST give the new memory its own `identifier` under its own `origin` and a `derived_from` link (3.2) to the origin pair.

> **Proposed (U-3).** Transfer intent is a requirement of the exchange, not of the memory, and this replaces the MUST of 3.5.2: it lives in the manifest as `intent`, one of `copy`, `move` or `federation` with the meanings in 3.5.2; an export with a manifest declares it there, and an export without a manifest or without the field is a `copy`, since copy obliges the source to nothing. No intent field is placed on the memory. This draft keeps what each intent means and the receiver's duties under it (the mapping in 3.5.2, the receipt in 3.5.4); the manifest proposal owns the field.

#### 3.5.3 Fidelity

The receiving side SHOULD be able to check that it received the same memory with the same history. In the audit profile, it MUST be able to, using `checksum` (1.3) and the verifiable history (3.3.3).

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

The markdown loading profile is the directory and loading contract of a root `MEMORY.md`: deeper files deferred, deferred memory surfaced one level down, and selective reads. Metadata is carried as front matter or in a sidecar, and `path` (1.3) records each file's place. When a projection to this profile drops fields, it MUST declare the loss. Hierarchy metadata beyond `path`: I-19 (1.3).

> **Proposed (U-15).** A file without front matter or sidecar derives its required fields: `identifier` and `path` are the file's relative path, `media_type` follows the extension (`.md` is `text/markdown`, otherwise `text/plain`), and `created_at` is the file's creation time or, where unavailable, its modification time. Front matter is YAML between `---` lines at the top of the file; a sidecar is `<file>.meta.yaml` beside the file with the same keys; front matter wins where both exist.

### 3.7 Conformance profiles

What each profile of 1.4 requires, each item pointing to the section that states the rule. An export's manifest declares the profiles it follows (Notes D). Whether "markdown loading" and "federation binding" remain declarable profile names is handed to the manifest proposal (Notes D).

**Minimal profile.** The required fields of 1.3 (`identifier`, `media_type`, `created_at`), a body, and an export that preserves unknown fields (1.3). Reachable from a folder of markdown memories with no other metadata. Provenance and versioning are not required (3.1.5, 3.3.2).

> **Proposed (U-13).** The dangling-reference rules of 3.5.5 belong to the minimal profile: every conforming import MUST keep a reference it cannot resolve and MUST NOT fail because of it, and a kept reference whose target the receiver cannot resolve counts as marked; the explicit `dangling` marker on the entry (U-2) and the evaluation note stay audit-profile items. Transfer intent is a rule on the export, not a field requirement of any profile (U-3), so a bare folder of markdown stays conformant.

**Markdown loading profile.** The loading contract of 3.6.6: a root `MEMORY.md`, deferred deeper files surfaced one level down, selective reads, metadata in front matter or a sidecar, `path` on each file (1.3), and a declared loss for every field the projection drops.

**Federation binding.** The endpoint set of 3.6.4 with a capability endpoint, each server declaring its capabilities; memory objects cross it in the runtime representation (3.4); identity passes through to each server (3.6.4).

**Audit profile.** Everything in the minimal profile, plus:

- `provenance` on every memory, with an accountable human (3.1.3);
- `checksum` and `version` on every memory (1.3);
- immutable revisions with a verifiable history (3.3.3);
- evidence on derived memories (3.1.4);
- recorded lifecycle events, including deletes (3.3.5);
- dangling references kept and marked (3.5.5); when a system is evaluated against this profile, its dangling references are noted;
- forget, tombstones and anti-resurrection (3.3.6).

> **Proposed (I-7b).** Forget, tombstones and anti-resurrection (3.3.6) belong to the minimal profile, not only the audit profile: every conforming store MUST deliver the four outcomes of 3.3.6 when it forgets, and every conforming receiver MUST honour anti-resurrection for the revisions a tombstone covers (U-10), because a receiver without the audit profile is exactly the one that would otherwise bring forgotten content back. The audit profile adds only the verifiable history over the tombstones (U-5).

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

No `provenance`, so the author is unknown (3.1.5). No `version`, so it cannot claim the audit profile (3.7). No `protocol_version`: the minimal profile does not require it on the memory (1.3); the manifest carries it for the export as a whole (Notes D).
