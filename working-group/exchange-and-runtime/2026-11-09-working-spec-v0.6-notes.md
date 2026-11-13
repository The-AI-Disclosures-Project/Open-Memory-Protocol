# Open Memory Protocol v0.6: Open questions, proposals and record

Companion to [editors' draft v0.6](2026-11-09-working-spec-v0.6.md). Plain section numbers (1.3, 3.5.1) refer to that document; lettered sections (C.2, H) to this one. Agreed decisions are in [the decisions document](2026-11-09-working-spec-v0.6-decisions.md).

## A. Proposed resolutions in v0.6

Every open question of v0.5 carries a proposed resolution in the specification, as a **Proposed (id)** block under the section it affects. The group accepts or rejects each one; until then the unmarked text beside it is the rule. This table gives the reason behind each proposal and the precedent it follows.

| Proposal | Where | Why |
|---|---|---|
| I-17 | 1.1 | The smallest reading of the agreed rule that a body may be any MIME-typed format while implementations need not process every format: one string slot, one encoding flag, and the existing stub for references. Precedent: Cognee §3.2 (text as baseline, other media embedded or referenced through typed descriptors with verifiable integrity), Sapience KO-1 v2 §6 (media by reference), the 11-06 decision that non-text bodies are allowed but not required. |
| I-18 | 1.1 | Answers both 10-14 sub-questions with the fields the draft already has plus one pointer field, keeping optional interchange fields few (2.1). Precedent: Cognee §3.2 epistemic roles and AIDP's ground truth / transcripts / inferences (now evidence relations), Context Nest's `type: source` and proposed `retrieval` block (the fetched copy is the memory, the fetch is its provenance), IBM's `source material` reference, Wes 10-14 on systems of record. |
| I-2a | 1.1 | Follows the 10-14 decision to leave the grain out of scope and the Sapience draft's own reading that granularity is a deployment choice (KO-3 §3.1: a KO may be a fact, a chunk or a versioned belief), while giving implementers the one rule they need: identity, not size, makes a memory. The Cognee draft (§3.2) likewise lets profiles carry entities, facts, summaries or memory blocks over one core, and `tags` is already the agreed home for the kind of a memory (1.3). |
| I-16 | 1.2 | Gabe proposed the tiers on the call and the group has since confirmed four assignments (`version`, `updated_at` on 10-14; `protocol_version`, `weight` on 11-06) without objecting to the rest, so the smallest resolution is to adopt the editors' table as the baseline and let objections name a row; the validator rule makes the table checkable by code. |
| U-7 | 1.2 | Gabe's call proposal named three tiers (audit-required, ACL-required, optional) and the group recorded that scope feeds access control and is system-set (IBM, AIDP, Cognee §3.3, CN); mapping the tier to a profile of its own, as Context Nest layers L0-L3 and Cognee §5 lets a deployment claim only what it implements, closes the gap without changing `scope`'s tier or its row. |
| I-19 | 1.3 | The smallest rule that lets the markdown loading profile round-trip: Packer's progressive disclosure is a directory tree, Context Nest derives `INDEX.md` and folder indexes from the files rather than storing them, and Sruly's 10-14 reason for keeping `path` was that folder structure already carries the discovery information. |
| I-26 | 1.3 | Keeps the agreed part of the row (optional on the memory, required by the manifest) and takes the 11-06 suggestion of a date-based format to match MCP, the binding most implementers named (I-10); the import rule follows the unknown-fields rule so an older store never rejects a newer memory. |
| U-1 | 1.3 | Gives Cognee PR #16 its deduplication hash as one optional field without touching the agreed `checksum` over metadata plus body, and carries Cognee §3.1's rule that identity is not text equality. Context Nest's body-only `checksum` shows the hash is cheap to compute on markdown stores. |
| I-23b | 1.3 | Uses the two mechanisms I-23 itself names and that 3.1.6 already relies on (a `contradicts` rel and `contribution: contradicted`, which v0.6's 3.1.1 vocabulary lists), and follows Cognee §3.5, where concurrent or unordered claims surface as conflicts instead of being silently resolved; it leaves resolution to implementations (5.4). |
| I-14 | 1.3 | Follows the call, where Gabe placed `status` outside the runtime format and overlapping versioning, and Misha's own description of it as approval state inside a store (Context Nest A.1 serves `published` only by default), so the protocol fixes the serving outcome and not the enum. Closes the parked item without adding an optional field that would go unimplemented (2.1). |
| I-21 | 1.3 | The group's agreed decisions since 10-14 (`media_type` required, `protocol_version` and `weight` optional, `version` audit-required) are decisions about rows of the table, so keeping the table as the core preserves them unchanged, while a second version number would multiply the compatibility matrix the manifest (5.3) and I-26 already have to handle. Profiles as the layering mechanism follow the Cognee draft §5 (RFC 6906 representation profiles over a common core) and the editors' note that the table stands until the group decides (5.1.1). |
| fields | 1.3 | Added in review so a validator built from the field table knows which optional fields the proposals introduce before they are accepted. |
| U-8 | 2.2 | The content is the union of what 3.5.1 says this draft depends on and what 5.3 already lists, so nothing new is invented; the owner follows the September 28 action (Vasilije to return with the missing exchange elements) and the fact that the working text derives from Cognee §3.6 and PR #16. |
| U-4 | 3.1.1 | The rename was done in review of PR #13 and is recorded in the v0.2 changelog and in Part 4's "recorded as decided" list; the open tag in the v0.5 key table was a leftover, so the smallest resolution is to record closure and the one migration rule a reader of old exports needs. |
| I-3a | 3.1.1 | Sruly on the 2026-09-28 call: a plain list of contributors avoids grading the result, which the group preferred to Gabe's none/draft/full AI-usage trailer; deriving the EU AI Act class from `kind` and `contribution` gives IBM's AI-usage disclosure without a second field, honouring the goal of keeping interchange-relevant optional fields few (2.1). |
| I-25 | 3.1.1 | Follows the 2026-11-06 agreement (attribution per revision, line-level MAY be derived from diffs) and Context Nest's precedent of storing history as keyframes plus diffs with `edited_by` per version, so no new standard field is needed; the extension clause reuses the 1.3 extension rule. |
| I-3b | 3.1.3 | Answers the split-accountability question from the September 28 notes (Misha's case: an agent writes on one person's instructions and another approves, ideally both named; regulators care who the accountable human is) with the smallest shape, one boolean, and keeps the agreed MUST of 3.1.3 intact while turning the editors' SHOULD into a checkable rule. |
| U-2 | 3.1.4 | Makes the Appendix A keys normative, which is the smallest shape an importer can code against, and resolves the unavailable-evidence case with the dangling marker Gabe proposed on 10-14 rather than a new field. Precedent: Cognee §3.2 (a derived memory with unavailable evidence must say so), Sapience §3.5 (source kept apart from version links), Context Nest's floating-versus-pinned `@N` links for the optional `version`. |
| I-20 | 3.1.4 | Takes the 10-15 review variant recorded in 5.1.3 and the Sapience draft's knowledge-object placement (confidence is an extraction estimate inside provenance, next to its source, never on the claim), while keeping the settled main question of I-20 and the 10-14 concern that a bare score cannot move between systems. |
| I-5a | 3.1.4 | Context Nest §3.2 keeps wikilinks in the prose but records lineage in a separate front-matter list and pins targets with `@N`, Cognee §3.4 wants derivations to reference exact input revisions, Sapience §3.5 asks to keep evidence apart from links with `supersedes` named, and 10-14 leaned against folding evidence into links; the shape is the one Appendix A uses, so no example changes. |
| I-6 | 3.2 | Keeps the agreed rule (audit-grade reconstructs the full chain, others leave islands) and answers Vasilije's objection on the call that full provenance on every object is too heavy by making the per-object duty one hop, which is exactly what Cognee §3.4 ("a derivation must reference the exact input revisions", "consolidation must name all inputs", deleted lineage keeps its surviving relationship) and Context Nest's per-node `derived_from` already do. |
| I-5b | 3.2 | AIDP separates transcripts from inferences and Cognee §3.4 references transcript turns from a derivation, while Wes on 10-14 and 3.1.4 prefer linking to a system of record over copying; the two paths reuse existing fields (`tags`, `evidence`, `rel`) and the dangling-reference rule, so an implementer needs no new field. |
| I-23a | 3.2 | Answers both consent sub-questions with one field, following Cognee §3.3 (portable policy carries retention or use constraints, and unsupported required rules cause rejection or restricted staging, never silent expansion) and the Sapience draft's consent per object with removal on revocation; `scope` cannot carry it because scope says who may read, not what may be done. |
| U-6 | 3.3.1 | Reconciles the unique-identifier rule with the 10-14 full-history export by qualifying uniqueness with the export kind the manifest already declares. Precedent: Sapience §3.1 (one stable identity shared by all versions, each version distinct), Context Nest's per-version history entries, the agreed rule that attribution is per revision. |
| I-4 | 3.3.2 | Keeps the agreed decisions (audit-required, in-place updates allowed, a declared comparator, incomparable versions allowed, wall-clock SHOULD NOT be the comparator) and picks the sequence number Gabe suggested on the call as the default; precedent: IBM's declared comparator, Context Nest's `version: integer >= 1`, Sapience's incremented version number, Mike's incomparable versions (10-14). |
| U-5 | 3.3.3 | Keeps the editors' audit-profile REQUIRED while honouring the 10-14 decision that in-place stores are supported and Gabe's call objection that all-immutable memory breaks markdown-on-disk, by stating immutability as an exchange outcome rather than a storage rule; the precedents are Cognee §3.1 (a correction "does not silently rewrite the exchanged history"), Context Nest's append-only chain with `verify`, and Sapience's reading that history is optional in the base form and required only in audit. |
| I-7a | 3.3.5 | Follows the editors' resolution in 5.1.4 and Gabe's call position that full audit is an enterprise, multi-user obligation, while taking from Context Nest §6.3.4 ("an importing implementation MUST honor them and MUST NOT reconstruct forgotten versions") and Cognee §3.5 ("a permitted tombstone may prevent resurrection") the one receiver-side duty that costs a minimal importer only an identifier check. |
| U-10 | 3.3.6 | Names exactly the three things 3.3.6 says a tombstone records (when, who, why) as fields and leaves the rest to implementations, as 5.4 intends. Precedent: Context Nest §6.3.2 (`tombstone: true`, `forgotten_at`, `forgotten_by`, closed `reason_code`, hashes retained so the chain verifies) and Cognee §3.5 (lifecycle events carry target revision, authorized actor, effective time and reason; a permitted tombstone prevents resurrection). |
| U-12 | 3.4 | Gabe's call position (omit scope from the runtime format, keep it in interchange because ACLs attach to it) and the agreed two-representation rule only hold if the `no` rows bind; the rest stays guidance per the review comment that each memory system takes the interchange form and uses whatever subset helps. The MUST rows are exactly the minimal profile's required fields, so no new obligation is created. |
| I-13 | 3.4 | The call agreed that auditable means traceable to one or more accountable humans and that audit-log storage is left to implementers, and the September 28 notes asked only for "the small hook" on the memory or the retrieval response; deriving the flag from the agreed definition gives consumers that hook without a stored field that could contradict the provenance it summarizes. |
| I-8 | 3.5.2 | Follows Cognee §3.1 (local identifiers allowed, mapping kept), which 3.5.2 already carries as an unmarked MUST, and PR #16's origin qualifier (5.1.2) so a store that re-exports memories from several origins can still name each one; IBM's new-memory-on-import case survives as re-derivation with a lineage link rather than as a lost identity. |
| U-3 | 3.5.2 | Cognee §3.6 makes intent explicit and distinct, the 5.3 working JSON already carries `intent`, and the agreed split (this document is the memory spec, the manifest is a follow-up) puts a once-per-export declaration in the manifest; the `copy` default lets an implementer read any manifest without failing on an absent field. |
| U-14 | 3.5.4 | Cognee §3.6 (retries must not duplicate objects or events) and §3.1 (matching content does not merge distinct revisions; different content under one revision identity is a conflict) give the rule; I-8's resolution supplies the stable pair, and the fallback to `checksum` and `exported_at` lets minimal-profile exports retry too. |
| I-2b | 3.5.4 | Makes the three views of I-2 interoperable without picking one: a claim store and a document store can exchange memories as long as the conversion is visible, which is what the receipt rule (Cognee §3.6, PR #12's silent 208-record loss) and the 3.1.2 rule that every writer is a contributor already ask for. Uses only the existing `derived_from` rel and the existing `imported` contribution value, so no new field is introduced. |
| I-22 | 3.5.7 | Follows Cognee §3.3 and §2 (permission to import is not permission to treat content as an instruction; restricted staging rather than silent acceptance) and Wes on 10-14 (an imported provenance chain is a claim and can be laundered); it reuses the existing `contribution` vocabulary instead of adding a field, and keeps the agreed out-of-scope line on chains of trust. |
| I-10 | 3.6.1 | The call did not agree on MCP as the home (IBM proposed it; Cognee prefers hooks for control, Context Nest a CLI for retrieval isolation), so the smallest rule that lets an implementer ship is Context Nest §4.3's: expose at least one binding and serve the same set through each, with Cognee §5's view that bindings are carriers of one object. Declaring the surface reuses the capability endpoint the federation binding already requires. |
| I-15a | 3.6.2 | Answers Vasilije's call question (one org server plus one personal server breaks; per-workspace may be too coarse) with Cognee §3.3's scope kinds as examples rather than a closed vocabulary, and the comparison notes' row on identity pass-through (point to existing auth, carry only what the union view needs). The qualified form is already the shape of the Appendix A example. |
| I-15b | 3.6.4 | Keeps the agreed rule (the protocol defines what recall returns, not how it is called) by confining the one query shape federation needs to the binding that AIDP contributed, where every endpoint but capability is optional; Gabe's read-back that the merge protocol comes second means the layer adapts to servers, not the reverse. |
| U-11 | 3.6.4 | Turns the call's common ground (scope feeds access control and the system sets it; Gabe's read-back that the layer takes the union of the servers' results) into one enforcement rule and one floor, following Cognee §3.3's "never silent access expansion" and the 1.3 rule that access control is enforced by the serving system from interchange fields. It adds a floor without defining merge or scope combination, which Part 4 leaves to implementations. |
| U-9 | 3.6.4 | Reconciles the AIDP endpoint set with the agreed recall rule by scoping the signature to the federation binding and fixing only a string query plus filters on fields the protocol already defines, so a federation layer can call any member with no per-server adapter while servers still compete on retrieval. `scope` is deliberately not a filter: it is system-set and never crosses a runtime surface (1.3, U-11). |
| I-12 | 3.6.5 | Follows the only position on record, Context Nest on the call ("no nested memories, compiled at runtime"), while keeping separate objects as the default since the existing 3.6.5 sentence already gives each its own metadata; naming compiled sources keeps the agreed 3.2 rule that an audit-grade system can reconstruct the chain behind what the agent saw. |
| U-15 | 3.6.6 | Raised in review of this draft: the minimal profile's headline case, a bare folder of markdown files, had no rule for deriving the three required fields or for where metadata sits. |
| U-13 | 3.7 | Gabe's 10-14 dangling rules were motivated by adoption (an import must not fail on a missing target) and Wes added that a dangling reference still means something in the audit chain, which splits cleanly into a minimal duty and an audit mark; copy as the default is the behaviour of every store that has no manifest (the source keeps its memories), matches IBM's one-system-at-a-time import, and leaves Cognee §3.6's explicit intent in force wherever a manifest exists. |
| I-7b | 3.7 | Context Nest §6.3.4 refuses to auto-delete derived content ("a summary of ten transcripts is not erased because one was") but flags it `review_required` and lists it in the forget result, and Cognee §3.5 leaves dependents to be deleted, invalidated or recomputed by policy; reusing 3.5.5 gives both outcomes without a new field. |

This document holds what the specification leaves out: the proposals that did not make it into the text, the questions still open, the items set aside or handed to another document, and the list of what the protocol leaves to implementations.

## B. Proposed, not agreed: alternatives and editors-added text

### B.1 A thin core with semantic conventions (I-21)

Ilan proposes in review (PR #13) to follow OpenTelemetry and keep the protocol core minimal. A memory would be:

```json
{ "identifier": "MEMORY.md", "media_type": "text/markdown", "body": "The user prefers concise answers.", "attributes": {} }
```

Every other field would become an attribute defined in **semantic conventions**. The conventions would be debated and versioned on their own schedule: the manifest declares `semantic_conventions_version` separately from `protocol_version` (D). Under this model the tiers of 1.2 and the profiles of 1.4 and 3.7 would become named sets of conventions. This was not reached on 2026-10-14 and is not adopted. The field table (1.3) stands until the group decides.

### B.2 Cognee's further fields (PR #16)

Cognee's PR #16 proposes `subject`, `kind`, `accuracy`, an `origin` qualifier, `invalidated_by` (a reverse pointer on the superseded memory, the counterpart of the `supersedes` link in 3.3.4), a list shape for `evidence`, and a second hash of the body alone for deduplication (U-1 in C). They are reflected where they overlap (1.3 `checksum` row via U-1, 3.1.4, 3.1.6, 3.3.4, D) and are otherwise left for review in PR #16.

### B.3 Alternatives to 3.1.6

- **Vouching** (Sruly, 10-14): instead of a carried accuracy score, a model or a person vouches for a memory.
- **Confidence per evidence entry** (review, 10-15): an optional confidence on each evidence entry instead of a record-level score, portable only together with who or what produced it, how and when. It would extend 3.1.4, not the field table. This is the open residual of I-20 (C).

### B.4 Editors' resolution for I-7

Forget, tombstones and anti-resurrection (3.3.6) belong to the audit profile (3.7), not the core. The group has not decided (I-7 in C).

### B.5 Text the editors added without discussion, by section

Profiles as a construct (1.4, 3.7) and the names "minimal" and "audit" are editors-added, as are the "markdown loading profile" (3.6.6) and "federation binding" (3.6.4) as named profiles; the thin core (B.1) would replace them with convention sets. The following sentences have the same status:

- 1.2: every field tier in 1.3 except `version`, `updated_at`, `protocol_version` and `weight` (I-16 in C).
- 1.3: the body row, which restates the body's place in the object and in the minimal profile; the key tiers of the contributor list in 3.1.1.
- 3.1.2: writers are contributors, maintenance agents included.
- 3.1.3: the accountable human for a maintenance agent MAY be the operator who runs it (from review).
- 3.1.4: a derived memory whose evidence is unavailable MUST say so (from Cognee §3.2).
- 3.3.3: immutable revisions with a verifiable history REQUIRED in the audit profile (U-5 in C).
- 3.5.2: a receiving system that assigns its own identifiers MUST keep the origin-to-local mapping (from Cognee §3.1).
- 3.5.6: credentials are not memory and MUST NOT be exported as memory (from Cognee §3.3).
- 1.3 (`protocol_version` row): the clause "an exporter MAY add it at export" is the editors'; the agreed part of that row is the optional tier and the manifest's expected requirement.
- 3.7: the markdown loading profile and the federation binding listed as profiles with checklists.
- Deleted from the body, recorded here: the v0.5 opening sentence of the provenance chapter, "Provenance and evidence are the protocol's main tools for answering who stands behind a memory and why to believe it. Trust and accuracy build on them."

## C. Open issues register

This register is the single owner of every issue's full description; the body carries the mark and at most a one-sentence statement of the question. U-numbers are provisional until the group assigns I-numbers.

### C.1 Open

| # | Issue | Where |
|---|---|---|
| I-2 | The atomic unit. Three views: a memory is the smallest semantic unit that carries meaning and can be evaluated true or false (Cognee, call); memories are documents with titles and authors, as in document stores (CN; Packer); a single claim is the unit, carrying its provenance, a confidence estimate, its versions and what it superseded (the knowledge object: arXiv 2601.15313, Appendix A; arXiv 2603.15994; arXiv 2603.17781; SSRN 10.2139/ssrn.5812343). The metadata of 1.3 is written to work for all three. Deferred 10-14 (D) | 2.2, 1.1 |
| I-3 | The shape of provenance: whether `contribution` and `ai_usage` are core, the EU AI Act terms for `ai_usage`, and how to record several accountable humans | 3.1.1, 3.1.3 |
| I-4 | Versioning: the form of `version` and its comparator, including incomparable versions. Mostly settled 10-14: audit-required, and in-place updates allowed (C.2); the form and the comparator remain. See U-6 for where the comparator is declared | 1.3, 3.3.2 |
| I-5 | Links: inline, metadata edges, or both; what a link targets (an identifier, or an identifier at a version); whether edges are typed in the core; how transcripts are exported or linked to. Appendix A pre-decides the edge shape (U-2) | 3.1.4, 3.2 |
| I-6 | Lineage depth required for audit: n hops back, or the full chain. The sentence in 3.2 marked agreed says an audit-grade system MUST be able to reconstruct the full chain, while the 2026-09-28 call left how the graph is built, stored and traversed to the implementation and v0.5 kept the minimum depth open | 3.2 |
| I-7 | Tombstones, anti-resurrection and delete of derived memories: core or audit profile, and what a delete means for memories derived from the deleted one. The editors propose audit (B.4) | 3.3.5, 3.3.6, 3.7 |
| I-8 | Identity on import: keep the origin `identifier`, or assign a new one with a recorded mapping. IBM's draft treats a memory as valid in one system at a time, with an import creating a new memory in the receiving system; Cognee's draft keeps the origin identity across copies. With `origin` in the manifest (D), the origin key survives either way. U-14 depends on this | 3.5.2 |
| I-10 | Runtime binding: MCP, hooks, CLI, or several. MCP was proposed as the home for the runtime binding: tools for remember and recall, interceptors for hooks, and file access as a tool (IBM; call). It is not agreed. Some implementers find hooks more controllable than MCP tools, and some find a CLI more reliable for retrieval isolation (call). SEP-2640 (Skills over MCP) was suggested as a way to get progressive disclosure over MCP without a file system (AIDP, thread) | 3.6.1 |
| I-12 | Compiled vs separate memories at runtime, and nesting | 3.6.5 |
| I-13 | An auditable flag on memories and retrievals: the protocol may define the flag, not the log | E |
| I-14 | `status` and visibility: standardize or leave to implementations. Parked, row in D | D |
| I-15 | Identity and scope granularity for federation, and whether federation needs any standard recall (review). See U-9 and U-11 | 3.6.2, 3.6.4 |
| I-16 | Whether the tier assignments in 1.3 hold | 1.2 |
| I-17 | Whether a body can be a structured value rather than a string (review), and how a non-text body such as image or audio is carried (11-06) | 1.1, 1.3 body row |
| I-18 | An optional schema or source-type field for structured or relational sources and opaque documents such as PDFs; whether a query-backed memory is the query output or its source data (10-14) | 1.1 |
| I-19 | Folder taxonomy and other hierarchy metadata beyond `path` (10-14) | 1.3 path row, 3.6.6 |
| I-20 (residual) | Confidence on evidence entries, the variant from review (10-15) described in B.3; the main question is settled (C.2) | 3.1.6 |
| I-21 | A thin core with separately versioned semantic conventions (review). Full proposal in B.1 | B |
| I-22 | Trust and sanitization of imported memories | 3.5.7 |
| I-23 | Use cases not yet covered (#use-cases list): contradictions kept and flagged rather than resolved (for example a `contradicts` link rel, or `contribution: contradicted` per 3.1.6), consent to hand a memory over, and consent to learn from a memory. Note: 3.1.6 uses `contribution: contradicted`, a value the `contribution` list in 3.1.1 does not name | 3.1.6, 3.2 |
| I-25 | Whether line-level attribution needs an optional field, or stays derived from diffs between revisions (11-06) | 3.1.1 |
| I-26 | The name of the version field, `protocol_version` or `omp_version`, and its format, for example date-based to match MCP's `MCP-Protocol-Version` (11-06) | 1.3 protocol_version row |

### C.2 Resolved

| # | Issue | Where |
|---|---|---|
| I-1 | ~~Markdown as the common body format vs the base object~~. Settled 10-14: the base object is metadata plus a typed body, and markdown is not preferred | 2.2 |
| I-4 (main) | ~~Whether `version` is required, and whether in-place updates are allowed~~. Mostly settled 10-14: audit-required, in-place allowed. The remainder stays open above; the decisions document lists the decision as recorded, not tagged | 1.3, 3.3.2 |
| I-9 | ~~How an export declares inferred provenance~~. Replaced by 3.1.5 (review): absent provenance means unknown | 3.1.5 |
| I-11 | ~~Change notification during a session~~: how a harness learns that a memory it already loaded has changed (for example through MCP resource subscriptions). Left to implementations (review); closed unless the group reopens it | 2.2 |
| I-20 (main) | ~~Accuracy and confidence as a standard field~~. Settled 11-06: provenance and evidence carry accuracy, plus an optional `weight` for relative ordering within one `origin`. the decisions document asks the group to confirm, since only `weight` carried an agreed tag in v0.5. The residual stays open above | 3.1.6 |

I-24: the number is not used in v0.5 (the sequence jumps from I-23 to I-25, and the changelog records "new open issues I-25 and I-26"); check the PR #13 and PR #16 history for a lost issue before assigning it.

### C.3 Untracked questions

| # | Question | Where |
|---|---|---|
| U-1 | A second hash of the body alone, for deduplication (Cognee, PR #16): tagged open in v0.5's checksum row with no issue number | 1.3 checksum row |
| U-2 | The shape of an evidence entry and of a link edge. `evidence` is "a list of references or strings" and the keys `ref`, `relation` and `dangling` that Appendix A uses are never defined; the link edge `{target, version, rel}` in Appendix A pre-decides what I-5 leaves open. Also undefined is how a derived memory "says so" when its evidence is unavailable (3.1.4), given that evidence pointing outside the store MAY be excluded from an export while the audit profile requires evidence on derived memories | 3.1.4, 3.2, Appendix A |
| U-3 | Whether an export MUST declare a transfer intent at all, and where the declaration lives once the manifest proposal exists (D); v0.5 tagged the section open but tracked only I-8 there | 3.5.2 |
| U-4 | The rename `role` to `contribution`: recorded as done in the changelog (review) but tagged open in v0.5's key table | 3.1.1 |
| U-5 | Immutable revisions and a verifiable history REQUIRED in the audit profile: editors-only text in a section v0.5 tagged open, and I-4 does not cover the audit requirement | 3.3.3, 3.7 |
| U-6 | Where the version comparator is declared: in the manifest (static per system version, D), by "the implementation" (3.3.2), or on each memory as Appendix A does (`"version": { "value": 2, "comparator": "integer" }`, while Appendix B carries the scalar `version: 2`). Also how several revisions of one `identifier` are serialized in a full-history export against the rule that `identifier` MUST be unique among the memories in one export | 3.3.2, 1.3 identifier row, Appendix A, Appendix B |
| U-7 | The ACL-required tier maps to no profile: 3.7 defines minimal and audit, and no profile in which ACL-required fields are required | 1.2 |
| U-8 | The manifest proposal: its content, author and timeline are unassigned (D) | D |
| U-9 | The federation binding's endpoint set includes `search` while 3.6.2 says the protocol MUST NOT fix a signature for recall; I-15 brushes this without owning it | 3.6.4 |
| U-10 | Which tombstone fields are standard (a tombstone records when, who and why) and which belong to the implementation's format: E defers to "the fields named in 3.3.6", which names no field keys | 3.3.6, E |
| U-11 | How `scope` being "set by the system, never by the agent" is enforced (no keyword, no rule), and how scopes combine under federation when `scope` is interchange-only and federation carries the runtime representation | 1.3 scope row, 3.6.4 |
| U-12 | Whether the placement table in 3.4 is normative at all ("guidance, not a requirement") while Appendix B relies on it to drop the audit fields | 3.4, Appendix B |
| U-13 | Whether transfer intent (3.5.2) and the dangling-reference rules (3.5.5) belong to the minimal profile or only to the audit profile; 3.7 lists dangling references under audit and intent under neither | 3.7 |
| U-14 | "Retries MUST NOT duplicate memories" (3.5.4) needs `origin` plus `identifier` identity, which I-8 leaves open and the manifest text in D is being replaced | 3.5.4 |

## D. Deferred, parked and handed off

### D.1 Handed to the manifest proposal (11-06)

This document is the individual memory spec; a follow-up proposal defines the manifest used once per export or import. That proposal covers attributes that are static for a given system version (for example supported MIME types, semantic tags and the version comparator), attributes that vary per transaction, and self-to-self migrations, when a system moves its own data between versions. It MUST declare the MIME types the exporting and importing systems support, it is expected to require `protocol_version`, and it MAY describe what a system's `weight` means. Until it exists, the v0.5 working text stands:

Every export SHOULD begin with a manifest that declares:

- `protocol_version`, and the profiles the export follows (3.7);
- `origin`: an identifier generated once per store. `origin` plus `identifier` is the global key of a memory (review; Cognee PR #16). Without it, two people who each export a `MEMORY.md` produce colliding identifiers;
- `exported_at`: the time the export is as of. It orders exports, and shows that a copy predates a forget (3.3.6) (review);
- the body formats present;
- whether it is a complete snapshot, a selection, or a full history (including memories no longer valid, for example for forensic review (10-14));
- any required extensions (Cognee §3.6).

The rule that absence from a partial export is not deletion stays in 3.5.1 and depends on the snapshot-or-selection declaration above. The thin-core proposal (B.1) would add `semantic_conventions_version` beside `protocol_version`. Appendix A of v0.5 illustrated the manifest as:

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

In v0.5 the "markdown loading profile" (3.6.6) and the "federation binding" (3.6.4) were declarable profile names, since an export's manifest declares its profiles; the manifest proposal must say whether they stay so. Author and timeline of the proposal are unassigned [open U-8].

### D.2 Parked

- The `status` field [open I-14]: string, optional; lifecycle or visibility state inside a store, for example draft, published; possibly implementation-specific; if kept, interchange only (call; CN). The placement table of v0.5 showed it as "yes, if kept" for interchange and "no" for runtime.

### D.3 Deferred (10-14)

- The atomic unit, the semantic scope of a single memory (I-2; the three views are in C.1).

### D.4 Left for review in PR #16

- Cognee's fields that do not overlap the field table (list in B.2).

### D.5 Out of scope for now (10-14)

- A third-party chain of trust for provenance. Sanitization of imported memories is I-22 (3.5.7).

### D.6 Raised, no issue number

- Immediate removal of wrongly stored content, whatever the retention rules, for example classified information stored by mistake: something the spec should make implementable, though not a requirement for every store (Wes, 10-14). The outcomes a forget delivers are in 3.3.6.

## E. Out of scope: left to implementations

Left to implementations, so that they can compete and improve on them:

- Storage, indexing, lookup, embeddings and internal mutation (all drafts; 10-14). In particular, markdown is not required as a storage format.
- The semantic scope of a single memory, for now (10-14; I-2).
- The recall function signature, ranking and retrieval algorithms [agreed].
- Confidence, accuracy and decay scoring, and how they weigh recency (10-14; 3.1.6).
- Federation merge and ranking logic (3.6.4) [agreed].
- Memory-maintenance agents (forget, consolidation, "dream" agents) and their algorithms. Their writes still carry provenance (3.1.2).
- Forget mechanics: how content is erased, what a store keeps so its history still verifies, and the tombstone format beyond the fields named in 3.3.6 [open U-10].
- Retrieval isolation, such as limits on graph traversal depth.
- Audit-log storage and delivery. The protocol may define a flag saying whether a memory or a retrieval is auditable [open I-13], but not the log.
- Access-control systems. The protocol carries `scope` tags that access policy attaches to, but does not define the policy language (IBM; CN).
- Third-party chains of trust for provenance, and how imported memories are sanitized (3.5.7) [open I-22].

## F. Discussion record: rationale and attributions by section

This section keeps every "who said what, when" and every source-draft citation that Parts 1 to 3 shed, grouped under the section the text now lives in, so that a participant can verify their position was recorded. Only the facts of the discussion are kept; the rules themselves are stated once, in the section named.

**Legend.** "call" = the 2026-09-28 exchange-and-runtime call. "10-14" and "11-06" = the 2026-10-14 and 2026-11-06 technical working meetings. "10-15" = a review comment of that date. "review" = a comment on PR #13. "PR #16" = Cognee's header proposals. "PR #12" = the round-trip field report. "thread" = the #exchange-and-runtime Discord thread. Source drafts, in `early-draft-specs/`: Packer (Letta, v0.2), IBM (v0.1), AIDP (AIDP / FMP), Cognee (v0.1; "Cognee §x" points into it), CN (Context Nest v0.1; "CN §x" points into it), AMS (the AMS Card, Mila / Mozilla). People are named as v0.5 names them: first name plus meeting code.

**Goals and scope (1.1, 1.4).**
- The two standardized things, the exchange format and the runtime plug-in points, and the design requirement that everything standardized work from a folder of files on one laptop up to a multi-user, multi-scope deployment with access control: 10-14. The goals-and-scope section was itself put forward on 10-14.
- Non-goals: a transfer format, not a storage format; markdown not required for storage or for the exported body; the semantic scope of one memory out of scope for now: 10-14.
- "Much agent memory today is markdown, and this design keeps it conformant without making it the standard": 10-14.
- Optional fields tend to go unimplemented, so the number of optional fields that matter for interchange is kept small: call.
- That this document is the individual memory spec and the manifest moves to a follow-up proposal: 11-06.

**1.1 Metadata plus body.**
- "Header" became "metadata" because "metadata" avoids implying a file: 10-14.
- The two-sided data contract, stable metadata that changes only through versioning or lifecycle events and a free-form payload the protocol does not prescribe: Cognee, on the call.
- Whether a body can be a structured value rather than a string (I-17): raised in review; how a non-text body is carried added on 11-06.
- The body format list, markdown, plain text, JSON, DocLang, XML (for example PubMed), HTML, CSV and others: 10-14 and 11-06. The SHOULD for `text/plain` and `text/markdown` and the MAY for any other valid MIME type: 11-06.
- The base object is metadata plus a typed body, not a markdown file: call, confirmed 10-14. The markdown loading profile (3.6.6) relates to it through Packer's loading contract.
- An optional schema or source-type field for structured and opaque sources (I-18): 10-14.
- The atomic unit (I-2): "the smallest semantic unit that carries meaning and can be evaluated true or false" is Cognee's view from the call; "documents with titles and authors" is the CN and Packer view; the single claim carrying provenance, confidence, versions and what it superseded is the knowledge object of arXiv 2601.15313 (Appendix A), arXiv 2603.15994, arXiv 2603.17781 and SSRN 10.2139/ssrn.5812343. 10-14 kept the question out of scope for now; the metadata is written to work for all three views.
- Stubs, whose body is a summary or pointer fetched before use "much as skills sit in context as stubs": Wes, 10-14; put forward on 10-14.

**1.2 Field tiers.**
- The four tiers were proposed by Gabe on the call.
- Every tier assignment in the field table is the editors', except `version` and `updated_at`, read back on 10-14, and `protocol_version` and `weight`, set on 11-06.

**1.3 Field table.**
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
- Cognee PR #16 proposes further fields (`subject`, `kind`, `accuracy`, an `origin` qualifier, `invalidated_by`, a list shape for evidence); they are reflected where they overlap (list in B.2) and otherwise left for review there.
- The thin core with semantic conventions (I-21, full text in B) was proposed by Ilan in review, following OpenTelemetry; not reached on 10-14.

**3.1 Provenance and evidence.**
- `contribution` renamed from `role`, which LLM APIs use for user / system / assistant: review. `ai_usage` to be aligned with EU AI Act terminology: review; IBM; call. `name` renamed from `model` so that every kind can be named: review. The tier column of the contributor table is the editors'.
- A plain list lets a memory record that a person asked an agent to save something and the agent rewrote it, without forcing a single grade on the result: Sruly, call.
- Attribution per revision, `at` kept as written, line-level attribution derivable from diffs: agreed 11-06. Whether that needs a field (I-25): 11-06.
- Writers are contributors (3.1.2): editors' text, not yet discussed.
- The accountable human: agreed on the call; the SHOULD to mark who is accountable when several humans appear is the editors'. The operator of a maintenance agent as its accountable human: review, carried by the editors.
- Evidence as a reference or a plain string when the source is not addressable: call. A reference that points outside the store: review. The relation kinds observed / stated / inferred / derived: Cognee §3.2; Cognee PR #16; AIDP's ground truth / transcripts / inferences. A derived memory whose evidence is unavailable says so: Cognee §3.2, carried by the editors. Exporting or linking transcripts (I-5): review.
- "Agent memory is often the wrong home for facts that belong in a system of record, such as a price list or a patient record": Wes, 10-14.
- Unknown authorship: a missing `provenance` MUST NOT be read as the user's own words: review. It replaces v0.1's heuristic provenance, which a receiver could not tell apart from real provenance; the change closed I-9.
- Accuracy: 10-14 asked whether a memory should carry its accuracy (Vasilije, 10-14; Cognee PR #16 `accuracy`). Two concerns from 10-14: a score cannot move between systems unless the algorithm that produced it is also standardized, and a system can become confidently wrong through self-reinforcing loops. Vouching, a model or a person vouching for a memory, was suggested instead: Sruly, 10-14. The provenance-and-evidence resolution is the editors' proposal, settled 11-06 together with `weight`.
- The variant that puts an optional confidence on each evidence entry, portable only together with who or what produced it, how and when: review, 10-15.

**3.2 Links and lineage.**
- The graph rule, audit-grade systems reconstruct the full chain and others may leave nodes unconnected: call.
- Consolidation names all its inputs: Cognee §3.4.
- Inline links in the body, `[[identifier]]`: CN. Typed edges in the metadata with `rel` values: Cognee §3.4; IBM override.
- Folding evidence into links as a `rel: evidence` edge was suggested in review; 10-14 leaned against it, because evidence answers why to believe a memory and may point outside the store, while links answer how memories relate. Keeping them separate was put forward on 10-14.

**3.3 Versioning and lifecycle.**
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

**3.4 Representations.**
- Two representations of one memory, interchange and runtime: call. Metadata the agent does not need can make it perform worse: 10-14.
- A markdown body the agent reads, with structured metadata stored separately: AIDP, thread.
- Each memory system takes the interchange form and uses whatever subset helps: review. Access control enforced by the serving system: call.

**3.5 Exchange.**
- The manifest text was marked for replacement by the follow-up proposal on 11-06.
- `origin` plus `identifier` as the global key, the way CloudEvents uses `source` plus `id`; "two people who each export a `MEMORY.md` produce colliding identifiers": review; Cognee PR #16. `exported_at` ordering exports and dating a copy against a forget: review.
- A full-history export, including memories no longer valid, for forensic review: 10-14. Required extensions, and absence from a partial export not read as deletion: Cognee §3.6.
- Transfer intent (copy, move, federation): Cognee §3.6; the federation intent: AIDP. IBM's draft treats a memory as valid in one system at a time, an import creating a new memory; Cognee's keeps the origin identity across copies; with `origin` in the manifest the origin key survives either way (the remainder is I-8). The MUST to keep an origin-to-local mapping: Cognee §3.1, carried by the editors.
- Fidelity: raised in the thread.
- Receipts: Cognee §3.6. "A round-trip field report found a store that applied 208 records and kept none, with no warning": PR #12.
- The dangling-reference rules were proposed by Gabe on 10-14; the causes, including a reader's scope that does not include the target: 10-14. "A dangling reference can still mean something in the audit chain even when nobody can follow it. Some dangling references point at things that should never have been stored as memory in the first place": Wes, 10-14.
- Credentials are not memory: Cognee §3.3, carried by the editors.
- "An imported provenance chain is a claim, and it can be laundered": Wes, 10-14. A third-party chain of trust for provenance out of scope for now: 10-14; the question was opened on 10-14 (I-22).

**3.6 Runtime binding.**
- The three surfaces, file access, tools and hooks: call. Observe / decorate: IBM. Plugins: AIDP.
- MCP as the home for the binding (I-10): IBM; call. Some implementers find hooks more controllable than MCP tools, and some find a CLI more reliable for retrieval isolation: call. SEP-2640 (Skills over MCP) for progressive disclosure without a file system: AIDP, thread.
- Recall not standardized, the protocol defining what recall returns and not how it is called: call. Whether federation needs some standard recall (I-15): review.
- The write minimum, an author, a time, and create-or-revise: call.
- Federation layer and its merge logic left to implementations: AIDP; call. Identity passes through to each server: call.
- Change notification left to implementations, closing I-11: review.
- The markdown loading contract (root `MEMORY.md`, deferred files, one level down, selective reads): Packer. Declaring loss on projection: Cognee §2.
- The federation endpoint set (upload, search, read, delete, a required capability endpoint): AIDP.
- Compiled versus separate memories at runtime (I-12) carries no attribution in v0.5.

**1.4 and 3.7 Profiles.**
- Profiles that let a deployment claim only what it implements: Cognee §5. The conformance section as a whole was editors' text. An exporter MAY add `protocol_version` at export: the editors.

**E Out of scope.**
- Storage, indexing, lookup, embeddings and internal mutation: all drafts; 10-14. The semantic scope of one memory: 10-14. Confidence, accuracy and decay scoring: 10-14. `scope` tags without a policy language: IBM; CN.

**C Open issues register, attributions carried on the rows.** I-1 settled 10-14. I-2 deferred 10-14. I-4 mostly settled 10-14. I-11 closed in review. I-15 raised in review. I-17 raised in review, extended 11-06. I-18 and I-19 raised 10-14. I-20 settled 11-06. I-21 raised in review. I-25 and I-26 raised 11-06.

**Papers.** The knowledge-object papers shared by lvrzhn on PR #13, arXiv 2601.15313, 2603.15994 and 2603.17781, and SSRN 10.2139/ssrn.5773922 (revised 10.2139/ssrn.5812343), informed the atomic-unit discussion (I-2, C) and the accuracy discussion (3.1.6).

## G. Sources

This draft distills the proposals in `early-draft-specs/` on `main`: the scoping note (Strauss and Rosenblat), Packer v0.2 (Letta), IBM v0.1, AIDP / FMP, Cognee v0.1, Context Nest v0.1 and the AMS Card (Mila / Mozilla). It also draws on the 2026-09-28 exchange-and-runtime call, the 2026-10-14 and 2026-11-06 technical working meetings, the review comments on PR #13, Cognee's header proposals in PR #16, and the #exchange-and-runtime thread. The date codes and source-draft abbreviations used in the decisions document are defined at the head of F.

## H. Change history

### Changes since v0.5

- The draft is now three documents: the specification, this notes document (open questions, proposals, alternatives, the discussion record, sources and change history) and the decisions document (what the group has agreed).
- The specification is reordered: the example memory first, then Part 1 the memory object (definition, tiers, field table, profiles at a glance), Part 2 goals and scope, Part 3 the remaining rules. Prose is shortened throughout; no MUST, SHOULD or MAY of v0.5 is removed, strengthened or weakened.
- Every open question (I-2 to I-26 still open, U-1 to U-14, and U-15 raised in review) carries a **Proposed (id)** block under the section it affects: new normative text, marked as proposed, for the group to accept or reject. Section A lists the reason behind each. Where an issue needed two proposals they are labelled a and b.
- Editorial changes to tables and examples: a body row is added to the field table (1.3); the parked `status` row moves from the field table to D.2; the manifest JSON moves from the appendix to D.1; `protocol_version` is removed from the minimal example; the runtime-projection caption says what the example shows.
- Attributions, meeting codes, PR numbers and source-draft citations move out of the specification into F.

The § references in the two verbatim entries below are v0.5 section numbers. This map translates them; external references to v0.5 sections (PR #13, PR #16, the September 28 notes) resolve through it.

| v0.5 | v0.6 specification |
|---|---|
| Title block | front matter |
| Sources | G (text); F (legend) |
| Changes since v0.2, Changes since v0.1 | H |
| §0.1 Status | front matter; the definition of [agreed] is quoted in the decisions document |
| §0.2 Goals, non-goals and scope | 2.1, 2.2; manifest description → D |
| §0.3 Conventions | front matter |
| §1 Goals | 2.1; the left-to-implementations list → E |
| §2.1 Metadata plus body | 1.1 |
| §2.2 Body formats | 1.1; 1.3 (`media_type` row); 2.2 |
| §2.3 Atomic unit | 2.2; 1.1; C (I-2); D |
| §2.4 Stubs | 1.1; 1.3 (`stub` row) |
| §3.1 Tiers | 1.2 |
| §3.2 Field table | 1.3; `status` row → D |
| §3.3 A thin core with semantic conventions | B; C (I-21) |
| §4 intro | B |
| §4.1 Contributor list | 3.1.1 |
| §4.2 Writers are contributors | 3.1.2 |
| §4.3 Accountable human | 3.1.3; 1.4 |
| §4.4 Evidence | 3.1.4 |
| §4.5 Unknown authorship | 3.1.5 |
| §4.6 Accuracy, confidence and weight | 3.1.6; 1.3 (`weight` row); C (I-20) |
| §5.1 A graph | 3.2 |
| §5.2 Depth | 3.2; C (I-6) |
| §5.3 Links between memories | 3.2 |
| §6 intro | 3.3.1 |
| §6.1 Version slot | 3.3.2 |
| §6.2 Immutable revisions | 3.3.3 |
| §6.3 Invalidation and supersession | 3.3.4 |
| §6.4 Delete | 3.3.5 |
| §6.5 Forget, tombstones and anti-resurrection | 3.3.6 |
| §7.1 Interchange is a superset of runtime | 3.4 |
| §7.2 Field placement | 3.4 (table); last sentence → 1.3 (`scope` row) |
| §8.1 Manifest | D (working text); 3.5.1; 2.2 |
| §8.2 Transfer intent | 3.5.2; C (I-8) |
| §8.3 Fidelity | 3.5.3; 3.7 |
| §8.4 Receipts | 3.5.4 |
| §8.5 Dangling references | 3.5.5; fourth bullet → 3.7 |
| §8.6 Credentials | 3.5.6 |
| §8.7 Trust on import | 3.5.7; 2.2; E |
| §9.1 What crosses the binding | 3.6.1 |
| §9.2 Candidate binding: MCP | C (I-10); one line in 3.6.1 |
| §9.3 Recall is not standardized | 3.6.2; 3.6.3 |
| §9.4 Federation | 3.6.4 |
| §9.5 Change notification | 2.2; C (I-11); D |
| §9.6 Multiple memories | 3.6.5 |
| §10 intro | 1.4 |
| §10.1 Minimal profile | 3.7 |
| §10.2 Markdown loading profile | 3.6.6 |
| §10.3 Federation binding | 3.6.4 |
| §10.4 Audit profile | 3.7 |
| §11 Out of scope | E; 2.2 (short form) |
| §12 Open issues | C |
| Appendix A (manifest) | D |
| Appendix A (memory) | Appendix A |
| Appendix B | Appendix B |
| Appendix C | Appendix C |
| Acknowledgements | I |

### Changes since v0.2

- `media_type` MUST be a valid MIME type. A system SHOULD support `text/plain` and `text/markdown` and MAY support any other valid MIME type, so bodies are no longer limited to text (11-06, §2.2, §3.2).
- New optional field: `protocol_version`, the protocol version a memory was written against. The manifest proposal is expected to require it. The name is still open (11-06, §3.2).
- New optional field: `weight`, a relative ordering among memories from one `origin` (11-06, §3.2, §4.6).
- `at` in `provenance` stays as written. Attribution is per revision, and line-level attribution MAY be derived from diffs (11-06, §4.1).
- This document is now the individual memory spec. The export/import manifest moves to a follow-up proposal (11-06, §0.2, §8.1).
- New open issues I-25 and I-26.

### Changes since v0.1

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

## I. Acknowledgements

Built from the proposals by Charles Packer (Letta), Gabe Goodhart and colleagues (IBM), Sruly Rosenblat and Ilan Strauss (AI Disclosures Project), Vasilije Markovic (Cognee), Misha Sulpovar (Context Nest), and Mila and Mozilla (AMS Card). It also draws on the 2026-09-28 call with Gabe Goodhart, Sruly Rosenblat, Vasilije Markovic, Alex Hancock and Misha Sulpovar, and on the review comments on PR #13 by Gabe Goodhart (with Rynne and Anna Lisa), Sruly Rosenblat and Ilan Strauss. v0.2 also reflects the 2026-10-14 technical working meeting and its participants, including Wes Jackson. v0.5 reflects the 2026-11-06 technical working meeting and its participants. The knowledge object papers shared by lvrzhn on PR #13 (arXiv 2601.15313, 2603.15994, 2603.17781; SSRN 10.2139/ssrn.5773922, revised 10.2139/ssrn.5812343) informed the atomic-unit discussion (C, I-2) and 3.1.6.
