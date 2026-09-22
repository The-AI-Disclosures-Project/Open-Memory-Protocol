"""Interface elements from the IBM draft §Interoperability between memory systems.

    Memory Body        raw text, no constraints
    Memory Identifier  unique within the originating system
    Lifecycle          author, AI usage / provenance, timestamps, versioning, source material
    Semantic Tags      arbitrary tags with semantic meaning; only the *schema* is standard
    Scope Tags         arbitrary tags defining scope; bound to ACL policies

    PROPOSAL => Memories are immutable ... Logical mutation is accomplished by override
    and invalidation.

The only field that ever changes on a record is `lifecycle.invalidated_at`, and it changes
once (None -> timestamp). Everything else is frozen.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

SCHEMA_VERSION = "ibm-omp-0.1"


def now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def new_id() -> str:
    return uuid.uuid4().hex


class Provenance(BaseModel):
    """AI usage in creating the memory (the draft ties this to the EU AI Act)."""

    model_config = ConfigDict(frozen=True)

    ai_used: bool = False
    model: str | None = None
    agent: str | None = None
    how: str | None = None
    """Free text: "verbatim user statement", "extracted from transcript", "consolidated" ..."""


class Lifecycle(BaseModel):
    model_config = ConfigDict(frozen=True)

    author: str
    """Identifier for the human author involved in creation."""
    provenance: Provenance = Field(default_factory=Provenance)
    created_at: str = Field(default_factory=now_iso)
    invalidated_at: str | None = None
    version: int = 1
    """Draft: versioning semantics are implementation detail but MUST have a standard
    comparator. Here: a monotonic integer per override chain."""
    source_material: list[str] = Field(default_factory=list)
    """Links or refs to what the memory was derived from."""


class MemoryRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str = Field(default_factory=new_id)
    body: str
    lifecycle: Lifecycle
    semantic_tags: list[str] = Field(default_factory=list)
    scope_tags: list[str] = Field(default_factory=list)
    supersedes: str | None = None
    """Id of the record this one overrides (logical mutation)."""
    origin: str | None = None
    """Set on import: "<system_id>:<original id>". A memory is valid in exactly one system;
    an imported copy is a *new* memory that remembers where it came from."""

    # --- lifecycle predicates
    def valid_at(self, ts: str | None = None) -> bool:
        ts = ts or now_iso()
        lc = self.lifecycle
        return lc.created_at <= ts and (lc.invalidated_at is None or lc.invalidated_at > ts)

    @property
    def is_valid(self) -> bool:
        return self.lifecycle.invalidated_at is None

    def invalidated(self, at: str | None = None) -> MemoryRecord:
        """Return a copy with invalidated_at set (the one permitted lifecycle transition)."""
        if self.lifecycle.invalidated_at is not None:
            return self
        return self.model_copy(
            update={
                "lifecycle": self.lifecycle.model_copy(update={"invalidated_at": at or now_iso()})
            }
        )


class ExportBundle(BaseModel):
    """Draft §Interface Implications: "Schema for export/import well-defined"."""

    schema_version: str = SCHEMA_VERSION
    system_id: str
    exported_at: str = Field(default_factory=now_iso)
    records: list[MemoryRecord]
    tag_context: dict[str, Any] = Field(default_factory=dict)
    """Optional vocabulary for tags, in the spirit of a JSON-LD @context: tag -> meaning/URI.
    Lets the importing system run its mapping/migration step."""
