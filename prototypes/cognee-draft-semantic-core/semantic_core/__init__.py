"""Cognee discussion draft v0.1 (early-draft-specs/draft-v0.1-cognee.md) as code.

The draft proposes a six-part contract every memory exchange should preserve. This package is
one prototype of that contract, at the same level as the Packer, AIDP and IBM prototypes:

- semantic_core.schema    : §3.1-3.6 as types (identity+revision, evidence role, scope/authority,
                            PROV-style derivation, lifecycle events, manifest + receipts)
- semantic_core.store     : a store that imports/exports exchanges and enforces the lifecycle,
                            tombstone, idempotency and policy rules the draft states
- semantic_core.cogx      : read/write COGX 0.1 archives (§4) without a Cognee dependency
- semantic_core.adapters  : the sibling prototypes (IBM records, FMP, Packer directories) as
                            exchanges, so each can be exercised against the same validator
- semantic_core.validator : checks an exchange against the contract; ships fixtures for the
                            cases §6 lists
"""

from semantic_core.schema import (
    Derivation,
    EvidenceRole,
    Exchange,
    LifecycleEvent,
    LifecycleKind,
    Manifest,
    MemoryObject,
    ObjectRef,
    Policy,
    PolicyRule,
    Receipt,
    ReceiptEntry,
    ReceiptStatus,
    Scope,
)
from semantic_core.store import SemanticStore

__version__ = "0.1.0"
__all__ = [
    "Derivation",
    "EvidenceRole",
    "Exchange",
    "LifecycleEvent",
    "LifecycleKind",
    "Manifest",
    "MemoryObject",
    "ObjectRef",
    "Policy",
    "PolicyRule",
    "Receipt",
    "ReceiptEntry",
    "ReceiptStatus",
    "Scope",
    "SemanticStore",
]
