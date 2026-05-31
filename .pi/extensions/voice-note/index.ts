import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";
import { Type } from "typebox";
import { exec, execSync } from "child_process";
import { promisify } from "util";

const execAsync = promisify(exec);

const VN_DIR = `${process.env.HOME}/Projex`;
const VN_GUI_PY = `${VN_DIR}/vn-gui.py`;
const GUI_PORT = 8765;
const DEFAULT_SPEED = "1.5";

function cmd(shell: string) {
  return execAsync(shell, { timeout: 30000, maxBuffer: 10 * 1024 * 1024 });
}

function isGuiRunning(): boolean {
  try {
    execSync(`curl -s --max-time 1 http://127.0.0.1:${GUI_PORT}/api/files > /dev/null 2>&1`);
    return true;
  } catch {
    return false;
  }
}

function startGui() {
  if (isGuiRunning()) return false;
  exec(`python3 ${VN_GUI_PY}`, { detached: true }, () => {});
  return true;
}

function stopGui() {
  try {
    execSync(`pkill -f "vn-gui.py" 2>/dev/null`);
  } catch {}
}

function listVoiceNotes(): string {
  try {
    const { stdout } = execSync(`ls -1 ${VN_DIR}/*.mp3 2>/dev/null`);
    const files = stdout.trim().split('\n').filter(Boolean);
    if (files.length === 0) return "No voice notes found.";
    return files.map(f => `🎙️ ${f.split('/').pop()}`).join('\n');
  } catch {
    return "No voice notes found.";
  }
}

export default function (pi: ExtensionAPI) {

  // ── Auto-start GUI on session start / reload ──
  pi.on("session_start", async (_event, ctx) => {
    if (startGui()) {
      ctx.ui.notify(`🌐 Voice Note GUI auto-started at http://127.0.0.1:${GUI_PORT}`, "success");
    } else {
      ctx.ui.notify(`🌐 Voice Note GUI already running at http://127.0.0.1:${GUI_PORT}`, "info");
    }
    ctx.ui.notify("🎙️ Voice Note extension loaded", "info");
  });

  // ── Cleanup GUI on Pi shutdown ──
  pi.on("session_shutdown", async (_event, _ctx) => {
    stopGui();
  });

  // ── Command: /vn ──
  pi.registerCommand("vn", {
    description: "Voice note controls — generate, play, list",
    getArgumentCompletions: (prefix: string) => {
      const items = [
        { value: "generate", label: "generate — Create and play a voice note" },
        { value: "play", label: "play — Play a voice note" },
        { value: "list", label: "list — Show available voice notes" },
        { value: "gui", label: "gui — Start the web GUI" },
        { value: "stop", label: "stop — Stop playback" },
      ];
      return items.filter(i => i.value.startsWith(prefix));
    },
    handler: async (args, ctx) => {
      const [action, ...rest] = (args || "").trim().split(/\s+/);

      switch (action) {
        case "generate":
          if (!rest.length) {
            ctx.ui.notify("Usage: /vn generate <text>", "error");
            return;
          }
          const text = rest.join(" ");
          ctx.ui.notify("🎙️ Generating voice note...", "info");
          try {
            await cmd(`voice_note "${text.replace(/"/g, '\\"')}"`);
            ctx.ui.notify("✅ Voice note generated and playing", "success");
          } catch (e: any) {
            ctx.ui.notify(`❌ Failed: ${e.message}`, "error");
          }
          break;

        case "play":
          if (!rest.length) {
            ctx.ui.notify("Usage: /vn play <filename>", "error");
            return;
          }
          const file = rest[0];
          ctx.ui.notify(`🎵 Playing: ${file}`, "info");
          try {
            await cmd(`vn-play "${VN_DIR}/${file}" ${DEFAULT_SPEED}`);
          } catch (e: any) {
            ctx.ui.notify(`❌ Failed: ${e.message}`, "error");
          }
          break;

        case "list":
          const notes = listVoiceNotes();
          ctx.ui.notify(notes, "info");
          break;

        case "gui":
          if (isGuiRunning()) {
            ctx.ui.notify(`🌐 GUI already running at http://127.0.0.1:${GUI_PORT}`, "info");
          } else {
            startGui();
            ctx.ui.notify(`🌐 Voice Note GUI started at http://127.0.0.1:${GUI_PORT}`, "success");
          }
          break;

        case "stop":
          try {
            await cmd("pkill -f 'mpv' 2>/dev/null; pkill -f 'termux-media-player' 2>/dev/null");
            ctx.ui.notify("⏹️ Playback stopped", "success");
          } catch (e: any) {
            ctx.ui.notify("⏹️ Stopped", "info");
          }
          break;

        default:
          ctx.ui.notify(
            "Voice Note Commands:\n" +
            "  /vn generate <text>  — Create & play\n" +
            "  /vn play <file>      — Play a note\n" +
            "  /vn list             — List notes\n" +
            "  /vn gui              — Start web GUI\n" +
            "  /vn stop             — Stop playback",
            "info"
          );
      }
    },
  });

  // ── Tool: generate_voice_note (LLM-callable) ──
  pi.registerTool({
    name: "generate_voice_note",
    label: "Generate Voice Note",
    description: "Generate a voice note from text and play it back at 1.5x speed with interactive controls",
    parameters: Type.Object({
      text: Type.String({ description: "The text to convert to speech" }),
      speed: Type.Optional(Type.Number({ description: "Playback speed (default 1.5)" })),
    }),
    async execute(_toolCallId, params, _signal, onUpdate, ctx) {
      const speed = params.speed?.toString() || DEFAULT_SPEED;
      const filename = `vn_${Date.now()}.mp3`;
      const filepath = `${VN_DIR}/${filename}`;

      onUpdate?.({ content: [{ type: "text", text: `🎙️ Generating voice note: "${params.text.slice(0, 50)}..."` }] });

      try {
        // Generate TTS
        await cmd(`python3 -c "from gtts import gTTS; gTTS(text='''${params.text.replace(/'''/g, '\\"\\"\\"')}''', lang='en').save('${filepath}')"`);

        // Play at speed
        ctx.ui.notify(`🔊 Playing at ${speed}x speed`, "info");
        exec(`vn-play "${filepath}" ${speed}`, { detached: true });

        return {
          content: [{ type: "text", text: `✅ Voice note saved: ${filename}\n🔊 Playing at ${speed}x — press q to quit` }],
          details: { filepath, speed },
        };
      } catch (e: any) {
        return {
          content: [{ type: "text", text: `❌ Failed to generate voice note: ${e.message}` }],
          details: { error: e.message },
          isError: true,
        };
      }
    },
  });

  // ── Tool: play_voice_note (LLM-callable) ──
  pi.registerTool({
    name: "play_voice_note",
    label: "Play Voice Note",
    description: "Play an existing voice note file with interactive controls (scrubbing, speed, pause)",
    parameters: Type.Object({
      filename: Type.String({ description: "Voice note filename (e.g., projex_overview.mp3)" }),
      speed: Type.Optional(Type.Number({ description: "Playback speed (default 1.5)" })),
    }),
    async execute(_toolCallId, params, _signal, _onUpdate, ctx) {
      const speed = params.speed?.toString() || DEFAULT_SPEED;
      const filepath = `${VN_DIR}/${params.filename}`;

      try {
        const { stdout } = await cmd(`test -f "${filepath}" && echo "exists"`);
        if (!stdout.trim()) {
          return {
            content: [{ type: "text", text: `❌ File not found: ${params.filename}` }],
            details: { available: listVoiceNotes() },
            isError: true,
          };
        }

        ctx.ui.notify(`🎵 Playing: ${params.filename} at ${speed}x`, "info");
        exec(`vn-play "${filepath}" ${speed}`, { detached: true });

        return {
          content: [{
            type: "text",
            text: `▶️ Playing: ${params.filename}\n\nControls: SPACE=play/pause, ←→=scrub, []=speed, q=quit`,
          }],
          details: { filepath, speed },
        };
      } catch (e: any) {
        return {
          content: [{ type: "text", text: `❌ Failed: ${e.message}` }],
          details: { error: e.message },
          isError: true,
        };
      }
    },
  });

  // ── Tool: stop_voice_note (LLM-callable) ──
  pi.registerTool({
    name: "stop_voice_note",
    label: "Stop Voice Note",
    description: "Stop any currently playing voice note",
    parameters: Type.Object({}),
    async execute() {
      try {
        await cmd("pkill -f 'mpv' 2>/dev/null; pkill -f 'termux-media-player' 2>/dev/null; echo stopped");
        return {
          content: [{ type: "text", text: "⏹️ Playback stopped" }],
          details: {},
        };
      } catch {
        return {
          content: [{ type: "text", text: "⏹️ Stopped" }],
          details: {},
        };
      }
    },
  });

  // ── Tool: list_voice_notes (LLM-callable) ──
  pi.registerTool({
    name: "list_voice_notes",
    label: "List Voice Notes",
    description: "List all available voice note files",
    parameters: Type.Object({}),
    async execute() {
      return {
        content: [{ type: "text", text: listVoiceNotes() }],
        details: {},
      };
    },
  });

  // ── Tool: start_vn_gui (LLM-callable) ──
  pi.registerTool({
    name: "start_vn_gui",
    label: "Start Voice Note GUI",
    description: "Start the web-based voice note GUI server at http://127.0.0.1:8765 with full interactive controls",
    parameters: Type.Object({}),
    async execute(_toolCallId, _params, _signal, _onUpdate, ctx) {
      if (isGuiRunning()) {
        return {
          content: [{ type: "text", text: `🌐 GUI already running at http://127.0.0.1:${GUI_PORT}\n\nOpen in your browser for:\n• Scrubbing (timeline + seek buttons)\n• Speed control (1x, 1.5x, 2x, 0.75x)\n• Play/Pause/Stop\n• Voice note library browser` }],
          details: { url: `http://127.0.0.1:${GUI_PORT}`, running: true },
        };
      }
      startGui();
      ctx.ui.notify("🌐 Voice Note GUI started", "success");
      return {
        content: [{ type: "text", text: `🌐 Voice Note GUI started at http://127.0.0.1:${GUI_PORT}\n\nOpen in your browser for the full interactive player with scrubbing, speed control, and more.` }],
        details: { url: `http://127.0.0.1:${GUI_PORT}`, running: true },
      };
    },
  });
}
