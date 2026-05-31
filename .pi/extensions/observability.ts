import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";

export default function (pi: ExtensionAPI) {
  const PROJECT_ROOT = process.cwd();

  async function run(cmd: string, args: string[]): Promise<{ stdout: string; stderr: string; code: number }> {
    const result = await pi.exec(cmd, args, { cwd: PROJECT_ROOT });
    return { stdout: result.stdout.trim(), stderr: result.stderr.trim(), code: result.code };
  }

  // Helper: log activity automatically when commands run
  async function logActivity(type: string, message: string, level = "info", source = "command") {
    try {
      await run("python3", [
        "automations/observability/activity_tracker.py", "log",
        "--type", type,
        "--message", message,
        "--level", level,
        "--source", source
      ]);
    } catch {
      // Silently fail — logging is non-critical
    }
  }

  // ═══════════════════════════════════════════════
  // ACTIVITY LOG COMMANDS
  // ═══════════════════════════════════════════════

  pi.registerCommand("log tail", {
    description: "View recent activity log",
    handler: async (args, ctx) => {
      const lines = args.trim() || "20";
      const result = await run("python3", ["automations/observability/activity_tracker.py", "tail", "--lines", lines]);
      ctx.ui.notify(result.stdout || "No activity logged yet.", "info");
    },
  });

  pi.registerCommand("log search", {
    description: "Search activity log",
    handler: async (args, ctx) => {
      const query = args.trim();
      if (!query) {
        ctx.ui.notify("Usage: /log search <query>", "info");
        return;
      }
      const result = await run("python3", ["automations/observability/activity_tracker.py", "search", "--query", query]);
      ctx.ui.notify(result.stdout || `No matches for "${query}".`, "info");
    },
  });

  pi.registerCommand("log stats", {
    description: "Show activity statistics",
    handler: async (args, ctx) => {
      const days = args.trim() || "30";
      const result = await run("python3", ["automations/observability/activity_tracker.py", "stats", "--days", days]);
      ctx.ui.notify(result.stdout || "No activity data.", "info");
    },
  });

  // ═══════════════════════════════════════════════
  // REPORT COMMANDS
  // ═══════════════════════════════════════════════

  pi.registerCommand("report daily", {
    description: "Generate daily digest report",
    handler: async (args, ctx) => {
      ctx.ui.notify("📊 Generating daily report...", "info");
      const format = args.trim() || "text";
      const result = await run("python3", ["automations/observability/report.py", "daily", "--format", format, "--output", "daily"]);

      if (result.code === 0) {
        // Also send as notification summary
        const textResult = await run("python3", ["automations/observability/report.py", "daily", "--format", "text"]);
        const summary = textResult.stdout.split("\n").slice(0, 10).join("\n");
        ctx.ui.notify(summary || "Report generated.", "info");
      } else {
        ctx.ui.notify(result.stderr || "Report generation failed.", "error");
      }
    },
  });

  pi.registerCommand("report weekly", {
    description: "Generate weekly summary report",
    handler: async (_args, ctx) => {
      ctx.ui.notify("📊 Generating weekly report...", "info");
      const result = await run("python3", ["automations/observability/report.py", "daily", "--format", "text", "--output", "weekly"]);
      ctx.ui.notify(result.stdout || "Weekly report generated.", "info");
    },
  });

  // ═══════════════════════════════════════════════
  // RECOVERY COMMANDS
  // ═══════════════════════════════════════════════

  pi.registerCommand("recovery check", {
    description: "Run system recovery check",
    handler: async (_args, ctx) => {
      ctx.ui.notify("🛡️  Running recovery check...", "info");
      const result = await run("python3", ["automations/observability/recovery.py", "check"]);
      ctx.ui.notify(result.stdout || "Recovery check complete.", "info");
    },
  });

  pi.registerCommand("recovery status", {
    description: "Show recovery system status",
    handler: async (_args, ctx) => {
      const result = await run("python3", ["automations/observability/recovery.py", "status"]);
      ctx.ui.notify(result.stdout || "No recovery data.", "info");
    },
  });

  pi.registerCommand("recovery log", {
    description: "View recovery event log",
    handler: async (args, ctx) => {
      const limit = args.trim() || "20";
      const result = await run("python3", ["automations/observability/recovery.py", "log", "--limit", limit]);
      ctx.ui.notify(result.stdout || "No recovery events.", "info");
    },
  });

  pi.registerCommand("recovery checkpoints", {
    description: "List saved checkpoints",
    handler: async (_args, ctx) => {
      const result = await run("python3", ["automations/observability/recovery.py", "list-checkpoints"]);
      ctx.ui.notify(result.stdout || "No checkpoints saved.", "info");
    },
  });

  // ═══════════════════════════════════════════════
  // DASHBOARD COMMAND
  // ═══════════════════════════════════════════════

  pi.registerCommand("dashboard", {
    description: "Show dashboard URL and quick stats",
    handler: async (_args, ctx) => {
      const dashboardPath = `${PROJECT_ROOT}/dashboard/index.html`;
      const stats = await run("python3", ["automations/observability/activity_tracker.py", "stats", "--days", "1"]);

      ctx.ui.notify(
        `📊 Projex Dashboard\n\n` +
        `Location: ${dashboardPath}\n\n` +
        `Open in browser:\n` +
        `  termux-open ${dashboardPath}\n\n` +
        `Activity (24h):\n${stats.stdout.split("\n").slice(2, 6).join("\n")}`,
        "info"
      );
    },
  });

  // ═══════════════════════════════════════════════
  // SYSTEM SUMMARY (all-in-one)
  // ═══════════════════════════════════════════════

  pi.registerCommand("system summary", {
    description: "Show complete system summary (health, social, tasks, agents)",
    handler: async (_args, ctx) => {
      ctx.ui.notify("📊 Compiling system summary...", "info");

      const results = await Promise.all([
        run("bash", ["automations/system/heartbeat.sh", "--status"]),
        run("python3", ["automations/agents/spawner.py", "status"]),
        run("python3", ["automations/social/scheduler.py", "stats"]),
        run("python3", ["automations/observability/activity_tracker.py", "stats", "--days", "1"]),
        run("bash", ["automations/general/todo.sh", "list", "--status", "all"]),
      ]);

      let summary = "📊 PROJEX SYSTEM SUMMARY\n";
      summary += "═".repeat(45) + "\n\n";

      // Heartbeat
      summary += results[0].stdout + "\n\n";

      // Agents
      summary += results[1].stdout + "\n\n";

      // Social
      summary += results[2].stdout + "\n\n";

      // Activity
      summary += results[3].stdout + "\n\n";

      // Tasks
      summary += results[4].stdout + "\n";

      ctx.ui.notify(summary, "info");

      logActivity("system_event", "System summary generated", "info", "command");
    },
  });

  // ═══════════════════════════════════════════════
  // AUTO-LOG ON SESSION START
  // ═══════════════════════════════════════════════

  pi.on("session_start", async (_event, ctx) => {
    await logActivity("system_event", "Pi session started", "info", "pi");
  });

  // Auto-log on agent start
  pi.on("before_agent_start", async (event, ctx) => {
    await logActivity("agent_action", `User prompt: ${event.prompt.slice(0, 100)}`, "info", "pi");
  });
}
