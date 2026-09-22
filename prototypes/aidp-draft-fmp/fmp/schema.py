"""Wire types for FMP (AIDP draft v0.1).

The draft names three memory types and eight endpoints and leaves exact fields "TBD".
This module is a concrete proposal for those fields. Every record carries a nested
`metadata` object for arbitrary extension, as the draft asks.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field

FMP_VERSION = "0.1"


def now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def new_id() -> str:
    return uuid.uuid4().hex


class MemoryType(str, Enum):
    file = "file"
    transcript = "transcript"
    inference = "inference"


# ------------------------------------------------------------------ ground truth: files


class FileUpload(BaseModel):
    name: str
    content: str
    mime: str = "text/plain"
    metadata: dict[str, Any] = Field(default_factory=dict)


class FileRecord(FileUpload):
    id: str
    uploaded_at: str


# ------------------------------------------------------------------- transcripts


class Message(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: str
    ts: str | None = None
    tool_name: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class TranscriptUpload(BaseModel):
    id: str | None = None
    """Client-supplied session id, so partial uploads of the same session can be merged."""
    source: str
    """Which harness/agent produced it, e.g. "langchain", "claude-code"."""
    messages: list[Message]
    started_at: str | None = None
    title: str | None = None
    partial: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class TranscriptRecord(BaseModel):
    id: str
    source: str
    started_at: str | None
    title: str | None
    partial: bool
    message_count: int
    metadata: dict[str, Any] = Field(default_factory=dict)
    messages: list[Message] | None = None
    """Only populated by read_transcripts when include_messages=true."""


# ------------------------------------------------------------------- inferences


class CreatedBy(BaseModel):
    kind: Literal["agent", "user", "memory_provider"] = "agent"
    name: str | None = None
    model: str | None = None


class InferenceUpload(BaseModel):
    content: str
    date: str = Field(default_factory=now_iso)
    created_by: CreatedBy = Field(default_factory=CreatedBy)
    based_on: list[str] = Field(default_factory=list)
    """References to what the inference is grounded in, e.g. "transcript:<id>#<turn>"."""
    metadata: dict[str, Any] = Field(default_factory=dict)


class InferenceRecord(InferenceUpload):
    id: str


# ------------------------------------------------------------------- search


class SearchRequest(BaseModel):
    query: str
    types: list[MemoryType] | None = None
    limit: int = Field(default=10, ge=1, le=100)
    since: str | None = None
    """ISO-8601 floor on the record's timestamp."""


class SearchHit(BaseModel):
    id: str
    type: MemoryType
    score: float
    snippet: str
    ts: str | None = None
    source: str | None = None
    ref: str
    """Stable reference for based_on, e.g. "transcript:<id>#<turn>" or "inference:<id>"."""
    server: str | None = None
    """Filled in by the federated client, never by the server."""


class SearchResponse(BaseModel):
    hits: list[SearchHit]


# ------------------------------------------------------------------- paging / misc


class Page(BaseModel):
    items: list[Any]
    next_cursor: str | None = None
    total: int


class DeleteRequest(BaseModel):
    id: str
    type: MemoryType


class UploadResponse(BaseModel):
    ids: list[str]


class Info(BaseModel):
    name: str
    fmp_version: str = FMP_VERSION
    description: str = ""
    memory_types: list[MemoryType]
    capabilities: dict[str, bool]
    """Endpoint name -> supported. `info` is always true."""


ALL_ENDPOINTS = [
    "info",
    "upload_files",
    "upload_transcript",
    "upload_inferences",
    "search",
    "read_transcripts",
    "read_inferences",
    "delete",
]
