# Community implementation examples

These independently maintained examples help implementers run experiments and report interoperability findings. Listing an example is not an endorsement, a conformance certification, or designation as an official reference implementation. Read each implementation’s draft coverage, security model, and limitations before using it.

## OMP on Cloudflare

**Repository:** [irvinebroque/omp-cloudflare](https://github.com/irvinebroque/omp-cloudflare)  
**Maintainer:** [irvinebroque](https://github.com/irvinebroque)  
**Draft target:** [Editors’ v0.5](../working-group/exchange-and-runtime/2026-11-06-working-spec-v0.5.md)  
**License:** Apache-2.0

A TypeScript example with a Cloudflare Worker, separate personal/company stores in Artifacts Git repositories, a minimal Pi-powered chat agent, an HTTP SDK, and six MCP tools. It demonstrates creating, recalling, revising, deleting, exporting, and importing small UTF-8 memories while retaining unknown JSON metadata and origin identity.

- [Run locally or deploy to your account](https://github.com/irvinebroque/omp-cloudflare#readme), including a Deploy to Cloudflare button. Local memory development uses an Artifacts simulator; chat requires Workers AI inference. Deployment requires Workers Paid and Artifacts access.
- [Pi agent architecture and limits](https://github.com/irvinebroque/omp-cloudflare/blob/main/docs/agent.md): conversations persist in SQLite Durable Objects; explicit tool-saved facts become portable OMP records.
- [Protocol coverage and experimental choices](https://github.com/irvinebroque/omp-cloudflare/blob/main/docs/protocol.md), including the snapshot envelope, typed-link handling, import receipts, and collision limits.
- [Validation record](https://github.com/irvinebroque/omp-cloudflare/blob/main/docs/validation.md) and [automated checks](https://github.com/irvinebroque/omp-cloudflare/actions).
- [Optional Codex memory skill and MCP setup](https://github.com/irvinebroque/omp-cloudflare/blob/main/codex/README.md).

The implementation uses one shared access key. Store routing and runtime applicability are not multi-user authorization. Deletion retains Git history. Its HTTP/MCP binding, archive identity map, concurrency token and runtime conventions are implementation choices, not adopted OMP schemas. It does not claim secure forgetting, binary transport, or full-profile conformance.

## Maintenance and possible adoption

Example code can evolve independently while this repository remains the home for protocol drafts and agreed interoperability requirements. File implementation bugs in the example’s repository; discuss protocol questions and candidate shared fixtures here.

The Cloudflare example is available for maintainers to consider adopting or transferring into the project’s organization. Any transfer, official reference designation, supported-version policy, and maintenance arrangement would need the project’s agreement through its normal governance process. This documentation change does not make that decision.

To propose another listing, include a maintainer, license, supported draft or profile, reproducible setup, validation evidence, and explicit implementation-specific limitations.
