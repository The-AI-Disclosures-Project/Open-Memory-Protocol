"""FastAPI reference server for the FMP endpoints (AIDP draft v0.1 §Possible Endpoints).

Every endpoint except /fmp/info may be disabled, either explicitly (`disabled=`) or because
the backend does not implement it. Disabled endpoints return 501 and are reported as
`false` in /fmp/info capabilities, which the draft says keeps the server compliant.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Query

from fmp.schema import (
    ALL_ENDPOINTS,
    DeleteRequest,
    FileUpload,
    InferenceUpload,
    Info,
    Page,
    SearchRequest,
    SearchResponse,
    TranscriptUpload,
    UploadResponse,
)
from fmp.store import Store


def _supported(store: Store, endpoint: str, disabled: set[str]) -> bool:
    if endpoint == "info":
        return True
    if endpoint in disabled or endpoint in getattr(store, "unsupported", frozenset()):
        return False
    return hasattr(store, endpoint)


def create_app(
    store: Store,
    *,
    name: str,
    description: str = "",
    disabled: set[str] | None = None,
) -> FastAPI:
    disabled = set(disabled or ())
    caps = {ep: _supported(store, ep, disabled) for ep in ALL_ENDPOINTS}
    app = FastAPI(title=f"FMP server: {name}", version="0.1")
    app.state.store = store
    app.state.info = Info(
        name=name, description=description, memory_types=list(store.memory_types), capabilities=caps
    )

    def require(ep: str) -> None:
        if not caps[ep]:
            raise HTTPException(501, f"{ep} is not supported by this memory server")

    @app.get("/fmp/info", response_model=Info)
    def info() -> Info:
        return app.state.info

    @app.post("/fmp/upload/files", response_model=UploadResponse)
    def upload_files(files: list[FileUpload]) -> UploadResponse:
        require("upload_files")
        return UploadResponse(ids=store.upload_files(files))

    @app.post("/fmp/upload/transcript", response_model=UploadResponse)
    def upload_transcript(t: TranscriptUpload) -> UploadResponse:
        require("upload_transcript")
        return UploadResponse(ids=[store.upload_transcript(t)])

    @app.post("/fmp/upload/inferences", response_model=UploadResponse)
    def upload_inferences(items: list[InferenceUpload]) -> UploadResponse:
        require("upload_inferences")
        return UploadResponse(ids=store.upload_inferences(items))

    @app.post("/fmp/search", response_model=SearchResponse)
    def search(req: SearchRequest) -> SearchResponse:
        require("search")
        return SearchResponse(hits=store.search(req))

    @app.get("/fmp/read_transcripts", response_model=Page)
    def read_transcripts(
        cursor: int = Query(0, ge=0),
        limit: int = Query(20, ge=1, le=200),
        include_messages: bool = False,
    ) -> Page:
        require("read_transcripts")
        items, total = store.read_transcripts(cursor, limit, include_messages)
        nxt = cursor + limit
        return Page(
            items=[i.model_dump() for i in items],
            total=total,
            next_cursor=str(nxt) if nxt < total else None,
        )

    @app.get("/fmp/read_inferences", response_model=Page)
    def read_inferences(cursor: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=200)) -> Page:
        require("read_inferences")
        items, total = store.read_inferences(cursor, limit)
        nxt = cursor + limit
        return Page(
            items=[i.model_dump() for i in items],
            total=total,
            next_cursor=str(nxt) if nxt < total else None,
        )

    @app.post("/fmp/delete")
    def delete(req: DeleteRequest) -> dict[str, Any]:
        require("delete")
        ok = store.delete(req.type, req.id)
        if not ok:
            raise HTTPException(404, f"no {req.type.value} with id {req.id}")
        return {"deleted": req.id}

    return app
