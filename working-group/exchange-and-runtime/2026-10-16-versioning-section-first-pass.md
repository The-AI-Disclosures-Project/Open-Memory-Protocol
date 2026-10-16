# Versioning and lifecycle: proposed §6 for working spec v0.2

*First pass for Gabe Goodhart and the group, 2026-10-15, by Oliver Zahn (Sapience Labs). Written against editors' draft v0.2 (PR #13 head 1da7418). Prose only, contributed under CC BY 4.0.*

*The document has three parts. **Part 1** is proposed replacement text for v0.2 §6. It keeps the numbering of §6.1 to §6.5 so every existing cross-reference in v0.2 still resolves. It adds §6.6 to §6.9. **Part 2** gives worked examples with expected outcomes so the rules can be checked and later turned into round-trip tests. **Part 3** discusses adversarial cases, edits other sections would need, open questions and sources. It is not spec text. Only Part 1 is meant for merging.*

*Source tags follow v0.2. "10-14" is the 2026-10-14 meeting, "review" is a comment on PR #13, and "#17" is Wes Jackson's threat model in PR #17 and its discussion. Points from the author's own PR #13 comments are tagged "(Zahn, review)" so readers can distinguish them from group positions.*

***

## Part 1. Proposed text for §6

## 6. Versioning and lifecycle

v0.2's opening paragraphs stand. Stores that change memories in place and stores that write superseding revisions are both supported. By default an export is a snapshot as of its `exported_at`, with history travelling only when the export declares it (10-14).

Each rule below includes its rationale. Rules that bind outside the audit profile concern what an export carries or how a receiver reads it. They do not govern how a store manages its own records.

### 6.1 Version slot, memory identity and revision identity

v0.2 text stands. `version` is audit-required and opaque. Its comparator is declared and MAY report two versions as incomparable, and wall-clock time SHOULD NOT be the comparator (IBM; Mike Burns, 10-14; call).

- The **memory identity** is `origin` plus `identifier` (§8.1), shared by all revisions of a memory (Wes Jackson, 10-14; Sapience §3.1).
- The **revision identity** is the memory identity plus `version`. A link, evidence entry, provenance entry or tombstone MAY target either.

`identifier` SHOULD be stable across exports from the same origin (Zahn, review). Supersedes edges, incremental exports and tombstones all need a receiver to recognise a memory it has seen before. An identifier that changes between exports makes an old copy look new.

A store without `version` has no revision identity. Where a rule needs one, it MAY name the content instead by a hash of the body alone (Cognee, PR #16, [open]). A `checksum` that covers provenance cannot serve because adding a `verified` entry would change it.

A receiver MUST NOT compare `version` values from different origins. Two stores that both count from 1 would appear to share a history, and a writer could claim a large number to look newest (Part 3, A4).

### 6.2 Immutable revisions and in-place updates

v0.2 text stands. A store MAY update a memory in place and need not keep earlier revisions; the audit profile requires immutable revisions with a verifiable history (v0.2 §6.2, editors' proposal). A store that updates in place and carries `updated_at` or `version` SHOULD update them. A receiver that already holds the memory can then tell it changed.

A store whose bodies never change MAY still change lifecycle metadata on an existing revision, such as `valid_until` and supersession links (Gabe Goodhart, 10-14). In the audit profile each such change MUST be recorded as a lifecycle event with a contributor and a time. Otherwise a receiver cannot tell when a memory stopped applying or who decided it. Such changes alter a `checksum` that covers metadata, which the audit profile's verifiable history has to allow for (open question 2).

### 6.3 Invalidation and supersession

#### 6.3.1 Two time axes

A memory carries two kinds of time (IBM; Cognee §3.5; Sapience §3.3; 10-14). These correspond to valid time and transaction time in bitemporal databases.

- **Valid time** is when the claim holds in the world, given by `valid_from` and `valid_until`.
- **Recorded time** is when the store wrote the revision, given by `created_at`, then `updated_at`.

`valid_until` is a pure cutoff (Gabe, 10-14) and MAY be in the future, for a planned change (Sruly Rosenblat, 10-14) or a temporary workaround (Wes, 10-14). For a planned change, the superseded revision carries a `valid_until` equal to the new revision's `valid_from`, so it still holds until then.

A historical read SHOULD say which axis it uses (Zahn, review). "What was true on 3 March" and "what did we believe on 3 March" are different questions, and audits usually ask the second. An export is a recorded-time cut, holding what the store believed at `exported_at`.

An exporter that does not know when a claim became true MUST leave `valid_from` out rather than copy recorded time into it, and a receiver reads a missing `valid_from` as unknown. As with unknown authorship (§4.5), a recorded time presented as a valid time cannot be distinguished from an actual valid time. §6.8 would then order revisions by when they were written down. Leaving valid time unknown lets a simple store use one timestamp for the two axes without misleading a receiver.

#### 6.3.2 Supersession edges

Supersession is an edge in `links` with `rel: supersedes`, from the newer revision to the one it replaces (Cognee §3.4; IBM; compare `prov:wasRevisionOf` in W3C PROV-O). It describes the relation between memories without giving a reason to believe either. It is therefore a link rather than evidence (§5.3; 10-14).

- The edge SHOULD target a revision where the store has revision identity, and MAY target the memory otherwise. An edge to "the memory" no longer says what was replaced once the history moves on. Appendix A already targets a revision.
- The edge SHOULD carry the reason for the change (for example correction, update, merge or expiry) and SHOULD name the contributor who made it (Zahn, review; Wes, 10-14). In the audit profile the contributor MUST be named. The reason and contributor explain the change without requiring a diff between revisions. When the replaced revision is not exported, the reason is often all a receiver has to judge it by (Sruly, review). An audit must be able to trace who retired a memory.
- A supersedes edge states that the newer revision replaces the older one as a description of the world. An edge that only records that one revision was written after another does not state that the newer one replaces the older one, and an exporter SHOULD NOT present it as a supersedes edge. §6.8 trusts edges first, so an edge that encodes arrival order would let a late, older fact win.
- Cognee's reverse pointer `invalidated_by` (PR #16) MAY also be carried. If both directions are carried and disagree, a receiver SHOULD report it in the receipt (§8.4) rather than pick one.
- One memory MAY supersede a different memory, for example in a merge.

v0.2's read rule stands. Current reads SHOULD exclude superseded memories and memories past `valid_until`, and historical reads SHOULD be explicit (Cognee §3.5). In stores that keep history, superseded revisions stay readable on request (Wes, 10-14).

#### 6.3.3 Branches

A claim can be true on one branch and not yet on another, for example in dev and not yet in main (Mike Burns, 10-14). The comparator MAY therefore be a partial order. Two revisions of one memory with no supersedes path between them, which the comparator reports as incomparable, are **branches**, and both are current (Zahn, review). A strict order would force a receiver to pick one. A later revision that supersedes both ends the branch.

If supersedes edges carry the lineage, the comparator only has to answer "is A an ancestor of B" and `version` can stay a display value (Zahn, review). A store that uses such a comparator writes an edge for every change it means as a replacement, so two revisions with no path between them are concurrent.

A receiver that can hold only one revision per memory (a single file, for example) says in its receipt which branch it kept under the identifier and where the other went.

### 6.4 Delete

v0.2 text stands, with one paragraph added. Following Misha Sulpovar's three lines (#17), an **invalidated or superseded** memory keeps its content and can be read as of a point in time. An **archived** memory keeps its content but drops out of default reads and can be brought back. A **forgotten** memory loses its content and leaves a tombstone (§6.5). Archiving is not erasure. A delete removes the memory and SHOULD leave an audit record. It MAY also leave a minimal tombstone (§6.5), which, when present, lets a receiver tell "deleted" from "never sent". A delete tombstone does not by itself prevent the memory from returning on a later import (v0.2 §6.4). An administrative scrub, for example of classified data stored by mistake, MAY be offered as a forget (Wes, 10-14).

### 6.5 Forget, tombstones and anti-resurrection

v0.2 text stands for the full tombstone and for anti-resurrection in the audit profile. This section splits I-7 as Wes proposes in #17 and Misha agreed there. How a store forgets stays with implementations (§11), while part of what crosses an export moves into the core.

- **Minimal tombstone (core).** A minimal tombstone holds the memory identity (or revision identity), when it was removed, and whether the removal was a forget or a delete, with no content (Zahn, review). A store that keeps a record of forgetting a memory SHOULD export one. A store that keeps a record of deleting a memory MAY export one. A store that keeps no such record carries no tombstone and still conforms. Without at least the identifier, a receiver cannot tell "forgotten" or "deleted" from "never sent". The forget/delete flag lets anti-resurrection apply only to forgets, as Misha proposes in #17.
- **Full tombstone (audit).** Who removed it and why, as v0.2 requires.
- **Receivers.** Outside the audit profile, a receiver holding a forget tombstone SHOULD NOT restore the memory from a copy older than the tombstone, unless the memory's origin sends it again. In the audit profile, the v0.2 MUST applies. A delete tombstone only tells the receiver that the memory was deleted rather than never sent. The receiver MAY decline to restore it.
- **Standing.** A tombstone is a claim by the store that issued it (§8.7). A receiver SHOULD honour a tombstone from the memory's origin, and one from another store for the copies that came through that store. It SHOULD treat any other tombstone as a claim to review. An erasure honoured at a store other than the origin still reaches that store's copies, while a forged tombstone cannot erase memories its issuer never held.

Ilan Strauss identified the remaining gap (review). If store B forgets a memory and store A, which never received the forget, later exports its unchanged copy, `exported_at` cannot flag it. A tombstone that travels closes this gap for receivers that hold it. It cannot make store A forget (open question 5).

### 6.6 Lifecycle state in an export

An export MUST let a receiver tell which of the states in §6.4 each memory is in. Superseded is conveyed by supersedes edges and invalidated by `valid_until`, both of which travel (§6.7). Archived cannot be derived from anything else, so an exported archived memory MUST be marked as archived. Forgotten is conveyed by a tombstone. A memory with no archived marker is in the state its edges and validity give it. A receiver that cannot tell an archived memory from a current one will serve it.

Whether the archived marker is the part of `status` (I-14) worth unparking, as Misha suggests in #17, or a field of its own is for the editors.

### 6.7 What travels in an export

Gabe asked whether versioning belongs in an export at all (review; 10-14). The proposal is a snapshot by default, with enough lifecycle metadata to import safely.

- **Snapshot by default.** An export holds the current revision of each memory it includes, as of `exported_at`. It MAY include archived memories, marked as such (§6.6), and the manifest SHOULD say whether it does. A migration that silently drops archived memories loses content the user can still bring back.
- **Lifecycle metadata travels.** An export MUST NOT silently drop `version`, `valid_from`, `valid_until`, the archived marker or the supersedes edges that the store holds for a memory it includes. A projection that drops them declares the loss (§10.2). Minimal forget tombstones SHOULD travel and delete tombstones MAY travel. In the audit profile, forget tombstones MUST travel (v0.2 §6.5). Without these a receiver cannot tell which revision is current, and an older copy can come back as new. These rules do not require a store to invent fields it does not keep.
- **History is optional and declared.** Full history, every superseded revision, is OPTIONAL and declared in the manifest (§8.1). A migration may want only what is current, while a forensic review may want everything (Wes, 10-14). An export without history still carries the supersedes edges of its current revisions, so a receiver knows history exists and can ask for it. A receiver treats edges whose targets are absent as dangling (§8.5).

### 6.8 Import ordering

When a receiver holds two revisions of the same memory (same `origin` and `identifier`), from imports or locally, it orders them as follows:

1. If a supersedes path connects them, the descendant is later.
2. If there is none and the comparator reports them incomparable, they are branches (§6.3.3).
3. Otherwise, if both carry `valid_from`, the one with the later valid time is later.
4. Otherwise the origin's comparator decides; failing that, the `exported_at` of the exports they arrived in; failing that, the origin's recorded time, in which case the receipt says so.

The order in which the receiver received them never decides which is later. This ordering is a SHOULD in the minimal profile and a MUST in the audit profile. A late-arriving older fact must not overwrite a newer one because it was written last. The same applies when an old export is imported after a newer one. Tracking systems that reconcile out-of-order reports face the same problem. The ordering says which revision is latest. Whether the latest revision applies yet is the read question of §6.3; a planned change is not current before its `valid_from`.

The ordering cannot tell a correction that moves valid time earlier from a late arrival unless the correction carries a supersedes edge. A store that updates in place and corrects a valid time SHOULD therefore export a supersedes edge with reason "correction" to the revision it replaced, even though it no longer holds that revision (the target then dangles, §8.5).

The ordering resolves honest disorder but does not resolve adversarial disorder. A forged valid time still wins step 3 (Part 3, A4; §8.7).

### 6.9 Assessments and the revision they concern

Proposed as an addition to §4.6. Baixin Guo raised this case in review on Appendix A. A reviewer verifies revision 1 ("updates are due Tuesdays"). The memory becomes revision 2 ("Fridays"), and a snapshot exports revision 2 with a contributor list that still holds the `verified` entry. The entry's `at` gives context but does not identify the revision, especially when versions are incomparable.

- A provenance entry whose `contribution` assesses the content (`verified`, `corrected`, `contradicted` and similar values) SHOULD identify the revision it concerns when the store knows it, using the revision identity or, in a store without versions, the body-only hash of what was checked (§6.1).
- An exporter MUST NOT present an assessment as concerning the exported revision unless it knows that it does. When it cannot tell, for example because the store updated the body in place and kept the contributor list, it marks the association as unknown. A receiver MUST NOT read an unknown association as an assessment of the current body. In a store with immutable revisions, an assessment recorded in a revision's own provenance concerns that revision.
- Identifying a revision does not require exporting it. A reference to a revision that is not in the export is a dangling reference (§8.5), and the receiver still learns that an earlier revision was checked.
- A confidence estimate on an evidence entry, if the group adopts one (Zahn, review), concerns the revision it was made about in the same way.

These rules do not make versioning mandatory in the minimal profile. Whether to believe the assessment stays with §8.7 (Baixin, review). Baixin has offered to contribute a worked example; Example 1 below is meant to be merged with his or replaced by it.

***

## Part 2. Worked examples

Each example states the expected outcome.

**Example 1. Verification and revision (Baixin Guo's case).** Revision 1 says status updates are due Tuesdays; Sam verifies it on 10 September. On 15 September Jordan has an agent record the move to Fridays as revision 2, valid from 15 September, superseding revision 1 with reason "update". On 1 October an evaluator verifies revision 2.

- *Store that records which revision each check concerns.* A snapshot exports revision 2 only. Sam's entry names revision 1 and the evaluator's names revision 2. Expected: the receiver can tell that Friday was checked on 1 October and that the Tuesday text was checked on 10 September. The reference to revision 1 dangles. No Tuesday body travels.
- *In-place store that kept Sam's entry and cannot tell what it concerned.* Expected: the export marks the association unknown, and the receiver does not treat Friday as verified on the strength of Sam's check.

**Example 2. Out-of-order arrival.** A store keeps the position of a tracked object as one memory (an event-style store would keep each report as its own memory, and the question would not arise). Reports reach it by two paths. The 10:05 report arrives at 10:06, the 10:00 report at 10:07. The store numbers revisions by arrival and writes no supersedes edge between them. Its comparator is a plain integer order.

- Expected: step 3 of §6.8 applies, and the 10:05 position is latest. The 10:00 report is kept as history or, in a store without history, dropped. Under "newest write wins" it would have overwritten the 10:05 position.
- *Old export variant.* A receiver that holds revision 2 of Example 1, with its edge, imports an old export holding only revision 1. Expected: step 1 applies and Friday stays latest.
- *Store with one time axis.* It leaves `valid_from` out (§6.3.1). Expected: step 4 applies, the comparator decides, and nothing is presented as an ordering in valid time.

**Example 3. Branches.** Revision 1 of a team memory reads "Deploys go through the release checklist." On main, revision 2a adds "and need a second reviewer." On dev, revision 2b adds "and run the migration dry run first." Both supersede revision 1, there is no path between them, and the comparator reports them incomparable.

- Expected: both are current, whichever arrives first.
- *Receiver with one file per memory.* It keeps one branch under the identifier, keeps the other as a separate memory linked with `rel: relates_to`, and its receipt says which went where.
- *Merge.* Revision 3 combines both additions and supersedes 2a and 2b with reason "merge". Expected: revision 3 alone is current.

**Example 4. Deletion and re-import.** A memory from origin O holds a person's phone number. The person asks for erasure, and O forgets it, keeping a tombstone with identifier, time and the forget flag (minimal), plus who and why (audit).

- *Old archive.* An archive exported by O before the forget is imported back into O. Expected: not restored; the receipt lists it as rejected because of the tombstone.
- *Tombstone travels.* Receiver R imported the memory last month and now imports a newer export from O that carries the tombstone. Expected: R does not restore the memory from any older copy (MUST in the audit profile, SHOULD outside it). Whether R must also erase the copy it already holds is open (question 5).
- *Store that never received the forget.* Store A imported the memory from O before the forget and later exports it. Expected: R recognises and refuses it only if A's export still names O and the original identifier, which depends on I-8 (open question 6).
- *Delete instead of forget.* O had deleted the memory as routine cleanup, with no erasure request, and exported a delete tombstone. Expected: R can tell the memory was deleted rather than never sent. If an old archive brings it back, R MAY restore it or decline; nothing obliges it either way.
- *Forged tombstone.* An export from origin X carries a tombstone naming O's memory, which never passed through X. Expected: R keeps the memory and reports the tombstone for review.

**Example 5. A forged supersedes edge.** An import from origin X carries an edge saying X's memory supersedes a revision of O's memory, reason "correction". Expected: R keeps O's revision current, records X's edge as a claim and lists it in the receipt (Part 3, A1). If O later writes the same edge, it is ordinary history.

***

## Part 3. Discussion (not proposed spec text)

### Adversarial cases

PR #17 separates integrity from trustworthiness. A verifiable history shows that a record was not altered after it was written. It does not show that the record should have been written (Wes, #17). Versioning opens four ways to do harm without altering any record. The protocol does not define controls for them (§11), but provides the fields a control would read.

- **A1. Forged supersedes edge.** An import claims to supersede a memory from another origin and so retires it from default reads. The proposal is that a receiver does not let an imported edge retire a memory from a different origin without its own review, and lists such edges in the receipt. Within one origin, an edge is ordinary history, and in the audit profile it names its contributor.
- **A2. Forged tombstone.** Covered by the standing rule in §6.5. A receiver that holds back a genuine tombstone keeps erased data until it checks. A receiver that obeys a forged tombstone loses data the origin still has. The standing rule keeps the common cases automatic and sends only the rest to review.
- **A3. Resurrection.** From a pre-forget archive (§6.5), from a store that never received the forget (open question 5), or under a new identifier after re-keying (open question 6).
- **A4. Inflated version or forged valid time.** A writer claims a large `version` or a late `valid_from` to come out latest. Versions are compared only within their origin (§6.1). A forged valid time inside one origin still wins step 3 of §6.8, and an integrity check will not catch it because the record is intact. A receiver that doubts an origin's valid times can review them under §8.7.

### Edits other sections would need

- **§3.2.** `identifier`: SHOULD be stable across exports from the same origin. `valid_from`: left out when unknown.
- **§4.6.** The bullets of §6.9.
- **§5.3 (I-5).** A supersedes link targets a revision where one exists. Other link types stay open.
- **§8.4.** Receipts also list memories rejected because of a tombstone, branches kept as separate memories, revisions ordered by recorded time, edges or tombstones held for review, and disagreeing forward and reverse pointers.
- **§8.7.** Imported supersedes edges and tombstones are claims by their issuer, like imported provenance.
- **§10.4.** Add the §6.8 ordering as a MUST and named contributors on supersedes edges.
- **§12.** I-4: branches and import ordering proposed. I-7: split as in §6.5. I-14: archived marker proposed in §6.6.

### Open questions

1. Which metadata fields may change on an immutable revision without a new revision (§6.2)? Is the supersedes reason a closed list or free text?
2. Should lifecycle metadata that may change on an immutable revision sit outside `checksum`, so the audit profile's hash chain survives a `valid_until` update?
3. Should a merge (supersession across memory identities) be its own relation?
4. Which `contribution` values count as assessments for §6.9, and is the body-only hash (PR #16) the right fallback for stores without versions?
5. How does a forget reach stores that hold a copy but were never sent the tombstone, and must a receiver that receives a forget tombstone erase the copy it already holds? Should a delete tombstone ever block re-import, or does it only make "deleted" distinguishable from "never sent"?
6. For I-8, should a re-exported memory keep its original `origin` and `identifier`, for example through Cognee's per-memory origin qualifier (PR #16)? Anti-resurrection across stores depends on it. v0.2 §8.2 notes IBM's model, in which a memory is valid in one system at a time.
7. Should a minimal tombstone ever cover a single revision, or always the whole memory?

### Sources and prior art

Editors' draft v0.2 (PR #13 head 1da7418) and its review comments through 2026-10-15, including Baixin Guo's; the 2026-10-14 meeting; Cognee's PR #16; Wes Jackson's threat model in PR #17 and Misha Sulpovar's reply there; `early-draft-specs/draft-v0.1-sapience.md` (Sapience §n), which rests on arXiv 2601.15313 (Appendix A, January 2026).

Prior art includes valid time and transaction time in bitemporal databases (SQL:2011); `prov:wasRevisionOf` in W3C PROV-O (2013); commit graphs in version control and vector clocks for partial orders; bitemporal fact edges with validity and invalidation in Zep (Rasmussen et al., arXiv 2501.13956, January 2025); update and delete operations on extracted memories in Mem0 (Chhikara et al., arXiv 2504.19413, April 2025).
