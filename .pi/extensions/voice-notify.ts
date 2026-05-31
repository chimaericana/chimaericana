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

  // Helper: check if termux-api is available
  async function hasTermuxApi(): Promise<boolean> {
    const result = await run("which", ["termux-speech-to-text"]);
    return result.code === 0;
  }

  // ═══════════════════════════════════════════════
  // VOICE COMMANDS
  // ═══════════════════════════════════════════════

  // /voice record — Record and transcribe speech
  pi.registerCommand("voice record", {
    description: "Record voice input and transcribe to text",
    handler: async (_args, ctx) => {
      if (!await hasTermuxApi()) {
        ctx.ui.notify("Termux:API not available. Install Termux:API app.", "error");
        return;
      }

      ctx.ui.notify("🎤 Listening... speak now", "info");

      const result = await run("bash", ["automations/voice/stt.sh", "--json"]);

      if (result.code !== 0) {
        ctx.ui.notify("Speech recognition failed. Check microphone permission.", "error");
        return;
      }

      try {
        const parsed = JSON.parse(result.stdout);
        ctx.ui.notify(`📝 Transcribed: "${parsed.text}"`, "info");

        // Send transcribed text as follow-up
        pi.sendUserMessage(
          `[Voice Input]\n\n${parsed.text}\n\nPlease process this voice input as if I typed it.`,
          { deliverAs: "followUp" }
        );
      } catch {
        ctx.ui.notify("Raw transcription:\n" + result.stdout, "info");
      }
    },
  });

  // /voice speak — Read text aloud
  pi.registerCommand("voice speak", {
    description: "Read text aloud using TTS",
    handler: async (args, ctx) => {
      const text = args || "";
      if (!text.trim()) {
        ctx.ui.notify("Usage: /voice speak <text to read aloud>", "info");
        return;
      }

      ctx.ui.notify("🔊 Speaking...", "info");
      await run("bash", ["automations/voice/tts.sh", text]);
    },
  });

  // /voice dictation — Continuous dictation mode
  pi.registerCommand("voice dictation", {
    description: "Start continuous voice dictation session",
    handler: async (_args, ctx) => {
      ctx.ui.notify("🎤 Dictation mode started. Say 'stop dictation' to end.", "info");

      pi.sendUserMessage(
        `Start a voice dictation session. Guide me through recording voice inputs one at a time. After each transcription, ask if I want to continue or stop. Build up a combined transcript of everything I dictate.`,
        { deliverAs: "followUp" }
      );
    },
  });

  // /voice commands — List available voice commands
  pi.registerCommand("voice commands", {
    description: "List all available voice commands",
    handler: async (_args, ctx) => {
      ctx.ui.notify(
        `🎤 Voice Commands:\n\n` +
        `/voice record — Record & transcribe speech\n` +
        `/voice speak <text> — Read text aloud\n` +
        `/voice dictation — Continuous dictation mode\n` +
        `/voice commands — Show this list\n\n` +
        `Requires Termux:API app installed on device.`,
        "info"
      );
    },
  });

  // ═══════════════════════════════════════════════
  // NOTIFICATION COMMANDS
  // ═══════════════════════════════════════════════

  // /notify send — Send a notification
  pi.registerCommand("notify send", {
    description: "Send a notification with optional type",
    handler: async (args, ctx) => {
      const message = args || "Test notification from Projex";
      ctx.ui.notify("Sending notification...", "info");
      await run("bash", ["automations/notifications/notify.sh", message]);
    },
  });

  // /notify history — View notification history
  pi.registerCommand("notify history", {
    description: "View recent notification history",
    handler: async (args, ctx) => {
      const count = args || "20";
      const result = await run("bash", ["automations/notifications/notify.sh", "--history", count]);
      ctx.ui.notify(result.stdout || "No notification history found.", "info");
    },
  });

  // /notify config — Show notification settings
  pi.registerCommand("notify config", {
    description: "Show notification configuration",
    handler: async (_args, ctx) => {
      const result = await run("bash", ["automations/notifications/notify.sh", "--config"]);
      ctx.ui.notify(result.stdout || "No config found. Default settings active.", "info");
    },
  });

  // /notify test — Send test notifications
  pi.registerCommand("notify test", {
    description: "Send test notifications for all types",
    handler: async (_args, ctx) => {
      ctx.ui.notify("Sending test notifications...", "info");
      await run("bash", ["automations/notifications/notify.sh", "--test"]);
    },
  });

  // ═══════════════════════════════════════════════
  // QUICK ACTIONS
  // ═══════════════════════════════════════════════

  // /quick note — Quick note via voice or text
  pi.registerCommand("quick note", {
    description: "Quick note with optional tags",
    handler: async (args, ctx) => {
      const note = args || "";
      if (!note.trim()) {
        ctx.ui.notify("Usage: /quick note <your note> [--tags tag1,tag2]", "info");
        return;
      }

      // Parse tags
      const tagsMatch = note.match(/--tags\s+(\S+)/);
      const tags = tagsMatch ? tagsMatch[1] : "";
      const noteText = tagsMatch ? note.replace(/--tags\s+\S+/, "").trim() : note;

      const result = await run("bash", ["automations/general/notes.sh", noteText, "--tags", tags]);
      ctx.ui.notify(result.stdout || "Note saved.", "info");
    },
  });

  // /quick todo — Quick todo item
  pi.registerCommand("quick todo", {
    description: "Add a todo item quickly",
    handler: async (args, ctx) => {
      const todo = args || "";
      if (!todo.trim()) {
        ctx.ui.notify("Usage: /quick todo <task> [--priority high|medium|low]", "info");
        return;
      }

      const result = await run("bash", ["automations/general/todo.sh", "add", todo]);
      ctx.ui.notify(result.stdout || "Todo added.", "info");
    },
  });

  // ═══════════════════════════════════════════════
  // SYSTEM COMMANDS
  // ═══════════════════════════════════════════════

  // /system status — Show system health
  pi.registerCommand("system status", {
    description: "Show system health and running processes",
    handler: async (_args, ctx) => {
      const hasApi = await hasTermuxApi();

      // Check disk space
      const disk = await run("df", ["-h", PROJECT_ROOT]);
      const diskLine = disk.stdout.split("\n").pop() || "";

      // Count files
      const fileCount = await run("find", ["automations", "-type", "f"]);
      const extCount = await run("find", [".pi/extensions", "-name", "*.ts", "-type", "f"]);

      const status = `📊 System Status\n\n` +
        `📁 Project: ${PROJECT_ROOT}\n` +
        `🔌 Termux:API: ${hasApi ? "Available" : "Not found"}\n` +
        `💾 Disk: ${diskLine.trim()}\n` +
        `📜 Automation scripts: ${fileCount.stdout.split("\n").filter(l => l).length}\n` +
        `🔧 Extensions: ${extCount.stdout.split("\n").filter(l => l).length}\n` +
        `📝 AGENTS.md: loaded\n`;

      ctx.ui.notify(status, "info");
    },
  });

  // /toast — Show Android toast message
  pi.registerCommand("toast", {
    description: "Show a brief Android toast message",
    handler: async (args, ctx) => {
      const message = args || "Hello from Projex!";
      await run("termux-toast", [message]);
      ctx.ui.notify(`Toast: "${message}"`, "info");
    },
  });
}
