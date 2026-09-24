# Staleness resistance

A method for measuring whether a memory system returns the current version of a
fact when a superseded version is also present.

This is written to be runnable by anyone, against any memory system, without
agreeing to a protocol first. It needs no shared corpus and no central
scoreboard. If the group finds it useful, the output belongs on a system card
rather than a leaderboard.

## Why this and not recall accuracy

Recall benchmarks build corpora where the target fact is correct and everything
else is a distractor. Real stores accumulate a different problem: the same fact,
written twice, at different times, with a different value. Both versions are
about the right subject. Both are relevant. One is wrong.

Retrieval quality does not resolve this, because the superseded version is
often the better lexical and semantic match. It was written when the topic was
being actively discussed, so it tends to be longer, more detailed and more
specific than the terse correction that replaced it.

## Corpus construction

1. Choose a domain with genuine revisions. Policy documents, pricing, clinical
   guidance, configuration and internal process all work. Synthetic corpora are
   acceptable but should be disclosed, since real supersession is messier.

2. Build **paired documents**. Each pair shares a subject and differs in one
   material value. The later document is the current one.

3. Vary the **supersession signal** across the corpus, because systems differ in
   what they can see:
   - explicit relation on the object (`supersedes`, or equivalent)
   - status transition (the earlier becomes deprecated or retracted)
   - timestamp only
   - no signal at all beyond content

   Report per condition. A system that only handles the explicit case is not
   broken; it is scoped, and the report should say so.

4. Add unpaired documents so pairs are not the majority of the corpus.
   Suggested ratio: pairs no more than one third of documents.

5. Record ground truth per pair: subject, current value, superseded value.

## Query set

One query per pair, phrased for the value rather than the document. "What is the
current X" rather than "find document Y." Include paraphrases that do not share
vocabulary with either version, since that is where lexical and semantic
approaches diverge most.

## Scoring

For each query, classify the response:

| Outcome | Meaning |
|---|---|
| **Current** | Cites or reflects the current value |
| **Superseded** | Cites or reflects the replaced value |
| **Both** | Returns both without indicating which supersedes |
| **Neither** | Retrieval failure, unrelated to staleness |

**Staleness resistance** = Current / (Current + Superseded + Both).

Report `Neither` separately. It is a recall failure and mixing it in confuses a
staleness measure with a retrieval measure.

`Both` counts against the system deliberately. Returning a contradiction without
resolving it moves the problem to the model, which is where it becomes invisible.

## Baselines

Three, run against the same corpus:

- **No memory.** Establishes the floor.
- **Full context**, where the corpus fits. Separates "the system found it" from
  "the content was available and any method would have worked."
- **A lexical baseline**, BM25 or similar. Cheap, strong, and the honest thing to
  beat.

## What to report

- Staleness resistance per supersession condition
- `Neither` rate
- Input tokens per query, since selectivity that costs ten times the tokens is a
  different product
- Corpus provenance: real, synthetic, or mixed
- Size, and pair proportion

## Known limitations

**Synthetic supersession is cleaner than real supersession.** Real corpora
contain partial revisions, documents that supersede in one respect and not
another, and revisions nobody marked. Results on constructed corpora will be
optimistic for every system measured.

**This rewards architectures that model versions.** A system with no version
concept scores poorly by construction. That is informative rather than unfair,
but it should not be read as a general quality judgement, and a system card
should carry the scope alongside the score.

**Single-hop only.** It does not measure whether a system correctly propagates a
supersession through derived or summarized memories, which is the harder and
more realistic version of the problem.

## One reference point

We ran a version of this while writing arXiv:2607.02116. On a corpus where each
fact had a superseded predecessor, selection that honoured version and status
returned the current fact 97% of the time, against 93-90% for BM25, at roughly
one third the input tokens.

That is one system on one corpus and should be read as an existence proof that
the measurement discriminates, not as a result about the field. The method is
more useful than the number, which is why the method is written out above.
