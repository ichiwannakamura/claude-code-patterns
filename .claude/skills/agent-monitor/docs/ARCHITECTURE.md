# Agent Monitor — Architecture & Reference

Detailed architecture, state machine, JSON schema, UI design, and troubleshooting
for the Agent Monitor dashboard. For quick-start usage, see [../SKILL.md](../SKILL.md).

## Architecture Overview

```
Claude Code Hook Events
  |  SubagentStart / SubagentStop
  |  PreToolUse / PostToolUse
  |  TaskCompleted / Stop
  v
state-tracker.py  --->  state.json  (shared state file)
                           |
                           v
                    server.js (HTTP + SSE)
                           |
                           v
                    Chrome --app  (compact dashboard window)
```

## Components

| File | Role |
|------|------|
| `scripts/state-tracker.py` | Hook handler that writes agent state to `state.json` |
| `scripts/server.js` | Lightweight HTTP server with Server-Sent Events (SSE) for real-time updates |
| `assets/dashboard.html` | Single-file dashboard UI (HTML + CSS + JS) |
| `scripts/launch.py` | Auto-start script for SessionStart hook |

## Agent States

Each agent progresses through these states:

| State | Japanese | Icon | Meaning |
|-------|----------|------|---------|
| `waiting` | 指示待ち | ⏳ | Agent registered, awaiting first tool call |
| `planning` | 作業構想中 | 📋 | Agent is in plan/explore mode (Plan, Explore, EnterPlanMode tools) |
| `working` | 作業中 | ⚙️ | Agent is actively executing tools (Read, Write, Edit, Bash, etc.) |
| `permission_wait` | 承認待ち | ⏳ | Tool call stuck >7s, likely awaiting user permission input |
| `completed` | 完了 | ✅ | Agent has finished its task |
| `error` | エラー | ❌ | Agent encountered an error or was terminated |

## State Tracking Logic

The `state-tracker.py` script receives hook events via stdin (JSON) and updates `state.json`.

### Event to State Mapping

```
SubagentStart          -> Create agent entry with state "waiting"
PreToolUse (Task)      -> Mark parent as "planning" (spawning child)
PreToolUse (Plan/Explore/EnterPlanMode) -> Mark as "planning"
PreToolUse (other)     -> Mark as "working"
PostToolUse            -> Update last_tool and timestamp
SubagentStop           -> Mark as "completed"
TaskCompleted          -> Mark as "completed"
Stop                   -> Mark all active agents as "completed"
```

### permission_wait Detection

When a `PreToolUse` event sets an agent to `working` state, if no corresponding
`PostToolUse` arrives within 7 seconds, the display state transitions to
`permission_wait`. This indicates the tool is likely blocked waiting for user
approval in the Claude Code CLI. The underlying `state` field remains `working`
while `display_state` changes to `permission_wait`.

## state.json Format

```json
{
  "last_updated": "2026-02-26T05:30:00.000Z",
  "session_id": "abc-123",
  "agents": {
    "agent-id-1": {
      "id": "agent-id-1",
      "type": "Explore",
      "description": "Search for hooks config",
      "state": "working",
      "display_state": "working",
      "state_jp": "作業中",
      "icon": "⚙️",
      "started_at": "2026-02-26T05:28:00.000Z",
      "updated_at": "2026-02-26T05:30:00.000Z",
      "last_tool": "grep hooks config",
      "tool_count": 5,
      "parent_id": null
    }
  },
  "stats": {
    "total": 3,
    "waiting": 0,
    "planning": 0,
    "working": 1,
    "completed": 2,
    "error": 0
  }
}
```

### Field Reference

| Field | Type | Description |
|-------|------|-------------|
| `state` | string | Canonical state from hook events (`waiting`, `planning`, `working`, `completed`, `error`) |
| `display_state` | string | UI-facing state, may differ from `state` (e.g., `permission_wait` when tool is stuck >7s) |
| `last_tool` | string | Human-readable label of the current tool operation (e.g., `"grep hooks config"`, `"$ git status"`) |

## Dashboard UI Design

The dashboard is a single HTML file that connects to the SSE endpoint for live updates.

### Layout

```
+-------------------------------------+
|  Agent Monitor        * 3 agents    |  <- Header with live count
+-------------------------------------+
|  ⚙️ Explore          作業中  0:42  |  <- Active agents (highlighted)
|     + Grep: searching hooks...      |
|  ✅ Bash              完了    0:15  |  <- Completed agents (dimmed)
|  ⏳ general-purpose   指示待ち      |  <- Waiting agents
+-------------------------------------+
|  待:1  構:0  作:1  完:1            |  <- Summary bar
+-------------------------------------+
```

### Design Principles

- **Compact**: Default size 360x500px — fits alongside IDE without overlap
- **Dark theme**: Low distraction, easy on the eyes during long sessions
- **Color-coded states**: Each state has a distinct accent color
- **Auto-scroll**: New agents appear at top, completed ones fade down
- **Elapsed time**: Shows running duration for active agents
- **Minimal chrome**: No address bar, no tabs (Chrome --app mode)

### Color Scheme

| State | Background | Accent |
|-------|-----------|--------|
| waiting | `#1c2128` | `#e2b714` (amber) |
| planning | `#1c2128` | `#a78bfa` (purple) |
| working | `#1c2128` | `#34d399` (green) |
| permission_wait | `#1c2128` | `#fbbf24` (amber) |
| completed | `#1c2128` | `#636e72` (gray) |
| error | `#1c2128` | `#f87171` (red) |

## Auto-Start via SessionStart Hook

The `launch.py` script handles automatic startup:

1. On `SessionStart` event, check if server is already running (port check)
2. If not running, start `server.js` as a background process
3. Open Chrome in `--app` mode pointing to `http://localhost:3847`
4. Window size: 360x500, positioned at top-right of screen

### Chrome --app Mode

```bash
# Windows
start chrome --app="http://localhost:3847" --window-size=360,500 --window-position=1560,0

# macOS
open -na "Google Chrome" --args --app="http://localhost:3847" --window-size=360,500

# Linux
google-chrome --app="http://localhost:3847" --window-size=360,500
```

This creates a clean, dedicated window — no address bar, no tabs, no bookmarks bar.

## Server Implementation (server.js)

A minimal Node.js HTTP server (no dependencies) that:

1. Serves `dashboard.html` at `/`
2. Provides SSE endpoint at `/events` — pushes state changes in real-time
3. Serves current state at `/api/state` — for initial load
4. Watches `state.json` for changes using `fs.watch()`
5. Runs on port 3847 (configurable)

The server uses only Node.js built-ins (`http`, `fs`, `path`) — zero npm dependencies.

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| Dashboard doesn't open | Chrome not in PATH | Add Chrome to system PATH or set `CHROME_PATH` env var |
| No agents appear | state-tracker not receiving events | Check `.claude/hooks/logs/` for errors |
| SSE disconnects | Server crashed | Check if port 3847 is in use; restart server |
| Stale agents shown | Session ended without cleanup | Dashboard auto-clears on new SessionStart |
| Agent stuck in "working" | No PostToolUse received | May show as `permission_wait` after 7s; check if CLI is waiting for user input |
