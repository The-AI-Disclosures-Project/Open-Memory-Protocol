"""IBM OMPI draft v0.1 (early-draft-specs/draft-v0.1-ibm.pdf) as code.

- ibm_memory.schema        : MemoryRecord (body, identifier, lifecycle, semantic + scope tags)
- ibm_memory.store         : immutable store with override/invalidate, time travel, scope ACLs,
                             and export/import between systems
- ibm_memory.packer_bridge : Packer-draft memory directory <-> records, round-trippable
- ibm_memory.middleware    : Remember / Recall (tools) and Observe / Decorate (hooks) for
                             LangChain create_agent
"""

from ibm_memory.middleware import IBMMemoryMiddleware
from ibm_memory.schema import ExportBundle, Lifecycle, MemoryRecord, Provenance
from ibm_memory.store import MemoryStore, ScopeDenied, ScopePolicy

__version__ = "0.1.0"
__all__ = [
    "ExportBundle",
    "IBMMemoryMiddleware",
    "Lifecycle",
    "MemoryRecord",
    "MemoryStore",
    "Provenance",
    "ScopeDenied",
    "ScopePolicy",
]
