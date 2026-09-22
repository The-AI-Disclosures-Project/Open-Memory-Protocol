# Prototypes

Experimental implementations developed as part of the Open Memory Protocol
Initiative.

## Current prototypes

- [`acp_memory_server/`](acp_memory_server/) — an ACP-based MCP server that
  indexes and searches coding agent session history.
- [`packer-draft-langchain-harness/`](packer-draft-langchain-harness/) — a LangChain
  `create_agent` harness whose middleware implements the four-rule harness contract
  from the Packer draft spec v0.2.
- [`aidp-draft-fmp/`](aidp-draft-fmp/) — Federated Memory Protocol (AIDP draft v0.1):
  reference `/fmp/*` server, a read-only FMP view over the ACP index, a federated
  client, and LangChain middleware with transcript-capture hooks.
- [`ibm-draft-memory-records/`](ibm-draft-memory-records/) — IBM draft v0.1: immutable
  memory records (body, lifecycle, provenance, semantic + scope tags), override and
  invalidate with time travel, scope ACLs, export/import between systems, a Packer
  round-trip bridge, and Remember / Recall / Observe / Decorate as LangChain middleware.
