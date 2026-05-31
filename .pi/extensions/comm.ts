import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";
import { execSync } from "child_process";
import { readFileSync, existsSync } from "fs";
import { join } from "path";

const PROJEX_ROOT = process.env.HOME + "/Projex";
const CONFIG_PATH = join(PROJEX_ROOT, "automations", "comm", "config.json");
const BRIDGE_SCRIPT = join(PROJEX_ROOT, "automations", "comm", "bot_bridge.py");

function loadConfig(): Record<string, any> {
  if (!existsSync(CONFIG_PATH)) return {};
  return JSON.parse(readFileSync(CONFIG_PATH, "utf-8"));
}

function runBridge(args: string): string {
  try {
    return execSync(`python3 "${BRIDGE_SCRIPT}" ${args}`, {
      encoding: "utf-8",
      timeout: 15000,
      cwd: PROJEX_ROOT
    }).trim();
  } catch (e: any) {
    return `Error: ${e.message || e}`;
  }
}

export default function (pi: ExtensionAPI) {

  pi.registerCommand("comm", {
    description: "Communication hub — send messages via Discord and Mattermost bots",
    handler: async (args, ctx) => {
      const parts = args.trim().split(/\s+/);
      const subcommand = parts[0]?.toLowerCase();

      if (!subcommand) {
        pi.sendUserMessage(
`📡 **Projex Communication Hub**

Available commands:
• \`/comm send <platform> <message>\` — Send to discord or mattermost
• \`/comm status\` — Show bot health and stats
• \`/comm config\` — Show current routing config
• \`/comm test\` — Send test message to all platforms`,
          { deliverAs: "followUp" }
        );
        return;
      }

      switch (subcommand) {
        case "send": {
          const platform = parts[1]?.toLowerCase();
          const message = parts.slice(2).join(" ");
          if (!platform || !message) {
            pi.sendUserMessage("Usage: `/comm send <discord|mattermost> <message>`", { deliverAs: "followUp" });
            return;
          }
          if (!["discord", "mattermost"].includes(platform)) {
            pi.sendUserMessage("Platform must be `discord` or `mattermost`", { deliverAs: "followUp" });
            return;
          }
          const escaped = message.replace(/"/g, '\\"');
          runBridge(`send general "Projex Message" "${escaped}" info`);
          pi.sendUserMessage(`✅ Message sent to **${platform}**`, { deliverAs: "followUp" });
          break;
        }

        case "status": {
          const output = runBridge("status");
          try {
            const status = JSON.parse(output);
            pi.sendUserMessage(
`📡 **Bot Bridge Status**

| Metric | Value |
|--------|-------|
| Messages Sent | ${status.sent} |
| Failed | ${status.failed} |
| Queued | ${status.queue_pending} |
| Discord | ${status.discord_connected ? "🟢 Connected" : "🔴 Offline"} |
| Mattermost | ${status.mattermost_connected ? "🟢 Connected" : "🔴 Offline"} |
| Started | ${status.started} |`,
              { deliverAs: "followUp" }
            );
          } catch {
            pi.sendUserMessage(`Bot Bridge Status:\n\`\`\`\n${output}\n\`\`\``, { deliverAs: "followUp" });
          }
          break;
        }

        case "config": {
          const config = loadConfig();
          if (!config || Object.keys(config).length === 0) {
            pi.sendUserMessage("⚠️ No configuration found. Update `automations/comm/config.json` with your bot tokens.", { deliverAs: "followUp" });
            return;
          }
          const dcEnabled = config.discord?.enabled ? "✅" : "❌";
          const mmEnabled = config.mattermost?.enabled ? "✅" : "❌";
          const dcTokenOk = config.discord?.token && !config.discord.token.startsWith("YOUR") ? "configured" : "not configured";
          const mmTokenOk = config.mattermost?.token && !config.mattermost.token.startsWith("YOUR") ? "configured" : "not configured";
          const routes = config.routing || {};
          const routeList = Object.entries(routes)
            .map(([cat, platforms]: [string, any]) => `  • ${cat} → ${Array.isArray(platforms) ? platforms.join(", ") : platforms}`)
            .join("\n");

          pi.sendUserMessage(
`⚙️ **Communication Config**

**Platforms:**
• Discord: ${dcEnabled} (${dcTokenOk})
• Mattermost: ${mmEnabled} (${mmTokenOk})

**Routing Rules:**
${routeList}`,
            { deliverAs: "followUp" }
          );
          break;
        }

        case "test": {
          runBridge(`send general "Projex Test" "Test message from Projex agent. If you see this, the communication bridge is working." info`);
          pi.sendUserMessage("🧪 Test message sent to all configured platforms. Check your Discord and Mattermost channels.", { deliverAs: "followUp" });
          break;
        }

        default:
          pi.sendUserMessage(`Unknown subcommand: \`${subcommand}\`. Use \`/comm\` to see available commands.`, { deliverAs: "followUp" });
          break;
      }
    }
  });

  pi.registerCommand("comm send", {
    description: "Send a message to Discord or Mattermost",
    handler: async (args, ctx) => {
      const parts = args.trim().split(/\s+/);
      const platform = parts[0]?.toLowerCase();
      const message = parts.slice(1).join(" ");
      if (!platform || !message) {
        pi.sendUserMessage("Usage: `/comm send <discord|mattermost> <message>`", { deliverAs: "followUp" });
        return;
      }
      if (!["discord", "mattermost"].includes(platform)) {
        pi.sendUserMessage("Platform must be `discord` or `mattermost`", { deliverAs: "followUp" });
        return;
      }
      const escaped = message.replace(/"/g, '\\"');
      runBridge(`send general "Projex Message" "${escaped}" info`);
      pi.sendUserMessage(`✅ Message sent to **${platform}**`, { deliverAs: "followUp" });
    }
  });

  pi.registerCommand("comm status", {
    description: "Show bot bridge health and stats",
    handler: async (args, ctx) => {
      const output = runBridge("status");
      try {
        const status = JSON.parse(output);
        pi.sendUserMessage(
`📡 **Bot Bridge Status**

| Metric | Value |
|--------|-------|
| Messages Sent | ${status.sent} |
| Failed | ${status.failed} |
| Queued | ${status.queue_pending} |
| Discord | ${status.discord_connected ? "🟢 Connected" : "🔴 Offline"} |
| Mattermost | ${status.mattermost_connected ? "🟢 Connected" : "🔴 Offline"} |
| Started | ${status.started} |`,
          { deliverAs: "followUp" }
        );
      } catch {
        pi.sendUserMessage(`Bot Bridge Status:\n\`\`\`\n${output}\n\`\`\``, { deliverAs: "followUp" });
      }
    }
  });

  pi.registerCommand("comm test", {
    description: "Send test message to all platforms",
    handler: async (args, ctx) => {
      runBridge(`send general "Projex Test" "Test message from Projex agent. If you see this, the communication bridge is working." info`);
      pi.sendUserMessage("🧪 Test message sent to all configured platforms.", { deliverAs: "followUp" });
    }
  });
}
