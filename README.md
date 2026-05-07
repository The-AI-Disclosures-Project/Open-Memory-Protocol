# acp-memory-server

An MCP server that gives a single, searchable view of your past coding-agent
transcripts across every locally-installed ACP-compatible agent (Claude Code,
Codex, Goose, …).

**How it works.** On startup, the server fetches the
[ACP registry](https://cdn.agentclientprotocol.com/registry/v1/latest/registry.json),
detects which registered agents are launchable on this machine (binary on
`PATH`, or `npx`/`uvx` available), and starts a background poller. Every
5 minutes it lazy-spawns each agent over ACP, calls `session/list` +
`session/load`, drains the replayed `session/update` notifications, and
indexes the turns into a local SQLite + FTS5 database. MCP tools query that
index.

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
| `get_session(agent, session_id, max_turns?)` | Full transcript for one session. |
| `refresh(agent?)` | Force a poll cycle now. |
| `refresh_agents()` | Re-run discovery (registry + PATH). |

## Configuration

`~/.config/acp-memory/config.toml` (all keys optional):

```toml
poll_interval_seconds = 300
auto_discover = true
registry_url = "https://cdn.agentclientprotocol.com/registry/v1/latest/registry.json"

[agents.my-custom-agent]
enabled = true
launch_cmd = "/usr/local/bin/my-acp-agent"
launch_args = ["--mode", "acp"]
launch_env = { FOO = "bar" }

[agents.codex-acp]
enabled = false   # disable a registry agent without uninstalling it
```

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
