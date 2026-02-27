/**
 * Agent Monitor — Lightweight HTTP Server with SSE
 *
 * Zero-dependency Node.js server that:
 * 1. Serves the dashboard HTML at /
 * 2. Provides Server-Sent Events at /events for real-time updates
 * 3. Serves current state at /api/state
 * 4. Watches state.json for changes and pushes updates via SSE
 *
 * Usage: node server.js [--port 3847]
 */

const http = require("http");
const fs = require("fs");
const path = require("path");

const PORT = parseInt(process.argv.find((_, i, a) => a[i - 1] === "--port") || "3847", 10);
const SKILL_DIR = path.resolve(__dirname, "..");
const STATE_FILE = path.join(SKILL_DIR, "state", "state.json");
const DASHBOARD_FILE = path.join(SKILL_DIR, "assets", "dashboard.html");

// Track SSE clients
const clients = new Set();

// Read state file safely
function readState() {
  try {
    if (fs.existsSync(STATE_FILE)) {
      return JSON.parse(fs.readFileSync(STATE_FILE, "utf-8"));
    }
  } catch (e) {
    // Ignore parse errors during atomic writes
  }
  return {
    last_updated: new Date().toISOString(),
    session_id: null,
    agents: {},
    stats: { total: 0, waiting: 0, planning: 0, working: 0, completed: 0, error: 0 },
  };
}

// Broadcast state to all SSE clients
function broadcast() {
  const state = readState();
  const data = `data: ${JSON.stringify(state)}\n\n`;
  for (const res of clients) {
    try {
      res.write(data);
    } catch {
      clients.delete(res);
    }
  }
}

// Watch state file for changes
const stateDir = path.dirname(STATE_FILE);
if (!fs.existsSync(stateDir)) {
  fs.mkdirSync(stateDir, { recursive: true });
}

let debounceTimer = null;
try {
  fs.watch(stateDir, (eventType, filename) => {
    if (filename === "state.json") {
      // Debounce rapid updates (atomic write = rename)
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(broadcast, 50);
    }
  });
} catch (e) {
  // Fallback: poll every 500ms if fs.watch unavailable
  setInterval(broadcast, 500);
}

// HTTP server
const server = http.createServer((req, res) => {
  // CORS headers for local development
  res.setHeader("Access-Control-Allow-Origin", "*");

  if (req.url === "/" || req.url === "/index.html") {
    // Serve dashboard
    try {
      const html = fs.readFileSync(DASHBOARD_FILE, "utf-8");
      res.writeHead(200, { "Content-Type": "text/html; charset=utf-8" });
      res.end(html);
    } catch (e) {
      res.writeHead(500, { "Content-Type": "text/plain" });
      res.end("Dashboard file not found: " + DASHBOARD_FILE);
    }
  } else if (req.url === "/events") {
    // SSE endpoint
    res.writeHead(200, {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
    });
    res.write(`data: ${JSON.stringify(readState())}\n\n`);
    clients.add(res);
    req.on("close", () => clients.delete(res));
  } else if (req.url === "/api/state") {
    // JSON API
    const state = readState();
    res.writeHead(200, { "Content-Type": "application/json; charset=utf-8" });
    res.end(JSON.stringify(state, null, 2));
  } else if (req.url === "/api/health") {
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ status: "ok", uptime: process.uptime() }));
  } else if (req.url === "/api/schema") {
    // Self-describing schema for state.json structure
    const schema = {
      version: "1.0",
      description: "Agent Monitor state schema",
      fields: {
        last_updated: { type: "string", format: "ISO 8601" },
        session_id: { type: "string|null" },
        agents: {
          type: "object",
          description: "Map of agent_id → agent object",
          agent_fields: {
            id: { type: "string" },
            type: { type: "string", values: ["subagent", "tool", "mcp", "hook"] },
            state: { type: "string", values: ["waiting", "planning", "working", "completed", "error"] },
            display_state: { type: "string", description: "UI display state, may include 'permission_wait'" },
            state_jp: { type: "string", description: "Japanese state label" },
            icon: { type: "string", description: "Emoji icon for agent type" },
            description: { type: "string|null" },
            last_tool: { type: "string|null" },
            tool_count: { type: "integer" },
            started_at: { type: "string", format: "ISO 8601" },
            updated_at: { type: "string", format: "ISO 8601" },
          },
        },
        stats: {
          type: "object",
          fields: ["total", "waiting", "planning", "working", "completed", "error"],
        },
      },
    };
    res.writeHead(200, { "Content-Type": "application/json; charset=utf-8" });
    res.end(JSON.stringify(schema, null, 2));
  } else {
    res.writeHead(404);
    res.end("Not found");
  }
});

server.listen(PORT, "127.0.0.1", () => {
  console.log(`Agent Monitor server running at http://127.0.0.1:${PORT}`);
});

// Graceful shutdown
process.on("SIGINT", () => {
  console.log("Shutting down Agent Monitor server...");
  for (const res of clients) {
    try { res.end(); } catch {}
  }
  server.close(() => process.exit(0));
});

process.on("SIGTERM", () => {
  server.close(() => process.exit(0));
});
