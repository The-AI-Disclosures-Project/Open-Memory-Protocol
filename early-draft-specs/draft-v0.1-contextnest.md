# Context Nest proposal: a governed Markdown profile for portable agent memory

**Discussion draft v0.1 | September 22, 2026 | PromptOwl contribution to OMPI**

**Status:** Proposed for discussion; not an adopted OMP standard. Context Nest 1.0 is a published specification with a reference implementation (the `ctx` CLI, an MCP server, the ContextNest desktop app, and a hosted nest server). Everything in §§3–5 is implemented and in daily use. §6.3 (the forget protocol) and the items marked *proposed* are not yet implemented and are offered here for the working group to shape.

**Spec:** [`github.com/PromptOwl/context-nest-spec`](https://github.com/PromptOwl/context-nest-spec) (`CONTEXT_NEST_SPEC.md`, Apache-2.0). The working copy in [`PromptOwl/ContextNest`](https://github.com/PromptOwl/ContextNest/blob/main/CONTEXT_NEST_SPEC.md) is ahead of it on the status lifecycle and client metadata; references of the form CN §n point at that copy, and Appendix A reproduces its version-history, checkpoint, and integrity sections.

---

## 0. Summary

**Eight keys and a link syntax. That is the entire wire format.**

A memory is a Markdown file with YAML front matter carrying eight keys (`title`, `type`, `tags`, `status`, `version`, `created_at`, `updated_at`, `checksum`) and links to other memories written in the prose. No schema to negotiate, no tokens spent at inference on a runtime handshake, nothing a person cannot read or `git diff`.

Everything else this proposal adds sits *around* that file, not inside it: a URI scheme so a memory can be addressed (and pinned to a point in time), a selector grammar so a set of memories can be named, an append-only version history with a hash chain so a memory can be trusted, and (proposed) a forget protocol so a memory can be removed without breaking the trust of what remains.

The bet is that a memory protocol gets adopted by being small. Any harness that already writes Markdown with front matter is one small change away from compliance; any harness that wants provenance, approval state, and audit replay gets them without leaving Markdown.

## 1. What OMP should standardize, and what it should not

The working group's areas of concern include the **atomic unit** of a memory, **runtime access** to it, and the **user constraints** on it (right to edit, right to be forgotten, right to leave). This proposal answers each of the three with a primitive that already exists in Context Nest, and proposes one more: a forget operation designed so that integrity verification still passes afterwards.

| Area | Primitive proposed here | CN reference |
|---|---|---|
| Atomic unit | Markdown + eight front-matter keys + in-prose links | §3 |
| Runtime access | `contextnest://` addressing + selector grammar; CLI/MCP/HTTP as bindings | §4 |
| User constraints | `status` (approval state), `version` + `checksum` + hash chain (the record), forget protocol | §5, §6 |

**Deliberately out of scope**, in agreement with several of the existing drafts:

- **Storage engine.** Files on disk, SQLite, a graph database, an object store: the protocol does not care. Storage is an implementation detail, not an interoperability semantic. Context Nest happens to be files, and the reference implementation indexes them into SQLite for search; a conforming implementation could do the reverse and *instantiate* Markdown to the user on demand.
- **Permissioning / RBAC.** Every organization already has one, and every harness integrates differently. Baking one in would deter adoption. The protocol records *who authored, who approved, who edited*; it does not say *who may read*. This is an open question for the working group, not a settled opinion.
- **The ontology itself.** The protocol defines the *shape* of a knowledge graph (typed nodes, tags, links in prose, `derived_from` lineage) and leaves the semantics to the vault. Two organizations can exchange nests without agreeing on a taxonomy, because the taxonomy travels with the content.

## 2. Relationship to the existing work

**Letta / Packer draft (v0.2).** Memories are Markdown; the only contract is what enters the context window. Context Nest is a Packer-compliant memory with front matter made mandatory and given eight fixed keys. Everything in §4–§6 is additive; a Packer-only harness can ignore it and still read every Context Nest file.

**IBM draft (v0.1).** Object and runtime foundations. Context Nest's `type` field and `derived_from` lineage are the object model; §4 is the runtime surface. Where IBM's draft asks for "the shape of an ontology but not the ontology," §3.3 is the concrete answer.

**AI Disclosures Project draft (v0.1).** Federation. Context Nest's namespace model (CN §4.0: `none` / `federated` / `scoped`) is a federation binding: a nest declares whether it resolves foreign URIs, and against which allow-list. Remote documents are never indexed locally, so publish decisions stay with their author.

**Cognee proposal (v0.1).** The semantic core. Context Nest supplies concrete carriers for four of its six parts: *identity and revision* (path + `version`), *provenance and lineage* (`derived_from`, `edited_by`, the hash chain), *time, lifecycle, and deletion* (`status`, `created_at`/`updated_at`, and the forget protocol in §6.3, which adopts cognee's "protection against unintended resurrection" as a hard requirement), and *exchange fidelity* (§6.2). *Scope, ownership, and authority* is the RBAC question left open above.

**Agent Memory System Card (Mila / Mozilla).** The reporting home. A Context Nest implementation should publish an AMS Card; this proposal does not duplicate any of its axes. The evaluation dimensions in OMP PR #6 (assembly fidelity, staleness resistance, cross-model consistency) are intended as inputs to a card, not a rival to one.

**`me.md` (Block / goose).** The same instinct at the personal scale: files on the user's machine, agents *propose*, the user decides. A `me.md` directory is a valid single-namespace nest; §6.2 makes the "user decides" step a `status: draft → published` transition with an author on record.

**Standards sketch (OMP PR #4).** Its four headings map directly: *Memory Object Format* → §3; *Memory Access Protocol* → §4; *Memory Rights* → §6; *Security Considerations* → §5 (tamper-evidence) and §6.3 (erasure that preserves verifiability).

**Prior art.** Cited in [`prior-art/`](../prior-art/); Context Nest's own entry is in `prior-art/emerging-standards.md`.

## 3. The atomic unit: eight keys and a link syntax

### 3.1 The file

```markdown
---
title: API Design Guidelines
type: document
tags: ["#engineering", "#api"]
status: published
version: 3
created_at: 2026-01-15T10:30:00Z
updated_at: 2026-02-01T14:22:00Z
checksum: sha256:a1b2c3…
---

# API Design Guidelines

Errors follow [Error Handling](contextnest://engineering/error-handling#codes).
Supersedes the v2 rules pinned at [checkpoint 7](contextnest://engineering/api-design@7).
```

| Key | Type | Role |
|---|---|---|
| `title` | string | Human name; resolution falls back to the filename |
| `type` | enum | **Structural** classification: `document`, `snippet`, `glossary`, `persona`, `prompt`, `source`, `tool`, `reference`, `skill` (CN §1.6) |
| `tags` | string[] | **Semantic** classification, `#`-prefixed, shared taxonomy |
| `status` | `draft` \| `pending_review` \| `approved` \| `published` \| `rejected` | Approval state (Appendix A.1); by default the resolver serves `published` only |
| `version` | integer ≥ 1 | Monotonic; bumped on publish |
| `created_at`, `updated_at` | ISO 8601 | Lifespan bounds |
| `checksum` | `sha256:<hex>` | SHA-256 of the body; the record primitive, living in the node rather than a sidecar |

Context Nest 1.0 (CN §1.4–1.5) requires only `title` and defaults the rest. **The OMP profile proposed here requires all eight to be present**, because the eight are what make a memory addressable, approvable, and verifiable without any external index. Optional keys (`author`, `description`, `derived_from`, `metadata`, `source`) are defined in CN §1.5 and any tool may add prefixed keys (CN §14).

The split between `type` (structural) and `tags` (semantic) is deliberate: the atomic unit carries both kinds of classification without a second key set.

### 3.2 Links

Edges are written in the prose, not in a ninth key:

```
[Title](contextnest://path)              floating: latest published version
[Title](contextnest://path#anchor)       a section
[Title](contextnest://path@N)            pinned: the version at nest checkpoint N
```

Obsidian-style wikilinks (`[[Title]]`, `[[Title#anchor]]`, `[[Title|alias]]`, `[[nodes/id]]`) produce the same `reference` edge as a `contextnest://` link (CN §1.7, §5.1). The target resolves against document titles first, case-insensitively, then paths; aliases and anchors are display-only, and a target that matches no published document produces no edge. `derived_from` (front matter, list of URIs) records lineage separately from reference, so "this summary was made from that transcript" is distinguishable from "this doc mentions that doc."

### 3.3 Why the graph lives in the prose

A separate edge index can fall out of sync with the content it describes; a link in the sentence that needs it cannot. Backlinks, the relationship graph (`context.yaml`, CN §5), and folder indexes (`INDEX.md`, CN §10) are all *derived* from the files and regenerable from them. This is the "shape of an ontology": the protocol fixes how nodes are typed, tagged, linked, and descended from one another, and says nothing about what the types and tags mean. Two nests with disjoint taxonomies still exchange cleanly, because the taxonomy is data.

## 4. Runtime: addressing, selection, and bindings

### 4.1 Addressing (CN §4)

`contextnest://` is the address. The scheme resolves paths, sections, tags (`contextnest://tag/x`), folders (`…/folder/`), full-text (`contextnest://search/q`), and pinned versions (`@N`). Pinned resolution returns the version recorded at checkpoint N of the *whole nest*, so an agent's context can be replayed exactly. Every resolution is logged (CN §9.2).

### 4.2 Selection (CN §2)

A selector names a set: atoms (`#tag`, `type:x`, `status:x`, a URI, `pack:id`) combined with `+` (AND), `|` (OR), `-` (NOT), and parentheses. A **pack** (CN §3) is a named, saved selector, stored as a YAML file in `packs/`, with optional includes, excludes, and agent instructions.

This is the protocol's answer to **context bleed**, the failure where a memory system silently mixes the user's roles and a question asked as a parent is answered as if asked by an executive. People are multitudes; the fix is not more context but *scoped* context:

```
#family -#work                 the parent, not the CEO
pack:standup                   three docs + two live sources, and nothing else
type:persona + #support        the agent's own role, isolated from the user's
```

Packs are the concrete form of what the field has been calling "memory views," "node sets," and "per-scope toggles." Because every access is traced with the document, version, and checkpoint it resolved to (CN §9.2), *which* view the agent used is on the record and can be rebuilt. More context does not mean better outcomes; a bounded, named, replayable set does.

### 4.3 Bindings

The protocol is the middle layer between inference-time context and storage. CLI (`ctx query <selector>`), MCP, and HTTP are bindings; a conforming implementation MUST expose at least one, and MUST resolve the same selector to the same set through each. The resolver returns documents; it never executes anything. Live data enters through `type: source` nodes (CN §1.9), which are human-readable runbooks describing a tool call; the *agent* hydrates them, and the trace records what it saw (`result_hash`), not the payload.

## 5. Governance: status, version, checksum

Three of the eight keys are governance primitives, and together they answer the objection that plain-text memory cannot be tamper-checked.

- **`status`** is approval state. The resolver serves `published` only; `pending_review` and `approved` let a revision sit in review without reaching an agent, and `rejected` is terminal and cannot be republished by accident (Appendix A.1). A draft cannot enter an agent's context by accident, and someone is on record for every transition. In a regulated setting this is the hook for "who approved what the agent knows": accountability for the *authorship of context*, which is the part of knowledge management nobody volunteers for and the part an auditor asks about first.
- **`version` + `checksum`** are the record. Each publish appends an entry to `.versions/<doc>/history.yaml` (CN §6) carrying `content_hash` and a `chain_hash` computed over the previous entry's chain hash, the content hash, the version, the editor, and the timestamp (CN §8.2). History files are append-only; `ctx verify` recomputes every chain and reports the first mismatch.
- **Checkpoints** (CN §7) bind every document's chain into a nest-level chain, so a checkpoint number identifies the state of the entire graph. The audit answer is complete and short: *the agent used document X, version 4, at checkpoint 7, last edited by Y on date Z*, and checkpoint 7 can be rebuilt to see exactly what it saw. This is traceability and inspection of the context plane.

Nothing here requires leaving Markdown, and nothing here is visible to a harness that does not want it.

### 5.1 Temporality: four clocks, one replayable past

A memory system has to answer two different time questions: *what is true now*, and *what did the agent know then*. Context Nest keeps them apart by recording time at four levels, each with its own meaning:

| Clock | Where it lives | Question it answers |
|---|---|---|
| `created_at`, `updated_at` | Front matter | When did this memory first exist, and when did its content last change? |
| `edited_at` | Each version entry in `history.yaml` | When was this revision *authored*? |
| `published_at` | Each version entry in `history.yaml` | When was this revision *approved* and made visible to agents? Absent if it never was. |
| `at` on a checkpoint | `.versions/context_history.yaml` | When did the *whole graph* take this shape? |

Separating `edited_at` from `published_at` is what lets a draft sit in review without leaking into context, and lets an auditor see the gap between a change being written and a change being trusted. `published_at` is also the source of truth for the checkpoint log: if that log is lost, it is rebuilt deterministically by replaying every published version in `published_at` order (Appendix A.4).

The past is addressed by checkpoint, not by timestamp. `contextnest://path@N` returns the version recorded in checkpoint N's `document_versions` map, and returns null if the document was not published at that checkpoint. Because a checkpoint pins every document at once, a pinned read gives a view of the graph where every document comes from the same moment. A link from A to B cannot resolve to a B that was published after A was read. Floating links (no `@N`) always return the latest published version, so staleness is a property of the link the author chose, not something the resolver guesses at.

What this does not do, and says so: it does not model *valid time* (when a fact was true in the world, as opposed to when it was recorded). A memory about a job someone held from 2019 to 2023 carries those dates in its content. Whether OMP needs a valid-time pair in front matter is left as an open question (§10). §6.3.5 proposes the two lifespan keys that are about the record, not the world: `expires_at` and `retain_until`.

## 6. User constraints: edit, leave, forget

### 6.1 Right to edit

It is a file. Editing bumps `version`, records `edited_by` and `edited_at`, and the previous version remains reconstructible. A user-owned nest is edited with any text editor; the reference implementation includes an editor but does not require one.

### 6.2 Right to leave

Export *is* the directory. A nest is a folder of Markdown with two regenerable YAML indexes and a `.versions/` tree; moving it is `cp`. Import into any Packer-compliant harness is lossless at the file level and loses only what that harness chooses not to read. Import into another Context Nest implementation preserves history, chains, and checkpoints, and `ctx verify` on the receiving side proves nothing was altered in transit. This is the export mechanism that makes ontology portability real, and it is the property a procurement requirement can name: *the vendor must hand back the nest, verifiable*.

### 6.3 Right to be forgotten: the forget protocol *(proposed)*

**The problem.** Append-only, hash-chained history is what makes a memory trustworthy, and it is precisely what makes erasure hard. Naive deletion of a version breaks every chain hash after it; naive deletion of a file leaves the content alive in keyframes, diffs, caches, derived documents, exports, and the context windows of agents that already read it. This section proposes an operation that honors the right while leaving verification intact.

**6.3.1 The forget operation.** `forget` takes a node, or a version range of a node, and a `reason_code` from a closed set: `user_request`, `legal`, `retention_expiry`, `error`. It never takes free text; the reason for forgetting is not itself stored in the nest.

**6.3.2 Tombstones preserve the chain.** For each forgotten version entry in `history.yaml`: the keyframe file is deleted and the `diff` field removed; `content_hash` and `chain_hash` are retained unchanged; the entry gains `tombstone: true`, `forgotten_at`, `forgotten_by`, `reason_code`. Because `chain_hash[n]` is computed from `content_hash[n]` and not from the content, every later entry still verifies. Verification treats a tombstoned entry as *hash-only*: it checks the chain, skips content recomputation, and reports the entry as `tombstoned` rather than `content_hash_mismatch`. The chain proves that something existed, when, and by whom; it no longer proves what.

**Storage consequence.** History is stored as keyframes plus forward diffs (Appendix A.2), so erasing one version touches its neighbours. Forgetting a version range MUST (a) write a fresh keyframe for the first retained version after the range, so later versions stay reconstructible without the erased content, and (b) re-express that retained version's diff so no context lines from the forgotten versions survive. The retained entries' `content_hash` values refer to their original stored form, so the re-keyframed entry is marked `rekeyed: true` with the new snapshot's hash alongside, and verification checks the new hash for that entry while the chain continues from the retained `chain_hash`. Node-level forget sidesteps this by tombstoning every version.

**6.3.3 Node-level forget.** The live file is replaced by a stub carrying the eight keys with `status: forgotten` and an empty body. Resolution of any `contextnest://` URI for that path, floating *or* pinned `@N`, returns `forgotten`, not `null`. An agent learns the memory was deliberately removed, which is different information from "never existed," and MUST NOT treat the stub as content. Selectors exclude `forgotten` nodes unless asked for them explicitly (`status:forgotten`). `forgotten` differs from `rejected` (Appendix A.1): a rejected node is hidden but its content and history remain, while a forgotten node keeps only its hashes. `forgotten` is a proposed sixth status value. An implementation that predates it normalizes the unknown value to `draft` (CN §1.5.1), which keeps the stub out of default retrieval, so the failure mode of an old reader is a hidden empty draft, not resurrected content.

**6.3.4 Anti-resurrection.** A forget MUST propagate:

- *Lineage.* Every node whose `derived_from` includes the forgotten URI is flagged `review_required: true` *(proposed key)* and listed in the forget result. The protocol does not auto-delete derived content (a summary of ten transcripts is not erased because one was), but it does refuse to let the derivation go unreviewed. Clearing the flag is a human publish.
- *Caches.* Any cached hydration or resolution keyed by a `result_hash` or `checksum` of the forgotten content is invalidated.
- *Packs.* Packs are selectors and re-evaluate on the next read. A pack whose `includes` names the forgotten URI resolves that entry to `forgotten`.
- *Exports and federation.* An exported nest carries tombstones; an importing implementation MUST honor them and MUST NOT reconstruct forgotten versions from a pre-forget copy it holds. A federated resolver returns `forgotten` across namespaces.
- *Checkpoints.* Existing checkpoints are not rewritten; a checkpoint that references a forgotten version resolves that document to `forgotten`. A forget is a content-publishing operation (the stub replaces the body), so it cuts a checkpoint like any publish (CN §7.1), and the boundary is on the record.

**6.3.5 Retention and lifespan.** Two optional front-matter keys *(proposed)*: `expires_at` (ISO 8601) triggers an automatic `forget` with `reason_code: retention_expiry`; `retain_until` blocks `forget` for non-`legal` reasons before that date. Decay, scoring, and consolidation are implementation-defined; the protocol fixes only the terminal state.

**6.3.6 The honest boundary.** A forget cannot reach a context window that already consumed the content, a model that was trained on it, or a copy outside the nest. The protocol records the boundary rather than pretending it away: the trace shows the last access before the forget, and the tombstone shows the forget. That is the most a portable memory format can promise.

**6.3.7 What stays.** By default, `edited_by` and timestamps survive on a tombstone: the fact that a person edited a document on a date is metadata about the nest, not content of the memory. Under `reason_code: legal` an implementation MAY replace `edited_by` with its SHA-256. Because `edited_by[n]` is an input to `chain_hash[n]` (Appendix A.5), this has a defined cost: verification of a tombstoned entry does not recompute that entry's own `chain_hash`. It accepts the stored value and checks that the next entry chains from it. Every later entry, and every checkpoint's `document_chain_hashes` binding, still verifies. What is lost is independent verification of the tombstoned entry's own metadata, which is the point of the erasure.

## 7. Adoption path

- **Harness that writes Markdown with front matter today:** add the missing keys, default `status: published`, compute `checksum`. One small change; no runtime change.
- **Harness with an MCP memory server:** expose `resolve(uri)` and `query(selector)`; the resolver contract is CN §9.1.
- **Reference implementation:** the `ctx` CLI (npm `@promptowl/contextnest-cli`) implements §§3–5 today as a CLI binding. A second, independent implementation in a general-purpose harness is the right next test, and this proposal is written so that one can be built from the canonical spec without reading PromptOwl code.
- **Procurement.** A regulated buyer can require, and test: *memories are eight-key Markdown; `verify` passes; export is the directory; `forget` leaves `verify` passing.* Those four sentences are the enforceable form of the right to leave and the right to be forgotten.

**Conformance levels** *(proposed)*: **L0** eight keys + links · **L1** addressing + selectors · **L2** versions, chains, checkpoints, `verify` · **L3** forget protocol + federation.

## 8. Implemented versus proposed

| Item | Status |
|---|---|
| Eight-key front matter, node types, `contextnest://` links | Implemented (CN 1.0 §1, §4) |
| `[[wikilink]]` edges, title-first resolution | Implemented (CN §1.7, §5.1) |
| Selector grammar, packs | Implemented (CN §2, §3) |
| Version history, hash chain, checkpoints, `ctx verify` | Implemented (CN §6–§8) |
| Five-value status lifecycle with alias normalization | Implemented (CN §1.5.1; `ctx` 2.6.0) |
| `edited_at` / `published_at` split, checkpoint rebuild from `published_at` | Implemented (CN §6.2, §7.3) |
| `client` caller metadata on versions and traces | Specified (CN §9.4) |
| Source nodes and hydration tracing | Implemented (CN §1.9, §9.3) |
| Namespaces and federation modes | Specified (CN §4.0); implementation partial |
| OMP profile: all eight keys required | Proposed |
| Forget protocol (§6.3): tombstones, `status: forgotten`, propagation, `expires_at`, `retain_until`, `review_required` | Proposed; not implemented |
| Conformance levels | Proposed |

## 9. Evaluation

Whether a memory system makes an agent better is not settled by its format. OMP PR #6 (open for reference while the group settles scope) proposes three evaluation dimensions: assembly fidelity (did the context assembled match the context intended), staleness resistance (does the system prefer the current published version under drift), and cross-model consistency, which a pack-and-checkpoint model makes measurable, because the intended set and the served set are both on the record. Results belong in an AMS Card.

## 10. Open questions for the working group

1. **Permissioning.** Should OMP define a read-authorization *shape* (not a system) the way §3.3 defines an ontology shape? This proposal leaves it out and would like to be argued with.
2. **Forget across trust boundaries.** §6.3.4 requires importers to honor tombstones; what, if anything, can a protocol do about an importer that does not?
3. **Key set.** Are eight the right eight? `author` is the obvious ninth; it is optional here because it is often an org, not a person, and `edited_by` in history already carries the accountable identity.
4. **Valid time.** §5.1 records when a memory was written, approved, and served, not when the fact it states was true. Should the OMP profile add an optional valid-time pair (`valid_from` / `valid_until`), or leave world-time in the content?


## Appendix A. Version history, checkpoints, and integrity (excerpted)

Condensed from the Context Nest specification as maintained in [`PromptOwl/ContextNest`](https://github.com/PromptOwl/ContextNest/blob/main/CONTEXT_NEST_SPEC.md) (§1.5.1, §4.1, §6–§8, §9.4), included here so the proposal can be implemented without leaving this repository. Normative keywords are as in that document.

### A.1 Status lifecycle (CN §1.5.1)

`status` is a five-value enum. Implementations MUST normalize raw values to one of these before validation, retrieval, or indexing.

| Canonical | Meaning | Served to agents? |
|---|---|---|
| `draft` | Editable scratch state. Default. | Only on an explicit opt-in. |
| `pending_review` | Submitted; reviewer has not signed off. | No |
| `approved` | Signed off; awaiting publish. | No |
| `published` | Live. | Yes, and by default the only one. |
| `rejected` | Terminal hide. | No. Implementations MUST refuse to publish a rejected document, to prevent silent resurrection. |

Synonyms from other systems (`active`, `live`, `archived`, `in_review`, `superseded`, ...) are accepted case-insensitively and canonicalized on the next write; unknown values fall back to `draft`. No state machine is enforced. **Metadata-only transitions (for example `published → rejected`) MUST NOT cut a new version; only content-publishing operations bump `version` and emit a checkpoint.**

### A.2 Storage model (CN §6.1)

History lives in `.versions/<doc>/` beside the live file. Version 1 and every `keyframe_interval`-th version (default 10) are stored as full snapshots (`v1.md`, `v10.md`); every other version is a unified diff from its predecessor, stored inline in `history.yaml`. Any version is reconstructed by applying diffs forward from the nearest keyframe, and implementations MUST be able to do so. The live file is always the authoritative latest version; `.versions/` is history only.

### A.3 Version entries (CN §6.2)

Each entry in `history.yaml` records:

- `version`: integer
- `keyframe`: `true` if a snapshot exists; otherwise omitted
- `diff`: unified diff from the previous version (omitted for keyframes)
- `edited_by`: author identity
- `edited_at`: when the revision was authored (ISO 8601)
- `published_at`: when it was published; omitted if it never was
- `note`: reason for change (optional)
- `content_hash`, `chain_hash`: see A.5
- `client`: optional caller metadata (A.6)

```yaml
keyframe_interval: 10
versions:
  - version: 1
    keyframe: true
    edited_by: john.doe@example.com
    edited_at: 2024-01-15T10:30:00Z
    published_at: 2024-01-20T09:00:00Z
    note: "Initial draft"
    content_hash: sha256:3a7bd3e2…
    chain_hash:   sha256:f4c2b3a1…
    client: { agent: claude-code, session_id: sess-9f2c41 }
  - version: 2
    diff: |
      @@ -5,3 +5,5 @@
       existing line
      +new line added
    edited_by: jane.smith@example.com
    edited_at: 2024-01-18T11:00:00Z
    published_at: 2024-01-22T14:00:00Z
    content_hash: sha256:9b2c1a4d…
    chain_hash:   sha256:1d3e5f7a…
```

### A.4 Nest checkpoints (CN §7)

Per-document versions alone cannot keep cross-links consistent: when B is republished, every link to B moves with it. A **checkpoint** is an immutable snapshot of the whole graph, the equivalent of a commit.

- Every publish (and only a publish, never a draft save) appends a checkpoint to `.versions/context_history.yaml` and updates `checkpoint` / `checkpoint_at` in `context.yaml`.
- Each entry records `checkpoint` (monotonic integer), `at`, `triggered_by` (the document whose publish created it), `document_versions` (every published path → its version at that instant), `document_chain_hashes` (every path → that version's `chain_hash`), and `checkpoint_hash`.
- The log is append-only and MUST NOT be edited by hand.
- **Rebuild.** If the log is missing or corrupt, implementations MUST rebuild it from the per-document histories. Collect every `{path, version, published_at}` where `published_at` is present. Sort by `published_at`, breaking ties by path and then version. Replay in that order, snapshotting a running `document_versions` map at each step and numbering the checkpoints from 1. From intact histories, the rebuild is equivalent to the original.
- **Pinned resolution (CN §4.1).** `path@N` reads checkpoint N's `document_versions`. It returns null if the path was not published at N. `@N` is a non-negative integer with no leading zeros; `@07` MUST be rejected. For a source node, a pinned read returns the *instructions* as authored at N, never a historical tool result.

### A.5 Integrity (CN §8)

```
content_hash[n]    = SHA-256(keyframe file text | diff string)
chain_hash[n]      = SHA-256(chain_hash[n-1] ":" content_hash[n] ":" version[n] ":" edited_by[n] ":" edited_at[n])
checkpoint_hash[n] = SHA-256(checkpoint_hash[n-1] ":" checkpoint[n] ":" at[n] ":" triggered_by[n] ":"
                             canonical_versions[n] ":" canonical_chain_hashes[n])
```

The genesis value for both chains is `contextnest:genesis:v1`. The two maps are serialized as JSON with sorted keys and no whitespace. Inputs are UTF-8; output is `sha256:<64 lowercase hex>`. Verifiers MUST reject an unknown algorithm prefix rather than pass it.

Writers MUST compute both hashes for every new entry; hash fields MUST NOT be modified once written. Checkpoints bind to the document chains through `document_chain_hashes`, so rewriting a document's history after a checkpoint is detectable even if the rewritten chain is internally consistent.

**Verification** is read-only and idempotent. It recomputes every `content_hash` and `chain_hash`, confirms each checkpoint's `document_chain_hashes` against the document histories, recomputes the checkpoint chain, and reports `content_hash_mismatch`, `chain_hash_mismatch`, `cross_chain_mismatch`, or `checkpoint_hash_mismatch` with the version or checkpoint affected. Failures MUST be surfaced, never silently ignored.

### A.6 Client metadata (CN §9.4)

Reads and writes SHOULD accept an optional `client` object (`agent`, `session_id`, plus bounded scalar custom keys), recorded on the version entry a publish seals and on the access traces a read emits. It answers "which agent wrote v7, in which session." It is a **label, not an identity claim**: implementations MUST NOT authorize from it, and it MUST NOT be an input to any hash. That is why histories recorded before any caller sent one still verify unchanged.

## Review basis

Context Nest Specification 1.0 at `PromptOwl/context-nest-spec` `main` as of 2026-09-22; OMP repository `main` as of 2026-09-22. This document is contributed under CC BY 4.0 per OMPI governance; the Context Nest specification and reference implementation keep their own licences.
