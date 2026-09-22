"""§3 "Meaning of the common core", one type per part.

The draft says exact field names and serialization "remain working group decisions"; these
are one concrete proposal so the rules can be tested.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

FORMAT_VERSION = "cognee-draft-0.1"


def now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def new_id() -> str:
    return uuid.uuid4().hex


# ------------------------------------------------------------------ §3.1 identity + revision


class ObjectRef(BaseModel):
    """Logical identity, qualified by origin authority and namespace."""

    model_config = ConfigDict(frozen=True)

    authority: str
    """Who minted the id: a system id, org, or user authority."""
    namespace: str = "memory"
    local_id: str

    def __str__(self) -> str:
        return f"{self.authority}/{self.namespace}/{self.local_id}"

    @classmethod
    def parse(cls, s: str) -> ObjectRef:
        a, n, lid = s.split("/", 2)
        return cls(authority=a, namespace=n, local_id=lid)


def content_digest(text: str | None, media: MediaDescriptor | None) -> str:
    h = hashlib.sha256()
    h.update((text or "").encode("utf-8"))
    if media:
        h.update(f"|{media.media_type}|{media.digest}".encode())
    return h.hexdigest()


# ------------------------------------------------------------------ §3.2 content + evidence


class EvidenceRole(str, Enum):
    """Epistemic roles, not truth labels."""

    source_artifact = "source_artifact"
    transcript = "transcript"
    human_assertion = "human_assertion"
    machine_derived = "machine_derived"


class MediaDescriptor(BaseModel):
    model_config = ConfigDict(frozen=True)

    media_type: str
    digest: str
    """sha256 of the bytes, so integrity is verifiable."""
    uri: str | None = None
    size: int | None = None


# ------------------------------------------------------------------ §3.3 scope + authority


class Scope(BaseModel):
    model_config = ConfigDict(frozen=True)

    subject: str | None = None
    """Whom the memory concerns."""
    owner: str | None = None
    """Who controls it."""
    author: str | None = None
    """Human author, if any."""
    agent: str | None = None
    """Generating agent, if any."""
    origin_system: str
    context: dict[str, str] = Field(default_factory=dict)
    """Applicable context: user, agent, session, run, project, team, organization, or
    qualified extensions ("acme:region"). A scope label is not an access grant."""


class PolicyRule(BaseModel):
    model_config = ConfigDict(frozen=True)

    principals: list[str]
    actions: list[str]
    """read, write, derive, export, delete, ... Unsupported required actions cause rejection."""
    resources: list[str] = Field(default_factory=lambda: ["*"])
    constraints: dict[str, Any] = Field(default_factory=dict)
    """e.g. {"retain_until": iso, "use": "no-training"}"""


class Policy(BaseModel):
    model_config = ConfigDict(frozen=True)

    rules: list[PolicyRule] = Field(default_factory=list)
    required: bool = True
    """If the receiver cannot map every principal and enforce every rule, it must reject or
    stage the object; never silently widen access."""


# ------------------------------------------------------------------ §3.4 provenance + lineage


class Derivation(BaseModel):
    """PROV-shaped: activity used input revisions, performed by an agent at a time."""

    model_config = ConfigDict(frozen=True)

    activity: str
    """extraction | correction | consolidation | re_derive | import | ..."""
    used: list[str] = Field(default_factory=list)
    """Exact input revision ids."""
    spans: list[str] = Field(default_factory=list)
    """Finer references: "<revision>#turn:3", "<revision>#chars:120-240"."""
    agent: str | None = None
    """Responsible actor or model."""
    at: str | None = None
    config_id: str | None = None
    unknown: bool = False
    """Unknown provenance must remain unknown, not be invented."""


# ------------------------------------------------------------------ §3.5 lifecycle


class LifecycleKind(str, Enum):
    supersede = "supersede"
    retract = "retract"
    invalidate = "invalidate"
    expire = "expire"
    delete = "delete"
    tombstone = "tombstone"


class LifecycleEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    event_id: str = Field(default_factory=new_id)
    kind: LifecycleKind
    target: str
    """Target revision id."""
    actor: str
    effective_at: str = Field(default_factory=now_iso)
    reason: str | None = None
    replacement: str | None = None
    """For supersede: the revision that replaces the target."""
    coverage: list[str] = Field(default_factory=list)
    """For delete: what the deletion covers (derivations, indexes, caches) under the
    receiver's control."""


class ObjectState(str, Enum):
    active = "active"
    superseded = "superseded"
    retracted = "retracted"
    invalidated = "invalidated"
    expired = "expired"
    deleted = "deleted"


# ------------------------------------------------------------------ the object


class MemoryObject(BaseModel):
    model_config = ConfigDict(frozen=True)

    ref: ObjectRef
    revision_id: str = Field(default_factory=new_id)
    predecessor: str | None = None
    """Previous revision id, for corrections."""
    role: EvidenceRole
    text: str | None = None
    media: MediaDescriptor | None = None
    scope: Scope
    policy: Policy = Field(default_factory=Policy)
    derivation: Derivation | None = None
    """Required for machine_derived (may be Derivation(unknown=True))."""
    recorded_at: str = Field(default_factory=now_iso)
    applies_from: str | None = None
    applies_until: str | None = None
    """When the claim applies, distinct from when it was recorded."""
    expires_at: str | None = None
    extensions: dict[str, Any] = Field(default_factory=dict)
    """Profile/extension payloads, keyed by extension name (e.g. "cogx.raw_node")."""

    @property
    def digest(self) -> str:
        return content_digest(self.text, self.media)


# ------------------------------------------------------------------ §3.6 exchange


class Profile(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    version: str
    required: bool = False


TransferIntent = Literal["copy", "move", "federate"]


class Manifest(BaseModel):
    format_version: str = FORMAT_VERSION
    source_system: str
    exported_at: str = Field(default_factory=now_iso)
    exchange_id: str = Field(default_factory=new_id)
    profiles: list[Profile] = Field(default_factory=list)
    object_kinds: list[str] = Field(default_factory=list)
    scope_coverage: list[str] = Field(default_factory=list)
    complete_snapshot: bool = False
    """False: absence from this exchange never implies deletion."""
    required_extensions: list[str] = Field(default_factory=list)
    transfer_intent: TransferIntent = "copy"
    notes: list[str] = Field(default_factory=list)


class Exchange(BaseModel):
    manifest: Manifest
    objects: list[MemoryObject] = Field(default_factory=list)
    events: list[LifecycleEvent] = Field(default_factory=list)


class ReceiptStatus(str, Enum):
    accepted = "accepted"
    transformed = "transformed"
    omitted = "omitted"
    unresolved = "unresolved"
    rejected = "rejected"


class ReceiptEntry(BaseModel):
    target: str
    """Origin revision id (or event id)."""
    kind: Literal["object", "event"] = "object"
    status: ReceiptStatus
    local_id: str | None = None
    reason: str | None = None
    transformations: list[str] = Field(default_factory=list)


class Receipt(BaseModel):
    exchange_id: str
    receiver: str
    mode: Literal["preserve", "re_derive", "hybrid"]
    entries: list[ReceiptEntry] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    retry: list[str] = Field(default_factory=list)
    """Targets that may be retried (unresolved), so partial failures state retry boundaries."""
    move_complete: bool | None = None
    """For transfer_intent=move: True only if every object was accepted, so the source may
    delete. None for copy/federate."""

    @property
    def counts(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for e in self.entries:
            out[e.status.value] = out.get(e.status.value, 0) + 1
        return out
