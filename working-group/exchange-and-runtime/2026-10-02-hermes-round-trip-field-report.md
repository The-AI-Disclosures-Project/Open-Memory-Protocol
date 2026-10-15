# Field report: round trip of a Hermes agent's memory through an existing portable format

> Input for the exchange-and-runtime thread: evidence for the open items **Import fidelity and
> receipts** and **Legacy stores with no metadata** in
> [`2026-09-28-common-ground.md`](2026-09-28-common-ground.md), and one proposed new whitespace row.
> Measured on 2026-10-02 by the Self-Improving Society (SIS) project.

## What we tested

SIS runs a multi-agent system on Hermes Agent profiles. The memory of one agent has two parts:

- `MEMORY.md` (2,117 bytes) and `USER.md` (536 bytes): Hermes' Markdown memory, entries separated
  by `§`.
- A private retrieval collection in Qdrant: 204 chunks, each with `text`, `source`, `source_hash`,
  `chunk_index`, `embed_model` and `ingested_at`. The vectors have 3,072 dimensions and cosine
  distance.

We exported that memory to `.mem` (Portable Memory, format 1.1.0, Python SDK 0.3.0), imported it into
an empty target and exported it again. We ran two variants:

- **A:** only the format's standard record types.
- **B:** the standard types plus one implementation-specific passthrough type.

## What came back intact

- `MEMORY.md` and `USER.md` came back byte-identical, with the same SHA-256.
- All 204 of 204 chunks came back with the same id, text, source, source hash, chunk index and
  embedding-model name.
- Importing twice changed nothing, and the re-export was byte-identical.
- The Ed25519 manifest signature rejected a different key and a one-byte change.

## What the standard types could not carry (variant A)

| Data | Result | Why |
|---|---|---|
| Ingestion time of each chunk (`ingested_at`) | Lost in 204 of 204 chunks | Chunk records have no time field. The parent resource has `created`/`modified`, but these 204 chunks come from **one** source document ingested on **10** different dates. The time survived only in variant B. |
| Owner (which host, which agent) | No field | We encoded it in the scope id (`ctx_sis_host_1_operator`) by our own convention. |
| Vector space (dimension, distance metric) | Not carried | Not exporting the vectors is expected. But the receiver cannot tell that it must re-embed, or whether old similarity scores remain comparable. |

This supports two header fields that the Sep 28 call already leans toward:

- `created_at` (no objection on the call), on **every** record, including retrieval chunks, not
  only on top-level memories.
- Scope or owner kept in interchange (proposed on the call).

## Two fidelity failures a receipt should catch

1. **The import report did not match what was stored.** We imported into the SDK's reference
   in-memory store.
   - The import report listed 208 standard records as applied: 1 context, 2 core, 1 resource and
     204 chunks.
   - The store kept 0 of them. Only the 204 passthrough records were stored.
   - No warning was raised.

   An import receipt should be computed from what the receiver actually persisted, not from what
   it was handed.
2. **Markdown entries were merged.** The SDK's Markdown adapter read Hermes' `§`-separated
   `MEMORY.md` as one entry and dropped the trailing newline. Our own mapping, which treats the
   whole file as one core block, round-tripped byte for byte.

   For the legacy-stores item: an export should declare how a Markdown store was split into
   memories, and a receipt should carry a checksum for each original file.

Also, `mem validate` reported OK without checking the signature. Only the importer checked the
signature, and only when it was given trusted keys.

## Proposals

1. **Import receipts.** For each record type, report the counts that were *handed over*,
   *persisted*, *transformed* and *dropped*, plus a digest of what was persisted. Any difference
   between handed over and persisted is a warning.
2. **`created_at` on every record**, including chunks.
3. **New whitespace row: derived indexes (embeddings).** Keep vectors out of the record. Have the
   manifest declare the embedding model, dimension and distance metric for each collection, so the
   receiver knows it must re-index and whether old similarity scores remain comparable.
4. **Owner in interchange.** Add a field, or a required kind of scope, that answers "whose memory is
   this?" without depending on a naming convention inside a scope id.
