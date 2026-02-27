---
name: agent-monitor
description: >
  Real-time dashboard that visualizes the status of all running AI agents, subagents, MCP servers,
  and hook processes. Auto-starts as a compact always-on-top browser window when Claude Code launches.
  Use this skill PROACTIVELY whenever subagents are spawned via Task tool, when the user wants to
  monitor agent activity, or when multiple parallel agents are running. Also use when the user mentions
  "dashboard", "monitor", "agent status", "progress tracking", or asks "what's running right now?"
user-invocable: true
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Task, WebFetch
---

# Agent Monitor — Real-Time Agent Status Dashboard

A lightweight, always-resident dashboard showing live status of every AI agent, MCP server call,
and hook process. Compact browser window (360x500px) that stays out of your way.

## Quick Start

### 1. Register hooks in .claude/settings.json

Add the state-tracker hook to each event listed below. Each entry follows this template
(add alongside existing hooks, do not replace them):

```json
{
  "type": "command",
  "command": "python3 \"${CLAUDE_PROJECT_DIR}/.claude/skills/agent-monitor/scripts/state-tracker.py\"",
  "timeout": 3000
}
```

**Events requiring the state-tracker hook:**
`SubagentStart`, `SubagentStop`, `PreToolUse`, `PostToolUse`, `TaskCompleted`, `Stop`

**SessionStart** uses the launch script instead (timeout 10000):

```json
{
  "type": "command",
  "command": "python3 \"${CLAUDE_PROJECT_DIR}/.claude/skills/agent-monitor/scripts/launch.py\"",
  "timeout": 10000
}
```

### 2. Manual server start (for testing)

```bash
node ".claude/skills/agent-monitor/scripts/server.js"
```

Then open `http://localhost:3847` in a browser.

### 3. Verify

Spawn a subagent -- its status should appear in the dashboard within 1 second.

## Agent States

| State | Display | Meaning |
|-------|---------|---------|
| waiting | ⏳ 指示待ち | Awaiting first tool call |
| planning | 📋 作業構想中 | Plan/Explore mode |
| working | ⚙️ 作業中 | Executing tools |
| permission_wait | ⏳ 承認待ち | Tool stuck >7s (needs user input) |
| completed | ✅ 完了 | Task finished |
| error | ❌ エラー | Error or terminated |

## Key Files

| File | Role |
|------|------|
| `scripts/state-tracker.py` | Hook handler -> state.json |
| `scripts/server.js` | HTTP + SSE server (port 3847) |
| `assets/dashboard.html` | Single-file dashboard UI |
| `scripts/launch.py` | Auto-start on SessionStart |

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed architecture, state machine,
JSON schema, UI design, color scheme, and troubleshooting.
