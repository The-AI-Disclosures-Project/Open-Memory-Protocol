# Sapience proposal: the knowledge object as a portable memory unit

**Discussion draft v0.2 | October 15, 2026 | Sapience Labs contribution to OMPI**

**Status:** Proposed for discussion; not an adopted OMP standard. This note restates, at the level of meaning, the knowledge object (KO) described in our public papers, and maps it onto the working draft *Open Memory Protocol: Memory Object, Exchange and Runtime* (editors' draft v0.2, 2026-10-14). Version 0.1 of this note, mapped onto editors' draft v0.1, is in early-draft-specs/draft-v0.1-sapience.md. It adds no fields beyond what those papers describe and proposes no algorithms.

**Prior work this note draws on (all public):**

- [KO-1] Zahn, Beton, Chana. *Attention Is Not Retention: The Orthogonality Constraint in Infinite-Context Architectures.* arXiv:2601.15313. v1 submitted 14 January 2026; v2 4 February 2026. Section 4.2 and Appendix A ("Knowledge Object Specification"). https://arxiv.org/abs/2601.15313
- [KO-2] Zahn, Chana. *Facts as First Class Objects: Knowledge Objects for Persistent LLM Memory.* arXiv:2603.17781, 18 March 2026. Sections 2.5 and 7. https://arxiv.org/abs/2603.17781
- [KO-3] Zahn, Chana. *Selective Memory for Artificial Intelligence: Write-Time Gating with Hierarchical Archiving.* arXiv:2603.15994, 16 March 2026. Sections 3.1 (granularity paragraph), 3.3, 3.4 and 4.4. https://arxiv.org/abs/2603.15994
- [KO-4] Zahn, Beton, Chana. *ANML: Attribution-Native Machine Learning with Guaranteed Robustness.* arXiv:2602.11690, 12 February 2026. https://arxiv.org/abs/2602.11690

Section references of the form "spec §n" point to the editors' draft. References of the form [KO-1 §4.2.2] point to the papers above.

## 1. Why another contribution

Several points from the 2026-10-14 call overlap with what the KO papers have described since January 2026, including confidence as an estimate carried in provenance rather than an accuracy score on the memory, two distinct timestamps, supersession as a first-class relation, and history that is kept rather than overwritten. This note puts that earlier description in one place so the group can cite it, borrow from it, or set it aside, alongside the other drafts in `early-draft-specs/`.

The knowledge object sits in the same tradition as nanopublications and knowledge graphs, which record what is asserted, who asserted it, when, and with what support [KO-2 §2.5]. Nothing here depends on a particular store; the papers themselves describe KOs held in a plain key-value store such as SQLite or PostgreSQL [KO-2 §7.1].

## 2. What a knowledge object is

A knowledge object is **one claim, held as its own addressable unit**. In its basic form the claim has three parts [KO-1 §4.2.2; KO-2 §7.1]:

- a **subject**, the entity the claim is about ("user", "patient_MR", "France");
- a **predicate**, the attribute or relationship ("name", "capital", "tumor_size");
- an **object**, the value ("Alice", "Paris", "3cm").

The object is not restricted to short strings. The specification types it as any value [KO-1 App. A.1], and the current arXiv version (v2, 4 February 2026) extends it to arbitrary media addressed by content hash [KO-1 v2 §6]. The unit itself can be coarser than a single fact; a KO "may represent a single fact, a document chunk, a claim with supporting evidence, or a versioned belief" [KO-3 §3.1]. In OMP terms, the claim is the body and its media type is declared by the metadata (spec §2.1, §2.2). Granularity is a deployment choice, which is how the papers treat it and how the working draft leaves it (spec §2.3, issue I-2).

Predicates can be drawn from a vocabulary the deployment declares, which keeps naming consistent across extractions [KO-1 §5.7], or left free, since KOs do not require schema definition or ontology engineering [KO-2 §2.5]. This matches the spec's position that tags and ontologies are declared elsewhere and the protocol defines only their shape (spec §3.2, `tags`).

## 3. Fields, at the level of meaning

### 3.1 Identity

A KO's identity is derived deterministically from its normalized subject and predicate [KO-1 §4.2.2; KO-2 §7.1]. A later claim about the same subject and predicate lands at the same identity (a consequence that matters more than the derivation), so all versions of "M.R.'s tumor size" share one stable identifier while each version is distinct [KO-1 §4.2.6, App. A.3].

This is the property raised on the call as "a stable identity shared by all versions". It fits spec §3.2 (`identifier`), which leaves the form of the identifier open, and spec §6.1 (`version`), which gives each revision its own place.

### 3.2 Provenance and the confidence estimate

Every KO carries provenance that records the source of the claim, the time it was extracted, a confidence value, a version number, and a pointer to the prior version [KO-1 §4.2.2, App. A.1]. Later papers describe the same record as source identifier, timestamp, verification status, consent and version links [KO-3 §3.4].

The placement of confidence has two features that may be useful to the group.

- **Confidence lives in provenance, not on the claim.** The specification records it as the *extraction* confidence, inside the provenance record next to the source [KO-1 App. A.1]. It is an estimate made by a particular step about a particular piece of support, not a property of the claim itself.
- **It is read together with where the claim came from.** Because the same record names the source and the verification status [KO-3 §3.4], a receiver can tell who or what produced the estimate and on what basis, and can discount it accordingly.

The call took a similar direction (confidence rather than accuracy, carried with evidence and the contributor who supplied it). This suggests that a confidence estimate, if adopted, belongs on an `evidence` entry (spec §4.4) or a `provenance` entry (spec §4.1), with the estimating person, model or process named, rather than as a top-level score on the memory. Spec §4.6 now takes the same route for accuracy (who checked a memory is provenance, what the check rests on is evidence) and leaves open whether an estimate travels on the evidence entry.

The papers also describe two routes by which claims arrive, either mapped from structured data or extracted from conversation as it happens, with the source recorded on the claim (for example, "team meeting, 2025-01-15") [KO-2 §7.4]. The route is part of where the claim came from, which is what spec §4.4 asks evidence to distinguish (observed, stated by a person, inferred by a model, or derived from other memories).

### 3.3 Two times

The KO papers distinguish two kinds of time.

- **recorded time**: when the claim was extracted and written, carried in provenance [KO-1 App. A.1];
- **the claim's own time**: when what the claim states was true, captured "for temporal facts ... when available" [KO-1 App. A.2], and visible in the version chain example, where successive values carry the dates they held (January 2024, June 2024, January 2025) [KO-1 §4.2.7].

Keeping them apart makes a question like "what did the system believe before the update" answerable separately from "what was true before the update" [KO-3 §3.3]. This maps to the spec's `created_at` / `updated_at` and `valid_from` / `valid_until`, respectively (spec §3.2, §6.3), which the 2026-10-14 meeting adopted as separate fields.

### 3.4 Supersession

When a claim changes, the new version **supersedes** the old one rather than replacing it. The papers record supersession as explicit, two-way links. The new object points to what it supersedes, and the old object points to what superseded it [KO-3 §3.3]. Successive versions form a chain (v1 → v2 → v3) in which the head is current and every earlier version stays readable [KO-1 §4.2.7; KO-3 §3.3].

Each version carries its own provenance [KO-1 App. A.3], so the chain records that a replacement happened and who or what supplied each replacement.

Read semantics follow from the chain. A query returns the current version by default, and history is returned only when explicitly requested [KO-1 §5.7]. This is the same split as the spec's current and historical reads (spec §6.3).

### 3.5 Supersession links are not evidence

The KO record keeps "where this came from" and "what this replaced" in separate places, with the source identifier and verification status separate from version links [KO-3 §3.4; KO-1 App. A.1, `source` versus `previous`]. A receiver can therefore tell a supporting source from a predecessor. This is the distinction discussed on the call between evidence (why believe this) and links (how this relates to other memories), and it supports keeping `evidence` (spec §4.4) and `links` with `rel: supersedes` (spec §5.3) as separate fields.

### 3.6 Attribution is a use of provenance, not the same thing

Provenance records origin. Attribution, crediting and where appropriate compensating the people whose knowledge a system relies on, is a downstream use that provenance makes possible [KO-2 §7.1; KO-4]. Discrete objects let outputs be traced to contributing sources through lineage [KO-3 §3.4]. For OMP this suggests keeping the contributor list (spec §4.1) and evidence (spec §4.4) rich enough to support attribution, without the protocol defining any attribution or credit scheme.

### 3.7 Consent

Each object can carry consent information, and a specific object can be removed when consent is revoked, from both current and archived storage [KO-3 §3.4]. Because the unit is one claim, consent can be honored claim by claim rather than document by document. This relates to the ACL-tier `scope` field (spec §3.2) and to delete (spec §6.4), though the papers do not define a scope vocabulary.

## 4. Lifecycle

**Supersede, do not overwrite.** A change archives the current version with a pointer and writes a new version with an incremented version number and a pointer back [KO-1 App. A.3]. Superseded objects move to an archive rather than being deleted, which keeps a complete audit trail of what the system held and when [KO-3 §4.4].

**History is optional in the base form.** The specification says KOs "optionally preserve version history" [KO-1 §4.2.7]. That matches the spec's choice to recommend immutable revisions without requiring them so that simple stores can conform, with verifiable history required only in the audit profile (spec §6.2, §10.4).

**Deletion is a separate act.** Archiving keeps a version available; deletion on consent revocation removes it [KO-3 §3.4]. The two should stay distinct in the protocol, as they are in spec §6.3 and §6.4.

## 5. Mapping onto the working draft

| KO concept | Source | Working draft |
|---|---|---|
| One claim as the unit; granularity left to the deployment | KO-1 §4.2.2; KO-3 §3.1 | §2.3, I-2 |
| Object may be any value or media | KO-1 App. A.1; KO-1 v2 §6 | §2.2, `media_type` |
| Identity from subject and predicate, shared by all versions | KO-1 §4.2.2; KO-2 §7.1 | §3.2 `identifier`, §6.1 |
| Version number and pointer to prior version | KO-1 App. A.1 | §3.2 `version`, §6.1 |
| Provenance: source, extraction time, verification status | KO-1 App. A.1; KO-3 §3.4 | §4.1, §4.4 |
| Confidence as an estimate inside provenance | KO-1 App. A.1 | §4.4 (proposed placement) |
| Recorded time versus the claim's own time | KO-1 App. A.1, A.2, §4.2.7 | §3.2 `created_at`, `valid_from`, `valid_until`; §6.3 |
| Two-way supersession links; current by default, history on request | KO-3 §3.3; KO-1 §5.7 | §5.3 `rel: supersedes`, §6.3 |
| Source kept apart from version links | KO-3 §3.4 | §4.4 versus §5.3 |
| Attribution as a downstream use of provenance | KO-2 §7.1; KO-4 | §4.1, §4.4 |
| Consent per object; removal on revocation | KO-3 §3.4 | §3.2 `scope`, §6.4 |
| Archive superseded versions; history optional in base form | KO-1 §4.2.7; KO-3 §4.4 | §6.2, §10.4 |

Where the KO papers are silent (manifests, transfer intent, receipts, tombstones, runtime bindings), this note has nothing to add, and the working draft's text stands.

## 6. Suggestions for the next revision

These follow from the mapping and are offered for discussion only. Editors' draft v0.2 already carries the third (spec §3.2) and proposes the second and fourth (spec §5.3, §3.2).

1. Place a confidence estimate on evidence or provenance entries, naming who or what made the estimate, rather than as a score on the memory.
2. Keep evidence and links as separate fields, with `supersedes` as a named link type.
3. Keep recorded time and valid time as separate fields in the core metadata.
4. Treat a stable identity shared by all versions of a memory as distinct from the identity of each version.

## Papers by first public date

Newest first. Dates are first public versions (arXiv v1 submission, Zenodo record creation, or DOI registration for SSRN).

- 11 August 2026. Zahn (Sapience Labs). *Sapience: A Hybrid Architecture for Long-Context Reasoning and Continual Learning*, v4.1. Zenodo, doi:10.5281/zenodo.21894569 (all versions: doi:10.5281/zenodo.21894568). The knowledge object as the unit of storage (§3.4). Not otherwise cited in this note.
- 18 March 2026. Zahn, Chana. *Facts as First Class Objects: Knowledge Objects for Persistent LLM Memory.* arXiv:2603.17781 [KO-2].
- 16 March 2026. Zahn, Chana. *Selective Memory for Artificial Intelligence: Write-Time Gating with Hierarchical Archiving.* arXiv:2603.15994 [KO-3].
- 6 March 2026. Zahn, Beton, Chana. *Constraint Gain: An Information-Theoretic Foundation for Valuing Negative Scientific Results.* Zenodo, doi:10.5281/zenodo.18895831 (all versions: doi:10.5281/zenodo.18895830). Counterfactual knowledge objects, which record a negative result as a claim of its own (§6.2, Definition 7). Not otherwise cited in this note.
- 12 February 2026. Zahn, Beton, Chana. *ANML: Attribution-Native Machine Learning with Guaranteed Robustness.* arXiv:2602.11690 [KO-4]. Cited here for attribution as a use of provenance; it does not define the knowledge object.
- 4 February 2026. Version 2 of arXiv:2601.15313 [KO-1 v2], cited here for §6 (objects as arbitrary media).
- 14 January 2026. Zahn, Beton, Chana. *Attention Is Not Retention: The Orthogonality Constraint in Infinite-Context Architectures.* arXiv:2601.15313 [KO-1], Appendix A "Knowledge Object Specification".
- 23 December 2025, revised 6 January 2026. Zahn, Chana. *Ideas Have Value: Context-Aware Attribution and Economic Settlement in Knowledge Provenance Graphs.* SSRN, doi:10.2139/ssrn.5773922; revised version doi:10.2139/ssrn.5812343. Knowledge objects as signed, typed, attributed units in a provenance graph (§4.1). Not otherwise cited in this note.

## Review basis

Prepared October 14, 2026 against the editors' draft v0.1 (2026-10-02) and the 2026-10-14 call; spec references updated to the editors' draft v0.2 (2026-10-14) on October 15, 2026. Every concept above is traced to a public paper; the trace, with sections and dates, is kept alongside this draft. This contribution states a design position and describes published work; it is not a claim of guarantees provided across implementations.
