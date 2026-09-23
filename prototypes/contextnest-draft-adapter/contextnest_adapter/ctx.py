"""A thin client for the `ctx` CLI, the Context Nest reference implementation.

Everything that makes a nest a nest (selector evaluation, published-only serving, version
history, hash chains, checkpoints, access tracing) happens inside `ctx`. This module only
builds argv, runs the binary, and parses its JSON.

The same client talks to a local nest directory or a hosted one: `vault` is either a path
(runs `ctx` with that directory as cwd) or an alias registered with
`ctx vault add <alias> --url <nest mcp url> --bearer-env CONTEXTNEST_API_KEY`.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class CtxError(RuntimeError):
    """`ctx` exited non-zero or returned something that is not the expected JSON."""


@dataclass(frozen=True)
class NestDocument:
    id: str
    title: str
    body: str

    @property
    def uri(self) -> str:
        return f"contextnest://{self.id}"


@dataclass(frozen=True)
class QueryResult:
    selector: str
    documents: list[NestDocument]
    hops: int
    raw: dict[str, Any] = field(repr=False, default_factory=dict)

    @property
    def ids(self) -> list[str]:
        return [d.id for d in self.documents]


class CtxClient:
    def __init__(
        self,
        vault: str | os.PathLike[str] | None = None,
        *,
        ctx_bin: str | None = None,
        timeout: float = 120.0,
        env: dict[str, str] | None = None,
    ) -> None:
        self.ctx_bin = ctx_bin or os.environ.get("CTX_BIN") or "ctx"
        if shutil.which(self.ctx_bin) is None:
            raise CtxError(
                f"`{self.ctx_bin}` not found on PATH. Install the reference implementation: "
                "npm install -g @promptowl/contextnest-cli"
            )
        self.timeout = timeout
        self.env = {**os.environ, **(env or {})}
        self.cwd: Path | None = None
        self.alias: str | None = None
        if vault is not None:
            p = Path(vault)
            if p.is_dir():
                self.cwd = p.resolve()
                # pin the vault so ctx never falls back to a registry default
                self.env["CONTEXTNEST_VAULT_PATH"] = str(self.cwd)
            else:
                self.alias = str(vault)

    @property
    def location(self) -> str:
        return str(self.cwd) if self.cwd else f"alias:{self.alias}" if self.alias else "default"

    # ------------------------------------------------------------------ plumbing
    def run(self, *args: str) -> str:
        argv = [self.ctx_bin]
        if self.alias:
            argv += ["--vault", self.alias]
        argv += list(args)
        proc = subprocess.run(
            argv,
            cwd=self.cwd,
            env=self.env,
            capture_output=True,
            text=True,
            timeout=self.timeout,
        )
        if proc.returncode != 0:
            msg = (proc.stderr or proc.stdout).strip()
            raise CtxError(f"{' '.join(argv[1:])}: {msg}")
        return proc.stdout

    def run_json(self, *args: str) -> Any:
        out = self.run(*args)
        try:
            return json.loads(out)
        except json.JSONDecodeError as e:
            raise CtxError(f"expected JSON from `ctx {' '.join(args)}`, got: {out[:200]!r}") from e

    # ------------------------------------------------------------------ reads
    def query(self, selector: str, *, hops: int = 0) -> QueryResult:
        """Resolve a selector (CN §2) to the published documents it names.

        hops=0 asks for exactly the selector's matches (ctx full mode). hops>0 also walks
        links out from them (graph mode, CN §5.1.1).
        """
        mode = ["--full"] if hops == 0 else ["--hops", str(hops)]
        data = self.run_json("query", selector, "--json", *mode)
        docs = [
            NestDocument(id=d["id"], title=d.get("title", d["id"]), body=d.get("body", ""))
            for d in data.get("documents", [])
        ]
        return QueryResult(selector=selector, documents=docs, hops=hops, raw=data)

    def read(self, node_id: str) -> NestDocument | None:
        """One published document by id; None if it does not resolve."""
        node_id = node_id.removeprefix("contextnest://")
        res = self.query(node_id, hops=0)
        return next((d for d in res.documents if d.id == node_id), None)

    def search(self, text: str, *, limit: int = 10) -> list[dict[str, Any]]:
        """Full-text search. Scores are ranking hints within this nest only."""
        data = self.run_json("search", text, "--json", "--limit", str(limit))
        return data if isinstance(data, list) else data.get("results", [])

    def latest_checkpoint(self) -> dict[str, Any] | None:
        """The nest's current checkpoint (CN §7), or None where ctx cannot report it."""
        try:
            data = self.run_json("checkpoint", "list", "--json", "-n", "1")
        except CtxError:
            return None  # e.g. hosted nests: checkpoint listing is local-only in ctx today
        return data[-1] if isinstance(data, list) and data else None

    # ------------------------------------------------------------------ writes
    def propose(self, node_id: str, *, title: str, body: str, tags: list[str]) -> str:
        """Write a new memory as a draft awaiting review. It is not served until published."""
        self.run(
            "add", node_id, "--title", title, "--body", body, "--tags", ",".join(tags)
        )
        self.run("update", node_id, "--status", "pending_review")
        return node_id
