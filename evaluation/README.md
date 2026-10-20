# Evaluation

Sketches for how a conforming memory system could be evaluated, and what the
existing benchmarks do not currently cover.

Companion to the benchmarks section of the prior-art survey, which catalogues
LongMemEval, MemoryAgentBench, AgentMemBench and Memory-R1. This directory does
not repeat that survey. It starts from what those benchmarks measure and asks
what a protocol conformance story would additionally need.

## What the existing benchmarks measure

Recall accuracy, under increasingly realistic conditions. Can the system find
the fact, across long horizons, across sessions, across distractors.

## What they do not measure

**Where the contract sits.** If the contract between an implementer and a memory
format is what enters the context window and what stays out, that is not what is
currently measured. Benchmarks measure what the store returned. Between the store
and the window sit ranking, truncation, compaction and whatever the harness does
last, and none of it is instrumented. A system can report a clean result set that
reaches the model as something else.

**Whether the retrieved memory was the one that should have been returned.** A
system can retrieve accurately and still return a fact superseded last quarter,
or scoped to a different project, or one the requesting user had no right to see.
Retrieval succeeded, which is what makes this failure hard to notice and hard to
debug. It is a common enough experience that some users disable memory features
rather than reason about them.

**Whether a past run can be reconstructed.** Not whether the same query returns
the same answer today, but whether the context assembled on a given date can be
rebuilt and shown to be what it was. That requires version history and an
assembly log, which is a structural property rather than an algorithmic one.

**Whether the same memory behaves the same on a different model.** Portability
that moves bytes but not behaviour is a weaker promise than it sounds.

**Whether memory helped at all.** Memory sometimes makes an agent worse, and a
protocol that cannot detect that will be adopted and then quietly resented.

## What this directory proposes

Seven dimensions grouped by where the measurement is taken, in [evaluation-dimensions.md](evaluation-dimensions.md),
and one of them worked through in enough detail to actually run, in
[staleness-resistance.md](staleness-resistance.md).

These are dimensions, not a leaderboard. The natural place to report them is the
Mila and Mozilla Agent Memory System Card, which is already designed for systems
to describe themselves along axes rather than to be ranked. Nothing here needs a
separate scoreboard, and a separate scoreboard would probably be worse.

## Open questions

- Should conformance require reporting on any of these, or is disclosure enough?
- Scope isolation needs a labelled corpus with overlapping personas. Does one
  exist, or does the group need to build it?
- Net benefit requires a task suite. Is that in scope for a memory protocol, or
  does it belong with the harnesses?
- Where should a determinism claim be reported: as a property on the system card,
  or as a field on the memory object?
