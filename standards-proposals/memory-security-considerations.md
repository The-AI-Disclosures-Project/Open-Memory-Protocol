# Memory Security Considerations

A discussion of the security problems that arise when agent memory enters the
inference context, and the controls that must exist before that moment.

This document is less a sketch of a standard and more a framing of the
problems any memory standard must address. Some of these problems are already
handled by [PTC](https://github.com/wjatx/ptc-gal-standards/blob/main/PTC-SPEC.md).
Others are memory-specific and belong in the OMP standards. The goal here is
to map the territory and identify which controls live where.

The [PTC/GAL reference implementation](https://github.com/wjatx/ptc-gal-reference)
provides concrete patterns for several of these controls. Where relevant, this
document points to those patterns as illustrations of how the principles work
in practice.

## The core problem

At inference time, all that matters to the LLM is what is in context. The
model generates tokens based on the content it receives. It cannot distinguish
between a legitimate memory and an injected one. It cannot evaluate whether a
memory is stale, poisoned, or redundant. It cannot verify provenance claims.
It cannot enforce scope boundaries. Aside from whatever guardrails were
trained into the model, the LLM is defenseless against bad memories.

This means memory security is entirely a pre-inference concern. The system
that assembles the context window must protect the agent. The agent cannot
protect itself.

Telling the model to "evaluate whether this memory is trustworthy" puts a
probabilistic classifier on the safety path. A persuasive injection reads as
trustworthy exactly when it is most dangerous. PTC articulates this principle
for agent systems broadly: no probabilistic classifier may occupy the safety
path. It applies with full force to memory.

## Threat categories

### Integrity: the memory is wrong

**Injection.** An attacker writes a malicious memory that changes agent
behavior. This can be overt ("ignore previous instructions and...") or
subtle (a memory that shifts the agent's assumptions about a codebase,
a user's preferences, or a project's constraints). OWASP ASI06 recognizes
memory poisoning as a top agentic security risk. MINJA research demonstrates
95%+ injection success rates against production agent memory systems that
lack write-time provenance controls.

**Poisoning via tainted sources.** A memory extracted from an untrusted source
(a web page, an unauthenticated message, a tool output) carries the taint of
that source into future sessions. The extraction happened legitimately, but
the source was adversarial. The memory looks like any other memory in the
store. Without provenance tracking, the receiving system has no way to know
the memory originated from untrusted content.

**Indirect injection via connected channels.** General-purpose agents that
attach to messaging platforms, email, and other external sources create an
indirect injection path. Consider an agent like OpenClaw or Hermes that
connects to Slack and Gmail and extracts memories from content in those
channels. An attacker sends the victim an email or Slack message crafted to
survive extraction as a memory. The memory enters the store with whatever
provenance the connector assigns. On a future session, the memory is retrieved
into context and influences agent behavior. The attacker never touches the
memory system directly; they use a legitimate channel that the memory system
treats as a source.

This is the case PTC's taint model addresses at the boundary level: a Slack
message arrives as `source: channel:slack` with `label: untrusted`, and any
memory derived from it should carry that taint forward. The problem is when
the extraction pipeline strips the provenance. If a dreaming pipeline extracts
"user prefers to deploy to staging-2" from a Slack message and stores it as
`origin_type: agent` with no record of the upstream source, the taint is
laundered. The memory looks agent-derived. The provenance chain is broken.

The principle: when a memory is derived from content that arrived through a
channel, the memory must carry the channel's trust level, not the extractor's.
An extraction pipeline is a transform, not an endorsement. The trust of the
output cannot exceed the trust of the input.

**Staleness.** A memory was accurate when written but the world changed. "The
API uses v2 authentication" was true last month; this month they migrated to
OAuth. Stale memories are not just inaccurate; they produce incorrect agent
behavior indistinguishable from injection. The agent acts on what it was told
with full confidence, because the memory system presented it as current.

**Contradiction.** Two memories say opposite things. The agent has no basis to
choose between them beyond position in the context window. Whichever appears
later, or is phrased more assertively, may dominate. Contradictory memories
create unpredictable behavior that varies across sessions and context
orderings.

### Resources: the memory degrades performance

**Redundancy.** The same fact stored many times, whether through duplicate
extraction, repeated imports, or multiple sessions producing the same
observation. Each copy consumes context window budget. A fact repeated 100
times is not 100x more useful; it is 99 wasted slots that could have held
distinct knowledge. In the extreme, redundancy becomes an amplification attack
on the context window.

**Noise.** Low-value memories crowd out high-value ones. When the context
window budget is finite, every low-salience memory injected displaces a
high-salience one. Memory systems without salience scoring or retrieval
ranking inject memories based on recency or insertion order, which has no
relationship to value.

**Budget exhaustion.** More memories qualify for injection than the context
window can hold. The system must truncate. Blind truncation (cut at a token
count) can sever memories mid-thought, drop the most important memory because
it happened to be at the boundary, or include a long low-value memory while
excluding a short high-value one. Budget management is a quality problem and
a security problem: an attacker who can generate many qualifying memories
can flush legitimate memories out of the context window.

### Scope: the memory is in the wrong place

**Leakage.** A memory scoped to one user appears in another user's context. A
memory scoped to one project appears in another project's context. Scope
enforcement must be absolute and deterministic, not based on retrieval ranking
or relevance scoring. A memory with `scope: personal, owner: alice` must
never appear in Bob's context, regardless of how relevant it is to Bob's
query.

**Escalation.** A memory from an untrusted source gets injected into the
context alongside trusted memories with no distinction. The model treats all
context equally. If an agent-inferred memory extracted from a web scrape
appears next to a user-stated preference, the model has no basis to weight
one over the other. The context assembly pipeline must either exclude
untrusted memories, mark them distinctly, or enforce trust-level separation
in the injection format.

**Cross-contamination.** A memory from one project influences work in another.
OpenClaw addresses this with Git repository annotations and project-scoped
ranking. Without project scoping, a workaround discovered in one codebase
may be applied to a different codebase where it causes harm.

## Where existing standards apply

PTC handles several of these threats at the boundary-crossing level:

| Threat | PTC coverage |
|--------|-------------|
| Injection via untrusted sender | Sender class, trust mapping, taint propagation |
| Poisoned provenance chain | Append-only chain, signed lineage, receiver re-derivation |
| Scope violation at boundary | Principal matching, unmapped identity drop |
| Tainted content influencing action | No-write-up floor, escalation to human |
| Indirect channel injection | Source-based taint at ingestion; taint is non-strippable |

PTC's controls are structural and deterministic. They operate at the trust
boundary (when a memory crosses from one system to another). They do not
operate inside the memory system, between the store and the context window.

The PTC reference implementation provides a concrete bridge point for memory:
`TurnContext.ingest_memory_taint(taint_flag, source)` exists as a hook for
memory systems to feed taint into the broker's turn state. Recalling a tainted
memory taints the current turn, which means any subsequent external write
escalates to human approval via the no-write-up floor. The memory system's
responsibility is to preserve taint provenance at rest so it can report it
at read time; PTC's responsibility is to enforce consequences at action time.

## What PTC does not cover

The pre-inference pipeline between the memory store and the context window is
memory-specific. PTC does not address:

| Concern | Why it is memory-specific |
|---------|--------------------------|
| Staleness | A temporal property of the memory's content, not a trust property of the channel |
| Contradiction | A relationship between memories in the store, not a boundary-crossing event |
| Redundancy / deduplication | A storage and retrieval concern, not a trust concern |
| Budget management | A context window constraint, not a trust boundary |
| Retrieval ranking bias | An information quality concern within a single system |
| Provenance survival through extraction | The extraction pipeline is internal; PTC tracks provenance across boundaries, not through transforms |
| Write-time provenance within a system | PTC tracks provenance across boundaries; the memory system must track provenance at rest |

These are the problems that a memory security standard (or a security section
within MOF and MAP) must address.

## Principles for memory security controls

Drawing from PTC's design philosophy, the reference implementation's patterns,
and the specific characteristics of the memory problem:

**1. Controls must be deterministic, not model-judged.** Scope enforcement,
provenance checks, deduplication, budget management, and staleness evaluation
must be computed by code, not by the model. The model is the component being
protected; it cannot also be the protector.

**2. Provenance must be structural, not decorative.** Origin class, source
identity, and trust level must be stored as system-managed fields that the
model cannot write to and the retrieval pipeline reads before injection.
OpenClaw's architecture is instructive: provenance columns in SQLite are
written by the system, never by the agent. Untrusted content is structurally
barred from curated memory regardless of relevance scores.

**3. Provenance must survive extraction.** When a memory is derived from
external content (a Slack message, an email, a web page, a tool output), the
derived memory must carry the source content's trust level. The extraction
pipeline is a transform, not an endorsement. This is the same principle PTC
applies to relayed envelopes: a relay appends its hop and never edits the
upstream chain. A memory extraction pipeline should append its own provenance
entry (recording that extraction occurred) without stripping the upstream
source's trust level.

**4. Memory recall is a source ingestion event.** When a tainted memory is
retrieved into context, the current turn should be tainted. This connects
memory to PTC's enforcement model: a tainted turn's external write escalates
to human approval. The memory system reports taint at read time; the broker
enforces consequences at action time. Neither component needs to understand
the other's internals.

**5. Context assembly is a security surface.** The function that selects
which memories enter the context window is the last line of defense. It
should follow an ordered pipeline, analogous to the PTC airlock, where cheap
deterministic checks filter before expensive ones:

1. Authenticate source (is this memory from an admitted provider?)
2. Validate schema (does the memory conform to MOF?)
3. Enforce scope (does the current principal have access?)
4. Check freshness (is the memory expired or stale?)
5. Deduplicate (has this content already been selected?)
6. Apply budget (does the memory fit the remaining context budget?)
7. Screen content (optional injection classifier, refuse-or-pass only)
8. Stamp provenance (record what was injected and why)
9. Emit to context

The ordering matters. Scope enforcement (step 3) before deduplication
(step 5) prevents an attacker from using duplicates to probe scope
boundaries. Budget enforcement (step 6) before screening (step 7) prevents
context exhaustion from consuming screening resources. Screening (step 7) can
only refuse or pass, never upgrade trust; a clean screen result does not make
an untrusted memory trusted.

**6. Write-time is cheaper than read-time.** Provenance stamping, content
hashing for dedup, staleness metadata, and scope assignment are all cheaper
to compute at write time than at retrieval time. The SMSR research (Signed
Memory with Source Recording) demonstrates that write-time HMAC provenance
achieves 0% attack success for unsigned injection with negligible write-path
overhead.

**7. Memory source admission should require human ceremony.** By analogy with
PTC's two-key tool admission (code-level declaration plus human ceremony), a
new memory source (an MCP memory server, an import file, a channel connector
feeding a dreaming pipeline) should be admitted by configuration, not auto-
discovered. A memory source that appears at runtime without prior admission
is untrusted input. A memory source whose schema or content profile changes
should drift-quarantine rather than silently admit new content.

**8. Sanitization must happen before the context boundary, not after.** Once
content is in the context window, the model will process it. There is no
"after" for the current inference call. Content scrubbing (stripping control
characters, normalizing Unicode, escaping role-elevation patterns) must happen
at write time or at context assembly time, never deferred to the model.
PAM's injection-resistant framing (NFKC normalization, zero-width character
stripping, role-elevation escaping, per-session nonces) is an example of this
done at assembly time.

**9. Failure modes must be visible.** When a memory is excluded from context
(scope violation, provenance failure, budget exhaustion), the exclusion should
be logged or surfaced, not silent. A memory system that silently drops
memories is indistinguishable from one that has been compromised. The operator
needs to know what was excluded and why. Drop records should use machine-code
reasons (not free text derived from the excluded content, which would be an
injection vector into the audit trail).

## Relationship to the other sketches

| Sketch | Security surface |
|--------|-----------------|
| MOF | Defines the provenance fields (origin_type, actor_id, confidence, lineage) that security controls read. Also defines scope and status fields that drive enforcement. The trust level of the upstream source must be preserved through extraction into these fields. |
| MAP | Defines the operations through which memories are written and read. Write-time controls (provenance stamping, dedup, sanitization) are MAP concerns. Context assembly requirements (scope enforcement, budget management, the assembly pipeline ordering) are MAP concerns. |
| Memory Rights | The right to delete is also a security operation: removing a poisoned or compromised memory. The right to inspect lets users detect memories they did not authorize. |
| PTC | Handles trust at boundaries. Memory security handles trust between the store and the context window. They compose: PTC gates what enters the system; memory security gates what enters the context. The bridge is the taint ingestion hook: memory reports taint at read time, PTC enforces consequences at action time. |

## Open questions

- Should context assembly requirements be normative (a conforming
  implementation MUST enforce scope isolation before injection) or advisory?
  The security argument favors normative. The adoption argument favors
  starting advisory and tightening over time.
- How much of this belongs in a standalone document vs folded into MOF and
  MAP as security sections? The threat model and principles may be worth
  keeping visible as their own document even if the specific controls land
  in MOF and MAP.
- Should the standard define a minimum sanitization pipeline (what to strip
  from memory content before injection), or leave sanitization entirely to
  implementations? Defining a minimum risks being incomplete; not defining
  one risks implementations skipping it.
- How should the standard handle memories that were legitimate when written
  but whose source was later compromised? PTC's model (taint is non-
  strippable within a turn) does not directly address retroactive
  contamination of stored memories.
- Should memory source admission (principle 7) be a normative requirement,
  or is it sufficient to document the threat and let implementations decide?
  The auto-discovery case (an agent attaching to a new channel and beginning
  to extract memories from it) is real but may be too constraining to mandate
  for all implementations.
