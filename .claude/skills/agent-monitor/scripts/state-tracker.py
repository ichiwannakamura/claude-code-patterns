#!/usr/bin/env python3
"""
Agent Monitor — State Tracker
Receives Claude Code hook events via stdin and updates state.json.

This script is called by multiple hook events (SubagentStart, SubagentStop,
PreToolUse, PostToolUse, TaskCompleted, Stop, SessionStart). It reads the
event JSON from stdin, determines what state change is needed, and atomically
updates the shared state file.
"""

import json
import sys
import os
import time
from datetime import datetime, timezone
from pathlib import Path

# State file location — sibling to the scripts directory
STATE_DIR = Path(__file__).parent.parent / "state"
STATE_FILE = STATE_DIR / "state.json"

# Tool names that indicate "planning" state
PLANNING_TOOLS = {"Plan", "Explore", "EnterPlanMode", "ExitPlanMode", "AskUserQuestion"}

# Tool names that indicate "working" state (active file/code operations)
WORKING_TOOLS = {
    "Read", "Write", "Edit", "Bash", "Grep", "Glob", "NotebookEdit",
    "WebFetch", "WebSearch", "Task"
}

PERMISSION_WAIT_THRESHOLD_S = 7  # Ported from Pixel Agents' PERMISSION_TIMER_DELAY_MS

# Unified state metadata (replaces get_state_icon / get_state_jp)
AGENT_STATE_META = {
    "waiting":    {"icon": "\u23f3",      "jp": "指示待ち"},      # ⏳
    "planning":   {"icon": "\U0001f4cb",  "jp": "作業構想中"},    # 📋
    "working":    {"icon": "\u2699\ufe0f","jp": "作業中"},        # ⚙️
    "completed":  {"icon": "\u2705",      "jp": "完了"},          # ✅
    "error":      {"icon": "\u274c",      "jp": "エラー"},        # ❌
    "permission_wait": {"icon": "\u23f3", "jp": "承認待ち"},      # ⏳
}
_DEFAULT_META = {"icon": "\u2753", "jp": "不明"}  # ❓


def format_tool_label(tool_name: str, tool_input: dict) -> str:
    """Format tool name + input into a human-readable label (ported from Pixel Agents)."""
    if tool_name == "Bash":
        cmd = tool_input.get("command", "").replace("\n", " ").strip()[:40]
        return f"$ {cmd}" if cmd else "Bash"
    if tool_name in ("Read", "Write", "Edit"):
        fp = tool_input.get("file_path") or tool_input.get("path", "")
        return f"{tool_name}: {Path(fp).name}" if fp else tool_name
    if tool_name == "Grep":
        pat = tool_input.get("pattern", "")[:30]
        return f"grep {pat}" if pat else "Grep"
    if tool_name == "Task":
        desc = tool_input.get("description", "")[:35]
        return f"Task: {desc}" if desc else "Task"
    return tool_name


def load_state() -> dict:
    """Load current state from file, or return empty state."""
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "session_id": None,
        "agents": {},
        "stats": {
            "total": 0, "waiting": 0, "planning": 0,
            "working": 0, "completed": 0, "error": 0
        }
    }


def save_state(state: dict) -> None:
    """Atomically save state to file."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    state["last_updated"] = datetime.now(timezone.utc).isoformat()
    # Recompute stats
    agents = state.get("agents", {})
    stats = {"total": 0, "waiting": 0, "planning": 0, "working": 0, "completed": 0, "error": 0}
    for agent in agents.values():
        s = agent.get("state", "waiting")
        stats["total"] += 1
        if s in stats:
            stats[s] += 1
    state["stats"] = stats

    # Compute display_state for each agent (permission-wait detection)
    now = datetime.now(timezone.utc)
    for agent in agents.values():
        s = agent.get("state", "waiting")
        updated = agent.get("updated_at", "")
        if s == "working" and updated:
            try:
                dt = datetime.fromisoformat(updated)
                if (now - dt).total_seconds() > PERMISSION_WAIT_THRESHOLD_S:
                    agent["display_state"] = "permission_wait"
                    meta = AGENT_STATE_META["permission_wait"]
                    agent["state_jp"] = meta["jp"]
                    agent["icon"] = meta["icon"]
                    continue
            except (ValueError, TypeError):
                pass
        agent["display_state"] = s

    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(STATE_FILE)


def update_agent_state(state: dict, agent_id: str, new_state: str, **extra) -> None:
    """Update an agent's state and metadata."""
    if agent_id not in state["agents"]:
        state["agents"][agent_id] = {
            "id": agent_id,
            "type": extra.get("agent_type", "unknown"),
            "description": extra.get("description", ""),
            "state": new_state,
            "state_jp": AGENT_STATE_META.get(new_state, _DEFAULT_META)["jp"],
            "icon": AGENT_STATE_META.get(new_state, _DEFAULT_META)["icon"],
            "started_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "last_tool": None,
            "tool_count": 0,
            "parent_id": extra.get("parent_id"),
        }
    else:
        agent = state["agents"][agent_id]
        agent["state"] = new_state
        agent["state_jp"] = AGENT_STATE_META.get(new_state, _DEFAULT_META)["jp"]
        agent["icon"] = AGENT_STATE_META.get(new_state, _DEFAULT_META)["icon"]
        agent["updated_at"] = datetime.now(timezone.utc).isoformat()
        if "last_tool" in extra:
            agent["last_tool"] = extra["last_tool"]
            agent["tool_count"] = agent.get("tool_count", 0) + 1
        if "description" in extra and extra["description"]:
            agent["description"] = extra["description"]


def handle_event(event: dict) -> None:
    """Process a hook event and update state accordingly."""
    hook_name = event.get("hook_event_name", "")
    session_id = event.get("session_id", "")

    state = load_state()

    # New session — clear old agents
    if hook_name == "SessionStart":
        state["agents"] = {}
        state["session_id"] = session_id
        save_state(state)
        return

    state["session_id"] = session_id or state.get("session_id")

    if hook_name == "SubagentStart":
        agent_id = event.get("agent_id", f"agent-{int(time.time())}")
        agent_type = event.get("agent_type", "unknown")
        update_agent_state(state, agent_id, "waiting", agent_type=agent_type)

    elif hook_name == "SubagentStop":
        agent_id = event.get("agent_id", "")
        if agent_id and agent_id in state["agents"]:
            update_agent_state(state, agent_id, "completed")

    elif hook_name == "TaskCompleted":
        # Mark the most recent non-completed agent as completed
        for aid in reversed(list(state["agents"].keys())):
            if state["agents"][aid]["state"] not in ("completed", "error"):
                update_agent_state(state, aid, "completed")
                break

    elif hook_name in ("PreToolUse", "PostToolUse"):
        tool_name = event.get("tool_name", "")
        tool_input = event.get("tool_input", {})

        # Find the most recent active agent to attribute this tool use to
        active_agent = None
        for aid in reversed(list(state["agents"].keys())):
            if state["agents"][aid]["state"] not in ("completed", "error"):
                active_agent = aid
                break

        if active_agent:
            if hook_name == "PreToolUse":
                if tool_name in PLANNING_TOOLS:
                    new_state = "planning"
                elif tool_name in WORKING_TOOLS or tool_name:
                    new_state = "working"
                else:
                    new_state = state["agents"][active_agent]["state"]
                update_agent_state(state, active_agent, new_state, last_tool=format_tool_label(tool_name, tool_input))
            else:
                # PostToolUse — just update the timestamp and tool count
                update_agent_state(
                    state, active_agent,
                    state["agents"][active_agent]["state"],
                    last_tool=format_tool_label(tool_name, tool_input)
                )

        # If tool is Task (spawning a new subagent), also track the parent context
        if hook_name == "PreToolUse" and tool_name == "Task":
            desc = tool_input.get("description", "")
            sub_type = tool_input.get("subagent_type", "general-purpose")
            # The SubagentStart event will create the actual agent entry

    elif hook_name == "Stop":
        # Session ending — mark all active agents as completed
        for aid in list(state["agents"].keys()):
            if state["agents"][aid]["state"] not in ("completed", "error"):
                update_agent_state(state, aid, "completed")

    save_state(state)


def main():
    """Entry point — read event JSON from stdin and process it."""
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            return
        event = json.loads(raw)
        handle_event(event)
    except json.JSONDecodeError:
        # Silently ignore malformed input — hooks must not crash
        pass
    except Exception:
        # Hooks must never crash — swallow all errors
        pass


if __name__ == "__main__":
    main()
