# Open Memory Protocol: where the drafts agree

> Working notes from the exchange-and-runtime sub-thread. A styled version of this page is in [`2026-09-28-common-ground.html`](2026-09-28-common-ground.html) (download to view).

A working matrix of every draft in `early-draft-specs/` on `main` (commit 7beb260), plus notes from the Sep 28 exchange-and-runtime call, for the draft due Oct 2, 2026. Discussion draft, 2026-09-28.

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
| Copy vs move vs federation | ◐ [not raised on the call] | ◐ drag-and-drop move | ◐ one system at a time | ● federation is the core | ● distinct, explicit intent | ◐ namespace modes incl. federated | — |
| Integrity / self-verification | — | — | — | — | ◐ typed media integrity | ● hash chain; verify | — |
| Capability declaration | — | — | — | ● /fmp/info required | ● manifest | — | ● the card |
| **Runtime** | | | | | | | |
| Read / write verbs | ◐ | ● 4-rule harness contract | ● remember / recall / observe / decorate | ● upload / search / read / delete / info | ○ deferred to bindings | ◐ query by selector | — |
| Transport: MCP / hooks | ◐ | ◐ file tools | ● MCP; hooks proposed | ● native / plugin + MCP / MCP | ○ deferred to bindings | ● CLI / MCP / HTTP bindings | — |
| What loads into context | ◐ | ● the main job | — | — | ◐ via Markdown profile | ◐ selectors and packs | — |
| Documentation / disclosure | — | — | — | — | ◐ implemented vs proposed | ◐ implemented vs proposed | ● |

## Call notes: exchange and runtime, Sep 28

Attendees: Gabe Goodhart (IBM), Sruly Rosenblat (AIDP), Vasilije Markovic (Cognee), Alex Hancock (Block), Misha Sulpovar (Context Nest). Scope: data format and runtime only. User scope and candidate implementations were set aside. The method was to read the drafts, find what they have in common, check it against the constraints of implementations we know, and distill one abstract representation.

## Convergence

### Where the drafts already agree

- **A memory is a portable object: a body plus metadata.** Storage, retrieval and internal mutation stay with the implementation. Every draft except the AMS Card says this.
- **Provenance matters.** IBM, AIDP, Cognee and Context Nest all want the author, human or AI origin, and a link to the source evidence.
- **Scope feeds access control, and the system sets it, not the agent.** IBM, AIDP, Cognee and Context Nest.
- **Change by adding, not overwriting, where the implementation can.** IBM, Cognee and Context Nest. Delete exists in IBM, AIDP, Cognee and Context Nest.

### What the call agreed

- **Header schema + any body.** The header is a rigorous schema that can be rendered into anything that renders schemas. The body can be any format, declared by `type`. Markdown is the assumed common case, but the spec has to support others: plain text, XML (e.g. PubMed), DocLang (IBM Docling), CSV, HTML. This matches Vasilije's "data contract": a stable transport header plus a free-form payload.
- **Two representations.** The *interchange* format (export/import) is a superset of the *runtime* format. Operational fields such as scope tags, ACL bindings and status/visibility travel in interchange. They stay out of the agent's context, where they would add noise or leak how the store is organized.
- **MCP is the runtime home.** Runtime access comes down to three things: tools (MCP), hooks (MCP interceptors) and file-system access, which is itself a tool. The spec should standardize the *shape of what passes through* them, not a new transport.
- **Recall signature is not standardized.** Implementations need room to provide their own flavors of recall and guidance on using them. Fixing one function signature "would inevitably fail."
- **Federation sits behind the agent.** A federation or governance layer merges sources and takes the union of their scopes. The agent can stay deliberately unaware of that and see one unified memory. Identity has to pass through. The merge protocol comes second; start with what the agent sees.
- **Lineage as a graph, depth up to the implementation.** Evidence and lineage are graph edges. A system that must pass audits can reconstruct the full chain; others can leave nodes as disconnected islands. The spec doesn't require full provenance on every object.
- **What "auditable" means.** A memory is auditable if it can be traced to one or more accountable humans. Full audit is a multi-user enterprise requirement, not a single-user one.
- **Field tiers.** Annotate each header field as **required**, **audit-required** or **optional**. That avoids MCP-auth's failure mode, where optional meant unimplemented.
### The header, field by field

At Gabe's suggestion, the call walked Context Nest v0.1's front matter as a starting strawman and checked it against IBM's record and Cognee's core.

| Field | Where the call landed | Tier (proposed) | Status |
|---|---|---|---|
| identifier | Rename `title` to `identifier`. It can be a readable title, a UUID or a path, carries no required meaning, and must be unique within a bulk export. It's needed for evidence links and for moving memories between systems. | required | [agreed] |
| type | The content/media type of the body (markdown, HTML, skill, structured data, DocLang…), not a semantic ontology. | required | [agreed] |
| tags | Semantic tags: a list or set of strings, free-form or drawn from an ontology (IBM's semantic tags). | optional | [agreed] |
| scope tags | Kept in interchange (ACLs need them) and left out at runtime. | interchange only | [agreed] |
| created_at | Straightforward. | required | [agreed] |
| version / updated | Gabe floated a sequence number or comparator instead of wall-clock time, with immutable revisions as a recommendation ("time travel") rather than a hard contract, since a hard rule breaks markdown-on-disk stores. `updated_at` came out of the first meeting. Not settled. Whatever lands, the header keeps a `version` slot with a declared comparator. Implementations with richer history (immutable revisions, hash chains, as-of reads) expose it there, possibly as an audit-required tier. | — | [open] |
| checksum | An integrity hash of the memory. | audit-required | [agreed] |
| provenance (was author) | A list of contributors, human and agent. It may replace `author`. | required, with the accountable human audit-required | [shape open] |
| evidence | A link back to source material (Cognee). It can be a reference to another identifier or a flat string. | optional, audit-required | [shape open] |
| links / edges | Raised on the call (Context Nest's wiki-syntax links form graph edges) and flagged by Gabe as "a really interesting topic" that many formats are working on. Nothing agreed yet. The identifier rename is partly there to make linking possible. | — | [open] |
| status / visibility | Published/unpublished and visibility inside a store. Possibly specific to one implementation. It would only belong in interchange, never at runtime. | — | [parked] |

## Divergence: still under discussion

- **Is markdown a base object?.** Vasilije: base memory objects shouldn't be interpretable as markdown. Gabe: markdown is too simple for memory, but it's what agents do today, and a format that diverges too far risks irrelevance. Allowing any body with a declared type mostly defuses this; what it means for the runtime profile is still open.
- **What is the atomic unit?.** Vasilije: the smallest semantic unit that carries meaning and can be judged true or false ("Vasilije left the cab"). The title/author framing fits a document store better than a collection of facts, and at fact size a title may just repeat the body.
- **The shape of provenance.** Options raised: an enumerated AI-usage value (none / draft / full, close to the EU AI Act's three-way split); a plain list of contributors; separate optional human and agent fields. There's also the case of an agent acting on a person's instructions with a second person approving — who is recorded?
- **Versioning and updates.** Is a version required, and what form does it take (sequence, comparator, semver)? Can a memory be updated in place, or is every change a new revision that supersedes the old one? Immutability suits audit and as-of reads; mutable files are how markdown stores work today. Does `updated_at` belong in the header at all? Proposed floor: keep a `version` slot whatever the answer, so richer history has somewhere to live.
- **Edges and cross-document linking.** How does one memory point to another? Options: links written inline in the body (wiki syntax, so they work across any format), a typed list of edges in the header (derived-from, supersedes, relates-to), or both. Open questions: what a link targets (identifier, identifier plus version, an origin-qualified ID), whether edges are typed, and what happens to a link when its target isn't in the export or is deleted. This connects to evidence, lineage-as-a-graph and identifier uniqueness.
- **Status and visibility.** Is lifecycle state (draft/published, visibility) general enough to standardize, or specific to one implementation? It overlaps with versioning and forget times. Parked.
- **Lineage depth.** n hops back versus the full chain. Most users want "where did this come from at that point in time"; finance and hedge funds want exact, fine-grained provenance. Where should the required floor sit?
- **Runtime surface.** Vasilije: MCP hasn't shown much promise, and hooks are the new standard because they give control. Misha: a CLI has been more reliable than MCP for retrieval isolation (e.g. hop limits during graph traversal). Gabe: all three meet under MCP (tools, interceptors, file system).
- **Identity and scope granularity.** Is the spec partly doing identity provisioning and federation? One server for work and one for personal breaks quickly; per-workspace may not be enough either. What is the lowest granularity for scope? Identity federation should be part of the protocol, not all of it.
- **Identifier uniqueness.** Unique within an export is agreed. Open: how it lines up with path-plus-version identities and with origin-qualified identity (Cognee §3.1) after import.
- **Delivering several memories at runtime.** When the memory layer returns several memories, are they compiled into one payload or passed raw? Can memories nest? If they can, each one carries its own metadata and provenance. Raised; not answered.

## Whitespace: new ground to decide on

Rows tagged "not raised on the call" come from the drafts and are proposed for discussion. Each item needs a call: **discuss** (it belongs in the spec and isn't settled), **out of spec** (leave it to implementers to compete on) or **answered** (proposed resolution below). Items are judged against three goals: _adoption_, easy to implement on today's stores; _auditability_, traceable to an accountable human when required; and _innovation_, which means standardizing the interface and leaving room for people to build better solutions rather than locking one in.

| Area | Call | Proposed resolution / question | Goals |
|---|---|---|---|
| Recall function signature | [out of spec] | Agreed on the call. Standardize the memory shape that recall returns, not the recall call itself. | _innovation_ |
| Federation merge and ranking logic | [out of spec] | Standardize the per-server interface and the union view the agent sees. How results are combined is where implementations compete. | _innovation_ |
| Memory controllers (forget, dream, consolidation agents) | [out of spec] | Their algorithms stay with implementations. The only requirement: their writes carry provenance like any other writer. The industry name ("memory controller"?) is open. | _innovation_ _auditability_ |
| Retrieval isolation (hop limits, traversal depth) | [out of spec] | Implementation behavior behind recall. It's one reason CLI and MCP implementations differ. | _innovation_ |
| Audit log storage and delivery | [out of spec] | Logs live apart from the memory and don't travel with every retrieval. Agreed on the call to leave this to implementers. | _innovation_ |
| Auditable flag on memories and retrievals | [discuss] | Should the header or retrieval response be able to mark something auditable or not, so a consumer knows whether it traces to an accountable human? This is the small hook that makes the audit layer above possible. | _auditability_ _adoption_ |
| Definition of "auditable" | [answered] | Traceable to one or more accountable humans. Adopt as the definition. | _auditability_ |
| Field tiers | [answered] | Required / audit-required / optional on every header field. Next step: fill in the tier column above. | _adoption_ _auditability_ |
| Body formats | [answered] | Any body, with its format declared in `type`. Markdown is the assumed common case; XML, DocLang, CSV, HTML and plain text must also be supported. | _adoption_ _innovation_ |
| Legacy stores with no metadata (e.g. a folder of .md memories) | [discuss] | Allow heuristic backfill (the agent authored it, the local user is the human), but the export must say the information is lossy or not auditable. How is that declared? | _adoption_ _auditability_ |
| Split accountability (initiator, agent, approver) | [discuss] | An agent writes on one person's instructions and another person approves. Does the provenance list need roles, or is naming the accountable human enough? | _auditability_ |
| Delete, forget and resurrection on import | [discuss] [not raised on the call] | If a re-import creates a new memory, an invalidated or deleted memory can come back from an old archive. Is a tombstone needed in interchange (Cognee §3.5, Context Nest §6.3)? | _auditability_ |
| Copy vs move vs federation | [discuss] | IBM: valid in one system at a time. Cognee: three distinct intents that keep origin identity. The answer decides what `identifier` means after import. | _adoption_ _auditability_ |
| Import fidelity and receipts | [discuss] [not raised on the call] | How does a receiver confirm it got the same memory with the same history, and report what was transformed or dropped? The checksum is part of this; a manifest or receipt may be the rest. | _auditability_ |
| Change notification at runtime | [discuss] [not raised on the call] | When a memory changes mid-session, how does the harness find out? MCP resource subscriptions are one candidate. Implementations would fill in the details. | _adoption_ _innovation_ |
| Conformance floor and profiles | [discuss] [not raised on the call] | AIDP makes every endpoint optional except `/info`; Cognee argues for a floor. Is there a minimum profile, with a Markdown loading profile (Packer) and a federation binding (AIDP) layered on top? | _adoption_ |
| Identity pass-through for federation | [discuss] | Point to existing auth (OAuth, MCP auth) rather than define our own? The spec probably only needs the identity fields the union view must carry. | _adoption_ |
| Dangling links on export | [discuss] [not raised on the call] | In a partial export, a link may point to a memory that wasn't included or was deleted. Keep it as an unresolved reference, drop it, or report it in the import results? | _adoption_ _auditability_ |
| Credentials in exports | [answered] [not raised on the call] | Excluded from memory exchange (Cognee §3.3), handled as a separate administrative operation. | _auditability_ |

## Actions from the call

- **Misha:** build this table and the call notes and share them on Discord (possibly also as a PR to the repo).
- **Vasilije:** review v1 and send back what's missing from the header.
- **Everyone:** settle the "discuss" rows and the field tiers ahead of the Oct 2 draft.

Sources: The-AI-Disclosures-Project/Open-Memory-Protocol, `main` @ 7beb260, `early-draft-specs/`.

