# acp-memory-server

An MCP server that gives a single, searchable view of your past coding-agent
transcripts across every locally-installed ACP-compatible agent (Claude Code,
Codex, Goose, …).

**How it works.** On startup, the server fetches the
[ACP registry](https://cdn.agentclientprotocol.com/registry/v1/latest/registry.json),
detects which registered agents are launchable on this machine (binary on
`PATH`, or `npx`/`uvx` available), and starts a background poller. Every
5 minutes it pulls each agent's session history into a local SQLite + FTS5
database. MCP tools query that index.

Two backends ship today:

- **Filesystem (default for Claude Code & Codex CLI).** Reads the agent's
  on-disk session store directly: `~/.claude/projects/*/*.jsonl` and
  `~/.codex/sessions/<year>/<month>/<day>/*.jsonl`. Captures 100% of local
  history, fast, no subprocess churn. Incremental scans are mtime-gated.
- **ACP (default for everything else).** Lazy-spawns each agent as an ACP
  subprocess, calls `session/list` + `session/load`, drains the replayed
  `session/update` notifications. For agents whose ACP adapter filters
  `session/list` by spawning cwd (e.g. Claude Code's adapter would, if used),
  cwd discovery iterates known project roots.

You can override the backend per agent in `config.toml` — see
[Configuration](#configuration) below. The filesystem backend is the reason
indexed coverage is ~16× higher than ACP-only would deliver: most agent ACP
adapters expose only a small recent slice of `session/list`, while the
filesystem store is complete.

## Install

```bash
git clone <this-repo>
cd acp-memory-server
uv pip install -e .          # or: pip install -e .
```

## First run

```bash
acp-memory doctor
```

That prints the database path, the registry fetch result, the agents detected
locally, and per-agent indexed status. Expect:

- `claude-code-acp` (or `claude-acp`) — `ok` once Claude Code is logged in.
- `codex-acp` — `ok` or `unsupported`, depending on installed Codex version.
- `goose` — currently `unsupported` on most builds (waiting on `session/load`).

If an agent shows `needs_auth`, run that agent's normal login flow (e.g.
`claude login`) and call the `refresh` MCP tool or wait for the next poll.

## Wire into Claude Code

Add to `~/.claude.json`:

```json
{
  "mcpServers": {
    "acp-memory": {
      "command": "acp-memory",
      "args": ["serve"]
    }
  }
}
```

Restart Claude Code. Then ask it: *"search my past sessions for 'database
migration'"* — it will call `search_memory` and return hits across every
agent it indexed.

## MCP tools

| Tool | Purpose |
| --- | --- |
| `search_memory(query, agent?, since?, limit?)` | FTS5 search across all indexed turns. `since` accepts `7d`, `24h`, `30m`, or ISO-8601. |
| `list_agents()` | Detected agents and per-agent status. |
| `list_sessions(agent?, limit?)` | Recent sessions, sorted by latest turn time. |
| `get_session(agent, session_id, offset?, limit?, only_human?, roles?)` | Paginated transcript. `only_human=true` keeps just user turns; `roles=["user","agent"]` for human + assistant only. Returns `total` and `has_more` for paging. |
| `refresh(agent?)` | Force a poll cycle now. |
| `refresh_agents()` | Re-run discovery (registry + PATH). |

## Configuration

`~/.config/acp-memory/config.toml` (all keys optional):

```toml
poll_interval_seconds = 300
auto_discover = true
registry_url = "https://cdn.agentclientprotocol.com/registry/v1/latest/registry.json"

# Define a custom agent the registry doesn't know about
[agents.my-custom-agent]
enabled = true
launch_cmd = "/usr/local/bin/my-acp-agent"
launch_args = ["--mode", "acp"]
launch_env = { FOO = "bar" }

# Force ACP polling instead of the default filesystem reader
[agents.claude-acp]
backend = "acp"

# Disable a registry agent without uninstalling it
[agents.codex-acp]
enabled = false

# ACP-only agent that needs cwd hints (override auto-discovery)
[agents.gemini]
cwds = ["/Users/me/code/foo", "/Users/me/code/bar"]
```

### Backend selection

Per-agent `backend` values:

- `"filesystem"` — read the agent's local session store (only for agents that
  have a parser: `claude-acp`, `claude-code-acp`, `codex-acp`).
- `"acp"` — lazy-spawn the agent as an ACP subprocess and use `session/list` +
  `session/load`.
- omitted — auto: filesystem if a parser exists, else ACP.

## Storage

- Database: `~/.local/share/acp-memory/db.sqlite` (or `$XDG_DATA_HOME/acp-memory`)
- Registry cache: `~/.cache/acp-memory/registry.json`
- Config: `~/.config/acp-memory/config.toml`

The database is plain SQLite with FTS5; you can `sqlite3` into it directly to
debug or run ad-hoc queries.

## Known caveats

- ACP `session/load` is **optional** in the protocol spec. Agents that don't
  advertise the `loadSession` capability are flagged `unsupported` and
  skipped. Codex and Goose are partial today; their indexed coverage will
  grow as upstream support matures.
- Some agents only expose process-local sessions over ACP (i.e. not the user's
  CLI history). For those, `session/list` may return little or nothing —
  `acp-memory doctor` will surface the empty result.
- The poller is headless: it cannot drive interactive auth flows. Agents that
  require `claude login` / equivalent must be authenticated manually first.

## Recursion guard

When the server spawns an agent, it sets `ACP_MEMORY_DISABLE_RECURSION=1` in
the agent's environment. If that variable is set when the server itself
starts, the server runs in a degraded "no-poll" mode (still serves search
queries from the existing index) so a chain of nested ACP launches never
fans out.
