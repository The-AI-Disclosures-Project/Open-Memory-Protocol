# OMP — Cognee draft (v0.1) semantic core, as code

A prototype of the six-part portable-memory contract proposed in
[`early-draft-specs/draft-v0.1-cognee.md`](../../early-draft-specs/draft-v0.1-cognee.md).
It sits alongside the Packer, AIDP and IBM prototypes as one more draft made runnable; the
draft's request that its contract be adopted as OMP's common core is a working-group
decision, not something this code assumes.

| Draft §3 | Here |
|---|---|
| 3.1 Identity and revision | `ObjectRef` (authority / namespace / local id) + immutable `revision_id` + `predecessor`. Receivers keep an origin-to-local map. Same revision id with different content is a conflict; equal content does not merge distinct revisions. |
| 3.2 Content, origin, evidence | `EvidenceRole`: source_artifact, transcript, human_assertion, machine_derived. Text baseline; `MediaDescriptor` with digest for other media. |
| 3.3 Scope, ownership, authority | `Scope` separates subject, owner, author, agent, origin system and context. `Policy` rules name principals, actions, resources, constraints. Unmapped principals or unenforceable required rules stage the object (`unresolved`); credentials in content are rejected. |
| 3.4 Provenance and lineage | `Derivation` (PROV-shaped: activity, used revisions, spans, agent, time, config). Unknown stays `unknown=True`. Unavailable evidence is declared in the receipt. |
| 3.5 Time, lifecycle, deletion | `applies_from/until` distinct from `recorded_at`. `LifecycleEvent` kinds: supersede, retract, invalidate, expire, delete, tombstone. Current reads exclude non-active states; historical reads are explicit and permission-checked. Deleting a revision invalidates its dependents; a tombstone blocks resurrection from an old archive. |
| 3.6 Exchange capability, fidelity | `Manifest` (format/profile versions, kinds, scope coverage, complete vs partial, required extensions, copy/move/federate). Object-level `Receipt`: accepted / transformed / omitted / unresolved / rejected, id mappings, reasons, conflicts, retry boundary. Retries never duplicate. Move completes only when every object landed. Modes: preserve, re_derive, hybrid. |

**COGX 0.1 codec** ([`cogx.py`](semantic_core/cogx.py)) reads and writes the draft's
reference format (manifest.json + JSONL streams, optionally `.cogx.tar.gz`) with no Cognee
dependency, and reports what each direction loses (COGX has no policy, lifecycle events or
tombstones; its memories carry no provenance). Raw nodes travel as an opaque extension.

**Adapters** ([`adapters.py`](semantic_core/adapters.py)) express the sibling prototypes
as exchanges, so the same validator runs over IBM records, FMP servers and Packer
directories. Their manifests note what each draft's model does not carry.

**Fixtures** ([`fixtures/`](fixtures/)) are the cases the draft's §6 asks for: evidence and
derivation, correction, consolidation, policy mapping, partial export, conflicting
revisions, required extension, expiry, deletion with a tombstone and an old archive trying
to resurrect the deleted revision, plus credential rejection and re-derive mode. Each fixture
states the receipt a receiver must produce and is re-imported to check idempotency.

## Install

```bash
uv sync --extra dev --extra adapters
```

## CLI

```bash
uv run semantic-core fixtures                                  # run all §6 cases
uv run semantic-core validate fixtures/02_correction.json      # contract findings
uv run semantic-core import fixtures/04_policy_mapping.json --map alice@source=alice
uv run semantic-core from-packer ../packer-draft-langchain-harness/examples/memory > packer.json
uv run semantic-core to-cogx packer.json ./packer_cogx         # for Cognee to import in preserve mode
uv run semantic-core validate ./some_export_from_cognee        # a COGX dir or .cogx.tar.gz
```

## A recorded two-way exchange with Cognee 1.5.3

[`examples/cognee_roundtrip.py`](examples/cognee_roundtrip.py) (uses `OPENROUTER_API_KEY` from
`prototypes/.env` as Cognee's `LLM_API_KEY` when that is unset) sends an exchange (the
Packer example directory plus a transcript and two derived memories, 10 objects) to a local
Cognee as COGX, exports the dataset back as COGX, and reads it with this codec. Results on
2026-09-22 with Cognee 1.5.3:

| Mode | `cognee.remember` | `cognee.export` | Read back here |
|---|---|---|---|
| preserve | completed, 10 items | 0 nodes, 0 edges, empty archive | nothing |
| re-derive | completed, 10 items | 71 nodes, 153 edges: 10 documents, 26 entities, 153 facts, 45 raw nodes | 234 objects, 0 validator errors; receipt 189 accepted, 45 transformed (raw nodes opaque) |

What the receipt and notes make visible, all consistent with the draft's own §4
assessment of COGX:

- Preserve mode accepts external memories and memory blocks but they do not reach the graph,
  and export covers the graph only, so nothing comes back. A receipt on Cognee's side would
  have said "accepted, not exported".
- Re-derive creates new identities: every returned record has a Cognee id and `scope: {}`;
  the `omp_revision_id` we put in metadata does not survive. Origin-to-local mapping has to
  be kept by the receiver, which this store does.
- Returned facts carry no provenance, so they import as `machine_derived` with
  `derivation.unknown = True`, and the 45 raw nodes are retained opaque.
- Two configuration facts surfaced on the way: `cognee.remember` runs an LLM pass even in
  preserve mode unless `self_improvement=False`, and Cognee's own OpenRouter key must be valid
  for re-derive.

## Test

```bash
uv run pytest
```

## License

Apache 2.0 (see [LICENSE](../../LICENSE)).
