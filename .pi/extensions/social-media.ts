import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";
import { Type } from "typebox";
import { StringEnum } from "@mariozechner/pi-ai";

export default function (pi: ExtensionAPI) {
  const PROJECT_ROOT = process.cwd();

  // Helper: run command in project directory
  async function run(cmd: string, args: string[]): Promise<{ stdout: string; stderr: string; code: number }> {
    const result = await pi.exec(cmd, args, { cwd: PROJECT_ROOT });
    return { stdout: result.stdout.trim(), stderr: result.stderr.trim(), code: result.code };
  }

  const PLATFORMS = ["twitter", "linkedin", "facebook", "instagram", "mastodon"] as const;

  // ═══════════════════════════════════════════════
  // SCHEDULER COMMANDS
  // ═══════════════════════════════════════════════

  // /social schedule — Queue a post for publishing
  pi.registerCommand("social schedule", {
    description: "Schedule a social media post",
    handler: async (args, ctx) => {
      if (!args.trim()) {
        ctx.ui.notify("Usage: /social schedule --platform twitter --text \"Post text\" [--schedule \"2026-05-28 09:00\"] [--campaign \"Summer\"]", "info");
        return;
      }

      const cliArgs = args.split(" ").filter(a => a.length > 0);
      const result = await run("python3", ["automations/social/scheduler.py", "add", ...cliArgs]);

      if (result.code === 0) {
        ctx.ui.notify(result.stdout, "info");
      } else {
        ctx.ui.notify(`Error: ${result.stderr || result.stdout}`, "error");
      }
    },
  });

  // /social queue — View scheduled posts
  pi.registerCommand("social queue", {
    description: "View scheduled posts queue",
    handler: async (args, ctx) => {
      const status = args || "pending";
      const result = await run("python3", ["automations/social/scheduler.py", "queue", "--status", status]);
      ctx.ui.notify(result.stdout || "Queue is empty.", "info");
    },
  });

  // /social publish — Publish a post now
  pi.registerCommand("social publish", {
    description: "Publish a scheduled post immediately",
    handler: async (args, ctx) => {
      const postId = args.trim();
      if (!postId) {
        ctx.ui.notify("Usage: /social publish <post-id>", "info");
        return;
      }

      const result = await run("python3", ["automations/social/scheduler.py", "publish", postId]);
      ctx.ui.notify(result.stdout || result.stderr, result.code === 0 ? "success" : "error");
    },
  });

  // /social cancel — Cancel a scheduled post
  pi.registerCommand("social cancel", {
    description: "Cancel a scheduled post",
    handler: async (args, ctx) => {
      const postId = args.trim();
      if (!postId) {
        ctx.ui.notify("Usage: /social cancel <post-id>", "info");
        return;
      }

      const result = await run("python3", ["automations/social/scheduler.py", "cancel", postId]);
      ctx.ui.notify(result.stdout || result.stderr, result.code === 0 ? "success" : "error");
    },
  });

  // /social stats — Show scheduler statistics
  pi.registerCommand("social stats", {
    description: "Show post scheduler statistics",
    handler: async (_args, ctx) => {
      const result = await run("python3", ["automations/social/scheduler.py", "stats"]);
      ctx.ui.notify(result.stdout || "No data yet.", "info");
    },
  });

  // ═══════════════════════════════════════════════
  // TRACKER COMMANDS
  // ═══════════════════════════════════════════════

  // /social track — Record a metric snapshot
  pi.registerCommand("social track", {
    description: "Record social media metric (followers, engagement, etc.)",
    handler: async (args, ctx) => {
      if (!args.trim()) {
        ctx.ui.notify("Usage: /social track --platform twitter --metric followers --value 1234", "info");
        return;
      }

      const cliArgs = args.split(" ").filter(a => a.length > 0);
      const result = await run("python3", ["automations/social/tracker.py", "record", ...cliArgs]);
      ctx.ui.notify(result.stdout || result.stderr, result.code === 0 ? "success" : "error");
    },
  });

  // /social metrics — Show current metrics
  pi.registerCommand("social metrics", {
    description: "Show current social media metrics",
    handler: async (args, ctx) => {
      const platform = args.trim();
      const cmdArgs = ["automations/social/tracker.py", "stats"];
      if (platform) cmdArgs.push("--platform", platform);

      const result = await run("python3", cmdArgs);
      ctx.ui.notify(result.stdout || "No metrics recorded yet. Use /social track to add metrics.", "info");
    },
  });

  // /social mention — Record a brand mention
  pi.registerCommand("social mention", {
    description: "Record a brand mention",
    handler: async (args, ctx) => {
      if (!args.trim()) {
        ctx.ui.notify("Usage: /social mention --add \"Brand mentioned in article\" --platform twitter [--sentiment positive]", "info");
        return;
      }

      const cliArgs = args.split(" ").filter(a => a.length > 0);
      const result = await run("python3", ["automations/social/tracker.py", "mentions", ...cliArgs]);
      ctx.ui.notify(result.stdout || result.stderr, result.code === 0 ? "success" : "error");
    },
  });

  // /social mentions — List brand mentions
  pi.registerCommand("social mentions", {
    description: "List brand mentions",
    handler: async (args, ctx) => {
      const search = args.trim();
      const cmdArgs = ["automations/social/tracker.py", "mentions"];
      if (search) cmdArgs.push("--search", search);

      const result = await run("python3", cmdArgs);
      ctx.ui.notify(result.stdout || "No mentions found.", "info");
    },
  });

  // ═══════════════════════════════════════════════
  // ALERTS COMMANDS
  // ═══════════════════════════════════════════════

  // /social alerts — Check for social media alerts
  pi.registerCommand("social alerts", {
    description: "Check for social media engagement alerts",
    handler: async (_args, ctx) => {
      const result = await run("python3", ["automations/social/alerts.py", "check"]);
      ctx.ui.notify(result.stdout, "info");
    },
  });

  // /social alerts-config — Manage alert configuration
  pi.registerCommand("social alerts-config", {
    description: "Manage alert thresholds and settings",
    handler: async (args, ctx) => {
      if (!args.trim()) {
        const result = await run("python3", ["automations/social/alerts.py", "config"]);
        ctx.ui.notify(result.stdout, "info");
        return;
      }

      const cliArgs = args.split(" ").filter(a => a.length > 0);
      const result = await run("python3", ["automations/social/alerts.py", "config", "--set", ...cliArgs]);
      ctx.ui.notify(result.stdout || result.stderr, result.code === 0 ? "success" : "error");
    },
  });

  // /social alerts-history — View alert history
  pi.registerCommand("social alerts-history", {
    description: "View alert history",
    handler: async (args, ctx) => {
      const limit = args.trim() || "20";
      const result = await run("python3", ["automations/social/alerts.py", "history", "--limit", limit]);
      ctx.ui.notify(result.stdout || "No alert history.", "info");
    },
  });

  // ═══════════════════════════════════════════════
  // QUICK SOCIAL COMMANDS
  // ═══════════════════════════════════════════════

  // /social draft — Draft a post (sends to LLM)
  pi.registerCommand("social draft", {
    description: "AI-draft a social media post from a briefing",
    handler: async (args, ctx) => {
      const briefing = args || "the following briefing";
      ctx.ui.notify("📝 Drafting social media post...", "info");
      pi.sendUserMessage(
        `Draft social media posts based on: ${briefing}\n\nCreate posts for Twitter/X (under 280 chars), LinkedIn (professional tone), and Instagram (visual-focused). Include relevant hashtags and engagement prompts for each platform.`,
        { deliverAs: "followUp" }
      );
    },
  });

  // /social calendar — Show upcoming scheduled posts
  pi.registerCommand("social calendar", {
    description: "Show upcoming scheduled posts calendar",
    handler: async (_args, ctx) => {
      const result = await run("python3", ["automations/social/scheduler.py", "due"]);
      ctx.ui.notify(result.stdout || "✅ No posts due for publishing.", "info");
    },
  });

  // /social export — Export social data
  pi.registerCommand("social export", {
    description: "Export social media data",
    handler: async (args, ctx) => {
      const format = args.trim() || "json";
      const result = await run("python3", ["automations/social/tracker.py", "export", "--format", format]);
      ctx.ui.notify(result.stdout || "No data to export.", "info");
    },
  });

  // ═══════════════════════════════════════════════
  // AUTO-ALERT CHECK (runs on session start)
  // ═══════════════════════════════════════════════

  pi.on("session_start", async (_event, ctx) => {
    // Run a quick alert check on startup
    try {
      const result = await run("python3", ["automations/social/alerts.py", "check"]);
      const alertCount = (result.stdout.match(/[🔥⚠️🚨📈🎉]/g) || []).length;
      if (alertCount > 0) {
        ctx.ui.notify(`🔔 ${alertCount} social media alert(s) on startup`, "info");
      }
    } catch {
      // Silently fail — alerts aren't critical
    }
  });
}
