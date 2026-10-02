# Open Memory Protocol: where the drafts agree

> Working notes from the exchange-and-runtime sub-thread. A styled version of this page is in [`2026-09-28-common-ground.html`](2026-09-28-common-ground.html) (download to view).

A working matrix of every draft in `early-draft-specs/` on `main` (commit 7beb260), plus notes from the Sep 28 exchange-and-runtime call: where the data shapes overlap and where the proposals don't align (yet). For the draft due Oct 2, 2026. Discussion draft, 2026-09-28.

## What's in main

- **Scoping note.** Strauss & Rosenblat (AIDP). Shared features across harnesses, assistants and enterprise systems; the "narrow waist" is a portable record plus consolidation lineage.
- **Packer v0.2 (Letta).** A `MEMORY.md` directory with progressive disclosure and a four-rule harness contract. Ownership, versioning and sync are explicitly out of scope.
- **IBM v0.1.** Immutable record (body, id, author, AI provenance, created/invalidated, version comparator, source, semantic + scope tags). Runtime verbs: remember, recall, observe, decorate.
- **AIDP / FMP v0.1.** Federated Memory Protocol: many memory servers behind one plugin, with `/fmp/*` endpoints over native, plugin + MCP, or plain MCP. Three types: ground truth, transcripts, inferences.
- **Cognee v0.1.** Six-part semantic core: identity/revision, evidence, scope/authority, PROV lineage, lifecycle/deletion, exchange manifest and receipts. COGX as workbench.
- **Context Nest v0.1.** Governed Markdown profile: version history, hash chain, checkpoints, status lifecycle, selectors, MCP binding. Forget protocol specified in §6.3.
- **AMS Card (Mila / Mozilla).** Structured documentation for memory systems, scoring performance and privacy separately. Documentation, not interchange.

## The matrix

**Key:** ● the draft specifies it · ◐ partial or mentioned · ○ out of scope by design · — not addressed

Cells rate what each draft *specifies*, not what is implemented. Cognee and Context Nest both say which parts are implemented and which are proposed. The scoping note is a survey, so its column shows what it identifies. Authors: please correct your own column.

| Primitive | Scoping | Packer | IBM | AIDP | Cognee | Context Nest | AMS |
|---|---|---|---|---|---|---|---|
| **The object** | | | | | | | |
| Body format | ● .md as common syntax | ● MEMORY.md dir | ◐ raw text body | ◐ files of any type | ● text baseline + typed media | ● markdown + front matter | — |
| Stable identifier | ◐ | ◐ file path | ● unique in origin system | ◐ id for delete | ● origin-qualified | ● URI, pinnable @version | — |
| Immutable revisions / versioning | ◐ | ○ version control out of scope | ● no update; override + invalidate; comparator | — | ● specified; not yet in COGX | ● append-only version chain | — |
| Semantic tags / ontology | ◐ | ◐ description field | ● tag schema; JSON-LD suggested | ◐ nested JSON metadata | ◐ deferred to domain profiles | ● type + tags; ontology shape | — |
| **Provenance and authority** | | | | | | | |
| Author; human vs AI origin | ◐ | ○ ownership out of scope | ● author + AI usage (EU AI Act) | ◐ "how it was created" | ● W3C PROV | ● author + client per version | ◐ documents it |
| Source / evidence link | ◐ | ◐ session_evidence metadata | ● source material (optional) | ● "exactly what it's based on" | ● epistemic roles | ◐ derived_from; source type | — |
| Lineage / consolidation | ● narrow waist | — | ◐ override chain | ◐ "based on" | ● all inputs named | ◐ derived_from + versions | — |
| Links / edges between memories | — | ◐ MEMORY.md points to nested files | ◐ source material link | ◐ "based on" | ◐ derivation references | ● [[wikilinks]] in prose | — |
| Scope tied to access control | ● surveyed | ○ who may write: out of scope | ● scope tags → ACLs, system-set | ◐ server-local permissions | ● subject / owner / authority / policy | ○ RBAC left out by design; scoping via selectors | ◐ |
| Human review / governed writes | ◐ | ○ out of scope | ◐ scope tags system-set | ● approval URL, admin sign-off | ◐ authorized actor on events | ● draft → published; approver recorded | ◐ |
| **Time and lifecycle** | | | | | | | |
| Created vs valid time | ◐ | — | ● created + invalidated | ◐ date field | ● record ≠ apply time | ● four clocks; pinned reads | — |
| Invalidation / supersession | ◐ | — | ● invalidation timestamp; override | — | ● distinct states | ◐ new version supersedes; status | — |
| Delete | ● | — | ● write / invalidate / delete | ● /fmp/delete | ● coverage + receipts | ● forget protocol §6.3 | ◐ |
| Tombstone / anti-resurrection | — | — | — | — | ● §3.5 | ● §6.3; imports must honor | — |
| **Exchange** | | | | | | | |
| Import / export | ● | ◐ portable directory | ● defined schema | ● read_* endpoints | ● manifest + receipts | ◐ export is the directory | — |
| Copy vs move vs federation | ◐ [federation discussed; copy/move not raised] | ◐ drag-and-drop move | ◐ one system at a time | ● federation is the core | ● distinct, explicit intent | ◐ namespace modes incl. federated | — |
| Integrity / self-verification | — | — | — | — | ◐ typed media integrity | ● hash chain; verify | — |
| Capability declaration | — | — | — | ● /fmp/info required | ● manifest | — | ● the card |
| **Runtime** | | | | | | | |
| Read / write verbs | ◐ | ● 4-rule harness contract | ● remember / recall / observe / decorate | ● upload / search / read / delete / info | ○ deferred to bindings | ◐ query by selector | — |
| Transport: MCP / hooks | ◐ | ◐ file tools | ● MCP; hooks proposed | ● native / plugin + MCP / MCP | ○ deferred to bindings | ● CLI / MCP / HTTP bindings | — |
| What loads into context | ◐ | ● the main job | — | — | ◐ via Markdown profile | ◐ selectors and packs | — |
| Documentation / disclosure | — | — | — | — | ◐ implemented vs proposed | ◐ implemented vs proposed | ● |

## Context: the #exchange-and-runtime thread

- **Before the call (9/22–9/25).** Misha suggested adding fidelity to Gabe's list: when a memory moves between systems, the receiving side should be able to check it is the same memory with the same history (see #8 and #9). Sruly backed Gabe's third point, working without a disk. He proposed the Skills-over-MCP extension (SEP-2640) as a natural way to get progressive disclosure over MCP, noting memory may update more often than skills. He also questioned markdown as the carrier for metadata: provenance, scope, revisions and embeddings needn't be in the agent's view, so a markdown body plus separately stored structured metadata may work better.
- **After the call (9/28).** Ben Labaschin pointed out the heavy overlap between the memory-model-and-context (MM&C) group, which defines the structure of the data, and this exchange-and-runtime (E&R) group, and suggested merging them. Gabe agreed, noted the call covered the shape of the data (header fields, body, linkage) and its use at export/import and at runtime, and asked Ben and Drew Breunig (MM&C) whether they object to a single workstream.
- **What this summary is for.** As Gabe framed it: where the data shapes overlap significantly, and where the existing proposals don't align (yet).

## Call notes: exchange and runtime, Sep 28

Attendees: Gabe Goodhart (IBM), Sruly Rosenblat (AIDP), Vasilije Markovic (Cognee), Alex Hancock (Block), Misha Sulpovar (Context Nest). Scope: data format and runtime only. User scope and candidate implementations were set aside. The method: go through the drafts, find what they have in common, check it against the constraints of implementations people know, and distill one abstract representation.

## Convergence

### Where the drafts already agree

- **A memory is a portable object: a body plus metadata.** Storage, retrieval and internal mutation stay with the implementation. Every draft except the AMS Card says this.
- **Provenance matters.** IBM, AIDP, Cognee and Context Nest all want the author, human or AI origin, and a link to the source evidence.
- **Scope feeds access control, and the system sets it, not the agent.** IBM, AIDP, Cognee and Context Nest.
- **Change by adding, not overwriting, where the implementation can.** IBM, Cognee and Context Nest. Delete exists in IBM, AIDP, Cognee and Context Nest.

### What the call converged on

[agreed] means at least two participants explicitly agreed and nobody objected. [proposed] means someone put it forward and it wasn't contested, but nobody explicitly signed on.

- **Header schema + any body [agreed].** Gabe's strawman: the header is a rigorous schema that can be rendered into anything that renders schemas, and the body is a string in any format, with markdown or plain text recommended as agent-friendly. Vasilije: "I completely agree." Other formats need room: DocLang (IBM Docling), CSV and XML (e.g. PubMed) were named, and Gabe's phrasing was "allow for that without requiring it." This matches Vasilije's "data contract": a stable transport header plus a free-form payload.
- **Export/import vs runtime representations [agreed].** Gabe distinguished a representation for export/import (migration) from one for runtime use. Export/import is likely a superset that carries operational fields the agent doesn't need, and that could "pollute or give hints to how the thing is organized." Vasilije called it "very important" and tied it to data contracts. It lines up with Sruly's thread point about keeping metadata out of the agent's view.
- **Don't standardize the recall signature [agreed].** Gabe: implementations need room for different flavors of recall and their own guidance on using it, and a fixed signature "would inevitably fail." Misha: "Fair enough."
- **Federation sits behind the agent [agreed].** Gabe's read-back: a federation or governance layer merges sources and takes the union of their scopes, and the agent can stay deliberately unaware of that and see one unified memory. Sruly: yes, and the merge logic needn't be specified. Misha: identity has to pass through. Vasilije: identity federation is part of the protocol, not the whole of it. Gabe: start from what the agent sees; the merge protocol comes second.
- **Lineage as a graph, depth up to the implementation [agreed].** Vasilije: full provenance on every object is too heavy, but people want to know where an object came from at a point in time, and some industries (finance) need exact detail. Gabe's strawman: model lineage as a graph; audit-grade systems can reconstruct it fully, and others can leave nodes as disconnected islands. Vasilije: "a great middle ground."
- **What "auditable" means [agreed].** Misha: from a regulatory standpoint, what matters is which human is accountable. Gabe: so auditable means you can trace a memory to one or more accountable humans. Misha: "Yep." Gabe: full audit is a multi-user enterprise requirement, not an individual-user one.
- **Annotate header fields by requirement [proposed].** Gabe: when this becomes a real draft, annotate header fields as audit-required, ACL-required or fully optional. He cautioned that optional fields tend to go unimplemented, as happened with MCP auth.

### The header, field by field

At Gabe's suggestion, the call walked Context Nest v0.1's front matter as a starting strawman. Gabe recapped the direction as a tightly scoped metadata header, with author extended into a provenance list and an identifier that supports evidence linkage. The call did not assign fields to tiers.

| Field | What was said | Status |
|---|---|---|
| identifier | Gabe proposed renaming `title` to `identifier`. It can be a readable title, a UUID or a path, carries no required meaning, and is unique among the memories in a bulk export. Sruly: an identifier is useful in general, especially for moving between systems. It is also what makes evidence links possible. Misha is still weighing how it fits path-plus-version identities. | [proposed] |
| type | The content type of the body (markdown, HTML, skills, structured data), not a semantic ontology. Misha: "that may be too constrained." | [discussed] |
| tags | Where the ontology lives: a list or set of strings, free-form or ontology-backed. | [discussed] |
| scope tags | Gabe: omit from the runtime format but keep in interchange, because ACLs attach to them. Authorship can cover cases like "what has Misha been up to." | [proposed] |
| created_at | "Pretty obvious." | [no objection] |
| version / updated | Gabe: all-immutable memory (a change creates a new superseding version) is too implementation-specific to be a hard contract, because it breaks markdown-on-disk. It may be a good recommendation for "zooming around in time." He also suggested a sequence number rather than real-world timestamps for versioning. Misha: that is how Context Nest implements it, and `updated_at` was added after the first meeting. Not settled. Whatever lands, the header keeps a `version` slot where richer history can live. | [open] |
| checksum | A quick hash for integrity. Gabe: "I like all of those." | [no objection] |
| provenance (was author) | Sruly: a list of everyone who contributed. Gabe: provenance may supersede author, and he recapped it as a provenance list of contributors. Its exact shape is open (see divergence). | [proposed] |
| evidence | Vasilije: evidence (where this came from) was missing. Gabe: it could be a reference to another memory's identifier, or flattened to a plain string. | [open] |
| links / edges | Misha: Context Nest's wiki-syntax links form graph edges, and it may be worth adding. Gabe: "linking is going to be a really interesting topic to discuss," since many formats are working on it. Not resolved. | [open] |
| status / visibility | Misha: published/unpublished and visibility inside a store. Gabe: it probably doesn't belong in the runtime format and may have a role in export/import; it overlaps with versioning. Put in the parking lot. | [parked] |

## Divergence: still under discussion

- **Markdown: common body format, not the base object (leaning).** Leaning toward markdown as the common body format rather than the base memory object. Vasilije doesn't think base memory objects should be markdown. Gabe finds markdown too simplistic for memory, but "it's what all the agents are doing today," and diverging too far risks irrelevance. Sruly: if this is exchange, you could hand over JSON and render it to markdown. Still open: what this means for a markdown-first loading profile.
- **What is the atomic unit?.** Vasilije: the base object is the smallest semantic unit that carries meaning and can be evaluated true or false ("Vasily left the cab"). Gabe: title and author fit a document store, less so a fact collection, and at that size a title may duplicate the body.
- **The shape of provenance.** Gabe: an AI-usage trailer with none / draft / full, similar to the EU AI Act's human / AI / mixed split. Sruly: when an assistant rewrites what you asked it to save, is that AI-generated? A plain list of contributors avoids grading it. Misha: separate optional human and agent fields. Misha's case: an agent updates memory on one person's instructions and another person approves. Whose name shows up? Ideally both. Misha: regulators care about who the accountable human is.
- **Versioning and updates.** Is a version required, and in what form? Can a memory change in place, or does every change create a new revision that supersedes the old one? Immutability suits audit and time travel; mutable files are how markdown stores work today. Does `updated_at` belong? Proposed floor: keep a `version` slot whatever the answer.
- **Edges and cross-document linking.** Raised on the call, not resolved. Options for discussion (not from the call): links written inline in the body (wiki syntax), a typed list of edges in the header (derived-from, supersedes, relates-to), or both. Questions: what a link targets (identifier, or identifier plus version), whether edges are typed, and what happens when the target isn't in the export or has been deleted.
- **Status and visibility.** Parked. Is lifecycle state (draft/published, visibility) general enough to standardize, or implementation-specific? It overlaps with versioning and forgetting times.
- **Lineage depth.** n hops back versus the full chain. Most users want "where did this come from at that point in time"; hedge funds and other financial firms want exact, fine-grained provenance. Where should the floor sit?
- **Runtime surface: is MCP the home?.** Gabe laid out three extremes: memory as local files the agent reads with shell tools; memory behind a server reachable only through tools; and a supervisor that uses hooks to decorate sessions and capture memories without the agent knowing. He proposed MCP (tools, interceptors for hooks, file access) as the logical home, standardizing only the shape of what passes through. Not agreed. Vasilije: MCP hasn't shown much promise; hooks are the new golden standard because they give control. Misha: a CLI has been more reliable than MCP for retrieval isolation (e.g. limiting graph hops), and they instrument hooks for consistency.
- **Identity and scope granularity.** Vasilije: is this partly identity provisioning and federation? One server for the organization and one personal breaks quickly, and even per-workspace may not be granular enough. What is the lowest granularity for scope?
- **Delivering several memories at runtime.** Misha: at runtime, is more than one memory passed? Compiled or raw? Can memories nest (each then carrying its own metadata and provenance)? His answer for Context Nest: no nested memories, compiled at runtime. Gabe took it into the three runtime extremes above. Not settled for the spec.
- **Writes.** Misha asked whether this covers writes. Gabe: defining the read shape constrains writes. A write needs author, date and time, and whether it updates something or creates something new; a title is optional. Misha: writes from a human, a webhook or an agent (e.g. a forget or "dream" agent) may need different authorship tagging.

## Whitespace: new ground to decide on

Rows tagged "not raised on the call" (or raised only in the thread) come from the drafts or the channel and are proposed for discussion. Each item needs a call: **discuss** (it belongs in the spec and isn't settled), **out of spec** (leave it to implementers to compete on) or **answered** (proposed resolution below). Items are judged against three goals: _adoption_, easy to implement on today's stores; _auditability_, traceable to an accountable human when required; and _innovation_, which means standardizing the interface and leaving room for people to build better solutions rather than locking one in.

| Area | Call | Proposed resolution / question | Goals |
|---|---|---|---|
| Recall function signature | [out of spec] | Agreed on the call. Standardize the memory shape that recall returns, not the recall call itself. | _innovation_ |
| Federation merge and ranking logic | [out of spec] | Standardize the per-server interface and the union view the agent sees. How results are combined is where implementations compete. | _innovation_ |
| Memory controllers (forget, dream, consolidation agents) | [out of spec] | Their algorithms stay with implementations. The only requirement: their writes carry provenance like any other writer. The industry name ("memory controller"?) is open. | _innovation_ _auditability_ |
| Retrieval isolation (hop limits, traversal depth) | [out of spec] | Implementation behavior behind recall. It's one reason CLI and MCP implementations differ. | _innovation_ |
| Audit log storage and delivery | [out of spec] | Logs live apart from the memory and don't travel with every retrieval. Agreed on the call to leave this to implementers. | _innovation_ |
| Auditable flag on memories and retrievals | [discuss] | Should the header or retrieval response be able to mark something auditable or not, so a consumer knows whether it traces to an accountable human? This is the small hook that makes the audit layer above possible. | _auditability_ _adoption_ |
| Definition of "auditable" | [answered] | Traceable to one or more accountable humans (Gabe and Misha on the call). Adopt as the definition. | _auditability_ |
| Field tiers | [proposed] | Proposed by Gabe: audit-required, ACL-required or fully optional on header fields. Next step: assign fields to tiers. | _adoption_ _auditability_ |
| Body formats | [answered] | Any body, with its format declared in `type`. Markdown is the common case; DocLang, CSV and XML were named as formats to allow ("allow for that without requiring it"). | _adoption_ _innovation_ |
| Legacy stores with no metadata (e.g. a folder of .md memories) | [discuss] | Allow heuristic backfill (the agent authored it, the local user is the human), but the export must say the information is lossy or not auditable. How is that declared? | _adoption_ _auditability_ |
| Split accountability (initiator, agent, approver) | [discuss] | An agent writes on one person's instructions and another person approves. Does the provenance list need roles, or is naming the accountable human enough? | _auditability_ |
| Delete, forget and resurrection on import | [discuss] [not raised on the call] | If a re-import creates a new memory, an invalidated or deleted memory can come back from an old archive. Is a tombstone needed in interchange (Cognee §3.5, Context Nest §6.3)? | _auditability_ |
| Copy vs move vs federation | [discuss] | IBM: valid in one system at a time. Cognee: three distinct intents that keep origin identity. The answer decides what `identifier` means after import. | _adoption_ _auditability_ |
| Import fidelity and receipts | [discuss] [raised in the thread (Misha), not on the call] | How does a receiver confirm it got the same memory with the same history, and report what was transformed or dropped? The checksum is part of this; a manifest or receipt may be the rest. | _auditability_ |
| Change notification at runtime | [discuss] [raised in the thread (Sruly: memory updates often), not on the call] | When a memory changes mid-session, how does the harness find out? MCP resource subscriptions are one candidate. Implementations would fill in the details. | _adoption_ _innovation_ |
| Conformance floor and profiles | [discuss] [not raised on the call] | AIDP makes every endpoint optional except `/info`; Cognee argues for a floor. Is there a minimum profile, with a Markdown loading profile (Packer) and a federation binding (AIDP) layered on top? | _adoption_ |
| Identity pass-through for federation | [discuss] | Point to existing auth (OAuth, MCP auth) rather than define our own? The spec probably only needs the identity fields the union view must carry. | _adoption_ |
| Dangling links on export | [discuss] [not raised on the call] | In a partial export, a link may point to a memory that wasn't included or was deleted. Keep it as an unresolved reference, drop it, or report it in the import results? | _adoption_ _auditability_ |
| Credentials in exports | [answered] [not raised on the call] | Excluded from memory exchange (Cognee §3.3), handled as a separate administrative operation. | _auditability_ |

## Actions

- **Misha:** summarize the discussion, where the data shapes overlap and where the proposals don't align yet. Done as this document (PR #10). Sruly asked for the notes.
- **Vasilije:** once he has the first version, come back with the elements missing from the higher-level representation.
- **Ben Labaschin and Drew Breunig:** respond to Gabe's question on merging MM&C and E&R into a single workstream.
- **Everyone:** settle the open header fields and tiers ahead of the Oct 2 draft.

Sources: The-AI-Disclosures-Project/Open-Memory-Protocol, `main` @ 7beb260, `early-draft-specs/`.

