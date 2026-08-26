# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

An MCP stdio server that gives a unified, FTS5-searchable view of past coding-agent transcripts across locally-installed ACP-compatible agents (Claude Code, Codex, Goose, ...). It auto-discovers agents from the ACP registry, polls each one in the background every 5 min, and exposes 6 MCP tools (`search_memory`, `list_agents`, `list_sessions`, `get_session`, `refresh`, `refresh_agents`) wired up via FastMCP in `server.py`.

## Commands

```bash
uv pip install -e .            # or pip install -e .
acp-memory                     # defaults to `serve` (MCP stdio entrypoint)
acp-memory doctor              # show config paths, registry fetch, detected agents, per-agent indexed status
acp-memory reindex             # rebuild FTS5 from `turns` table
acp-memory reindex --agent <id> # wipe one agent's sessions/turns; next poll repopulates
acp-memory -v serve            # debug logging
```

No tests, no CI. `ruff` config is present (line-length 110, py311) but ruff is not a project dependency — run via `uvx ruff check .` if needed.

## Architecture: two backends, one Index

The poller selects a backend **per agent**:

- **Filesystem backend** (`filesystem_backend/` package) — preferred whenever a parser exists. Each agent has its own module: `claude_code.py`, `codex.py`, `goose.py`, `cursor.py`, `cline.py` (handles Cline + Roo + Kilo by publisher dir), `zed.py`, `gemini_cli.py` (handles Gemini + Qwen), `continue_dev.py`, `aider.py`. The package `__init__.py` is the registry — `FILESYSTEM_AGENTS` declares each `(id, name, scanner, available)` plus aliases for IDs the same store has been seen registered under (e.g. `claude-acp` aliases `claude-code-acp`).
- **ACP backend** (`poller._poll_one`) — fallback for agents without a filesystem parser. Lazy-spawns the agent as an ACP subprocess via `acp.spawn_agent_process`, calls `session/list` + `session/load`, drains replayed `session/update` notifications via `CollectingClient` (a passive `acp.Client` whose other callbacks all `raise method_not_found`). Each tick spawns and terminates — subprocesses are not kept alive.

Backend resolution (`poller._backend_for`): `cfg.agent_overrides[id].backend` if set, else `"filesystem"` if `has_filesystem_backend(id)`, else `"acp"`. Both backends produce the same `IndexedTurn`/`SessionRecord` dataclasses that flow into `Index`.

### Filesystem-only agents

Some agents (Cursor, Cline-in-VS-Code, Zed, Continue, Aider) aren't in the ACP registry at all, but their on-disk stores are well-documented. `filesystem_backend.discover_filesystem_only_agents()` runs after registry detection and synthesizes an `AgentSpec` (with empty `launch_cmd`) for any registered scanner whose `available()` returns True and that wasn't already detected via the ACP registry. The poller routes them to the filesystem backend automatically because `has_filesystem_backend()` is True for their id — `launch_cmd` is never used. This is wired up in `detect.detect_agents()`, which is also why filesystem agents show up under "local detection" in `acp-memory doctor` with empty launch commands.

### Per-agent incremental signal

Each scanner picks the right watermark for its store shape and stashes it in `sessions.raw_meta_json`:

- **Per-file JSONL stores** (Claude Code, Codex, Gemini CLI, Continue): `source_mtime` of the session file. Skip if not advanced.
- **SQLite stores** (Goose, Cursor, Zed): a per-row updated_at field (`goose_last_msg_ts`, `cursor_last_updated_ms`, `zed_updated_at_ts`). The DB's overall mtime advances on every interaction, so global mtime gating doesn't help — we drive per-session diffs from inside the DB.
- **Per-repo Markdown** (Aider): file mtime + per-session chunking on `# aider chat started at` headers. Session id is `sha1(path|started_at)` so re-scans dedupe cleanly via the `(agent_id, session_id, turn_index)` UNIQUE.

`existing_watermark_field(idx, agent_id, session_id, key)` in `_common.py` is the helper for pulling these out of `raw_meta_json` on the next scan.

### Cursor: orphan composers

`composer.composerHeaders` (in `ItemTable`) only lists the *active* composer set — typically 10–20 entries — but `cursorDiskKV` holds historical `composerData:*` rows for hundreds of older conversations. The scanner unions both: headers give workspace/title for active composers; orphans are recovered straight from `composerData` and probed for `workspaceUris` on their first bubble if the composerData itself lacks a workspace identifier. Without this, a Cursor with ~400 composers will index only ~20.

### Zed: zstd payloads

`threads.db`'s `data` column is JSON when `data_type='json'`, Zstd-compressed JSON when `data_type='zstd'`. The `zstandard` package is a hard dependency for this reason. Sidebar metadata (titles, `main_worktree_paths`) lives in a separate `db/0-stable/db.sqlite` — `zed.scan` joins them on `thread_id`.

### Cline family

Cline, Roo Code, and Kilo Code all use the same Anthropic-format storage (`tasks/<id>/api_conversation_history.json`) under different publisher dirs. One parser in `cline.py` (`_scan_family`) handles all three; the entry-point functions just pass different publisher ids. The cwd isn't stored inside the task files — it lives in `<publisher>/state/taskHistory.json`, which the scanner loads once per publisher dir.

## Index write model

`index.py` runs **one writer task** that drains an asyncio queue (`Index._writer_loop`), so all writes are serialized through a single long-lived connection. Reads use **short-lived connections** (`_connect(self.path)` → use → close) to avoid lock contention with the writer. When you add a new write op, add a `_xxx_sync` helper, an async enqueue wrapper, and a branch in `_writer_loop`. Use `await idx.drain()` to wait for all enqueued writes to apply.

The FTS5 table `turns_fts` is a **regular** (not external-content) FTS table kept in sync by `turns_ai`/`turns_ad`/`turns_au` triggers. `Index._migrate` detects pre-existing `content='turns'` external-content FTS from older versions, drops it, recreates as regular FTS, and repopulates. Don't switch back to external-content — it broke because `turns` doesn't have a `tool_summary` column.

## ACP quirks worth knowing

- **`session/load` has no end signal.** The poller waits for `SESSION_LOAD_QUIET_SECONDS` (1.5s) of silence on the update queue, capped by `SESSION_LOAD_TIMEOUT_SECONDS` (60s).
- **stdio buffer.** Default `asyncio.StreamReader` limit is 64 KB; a single `session/update` replay line can easily exceed that. We pass `transport_kwargs={"limit": 16 * 1024 * 1024}` to `spawn_agent_process`.
- **cwd-filtered `session/list`.** Some ACP adapters silently filter sessions by the spawning cwd. `cwds.py` discovers known project roots per agent (e.g. by reading `~/.claude/projects/*/`); the poller then calls `list_sessions(cwd=...)` once per root and de-dupes by `session_id`. `config.toml` can override: `cwds = [...]` for explicit list, `cwds = []` for a single unscoped call.
- **`loadSession` is optional.** Agents that don't advertise the capability are marked `status=unsupported` and skipped.
- **Headless auth.** `CollectingClient.request_permission` always raises; the server can't drive interactive auth. Auth failures from `session/list` get mapped to `status=needs_auth`.

## Recursion guard

When the server spawns an agent, it sets `ACP_MEMORY_DISABLE_RECURSION=1` in the child env. If that env var is set when the server itself starts, the lifespan (`server._lifespan`) skips registry fetch + poller startup and runs in degraded "search-only" mode. This prevents fan-out when an agent we spawn happens to auto-load us back as an MCP server.

## Storage

- DB: `~/.local/share/acp-memory/db.sqlite` (or `$XDG_DATA_HOME/acp-memory`) — plain SQLite + FTS5, safe to `sqlite3` into for ad-hoc queries.
- Config: `~/.config/acp-memory/config.toml` — all keys optional. See README.md `## Configuration` for the schema (`[agents.<id>]` overrides: `enabled`, `launch_cmd`, `launch_args`, `launch_env`, `cwd`, `cwds`, `backend`).
- Registry cache: `~/.cache/acp-memory/registry.json` (TTL `registry_cache_ttl_seconds`, default 24h).

## Adding a new filesystem parser

1. Create `filesystem_backend/<agent>.py` exporting `scan(idx, agent_id) -> Iterator[ScanResult]` and `available() -> bool`. Use the helpers in `_common.py` (`iso_to_epoch`, `content_to_text`, `existing_mtime`, `existing_watermark_field`).
2. Pick the right watermark: file-mtime for per-session files, per-row `updated_at` for shared SQLite stores. Stash it in `raw_meta_json` and check it on the next scan.
3. Add a `FilesystemAgent(...)` entry to `FILESYSTEM_AGENTS` in `filesystem_backend/__init__.py`. If the agent is also in the ACP registry, use the registry id as the canonical id (so both detection paths converge); add the alternate name to `aliases`.
4. If the agent's ACP adapter is cwd-filtered, add a `_<agent>_cwds()` discoverer in `cwds.py` and register it in `_DISCOVERERS` — this only matters for the ACP path.

## Wiring this server into Claude Code (or any MCP client)

```json
{"mcpServers": {"acp-memory": {"command": "acp-memory", "args": ["serve"]}}}
```

The server is stdio-only; logs go to stderr. Set `ACP_MEMORY_LOG_LEVEL=DEBUG` for verbose output.
