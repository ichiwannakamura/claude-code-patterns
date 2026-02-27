# Claude Code Best Practices

Reference implementation demonstrating configuration patterns for [Claude Code](https://claude.ai/code): skills, agents, hooks, and commands.

## Key Components

| Component | Pattern | Description |
|---|---|---|
| **Weather System** | Command → Agent → Skills | Sequential workflow with preloaded skills |
| **Presentation** | Self-evolving agent | Agent that updates its own skills after each execution |
| **Agent Monitor** | Hook → State → SSE → Browser | Real-time dashboard for monitoring agent states |
| **Hooks (Sound)** | Cross-platform Python | Sound notification system for hook events |

## Architecture Patterns

### Command → Agent → Skills
```
/weather-orchestrator (command) → weather (agent) → weather-fetcher + weather-transformer (skills)
```

### Hook-Driven Monitoring
```
Claude Code Hooks → state-tracker.py → state.json → server.js (SSE) → dashboard.html
```

### Self-Evolving Agent
```
presentation-curator agent → edits slides → updates its own skill definitions
```

## Quick Start

This is a **reference implementation**, not an application. Clone and explore the `.claude/` directory to see the patterns in action.

```bash
# Explore skills
ls .claude/skills/

# Explore agents
ls .claude/agents/

# Explore hooks
ls .claude/hooks/

# Explore commands
ls .claude/commands/
```

## Documentation

- `CLAUDE.md` — Project instructions and custom AI guidance
- `reports/` — Technical analysis and pattern documentation
- `weather-orchestration/weather-orchestration-architecture.md` — Weather system flow diagram

## License

MIT
