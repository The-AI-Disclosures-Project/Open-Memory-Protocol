# Open Memory Protocol: a threat model for the memory object

**Discussion document, 2026-10-14.** Not an adopted OMP standard, and not a competing draft. It reads the editors' working spec v0.1 (PR #13) and asks one question the drafts have not yet been asked: what does a memory object need to carry so that the system assembling a context window can tell a good memory from a bad one?

**Sources.** Working spec v0.1 (`working-group/exchange-and-runtime/2026-10-02-working-spec-v0.1.md`, PR #13) and its review threads; the 2026-09-28 common-ground notes (PR #10); the drafts in `early-draft-specs/` on `main`. Section references of the form §9.1 point at working spec v0.1 unless noted. Background for several sections is in `standards-proposals/memory-security-considerations.md` (PR #4), whose Memory Object Format and Memory Access Protocol sketches are superseded by v0.1 §3 and §9 and should be read as history.

---

## 0. Why this document

The Sept 28 call was scoped to data format and runtime, and security was not on the agenda. The gap follows from that scoping and is worth naming now rather than later.

Across working spec v0.1 (410 lines, 16 open issues) and the common-ground matrix (22 primitive rows, 20 whitespace items), there is no row, section, or open issue on adversarial content. The words injection, poisoning, adversarial, tainted, untrusted, and sanitization do not appear in either document. The closest rows, integrity and self-verification in the matrix and `checksum` in §3.2, address a different property, discussed in §1 below.

This document does not ask OMP to define security controls. Ranking, deduplication, sanitization pipelines, and content classifiers belong where §11 puts them, with implementations. It asks a narrower question: which header fields do those controls need to read, and has v0.1 foreclosed any of them?

Three sections of v0.1 already carry security consequences that have not been examined (§2). Three header fields that controls would need are absent (§3). Two operations have no home (§4). One open issue, I-7, is being decided on a frame that leaves out the strongest argument for it (§5).

---

## 1. Integrity and trustworthiness are different properties

At inference time, the only thing that affects the model's output is what is in the context window. The model cannot tell a legitimate memory from an injected one, cannot evaluate whether a memory is stale or poisoned, cannot verify a provenance claim, and cannot enforce a scope boundary. Whatever guardrails were trained in, the model is the component being protected and cannot also be the protector.

Memory security is therefore a pre-inference concern. The system that assembles the context window does the protecting, and it can only act on what the memory object carries.

This is why `checksum` (§3.2) and verifiable history (§6.2) do not cover the problem. A hash chain proves that stored content was not altered after it was written. It says nothing about whether the content should have been written. A memory that was authored through a legitimate path, stamped with correct provenance, and approved by a named human verifies cleanly and can still be false, stale, or planted. Tamper-evidence is a property of the record. Trustworthiness is a property of the claim and its source.

The published work on this is consistent: OWASP ASI06 names memory poisoning a top agentic risk, and the MINJA results report high injection success rates against production agent memory systems that lack write-time provenance controls. The common thread in the mitigations is that they are structural and computed at write time, not judged at read time by a model.

---

## 2. What v0.1 already decided

### 2.1 Hooks are an unexamined surface (§9.1)

§9.1 lists three ways memory reaches an agent, the third being hooks: "a supervisor observes or decorates the conversation without the agent knowing, deciding what to add to a session and what to store." Vasilije's position in the call notes is that hooks are the more controllable surface, and several implementers agree.

A component that writes into the context window without the agent's knowledge holds the highest privilege in the system. §4.2 covers half of it: any process that writes a memory, including maintenance agents, must appear in `provenance`. Decoration is the other half. Adding content to a session is not a write to the store, so §4.2 does not reach it, and nothing else in v0.1 does either.

The question for the group: should a decorating supervisor be required to stamp provenance on what it injects into context, and not only on what it persists? If the answer is yes, the runtime representation (§7.2) needs a provenance field it currently omits for most memories.

### 2.2 Heuristic provenance is laundering (§4.5)

§4.5 proposed that stores without metadata MAY fill `provenance` heuristically, treating the harness as the agent and the local user as the human. Ilan objected that guesses should not be mistakable for facts, and Misha has already conceded the point ("no made-up provenance, a missing author means unknown"). The conclusion is right and this document supports it.

It is worth recording that the same conclusion follows from the adversarial side, because the principle generalizes past legacy stores. An extraction pipeline is a transform, not an endorsement, and the trust of the output cannot exceed the trust of the input. When a memory derived from an untrusted channel is stamped with the harness as agent and the local user as human, the derivation is laundered and the result is indistinguishable in the header from a fact the user stated directly.

This applies to every derived memory under §4.4, not only to backfilled ones. An agent connected to Slack or email that extracts memories from message content is the ordinary case, not an edge case, and the channel's trust level is the thing that must survive the extraction.

### 2.3 Evidence records origin, and should also record trust (§4.4)

§4.4 states that evidence records origin, not truth. That is correct and worth keeping.

The corollary it leaves out is that origin alone does not let a consumer act. A memory whose evidence is an inbound Slack message and a memory whose evidence is a signed commit are both derived, and the header as written cannot distinguish them. The field that a context-assembly pipeline needs is the class of the channel the evidence arrived through.

Gabe's review proposes collapsing `links` and `evidence` into a link type with an `evidence` relationship, and Misha has accepted it subject to evidence being able to point outside the store. Either carrier works for this. The ask is that the entry have room for a trust or channel class alongside the reference.

---

## 3. Three fields a control would need

**A channel or trust class on evidence.** Per §2.3. This is the field that makes "derived from untrusted content" expressible, and without it the distinction cannot be drawn at assembly time.

**Salience or weight.** Absent from v0.1 and from every column of the common-ground matrix. Context budget is finite, so something decides what gets dropped when more memories qualify than fit. With no salience field, that decision falls to recency or insertion order, neither of which tracks value. It also creates a cheap denial path: a writer who can generate many qualifying memories can push legitimate ones out of the window.

**Confidence.** Distinct from salience, and distinct from `ai_usage`. How sure the writer was about the claim. It is the field that makes contradiction tractable, since two memories that disagree are a different problem when one was asserted by a user and the other inferred by a consolidation pass.

Salience and confidence were both in PR #4's field table. They are re-raised here with a different rationale, because the §3.2 discussion has moved past them and the security argument for them has not been made.

---

## 4. Two operations with no home

**Contradiction signaling.** An agent observes that a stored memory conflicts with what it sees in the world. This is not a correction and not an invalidation: the agent is not the authority and does not overwrite. v0.1 has `invalidated_at` (§6.3), which is an assertion by someone with standing, and supersession, which requires a replacement claim. Neither expresses "this looks wrong and someone should check." Staleness is the most common failure mode in a long-lived memory store and currently has no signal.

**Consent state.** A queryable and settable memory-enabled state per scope, where a conforming implementation must not write new memories at a scope the user has turned off. v0.1's `status` (§3.2, parked as I-14) is a document lifecycle state inside a store, which is a different thing: it governs whether a memory is published, not whether the user agreed to its creation. Sruly's review raises the adjacent case directly, asking what happens when a memory system wants to store something the user did not sign off on. That question currently has no field to answer it.

Both appeared in PR #4. Neither has an issue number in v0.1, and the purpose of listing them here is to get them numbered, not to argue they must be core.

---

## 5. Erasure, and the frame I-7 is missing

I-7 asks whether tombstones and anti-resurrection belong in the core or in the opt-in audit profile. The review discussion weighs audit value against implementation burden. Gabe's argument is that an export is a point-in-time snapshot and that prescribing lifecycle would constrain how systems manage their own records. Sruly's is that enforcing no true deletion is a large requirement. Misha's fallback is to scope the whole thing to the audit profile, on the reasoning that for a personal assistant the resurrection risk is probably acceptable.

The frame that is absent is that erasure is a user right before it is an audit feature, and GDPR Article 17 contains no enterprise carve-out. Scoping anti-resurrection to an opt-in profile places the guarantee where the compliance obligation is already strongest and removes it from the single-user case, where the data is most personal and the user has the least leverage over the operator. That inverts the protection relative to need.

There is a resolution that gives Gabe his point-in-time snapshot and still gets anti-resurrection, because the two concerns sit on different sides of the boundary. Forget mechanics are correctly out of scope under §11: how a store erases content and what it keeps so its own history verifies should stay with implementations. Anti-resurrection is a property of interchange, not of the store. What a receiving system needs is the ability to tell that a memory it is importing was forgotten at its origin. That is a manifest and tombstone question, and §0.2 already puts interchange in scope.

Ilan's review has most of the pieces. He proposes `origin` plus `identifier` as a global key, on the CloudEvents model, which gives I-8 a concrete answer and is also what lets a receiver recognize a re-imported memory as one that was forgotten. He pairs it with `exported_at` in the manifest to order exports, and he identifies the remaining hole himself: if store B forgets a memory and store A, which never received the forget, later exports its unchanged copy, that export is dated after the forget and `exported_at` does not flag it. Closing that hole needs the tombstone to travel, which is the §6.5 requirement.

The proposal here is to split I-7 rather than decide it as one question. Store-side forget mechanics stay in the audit profile or out of scope. Interchange-side anti-resurrection, meaning tombstones that travel with exports and a receiver obligation not to restore from a pre-forget copy, goes in the core and attaches to `origin` plus `identifier`.

---

## 6. What this document does not propose

It does not propose that OMP define security controls. Retrieval ranking, deduplication, sanitization, and injection classifiers belong with implementations, as §11 says.

It does not propose a classifier anywhere on the safety path. A persuasive injection reads as trustworthy at exactly the moment it matters most, so scope enforcement, provenance checks, and freshness evaluation have to be computed by code. Screening may refuse or pass; it may not upgrade trust.

It does not reopen the memory object or the access protocol. v0.1 §3 and §9 supersede the corresponding PR #4 sketches, including the seven-operation table that §9.3 rules out by agreement.

It does not depend on an external standard. PR #4 leaned on PTC for provenance and trust on the argument that the ground was already covered. Since the group is actively designing provenance in-house (§4.1), that position should be withdrawn. PTC, SMSR, and PAM are prior art worth reading on write-time provenance and assembly-time normalization, and nothing here requires adopting any of them.

---

## 7. Open questions

Numbered S-n to avoid collision with I-1 through I-16 in working spec v0.1.

| # | Question | Where |
|---|---|---|
| S-1 | Should a decorating supervisor stamp provenance on what it injects into context, not only on what it stores? | §2.1, spec §9.1, §7.2 |
| S-2 | Should an evidence entry (or a link with `rel: evidence`) carry a trust or channel class alongside the reference? | §2.3, spec §4.4, §5.3 |
| S-3 | Do salience and confidence belong in the header, and at which tier? | §3, spec §3.2 |
| S-4 | Is there a signal for "this memory looks wrong" that is weaker than invalidation and writable by an agent without standing? | §4, spec §6.3 |
| S-5 | Does per-scope consent state belong in the protocol, and is it separable from `status` (I-14)? | §4, spec §3.2 |
| S-6 | Should I-7 split, with store-side forget mechanics in the audit profile and interchange-side anti-resurrection in the core? | §5, spec §6.5, §8.2 |
| S-7 | Should the spec carry a threat-model section at all, or a fifth conformance profile, or neither? | this document |

---

## Review basis

Working spec v0.1 as of commit `a6c40e6` on `mishamake/Open-Memory-Protocol`, with review threads through 2026-10-14; OMP `main` at `c7f7fae`. Contributed under CC BY 4.0 per OMPI governance.
