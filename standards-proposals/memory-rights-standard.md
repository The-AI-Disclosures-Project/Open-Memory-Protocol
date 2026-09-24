# Memory Rights Standard

A sketch of the obligations a memory system operator has to the user whose
data it holds. This is a governance standard, not a protocol. It defines what
implementations must allow users to do, without prescribing how the UI works.

## The problem

Agent memory systems accumulate personal data: preferences, decisions, work
patterns, conversation-derived facts. Users have a reasonable expectation of
control over this data. Regulations (GDPR, CCPA) impose legal obligations.
But no agent memory system today defines a consistent set of user rights, and
most enterprise services offer no portability at all.

## The sketch

A minimum set of user rights that conforming memory systems should support.
These rights apply broadly to any system that stores user-derived AI context,
not just agent memory.

### Right to export

A conforming implementation should support exporting all memories owned by a
user in the MOF exchange format. This is the portability primitive. A user who
wants to switch memory providers, agent harnesses, or platforms can take their
memories with them.

### Right to delete

A conforming implementation should support hard deletion of user-owned
memories on request. Not soft-delete, not retraction: the content is gone.
Provenance chains that reference deleted memories get a tombstone ("this
memory was deleted at [timestamp]") rather than the content.

This aligns with GDPR Article 17. Philosophical arguments for retraction-over-
deletion (preserving the record that something was once believed) do not
satisfy the right to erasure.

### Right to edit

A conforming implementation should support user-initiated updates to their own
memories. The user is the authority on facts about themselves. If the system
extracted "user prefers dark mode" and the user corrects it, the correction
takes precedence over the extraction.

### Right to inspect

A conforming implementation should allow users to see what memories are stored
about them. The format should be human-readable (not a raw database dump). For
file-based systems this is inherent (the files are on disk). For service-based
systems this requires an inspection interface.

### Right to disable

A conforming implementation should allow users to turn memory off, at minimum
at the personal and project scope levels. When memory is disabled at a scope,
the system must not write new memories at that scope. Existing memories may be
retained (disabling is not deletion) but must not be used for context
injection.

The consent signal itself is a protocol concern (defined in the Memory Access
Protocol). The obligation to honor it is a governance concern (defined here).

### Consent for derived memories

When a system extracts a memory about a user from a conversation (as opposed
to the user explicitly asking the system to remember something), the user
should be informed that extraction occurred and given the opportunity to
review, edit, or delete the result. The mechanism for notification is a
product decision; the obligation to provide it is a governance one.

## Relationship to other standards

- **[PTC](https://github.com/wjatx/ptc-gal-standards/blob/main/PTC-SPEC.md)**:
  handles trust verification when memories cross boundaries. The rights
  standard defines what the operator must allow; PTC defines how trust is
  verified when those operations happen across systems.
- **GDPR / CCPA**: the rights standard is designed to be consistent with
  existing data protection regulations, not to replace them. Conformance
  should make regulatory compliance easier, not harder.
- **Agent Memory System Card** (Mila/Mozilla): the system card is a
  transparency and documentation format. The rights standard is an obligation
  framework. They complement each other: a system card describes what a
  memory system does; the rights standard says what it must allow.

## What this does not define

- The UI for exercising rights (product decision)
- Data retention policies (deployment decision)
- Consent mechanisms for multi-user or team-scoped memories (complex, needs
  more thought)
- Cross-jurisdictional compliance details (legal, not technical)

## Open questions

- Should these rights be requirements for OMP conformance, or a separate
  standard that OMP references? The governance answer is to require them. The
  adoption answer depends on whether making them mandatory would discourage
  implementations from claiming conformance.
- How do rights apply to team or organization-scoped memories? If a memory is
  scoped to a team, can any team member delete it, or only the creator?
- Should there be a right to know *why* a memory was surfaced in a particular
  context? This is an explainability concern that goes beyond data rights.
- This standard applies to any system storing user-derived AI context, not
  just agent memory. Should it be published independently of OMP so other
  projects can adopt it without implementing a memory protocol?
