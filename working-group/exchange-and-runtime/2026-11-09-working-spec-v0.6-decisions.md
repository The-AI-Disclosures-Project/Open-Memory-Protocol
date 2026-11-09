# Open Memory Protocol v0.6: Agreed decisions

Companion to [editors' draft v0.6](2026-11-09-working-spec-v0.6.md). Section numbers refer to that document.

"[agreed]" means "at least two participants explicitly agreed on a call and nobody objected." Agreed is not adopted. Each row gives the decision, the meeting, where it now sits, and the open remainder by issue id.

| Topic | Decision | Meeting | Where | Open remainder |
|---|---|---|---|---|
| Goals and scope | Full audit is a multi-user enterprise requirement, not a single-user one; audit obligations sit in tiers so individual users do not carry them. | 2026-09-28 call (inferred; v0.5 cites no meeting) | 2.1, 1.2 | |
| Goals and scope | The base object is metadata plus a typed body, not a markdown file, and markdown is not preferred. Closes I-1. | 2026-10-14 | 2.2, 1.1 | |
| Goals and scope | This document is the individual memory spec; the export/import manifest is a follow-up proposal. | 2026-11-06 | 2.2, 3.5.1 | U-8 (who owns the manifest proposal); working text in 5.3 |
| Memory object | A memory is metadata plus a body: the metadata is a schema for the managing system, the body is what is semantically relevant to the agent. | 2026-09-28 call | 1.1 | |
| Memory object | The body MAY be in any format with a valid MIME type, and `media_type` declares which. | 2026-10-14 and 2026-11-06 | 1.1, 1.3 | I-17 (structured and non-text bodies) |
| Fields | `media_type` is required and MUST be a valid MIME type; a system SHOULD support `text/plain` and `text/markdown` and MAY support any other valid MIME type. | 2026-11-06 | 1.3 | |
| Fields | `protocol_version` is optional on the memory; the manifest proposal is expected to require it. | 2026-11-06 | 1.3 | I-26 (name and format) |
| Fields | `valid_until` replaces `invalidated_at` and MAY be a future date. | 2026-10-14 | 1.3, 3.3.4 | |
| Fields | `weight` is an optional, unbounded float with no prescribed mathematical meaning that orders memories from one `origin` relative to each other. | 2026-11-06 | 1.3, 3.1.6 | |
| Provenance | Attribution is per revision: `provenance` records who contributed to a revision and in what sequence; line-level attribution MAY be derived from diffs; `at` stays as written. | 2026-11-06 | 3.1.1 | I-25 (a field for line-level attribution) |
| Provenance | A memory is auditable if it can be traced to one or more accountable humans; in the audit profile every memory MUST carry a `provenance` entry with `kind: human`. | 2026-09-28 call (inferred; v0.5 cites no meeting) | 3.1.3, 2.1 | I-3 (several accountable humans); the SHOULD and MAY in 3.1.3 are editors' text (5.1.5) |
| Links | Evidence and lineage form a graph of memories and sources; an audit-grade system MUST be able to reconstruct the full chain behind a memory; other systems MAY leave nodes unconnected. | 2026-09-28 call | 3.2 | I-6 (minimum lineage depth) |
| Representations | Interchange and runtime are two representations of one memory; interchange carries the full metadata and runtime is a projection of it. | 2026-09-28 call | 3.4 | |
| Runtime | The protocol MUST NOT fix a signature for recall; it defines what recall returns (memory objects in the runtime representation), not how it is called. Recall signature, ranking and retrieval algorithms are out of scope. | 2026-09-28 call | 3.6.2, 2.2, 5.4 | I-15 (standard recall for federation) |
| Runtime | A federation layer MAY sit between several memory servers and the agent and present one unified memory; identity MUST pass through it to each server; merge and ranking logic is out of scope. | 2026-09-28 call | 3.6.4, 2.2, 5.4 | I-15 (identity and scope granularity) |

**Recorded as decided, group to confirm.** v0.5 records these in its changelogs, as read-backs, or in the issue list, while the body text that carries them is not tagged [agreed].

- `version` is audit-required, not required, and stores that change memories in place and stores that never change them are both supported (2026-10-14, changelog; the issue list calls I-4 "mostly settled" while the field row and the store sentence are tagged proposed). Remainder: the form of `version` and its comparator, including incomparable versions (I-4). Where: 1.3, 3.3.1, 3.3.2.
- `created_at` records when the system learned something; `valid_from` records when it became true (2026-10-14, changelog; the two field rows are tagged "no objection" and proposed). Where: 1.3, 3.3.4.
- The protocol defines no portable accuracy or confidence score; accuracy travels as provenance and evidence, plus the agreed `weight` (settled 2026-11-06 in the issue list, I-20, while the section heading still said proposed). Remainder: an optional confidence on each evidence entry (I-20 residual). Where: 3.1.6.
- Tier assignments: `version` (audit-required) and `updated_at` (optional) were read back on 2026-10-14; `protocol_version` and `weight` (both optional) were set on 2026-11-06; every other tier is the editors' (I-16). Where: 1.2, 1.3.
- "Header" is now "metadata" (2026-10-14, changelog). Where: 1.1.
- `type` is now `media_type`, provenance `role` is now `contribution`, and `model` is now `name` (closed in review of PR #13, not on a call). Where: 1.3, 3.1.1.

**Closed by review, not agreed on a call.**

- I-9: replaced by the unknown-authorship rule. Where: 3.1.5; 5.2.2.
- I-11: left to implementations unless reopened. Where: 2.2; 5.2.2.
