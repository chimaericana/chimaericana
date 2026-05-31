import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";

export default function (pi: ExtensionAPI) {
  const PROJECT_ROOT = process.cwd();

  async function run(cmd: string, args: string[]): Promise<{ stdout: string; stderr: string; code: number }> {
    const result = await pi.exec(cmd, args, { cwd: PROJECT_ROOT });
    return { stdout: result.stdout.trim(), stderr: result.stderr.trim(), code: result.code };
  }

  // ═══════════════════════════════════════════════
  // HEARTBEAT COMMANDS
  // ═══════════════════════════════════════════════

  pi.registerCommand("heartbeat status", {
    description: "Show system heartbeat status",
    handler: async (_args, ctx) => {
      const result = await run("bash", ["automations/system/heartbeat.sh", "--status"]);
      ctx.ui.notify(result.stdout || "No heartbeat data yet.", "info");
    },
  });

  pi.registerCommand("heartbeat check", {
    description: "Run an immediate system health check",
    handler: async (_args, ctx) => {
      ctx.ui.notify("💓 Running health check...", "info");
      const result = await run("bash", ["automations/system/heartbeat.sh", "--check"]);
      ctx.ui.notify(result.stdout, "info");
    },
  });

  pi.registerCommand("heartbeat log", {
    description: "View recent heartbeat log",
    handler: async (args, ctx) => {
      const count = args.trim() || "10";
      const result = await run("bash", ["automations/system/heartbeat.sh", "--log", count]);
      ctx.ui.notify(result.stdout, "info");
    },
  });

  pi.registerCommand("heartbeat start", {
    description: "Start the heartbeat daemon (background monitoring)",
    handler: async (_args, ctx) => {
      const result = await run("bash", ["automations/system/heartbeat.sh", "--start"]);
      ctx.ui.notify(result.stdout, "info");
    },
  });

  pi.registerCommand("heartbeat stop", {
    description: "Stop the heartbeat daemon",
    handler: async (_args, ctx) => {
      const result = await run("bash", ["automations/system/heartbeat.sh", "--stop"]);
      ctx.ui.notify(result.stdout, "info");
    },
  });

  // ═══════════════════════════════════════════════
  // TRIGGER COMMANDS
  // ═══════════════════════════════════════════════

  pi.registerCommand("trigger list", {
    description: "List all event triggers",
    handler: async (_args, ctx) => {
      const result = await run("python3", ["automations/triggers/trigger_engine.py", "list"]);
      ctx.ui.notify(result.stdout || "No triggers configured.", "info");
    },
  });

  pi.registerCommand("trigger add", {
    description: "Add a new event trigger",
    handler: async (args, ctx) => {
      if (!args.trim()) {
        ctx.ui.notify("Usage: /trigger add --type cron --name \"daily_report\" --schedule \"0 8 * * *\" --command \"bash script.sh\"", "info");
        return;
      }
      const cliArgs = args.split(" ").filter(a => a.length > 0);
      const result = await run("python3", ["automations/triggers/trigger_engine.py", "add", ...cliArgs]);
      ctx.ui.notify(result.stdout || result.stderr, result.code === 0 ? "success" : "error");
    },
  });

  pi.registerCommand("trigger fire", {
    description: "Manually fire a trigger",
    handler: async (args, ctx) => {
      const id = args.trim();
      if (!id) {
        ctx.ui.notify("Usage: /trigger fire <trigger-id>", "info");
        return;
      }
      const result = await run("python3", ["automations/triggers/trigger_engine.py", "fire", id]);
      ctx.ui.notify(result.stdout || result.stderr, result.code === 0 ? "success" : "error");
    },
  });

  pi.registerCommand("trigger remove", {
    description: "Remove a trigger",
    handler: async (args, ctx) => {
      const id = args.trim();
      if (!id) {
        ctx.ui.notify("Usage: /trigger remove <trigger-id>", "info");
        return;
      }
      const result = await run("python3", ["automations/triggers/trigger_engine.py", "remove", id]);
      ctx.ui.notify(result.stdout || result.stderr, result.code === 0 ? "success" : "error");
    },
  });

  pi.registerCommand("trigger log", {
    description: "View trigger execution log",
    handler: async (args, ctx) => {
      const limit = args.trim() || "20";
      const result = await run("python3", ["automations/triggers/trigger_engine.py", "log", "--limit", limit]);
      ctx.ui.notify(result.stdout || "No trigger log found.", "info");
    },
  });

  pi.registerCommand("trigger check", {
    description: "Check and fire any due triggers",
    handler: async (_args, ctx) => {
      const result = await run("python3", ["automations/triggers/trigger_engine.py", "check"]);
      ctx.ui.notify(result.stdout, "info");
    },
  });

  pi.registerCommand("trigger toggle", {
    description: "Enable or disable a trigger",
    handler: async (args, ctx) => {
      if (!args.trim()) {
        ctx.ui.notify("Usage: /trigger toggle <trigger-id> [--enable|--disable]", "info");
        return;
      }
      const cliArgs = args.split(" ").filter(a => a.length > 0);
      const result = await run("python3", ["automations/triggers/trigger_engine.py", "toggle", ...cliArgs]);
      ctx.ui.notify(result.stdout || result.stderr, result.code === 0 ? "success" : "error");
    },
  });

  // ═══════════════════════════════════════════════
  // SUBAGENT COMMANDS
  // ═══════════════════════════════════════════════

  pi.registerCommand("agent spawn", {
    description: "Spawn a background subagent for a task",
    handler: async (args, ctx) => {
      if (!args.trim()) {
        ctx.ui.notify("Usage: /agent spawn --type report --prompt \"Generate daily report\"", "info");
        return;
      }
      const cliArgs = args.split(" ").filter(a => a.length > 0);
      ctx.ui.notify("🤖 Spawning subagent...", "info");
      const result = await run("python3", ["automations/agents/spawner.py", "spawn", ...cliArgs]);
      ctx.ui.notify(result.stdout || result.stderr, result.code === 0 ? "success" : "error");
    },
  });

  pi.registerCommand("agent list", {
    description: "List all subagents",
    handler: async (args, ctx) => {
      const status = args.trim() || "all";
      const result = await run("python3", ["automations/agents/spawner.py", "list", "--status", status]);
      ctx.ui.notify(result.stdout || "No subagents found.", "info");
    },
  });

  pi.registerCommand("agent stop", {
    description: "Stop a running subagent",
    handler: async (args, ctx) => {
      const id = args.trim();
      if (!id) {
        ctx.ui.notify("Usage: /agent stop <agent-id>", "info");
        return;
      }
      const result = await run("python3", ["automations/agents/spawner.py", "stop", id]);
      ctx.ui.notify(result.stdout || result.stderr, result.code === 0 ? "success" : "error");
    },
  });

  pi.registerCommand("agent results", {
    description: "View subagent results",
    handler: async (args, ctx) => {
      const id = args.trim();
      if (!id) {
        ctx.ui.notify("Usage: /agent results <agent-id>", "info");
        return;
      }
      const result = await run("python3", ["automations/agents/spawner.py", "results", id]);
      ctx.ui.notify(result.stdout || result.stderr, result.code === 0 ? "success" : "error");
    },
  });

  pi.registerCommand("agent status", {
    description: "Show subagent system status",
    handler: async (_args, ctx) => {
      const result = await run("python3", ["automations/agents/spawner.py", "status"]);
      ctx.ui.notify(result.stdout || "No agent data yet.", "info");
    },
  });

  // ═══════════════════════════════════════════════
  // HEARTBEAT ON SESSION START
  // ═══════════════════════════════════════════════

  pi.on("session_start", async (_event, ctx) => {
    // Quick health check on startup
    try {
      const hbResult = await run("bash", ["automations/system/heartbeat.sh", "--check"]);
      const status = hbResult.stdout.trim();
      if (status.includes("critical") || status.includes("warning")) {
        ctx.ui.notify(`💓 System health: ${status}`, "info");
      }
    } catch {
      // Silently fail — heartbeat isn't critical
    }

    // Check for due triggers
    try {
      const triggerResult = await run("python3", ["automations/triggers/trigger_engine.py", "check"]);
      const fireCount = (triggerResult.stdout.match(/🔥/g) || []).length;
      if (fireCount > 0) {
        ctx.ui.notify(`🔥 ${fireCount} trigger(s) fired on startup`, "info");
      }
    } catch {
      // Silently fail
    }
  });
}
