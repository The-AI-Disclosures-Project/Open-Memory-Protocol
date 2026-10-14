# Open Memory Protocol: Memory Object, Exchange and Runtime

**Editors' draft v0.2, 2026-10-14**. Exchange and Runtime sub-thread, written with the Memory Model and Context (MM&C) overlap in mind. Not an adopted OMP standard.

**Sources.** This draft distills the proposals in `early-draft-specs/` on `main`: the scoping note (Strauss and Rosenblat), Packer v0.2 (Letta), IBM v0.1, AIDP / FMP, Cognee v0.1, Context Nest v0.1 and the AMS Card (Mila / Mozilla). It also draws on the 2026-09-28 exchange-and-runtime call, the 2026-10-14 technical working meeting, the review comments on PR #13, Cognee's header proposals in PR #16, and the #exchange-and-runtime thread. Section references in parentheses point to the source draft, for example (IBM), (Cognee §3.5), (CN §6.3). "Call" means the 2026-09-28 call. "10-14" means the 2026-10-14 meeting. "Review" means a comment on PR #13.

### Changes since v0.1

- "Header" is now **metadata** (10-14), and `type` is now **`media_type`** (review).
- The draft now states its goals and non-goals up front (§0.2): it is a transfer format, not a storage format. Markdown is neither required nor preferred (10-14).
- `version` is **audit-required**, not required. Stores that change memories in place and stores that never change them are both supported (10-14, §6).
- **`valid_until`** replaces `invalidated_at` and may be a future date (10-14). `created_at` records when the system learned something; `valid_from` records when it became true (10-14).
- `provenance` is optional outside the audit profile. An exporter that doesn't know who wrote a memory leaves it out rather than inventing it (review, §4.5).
- New: a `stub` flag (§2.4), `path` kept separate from `identifier` (§3.2), `origin` and `exported_at` in the manifest (§8.1), a rule for dangling references (§8.5), and a note on trust when importing (§8.7).
- Accuracy and confidence are handled through provenance and evidence, as an editors' proposal (§4.6).
- The thin core with semantic conventions is listed as an open proposal (§3.3).
- Provenance `role` is now `contribution`, and `model` is now `name` (review).

---

## 0. Status, scope and conventions

### 0.1 Status

This is a working draft for discussion. Every section carries a status:

- **[agreed]**: at least two participants explicitly agreed on a call and nobody objected.
- **[proposed]**: put forward on a call, in a review or in a source draft and not contested, but nobody explicitly signed on.
- **[open]**: raised and not resolved.
- **[discussed]**, **[no objection]**, **[parked]**: used for metadata fields, as in the call notes.
- **[editors]**: text the editors added to make the draft complete. It has not been discussed yet.

### 0.2 Goals, non-goals and scope [proposed, 10-14]

The protocol standardizes two things (10-14):

1. **An exchange format.** What metadata travels with a memory so that one system can export it and another can import it and represent it well. This serves portability and data ownership.
2. **Runtime plug-in points.** What an agent harness consumes at runtime, and where a memory system plugs in, so that memory systems and harnesses can be built and chosen independently.

Everything standardized MUST work down to a folder of memory files on one laptop and up to a multi-user, multi-scope deployment with access control (10-14).

**Non-goals.** This is a transfer format, not a storage format. The protocol says nothing about how a system stores, indexes or looks up memories. Markdown is not required for storage or for the exported body (10-14). The semantic scope of a single memory (a fact, a document) is out of scope for now (10-14, §2.3).

In scope: the memory object (its metadata and body), the fields it carries, how memories link to each other and to evidence, versioning and lifecycle, the export/import (interchange) representation, the runtime representation, and the shape of what crosses a runtime binding. Also out of scope: everything listed in §11.

### 0.3 Conventions

The key words MUST, MUST NOT, SHOULD, SHOULD NOT, MAY and RECOMMENDED are to be read as in RFC 2119 and RFC 8174. **In this draft, every normative statement is proposed.** A MUST states what the editors propose the requirement should be once adopted. It does not claim the group has agreed to it.

---

## 1. Goals

The design is judged against three goals.

1. **Adoption.** A folder of markdown memories, a database-backed store and a graph store can all conform with little work. Most metadata fields are optional, and the smallest profile (§10.1) can be met by today's harnesses.
2. **Auditability.** When a deployment needs it, every memory can be traced to one or more accountable humans (§4.3) [agreed], its history can be verified, and its lifecycle events are recorded. These requirements sit in tiers (§3.1) so that individual users are not forced to carry enterprise obligations. Full audit is a multi-user enterprise requirement, not a single-user one [agreed].
3. **Room for innovation.** The protocol standardizes interfaces and the shape of data, not algorithms. Recall, ranking, confidence scoring, federation merge logic, memory-maintenance agents, retrieval isolation and audit-log delivery are left to implementations to compete on (§11).

---

## 2. The memory object

### 2.1 Metadata plus body [agreed]

A memory is **metadata** plus a **body**.

- The **metadata** is a rigorous schema that can be rendered into any format that renders schemas (JSON, YAML front matter, a database row). It is for the system that manages the memory. v0.1 called it the header. "Metadata" avoids implying a file (10-14).
- The **body** is what is semantically relevant to the agent. It is a string in any text format, declared by the `media_type` field (§3).

This is a two-sided data contract: stable metadata that changes only through versioning or lifecycle events (§6.2), and a free-form payload the protocol does not prescribe (Cognee, from the call).

Whether a body can be a structured value rather than a string is issue I-17 (review).

### 2.2 Body formats [agreed, 10-14]

The body MAY be in any text format: markdown, plain text, JSON, DocLang, XML (for example PubMed), HTML, CSV and others. `media_type` declares which. Implementations need not process every format. The protocol does not prefer markdown. Much agent memory today is markdown, and this design keeps it conformant without making it the standard (10-14).

The base object is the metadata plus a typed body, not a markdown file (call; 10-14). Section 10.2 defines how a markdown-first loading profile relates to that (Packer).

Some sources need more than a media type. Structured or relational sources and opaque documents such as PDFs are handled differently downstream. Whether to add an optional schema or source-type field is issue I-18 (10-14).

### 2.3 Atomic unit [deferred, 10-14]

The protocol does not fix the size of a memory. One view: a memory is the smallest semantic unit that carries meaning and can be evaluated true or false (Cognee, from the call). Another: memories are documents with titles and authors, as in document stores (CN, Packer). The metadata in §3 is written to work for both. The 2026-10-14 meeting kept this out of scope for now. See issue I-2.

### 2.4 Stubs [proposed, 10-14]

A memory MAY be a **stub**. Its body is a summary or pointer, and the full body has to be fetched before use, much as skills sit in context as stubs (Wes, 10-14). A stub carries `stub: true` so that an agent knows to fetch the full body if it needs it.

---

## 3. Metadata fields

### 3.1 Tiers [proposed]

Each field carries one tier (proposed by Gabe on the call):

| Tier | Meaning |
|---|---|
| **required** | Every conforming memory carries it |
| **audit-required** | Required in the audit profile (§10.4); optional otherwise |
| **ACL-required** | Required where access control applies; interchange only |
| **optional** | May be omitted in every profile |

Optional fields tend to go unimplemented, so the protocol SHOULD keep the number of optional fields that matter for interchange small (from the call).

**Every tier assignment in §3.2 is proposed by the editors, except `version` and `updated_at`, which were read back on 2026-10-14.**

### 3.2 Field table

| Field | Type | Tier [editors] | Status | Definition |
|---|---|---|---|---|
| `identifier` | string | required | [proposed] | Identifies the memory within its origin system, and stays the same across all versions of that memory (10-14). Carries no required meaning. UUIDs are RECOMMENDED (10-14). MUST be unique among the memories in one export. Together with the manifest's `origin` (§8.1), forms a global key (review; Cognee PR #16). Replaces `title` as the key (call; IBM "memory identifier"; Cognee §3.1) |
| `path` | string | optional | [proposed, 10-14] | Where the memory sat in the origin store's hierarchy, for example a folder path. Kept separate from `identifier` because folder structure carries discovery and progressive-disclosure information (Sruly, 10-14). See issue I-19 |
| `title` | string | optional | [proposed] | A human-readable label. May duplicate the body for fact-sized memories (call) |
| `media_type` | string | required | [discussed] | The content or media type of the body (for example `text/markdown`, `application/json`, `text/html`, `text/csv`, `application/xml`). Not a semantic ontology. Renamed from `type`, which agent harnesses already use for the kind of a memory (review; CN; call) |
| `stub` | boolean | optional | [proposed, 10-14] | `true` when the body is a summary or pointer and the full body must be fetched (§2.4) |
| `tags` | list of strings | optional | [discussed] | Semantic tags. Free-form, or values drawn from a vocabulary declared elsewhere (for example a JSON-LD `@context` or schema.org). This is where a system records the kind of a memory (fact, preference, decision, observation) without the protocol requiring an ontology (IBM; CN; 10-14). Tags MAY cross into the runtime representation (§7.2) |
| `scope` | list of strings | ACL-required | [proposed] | Scope tags that access policy attaches to. Set by the system, never by the agent. Interchange only (§7). A scope tag is neither an access grant nor proof of ownership (IBM; Cognee §3.3; call) |
| `created_at` | ISO 8601 timestamp | required | [no objection] | When the system recorded the memory. Distinct from when the claim became true (`valid_from`) (10-14) |
| `valid_from` | ISO 8601 timestamp | optional | [proposed, 10-14] | When the claim became true in the world (IBM; Cognee §3.5; 10-14) |
| `valid_until` | ISO 8601 timestamp | optional | [agreed, 10-14] | When the claim stops being true. MAY be in the future, for example a temporary workaround to retry at a set time. Replaces `invalidated_at` (review; 10-14) |
| `version` | opaque, with a declared comparator | audit-required | [proposed, 10-14] | The revision of this memory. See §6.1 |
| `updated_at` | ISO 8601 timestamp | optional | [proposed, 10-14] | When this revision was written. Allows stores that change memories in place (10-14) |
| `checksum` | string (`algorithm:hex`) | audit-required | [no objection] | An integrity hash of the metadata-covered fields plus the body (CN; call). Cognee proposes a second hash of the body alone for deduplication (PR #16), [open] |
| `provenance` | list of contributors | optional; audit-required, with an accountable human | [proposed] | Everyone and everything that contributed. Replaces `author`. A missing `provenance` means the author is unknown (review). See §4 |
| `evidence` | list of references or strings | optional; audit-required when the memory is derived | [open] | What the memory rests on, inside or outside the store. See §4.4 |
| `links` | list of edges | optional | [open] | References to other memories. See §5 |
| `status` | string | optional | [parked] | Lifecycle or visibility state inside a store (for example draft, published). Possibly implementation-specific. If kept, interchange only (call; CN) |

Implementations MAY add fields. Unknown fields MUST be preserved on export and MUST NOT change the meaning of standard fields (Cognee §5).

Cognee's PR #16 proposes further fields (`subject`, `kind`, `accuracy`, an `origin` qualifier, `invalidated_by`, a list shape for evidence). They are reflected here where they overlap (§4.4, §4.6, §6.3, §8.1) and are otherwise left for review there.

### 3.3 A thin core with semantic conventions [open, proposal]

Ilan proposes in review to follow OpenTelemetry and keep the protocol core minimal. A memory would be:

```json
{ "identifier": "MEMORY.md", "media_type": "text/markdown", "body": "The user prefers concise answers.", "attributes": {} }
```

Every other field would become an attribute defined in **semantic conventions**. The conventions would be debated and versioned on their own schedule: the manifest declares `semantic_conventions_version` separately from `protocol_version`. Under this model the tiers of §3.1 and the profiles of §10 would become named sets of conventions.

This was not reached on 2026-10-14 and is not adopted. The draft keeps the field table above until the group decides. See issue I-21.

---

## 4. Provenance and evidence

Provenance and evidence are the protocol's main tools for answering who stands behind a memory and why to believe it. Trust (§8.7) and accuracy (§4.6) build on them rather than adding new fields [editors].

### 4.1 Contributor list [proposed]

`provenance` is a list. Each entry names one contributor:

| Key | Tier [editors] | Meaning |
|---|---|---|
| `id` | required | An identifier for the contributor (a person, an agent, a system) |
| `kind` | required | `human`, `agent` or `system` |
| `contribution` | optional | What the contributor did, for example `authored`, `instructed`, `approved`, `edited`, `imported`, `verified`, `corrected`. Renamed from `role`, which LLM APIs use for user / system / assistant (review) [open] |
| `ai_usage` | optional | How much AI was involved. Values to be aligned directly with EU AI Act terminology (review; IBM; call) [open] |
| `name` | optional | A name for the contributor, whether a human, an agent, a model or a system. Renamed from `model` so that every kind can be named (review) |
| `at` | optional | When this contributor acted |

A plain list lets a memory record, for example, that a person asked an agent to save something and the agent rewrote it, without forcing a single grade on the result (Sruly, call). Whether `contribution` and `ai_usage` are part of the core is open (issue I-3).

### 4.2 Writers are contributors [editors]

Any process that writes a memory, including forget, consolidation and other maintenance agents, MUST appear in `provenance` like any other writer. The protocol does not define what those agents do (§11).

### 4.3 Accountable human [agreed]

A memory is **auditable** if it can be traced to one or more accountable humans. This applies only in the audit profile (§10.4), where every memory MUST carry at least one `provenance` entry with `kind: human`, and SHOULD mark who is accountable when several humans appear (for example the person who gave the instructions and the person who approved) [proposed].

Accountability is assigned, not a sign-off on each memory. For a consolidation or other maintenance agent, the accountable human MAY be the operator who runs that agent (review) [editors]. A system that cannot name an accountable human does not claim the audit profile. It is still a conforming store.

### 4.4 Evidence [open]

`evidence` records what a memory rests on: source material, transcript turns, other memories, or a person's statement. Each entry is a reference or a plain string when the source is not addressable (call). A reference MAY point outside the store: a file, a URL, a record in a system of record, or a turn in a transcript (review). Implementations SHOULD distinguish how the memory relates to its evidence: observed, stated by a person, inferred by a model, or derived from other memories (Cognee §3.2; Cognee PR #16; AIDP ground truth / transcripts / inferences). Evidence records origin, not truth.

A derived memory whose evidence is unavailable MUST say so rather than omit the field silently (Cognee §3.2) [editors].

Evidence that points outside the store may not travel with an export. §8.5 covers what happens then. How to export transcripts, or link to messages inside them, is open (review; issue I-5).

Agent memory is often the wrong home for facts that belong in a system of record, such as a price list or a patient record. A memory SHOULD link to the system of record rather than copy from it (Wes, 10-14) [proposed].

### 4.5 Unknown authorship [proposed]

A store that does not know who wrote a memory (for example a folder of markdown files) MUST leave `provenance` out rather than fill it with guesses. A receiving system MUST read a missing `provenance` as "author unknown". In particular, it MUST NOT read it as the user's own words (review). Such memories conform to the minimal profile but cannot claim the audit profile. This replaces v0.1's heuristic provenance, which a receiver could not tell apart from real provenance.

### 4.6 Accuracy and confidence [open, editors' proposal]

The 2026-10-14 meeting asked whether a memory should carry its accuracy (Vasilije, 10-14; Cognee PR #16 `accuracy`). Two concerns were raised. A score cannot move between systems unless the algorithm that produced it is also standardized. And a system can become confidently wrong through self-reinforcing loops (10-14). Vouching was suggested instead: a model or a person vouches for a memory (Sruly, 10-14).

**Editors' proposal: no standard accuracy or confidence score.** Accuracy is conveyed through provenance and evidence, which already travel:

- **Who checked it** is provenance. A person, an agent or an evaluator (for example an LLM judge) that confirms, corrects or contradicts a memory appears as a contributor with `contribution: verified`, `corrected` or `contradicted`, plus `at`. Humans and agents can be mixed, and the record shows which is which.
- **What the check rests on** is evidence: the source, the transcript or the later memory that confirmed or contradicted it.
- **Receivers compute their own confidence** from those records with their own algorithm, which the protocol leaves to implementations (§11).
- An implementation MAY carry its own score as an extension field. It SHOULD name the system that produced the score, so that a receiver does not mistake it for a portable value.

See issue I-20.

---

## 5. Links, lineage and edges

### 5.1 A graph [agreed]

Evidence and lineage form a graph whose nodes are memories and sources. How the graph is built, stored and traversed is left to the implementation. An audit-grade system MUST be able to reconstruct the full chain behind a memory. Other systems MAY leave nodes unconnected (call).

### 5.2 Depth [open]

The protocol does not require full provenance on every object. The minimum lineage an audit-grade system must keep (n hops back, or the full chain) is open (issue I-6). Consolidation SHOULD name all its inputs (Cognee §3.4).

### 5.3 Links between memories [open]

Memories MAY reference each other. Two carriers are under discussion, and they are not exclusive:

- **Inline links in the body**, for example wiki syntax `[[identifier]]` (CN). These work in any format that can carry text.
- **Typed edges in the metadata**, for example `links: [{target, rel}]`, with `rel` values such as `derived_from`, `supersedes`, `relates_to` (Cognee §3.4; IBM override).

**Links and evidence stay separate** [proposed, 10-14]. Folding evidence into links as a `rel: evidence` edge was suggested in review. On 2026-10-14 the meeting leaned against it: evidence answers why to believe a memory and may point outside the store, while links answer how memories relate to each other.

Open: what a link targets (identifier, or identifier at a version) and whether edges are typed in the core. See issue I-5. Missing targets are covered in §8.5.

---

## 6. Versioning and lifecycle

Both kinds of store are supported: those that change memories in place and those that never change a memory and write superseding revisions instead. Neither is required (10-14) [proposed]. IBM originally proposed immutable memories with supersession for everything. Most systems may work that way, but requiring it would rule out memory files edited in place on disk (10-14).

Whether versioning belongs in a point-in-time export at all was raised in review and again on 2026-10-14. By default an export is a snapshot as of its `exported_at` time (§8.1). History travels only when the export declares it (audit profile, federation) [proposed].

### 6.1 Version slot [proposed, 10-14]

`version` is audit-required (§3.2). When present, its format is left to the implementation (a sequence number, semantic version or other), and the implementation MUST declare a comparator (IBM). The comparator MAY report two versions as **incomparable**, for example revisions on different branches where both are valid. Versions need not be totally ordered (Mike, 10-14). Wall-clock time SHOULD NOT be the comparator (call). `identifier` stays the same across versions (§3.2).

### 6.2 Immutable revisions [open]

A change SHOULD create a new revision that supersedes the old one, rather than overwrite it in place, so history can be read "as of" a point in time (IBM; Cognee §3.1; CN). This is RECOMMENDED, not required (call; 10-14). **Proposed by the editors:** in the audit profile (§10.4), immutable revisions and a verifiable history (for example a hash chain) are REQUIRED.

Even where the body never changes, a system MAY update lifecycle metadata such as `valid_until`, supersession links and forget markers (10-14) [proposed].

### 6.3 Invalidation and supersession [proposed]

Recording time is distinct from when a claim applies (Cognee §3.5; 10-14). A memory stops applying at its `valid_until` without being deleted (IBM; 10-14). A newer revision or another memory MAY supersede it with a `supersedes` link. Cognee proposes the reverse pointer, `invalidated_by`, on the superseded memory (PR #16). Current reads SHOULD exclude memories past `valid_until` and superseded memories. Historical reads SHOULD be explicit (Cognee §3.5).

### 6.4 Delete [proposed]

A conforming store MAY delete a memory (IBM; AIDP `/fmp/delete`; Cognee; CN). A delete SHOULD leave an audit record (who, when, why) with no content. A delete does not by itself stop the content from coming back on a later import. What a delete means for memories derived from the deleted one is open (review; issue I-7).

### 6.5 Forget, tombstones and anti-resurrection [proposed]

A **forget** erases a memory's content on purpose, for example to honor an erasure request, while its history stays verifiable (Cognee §3.5; CN §6.3). A **tombstone** is the record a forget leaves behind. This section states the outcomes a conforming store delivers. How a store achieves them is left to implementations (§11).

The need goes beyond regulated erasure requests. Some deployments must be able to remove content immediately, whatever their retention rules, for example classified information stored by mistake. That was raised on 2026-10-14 as something the spec should make implementable, though not a requirement for every store (Wes, 10-14).

- After a forget, the content of every revision it covers MUST NOT be retrievable from the store or from its exports.
- A store that offers a verifiable history (§6.2) MUST still verify after a forget.
- A forget MUST leave a tombstone that records when it happened, who did it and why. The tombstone MUST NOT contain the forgotten content.
- **Anti-resurrection.** A receiving system MUST NOT restore forgotten content from an older archive or a pre-forget copy. Tombstones travel with exports (§8) so that receivers can tell. Recognizing a re-imported memory needs `origin` plus `identifier`. Showing that a copy predates the forget needs `exported_at` (review; §8.1).

Without tombstones, an interchange rule that turns every re-import into a new memory lets an invalidated or deleted memory come back from an old archive (Cognee §3.5). Cross-draft adapter fixtures reproduce this case. **Editors' proposal for issue I-7:** this section belongs to the audit profile (§10.4), not the core.

---

## 7. Representations

### 7.1 Interchange is a superset of runtime [agreed]

There are two representations of the same memory (call):

- **Interchange** (export and import, migration): the full metadata, including operational fields a receiving system needs to integrate the memory.
- **Runtime** (what an agent sees): a projection of the interchange form. It omits fields that would add noise to the agent's context or reveal how the store is organized. Metadata the agent does not need can make it perform worse (10-14).

This lines up with keeping metadata out of the agent's view, for example a markdown body the agent reads with structured metadata stored separately (AIDP, thread).

### 7.2 Field placement [proposed]

Which fields reach the agent is left to each memory system. It takes the interchange form and uses whatever subset helps (review). The table below is guidance, not a requirement.

| Field | Interchange | Runtime |
|---|---|---|
| `identifier`, `media_type`, `body` | yes | yes |
| `stub` | yes | yes, when true |
| `title`, `tags`, `created_at` | yes | yes |
| `path` | yes | MAY be shown, for progressive disclosure |
| `version`, `updated_at`, `valid_from`, `valid_until` | yes | when the implementation needs them |
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

Every export SHOULD begin with a manifest that declares:

- `protocol_version`, and the profiles the export follows (§10);
- `origin`: an identifier generated once per store. `origin` plus `identifier` is the global key of a memory, the way CloudEvents uses `source` plus `id` (review; Cognee PR #16). Without it, two people who each export a `MEMORY.md` produce colliding identifiers;
- `exported_at`: the time the export is as of. It orders exports, and shows that a copy predates a forget (§6.5) (review);
- the body formats present;
- whether it is a complete snapshot, a selection, or a full history (including memories no longer valid, for example for forensic review (10-14));
- any required extensions (Cognee §3.6).

Absence from a partial export MUST NOT be read as deletion (Cognee §3.6).

### 8.2 Transfer intent [open]

An export MUST declare its intent (Cognee §3.6):

- **copy**: the source keeps its memories.
- **move**: the source deletes its memories only after a durable, conforming import on the receiving side.
- **federation**: no transfer. The memory is read where it resides (AIDP).

IBM's draft treats a memory as valid in one system at a time, with an import creating a new memory in the receiving system. Cognee's draft keeps the origin identity across copies. With `origin` in the manifest (§8.1), the origin key survives either way. Whether an imported memory keeps its origin `identifier` or receives a new one with a recorded mapping is issue I-8. A receiving system that assigns its own identifiers MUST keep the origin-to-local mapping (Cognee §3.1) [editors].

### 8.3 Fidelity [proposed, raised in the thread]

The receiving side SHOULD be able to check that it received the same memory with the same history. In the audit profile, it MUST be able to, using `checksum` and the verifiable history (§6.2).

### 8.4 Receipts [proposed]

An import SHOULD produce a receipt that lists, per memory, whether it was accepted, transformed, omitted or rejected, with reasons and any identifier mappings (Cognee §3.6). Retries MUST NOT duplicate memories. A round-trip field report found a store that applied 208 records and kept none, with no warning (PR #12). Receipts make that case visible.

### 8.5 Dangling references [proposed, 10-14]

A link or an evidence reference may point at something the receiver cannot resolve. The target may have been left out of a partial export or deleted. It may live outside the store, such as a session log, a file or a system of record. Or the reader's scope may not include it, so a reference that resolves for one person dangles for another (10-14). The following is proposed by Gabe, 10-14:

- A system MUST be able to hold dangling references. It MUST keep them and mark them as dangling rather than drop them silently.
- An import MUST NOT fail because of a dangling reference.
- A system MAY try to resolve dangling references during import or later, including by asking a person.
- When a system is evaluated against the audit profile, its dangling references are noted.

A dangling reference can still mean something in the audit chain even when nobody can follow it. Some dangling references point at things that should never have been stored as memory in the first place (Wes, 10-14; §4.4).

### 8.6 Credentials [editors]

Credentials (passwords, API keys, tokens) are not memory and MUST NOT be exported as memory (Cognee §3.3).

### 8.7 Trust on import [open, 10-14]

A receiving system cannot verify provenance that was recorded in a system it doesn't control. An imported provenance chain is a claim, and it can be laundered (Wes, 10-14). Receivers SHOULD treat imported provenance and evidence as claims made by the exporting `origin`, not as facts. `checksum` and a verifiable history let a receiver check integrity, not truth. Receivers MAY review or sanitize imported memories before agents rely on them. How to do that is left to implementations. A third-party chain of trust for provenance is out of scope for now (10-14). See issue I-22.

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

The protocol MUST NOT fix a signature for recall. Implementations provide their own recall and their own guidance on using it. The protocol defines what recall returns (memory objects in the runtime representation), not how it is called (call). Review asked whether federation needs some standard recall. That is part of issue I-15.

A write needs, at minimum, an author, a time, and whether it creates a memory or revises an existing one (call) [proposed].

### 9.4 Federation [agreed]

When several memory servers are connected, a federation layer MAY sit between them and the agent and present one unified memory. How it merges results and combines scopes is left to the implementation (AIDP; call). Identity MUST pass through the federation layer to each server (call).

### 9.5 Change notification [proposed]

Memory can change during a session. How a harness learns that a memory it already loaded has changed (for example through MCP resource subscriptions) is left to implementations (review). Issue I-11 is closed unless the group reopens it.

### 9.6 Multiple memories [open]

Whether a server returns several memories compiled into one payload or as separate objects, and whether memories can nest, is issue I-12. If they are returned separately, each carries its own runtime metadata.

---

## 10. Conformance levels [editors]

Profiles let a deployment claim only what it implements (Cognee §5). An export's manifest declares its profiles. Under the thin-core proposal (§3.3), each profile would become a named set of semantic conventions.

### 10.1 Minimal profile

The required fields of §3.2 (`identifier`, `media_type`, `created_at`), a body, and an export that preserves unknown fields. Meant to be reachable from a folder of markdown memories with no other metadata. Provenance and versioning are not required (§4.5, §6.1).

### 10.2 Markdown loading profile

The directory and loading contract of Packer: a root `MEMORY.md`, deeper files deferred, deferred memory surfaced one level down, and selective reads (Packer). Metadata fields are carried as front matter or in a sidecar, and `path` (§3.2) records each file's place. When a projection to this profile drops fields, it MUST declare the loss (Cognee §2).

### 10.3 Federation binding

The endpoint set of AIDP / FMP (upload, search, read, delete, and a required capability endpoint), carrying memory objects in the runtime representation (AIDP). Each server declares its capabilities.

### 10.4 Audit profile

Everything in the minimal profile, plus:

- `provenance` on every memory, with an accountable human (§4.3);
- `checksum` and `version` on every memory;
- immutable revisions with a verifiable history (§6.2);
- evidence on derived memories (§4.4);
- recorded lifecycle events, including deletes;
- dangling references kept and marked (§8.5);
- forget, tombstones and anti-resurrection (§6.5, editors' proposal for issue I-7).

---

## 11. Out of scope

Left to implementations, so that they can compete and improve on them:

- Storage, indexing, lookup, embeddings and internal mutation (all drafts; 10-14). In particular, markdown is not required as a storage format.
- The semantic scope of a single memory, for now (10-14; issue I-2).
- The recall function signature, ranking and retrieval algorithms [agreed].
- Confidence, accuracy and decay scoring, and how they weigh recency (10-14; §4.6).
- Federation merge and ranking logic (§9.4) [agreed].
- Memory-maintenance agents (forget, consolidation, "dream" agents) and their algorithms. Their writes still carry provenance (§4.2).
- Forget mechanics: how content is erased, what a store keeps so its history still verifies, and the tombstone format beyond the fields named in §6.5.
- Retrieval isolation, such as limits on graph traversal depth.
- Audit-log storage and delivery. The protocol may define a flag saying whether a memory or a retrieval is auditable (issue I-13), but not the log.
- Access-control systems. The protocol carries `scope` tags that access policy attaches to, but does not define the policy language (IBM; CN).
- Third-party chains of trust for provenance, and how imported memories are sanitized (§8.7).

---

## 12. Open issues

| # | Issue | Where |
|---|---|---|
| I-1 | ~~Markdown as the common body format vs the base object~~. Settled 10-14: the base object is metadata plus a typed body, and markdown is not preferred | §2.2 |
| I-2 | The atomic unit: the smallest meaningful claim, or a document. Deferred 10-14 | §2.3 |
| I-3 | The shape of provenance: whether `contribution` and `ai_usage` are core, the EU AI Act terms for `ai_usage`, and how to record several accountable humans | §4.1, §4.3 |
| I-4 | Versioning: the form of `version` and its comparator (including incomparable versions). Mostly settled 10-14: audit-required, and in-place updates allowed | §6.1, §6.2 |
| I-5 | Links: inline, metadata edges, or both; what a link targets; how transcripts are exported or linked | §4.4, §5.3 |
| I-6 | Lineage depth required for audit | §5.2 |
| I-7 | Tombstones, anti-resurrection and delete of derived memories: core or audit profile. Editors propose audit | §6.4, §6.5 |
| I-8 | Identity on import: keep the origin identifier, or assign a new one with a mapping (`origin` now in the manifest) | §8.1, §8.2 |
| I-9 | ~~How an export declares inferred provenance~~. Replaced by §4.5: absent provenance means unknown | §4.5 |
| I-10 | Runtime binding: MCP, hooks, CLI, or several | §9.2 |
| I-11 | ~~Change notification during a session~~. Left to implementations (review) | §9.5 |
| I-12 | Compiled vs separate memories at runtime, and nesting | §9.6 |
| I-13 | An auditable flag on memories and retrievals | §11 |
| I-14 | Status and visibility: standardize or leave to implementations (parked) | §3.2 |
| I-15 | Identity and scope granularity for federation, and whether federation needs any standard recall (review) | §9.3, §9.4 |
| I-16 | Whether the tier assignments in §3.2 hold | §3 |
| I-17 | Whether a body can be a structured value rather than a string (review) | §2.1 |
| I-18 | An optional schema or source-type field for structured sources and opaque documents; is a query-backed memory the query output or its source data (10-14) | §2.2 |
| I-19 | Folder taxonomy and other hierarchy metadata beyond `path` (10-14) | §3.2, §10.2 |
| I-20 | Accuracy and confidence through provenance and evidence (editors' proposal), vs a standard field (Cognee PR #16) | §4.6 |
| I-21 | A thin core with separately versioned semantic conventions (review) | §3.3 |
| I-22 | Trust and sanitization of imported memories | §8.7 |

---

## Appendix A. Example in JSON (interchange)

Manifest:

```json
{
  "protocol_version": "0.2",
  "profiles": ["minimal", "audit"],
  "origin": "store:6f1c2a9e-4b7d-4e2a-9c1f-3d8e5a7b0c42",
  "exported_at": "2026-10-14T18:00:00Z",
  "selection": "snapshot",
  "intent": "copy",
  "media_types": ["text/markdown"]
}
```

One memory:

```json
{
  "identifier": "9b2e7c14-3f6a-4d1e-8a5b-2c7f9e0d4b31",
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
  "body": "Status updates are due Fridays from Sep 15. They were due Tuesdays before that."
}
```

## Appendix B. The same memory as markdown with front matter (runtime projection)

```markdown
---
identifier: 9b2e7c14-3f6a-4d1e-8a5b-2c7f9e0d4b31
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

`scope`, `checksum`, the `approved` and `verified` provenance entries and the audit fields are omitted from the runtime projection (§7.2). They remain in the interchange form.

## Appendix C. The smallest conforming memory (minimal profile)

```markdown
---
identifier: MEMORY.md
media_type: text/markdown
created_at: 2026-10-14T00:00:00Z
---

The user prefers concise answers.
```

No `provenance`, so the author is unknown (§4.5). No `version`, so it cannot claim the audit profile.

---

## Acknowledgements

Built from the proposals by Charles Packer (Letta), Gabe Goodhart and colleagues (IBM), Sruly Rosenblat and Ilan Strauss (AI Disclosures Project), Vasilije Markovic (Cognee), Misha Sulpovar (Context Nest), and Mila and Mozilla (AMS Card). It also draws on the 2026-09-28 call with Gabe Goodhart, Sruly Rosenblat, Vasilije Markovic, Alex Hancock and Misha Sulpovar, and on the review comments on PR #13 by Gabe Goodhart (with Rynne and Anna Lisa), Sruly Rosenblat and Ilan Strauss. v0.2 also reflects the 2026-10-14 technical working meeting and its participants, including Wes Jackson.
