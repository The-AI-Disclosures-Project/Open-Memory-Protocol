"""FMP client side: one server (`FMPClient`) and many servers as one view (`FederatedMemory`).

Routing policy is per server and lives in `ServerConfig`, answering the draft's open
questions in the simplest way:
- search fans out to every server and merges by score;
- transcripts go to every server with `send_transcripts=True`;
- inferences go to the server the agent names, else every server with `accept_inferences=True`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import httpx

from fmp.schema import (
    FileUpload,
    InferenceRecord,
    InferenceUpload,
    Info,
    MemoryType,
    SearchHit,
    SearchRequest,
    TranscriptRecord,
    TranscriptUpload,
)


class FMPError(RuntimeError):
    pass


class FMPClient:
    def __init__(
        self,
        url: str,
        *,
        name: str | None = None,
        http: httpx.Client | None = None,
        timeout: float = 30.0,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.url = url.rstrip("/")
        self.name = name or self.url
        self._http = http or httpx.Client(timeout=timeout, headers=headers or {})
        self._owned = http is None
        self._info: Info | None = None

    def _req(self, method: str, path: str, **kw: Any) -> Any:
        r = self._http.request(method, f"{self.url}{path}", **kw)
        if r.status_code == 501:
            raise FMPError(f"{self.name}: {path} not supported")
        if r.status_code >= 400:
            raise FMPError(f"{self.name}: {method} {path} -> {r.status_code} {r.text[:200]}")
        return r.json()

    def info(self, refresh: bool = False) -> Info:
        if self._info is None or refresh:
            self._info = Info.model_validate(self._req("GET", "/fmp/info"))
        return self._info

    def supports(self, endpoint: str) -> bool:
        return self.info().capabilities.get(endpoint, False)

    def search(self, req: SearchRequest) -> list[SearchHit]:
        data = self._req("POST", "/fmp/search", json=req.model_dump(mode="json"))
        hits = [SearchHit.model_validate(h) for h in data["hits"]]
        for h in hits:
            h.server = self.name
        return hits

    def upload_files(self, files: list[FileUpload]) -> list[str]:
        return self._req("POST", "/fmp/upload/files", json=[f.model_dump() for f in files])["ids"]

    def upload_transcript(self, t: TranscriptUpload) -> str:
        return self._req("POST", "/fmp/upload/transcript", json=t.model_dump(mode="json"))["ids"][0]

    def upload_inferences(self, items: list[InferenceUpload]) -> list[str]:
        return self._req(
            "POST", "/fmp/upload/inferences", json=[i.model_dump(mode="json") for i in items]
        )["ids"]

    def read_transcripts(
        self, cursor: str | None = None, limit: int = 20, include_messages: bool = False
    ) -> tuple[list[TranscriptRecord], str | None, int]:
        data = self._req(
            "GET",
            "/fmp/read_transcripts",
            params={
                "cursor": int(cursor or 0),
                "limit": limit,
                "include_messages": include_messages,
            },
        )
        return (
            [TranscriptRecord.model_validate(i) for i in data["items"]],
            data["next_cursor"],
            data["total"],
        )

    def read_inferences(
        self, cursor: str | None = None, limit: int = 20
    ) -> tuple[list[InferenceRecord], str | None, int]:
        data = self._req(
            "GET", "/fmp/read_inferences", params={"cursor": int(cursor or 0), "limit": limit}
        )
        return (
            [InferenceRecord.model_validate(i) for i in data["items"]],
            data["next_cursor"],
            data["total"],
        )

    def delete(self, type_: MemoryType, id_: str) -> None:
        self._req("POST", "/fmp/delete", json={"type": type_.value, "id": id_})

    def close(self) -> None:
        if self._owned:
            self._http.close()


@dataclass
class ServerConfig:
    name: str
    url: str
    send_transcripts: bool = True
    accept_inferences: bool = True
    headers: dict[str, str] = field(default_factory=dict)
    http: httpx.Client | None = None  # for tests: a starlette TestClient is an httpx.Client

    def connect(self) -> FMPClient:
        return FMPClient(self.url, name=self.name, http=self.http, headers=self.headers)


class FederatedMemory:
    """Many FMP servers, one view. This is the "one plugin, many servers" object."""

    def __init__(self, servers: list[ServerConfig]) -> None:
        self.configs = {s.name: s for s in servers}
        self.clients = {s.name: s.connect() for s in servers}
        self.last_errors: list[str] = []

    def _supports(self, name: str, endpoint: str) -> bool:
        try:
            return self.clients[name].supports(endpoint)
        except (FMPError, httpx.HTTPError) as e:
            self.last_errors.append(f"{name}: {e}")
            return False

    # --- read
    def search(
        self,
        query: str,
        *,
        types: list[MemoryType] | None = None,
        limit: int = 10,
        since: str | None = None,
        servers: list[str] | None = None,
    ) -> list[SearchHit]:
        req = SearchRequest(query=query, types=types, limit=limit, since=since)
        hits: list[SearchHit] = []
        self.last_errors = []
        for name, client in self.clients.items():
            if servers and name not in servers:
                continue
            if not self._supports(name, "search"):
                continue
            try:
                hits.extend(client.search(req))
            except (FMPError, httpx.HTTPError) as e:
                self.last_errors.append(str(e))
        hits.sort(key=lambda h: h.score, reverse=True)
        return hits[:limit]

    # --- write
    def upload_transcript(self, t: TranscriptUpload) -> dict[str, str]:
        out = {}
        self.last_errors = []
        for name, client in self.clients.items():
            if self.configs[name].send_transcripts and self._supports(name, "upload_transcript"):
                out[name] = client.upload_transcript(t)
        return out

    def remember(self, inf: InferenceUpload, *, server: str | None = None) -> dict[str, str]:
        out = {}
        targets = (
            [server] if server else [n for n, c in self.configs.items() if c.accept_inferences]
        )
        for name in targets:
            client = self.clients.get(name)
            if client is None:
                raise FMPError(f"unknown memory server {name!r}")
            if not self._supports(name, "upload_inferences"):
                if server:
                    raise FMPError(f"{name} does not accept inferences")
                continue
            out[name] = client.upload_inferences([inf])[0]
        return out

    def describe(self) -> str:
        lines = []
        for name, client in self.clients.items():
            try:
                info = client.info()
            except (FMPError, httpx.HTTPError) as e:
                lines.append(f"- {name}: unreachable ({e})")
                continue
            cfg = self.configs[name]
            caps = ", ".join(k for k, v in info.capabilities.items() if v and k != "info")
            lines.append(
                f"- {name}: {info.description or info.name} · types="
                f"{'/'.join(t.value for t in info.memory_types)} · "
                f"transcripts {'sent' if cfg.send_transcripts and info.capabilities.get('upload_transcript') else 'NOT sent'} · "
                f"inferences {'accepted' if cfg.accept_inferences and info.capabilities.get('upload_inferences') else 'NOT accepted'} · "
                f"endpoints: {caps}"
            )
        return "\n".join(lines)

    def close(self) -> None:
        for c in self.clients.values():
            c.close()
