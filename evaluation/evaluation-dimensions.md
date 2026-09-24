# Evaluation dimensions

Axes a memory system could report against, organised by **where the measurement
is taken**. That grouping is deliberate: existing benchmarks measure the store,
while the thing an implementer contracts to deliver is the context window.

The framing throughout is disclosure rather than ranking. A system scoring poorly
on an axis it does not claim to serve has not failed. It has been honest about
its scope.

---

## A. At assembly time: what actually entered the window

If the contract is what goes into the context window and what stays out, almost
nothing currently measures it directly. Benchmarks measure what the
store returned, which is a different quantity separated from the window by
ranking, truncation, compaction and whatever the harness does last.

### A1. Assembly fidelity

**Measures:** the difference between what the memory system selected and what the
model actually received.

**Why it is not covered:** it requires instrumentation at the harness boundary,
not the store boundary. A store can report a perfect result set that is then
truncated, reordered, or summarised into something else.

**How:** capture the assembled context at the point of inference. Report, per
query: items selected, items that survived to the window, items dropped, and
what dropped them (budget, ranking, compaction, deduplication). A system that
cannot produce this record cannot report the axis.

This is the axis that most needs the access-protocol work, because it can only be
measured where the harness and the memory system meet.

### A2. Budget efficiency

**Measures:** input tokens consumed per accepted answer.

**How:** hold answer quality fixed and report token cost, or report both and show
the tradeoff. This is where selective retrieval either justifies itself or does
not.

---

## B. On the selection: was it the right content

### B1. Staleness resistance

**Measures:** when a corpus holds a fact and its superseded predecessor, how
often the current one comes back.

**Why it is not covered:** benchmarks build corpora where the target is correct
and other content is a distractor. Superseded content is a near-duplicate, not a
distractor, and it is frequently the better lexical match because it was written
when the topic was live.

Worked through in [staleness-resistance.md](staleness-resistance.md).

### B2. Scope isolation

**Measures:** when memories belong to different projects, personas or
permissions, how often retrieval crosses a boundary it should not.

**Why it is not covered:** benchmarks are typically single-scope. Everything in
the corpus is legitimately available to the query.

**How:** a corpus partitioned into overlapping scopes with deliberately similar
content, queries labelled by originating scope, scored on the proportion of
returned items from the wrong scope. This is the measurable form of a familiar
failure: asking a question in one role and being answered as though you were in
another.

A system with no scope model cannot score here, which is the useful signal.

---

## C. Across runs and models: can the result be relied on

### C1. Repeatability

**Measures:** whether a past run can be reconstructed. Not whether the same query
returns the same answer today, but whether the exact context assembled on a given
date can be rebuilt and shown to be what it was.

**Why it is separate from determinism:** a deterministic selector gives you the
same answer twice under identical conditions. Repeatability asks a harder
question, because conditions change. The store has been written to since. To
reconstruct, a system needs the version history of every item and a log of what
was assembled, which is a structural requirement rather than an algorithmic one.

**How:** run a query, record the assembled context, continue writing to the store
for a period, then ask the system to reproduce the original assembly. Score exact
reconstruction, partial reconstruction, and failure.

**This axis has a prerequisite, and stating it is the point.** A system without
per-item version history and an assembly log cannot pass at any level. That is
not a criticism of such systems. It does mean that if a protocol wants
reconstruction to be a property implementers can rely on, the fields it depends
on cannot be optional.

Determinism of the selector should be reported alongside, as a three-valued
property (deterministic, non-deterministic, or configurable) rather than scored.
A pass or fail framing flatters architectures that chose determinism and
penalises approaches that traded it away deliberately.

### C2. Cross-model consistency

**Measures:** whether the same memory produces consistent behaviour when supplied
to different models.

**Why it matters:** portability that moves bytes but not behaviour is not
portability. If the same memory yields different answers on different models,
"take your memory with you" is a weaker promise than it sounds.

**How:** hold the assembled context fixed, vary the model across a set, and
measure agreement on a fixed question set. Report agreement rate and the models
tested, since the result is only meaningful relative to the set.

Prior art exists: the Portable Agent Memory work reports transfer continuity
scores of 0.83 to 0.92 across four model families. That metric or something like
it is a reasonable starting point rather than something to invent fresh.

---

## D. On the outcome: did any of it help

### D1. Net task benefit

**Measures:** whether the memory system improves task outcomes against two
baselines: no memory, and the same content supplied in full context.

**Why it is not covered:** benchmarks measure retrieval quality, not whether
retrieval helped. Memory sometimes makes an agent worse, and nothing currently
detects that.

**How:** a fixed task suite run three ways, reporting the delta. The full-context
baseline separates "memory helped" from "this content helped, and memory was an
expensive way to deliver it."

---

## Not here, deliberately

Storage efficiency, write throughput and extraction quality. These are
implementation concerns that sit below the protocol per the standards sketches.
They matter to operators and belong in vendor documentation rather than in a
conformance story.
