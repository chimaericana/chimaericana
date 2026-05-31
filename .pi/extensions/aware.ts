import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";

export default function (pi: ExtensionAPI) {
  const PROJECT_ROOT = process.cwd();
  const AWARE = `${PROJECT_ROOT}/aware`;
  const ENGAGE = `${PROJECT_ROOT}/automations/aware/engage.py`;
  const JOURNAL = `${PROJECT_ROOT}/automations/aware/journal.py`;

  async function run(cmd: string, args: string[]): Promise<{ stdout: string; stderr: string; code: number }> {
    const result = await pi.exec(cmd, args, { cwd: PROJECT_ROOT });
    return { stdout: result.stdout.trim(), stderr: result.stderr.trim(), code: result.code };
  }

  async function readPromptFile(type: string): Promise<string[]> {
    const path = `${AWARE}/prompts/${type}.md`;
    const result = await run("cat", [path]);
    if (result.code !== 0) return [];
    
    // Extract prompt body text (text after ">")
    const lines = result.stdout.split("\n");
    const prompts: string[] = [];
    let currentPrompt = "";
    let inPrompt = false;

    for (const line of lines) {
      if (line.startsWith("## Prompt")) {
        if (currentPrompt.trim()) prompts.push(currentPrompt.trim());
        currentPrompt = "";
        inPrompt = false;
      } else if (line.trim().startsWith(">") || (inPrompt && line.startsWith('"'))) {
        inPrompt = true;
        const text = line.replace(/^>\s*/, "").replace(/^"/, "").replace(/"$/, "");
        if (text) currentPrompt += text + " ";
      }
    }
    if (currentPrompt.trim()) prompts.push(currentPrompt.trim());
    return prompts;
  }

  function quickNotify(msg: string, level: string = "info") {
    try {
      pi.sendUserMessage(msg, { deliverAs: "followUp" });
    } catch {
      // Fallback
      console.log(msg);
    }
  }

  // ═══════════════════════════════════════════════════════════
  // PROMPT LIBRARY COMMANDS
  // ═══════════════════════════════════════════════════════════

  // /aware morning — Start the day with intention
  pi.registerCommand("aware morning", {
    description: "Start your morning reflection — set intentions for the day",
    handler: async (_args, ctx) => {
      ctx.ui.notify("☀️ Morning reflection...", "info");
      await run("python3", [ENGAGE, "record", "morning"]);
      quickNotify(
        "☀️ **Good morning!** Let's set the tone for today.\n\n" +
        "What's **one thing** you want to make true today? Could be something you accomplish, " +
        "a feeling you want to carry, or a way you want to show up.\n\n" +
        "Tell me and I'll log it, and we can build from there."
      );
    },
  });

  // /aware evening — Reflect on the day
  pi.registerCommand("aware evening", {
    description: "Evening reflection — review your day and capture wins",
    handler: async (_args, ctx) => {
      ctx.ui.notify("🌙 Evening reflection...", "info");
      await run("python3", [ENGAGE, "record", "evening"]);
      quickNotify(
        "🌙 **Evening check-in.** Let's close the day intentionally.\n\n" +
        "What's **one win** from today — something that made it matter? " +
        "And what's **one thing** you'd do differently if you could?\n\n" +
        "Even small observations count. Tell me what comes to mind."
      );
    },
  });

  // /aware notice <thing> — Log something you noticed
  pi.registerCommand("aware notice", {
    description: "Log something you noticed — builds awareness patterns",
    handler: async (args, ctx) => {
      const thing = args.trim();
      if (!thing) {
        quickNotify(
          "👀 **What did you notice?**\n\n" +
          "Could be anything: something about your energy, a pattern in your day, " +
          "a conversation, a feeling, or something in your environment.\n\n" +
          "Try: `/aware notice I felt really focused after my coffee today`"
        );
        return;
      }
      ctx.ui.notify("👀 Noted!", "info");
      await run("python3", [JOURNAL, "log", "notice", `"User noticed: ${thing}"`, thing]);
      await run("python3", [ENGAGE, "record", "notice"]);
      quickNotify(
        `👀 **Noticed and logged:** "${thing}"\n\n` +
        `This goes into your awareness journal. Over time, these small observations ` +
        `paint a picture of patterns and opportunities. I'll keep track.`
      );
    },
  });

  // /aware spark — Get a creative prompt
  pi.registerCommand("aware spark", {
    description: "Get a creative spark — inspiration, reflection, or a thought experiment",
    handler: async (_args, ctx) => {
      ctx.ui.notify("✨ Spark incoming...", "info");
      await run("python3", [ENGAGE, "record", "spark"]);

      const sparks = [
        "✨ **Here's a spark for you:**\n\nWhat's something you're curious about right now that has nothing to do with work? Follow that thread for a minute — where does it lead?",
        "✨ **Spark:**\n\nWhat if you had zero constraints for a day — time, money, location, all unlimited. What would you actually do? The answer often reveals more than you'd expect.",
        "✨ **Spark:**\n\nYou're weighing two options. What's the **third thing** you haven't considered? Sometimes the best path is the one not on the table yet.",
        "✨ **Spark:**\n\nWhat's something you believe that you never actually chose to believe? Something absorbed from family, culture, or circumstance. Is it still serving you?",
        "✨ **Spark:**\n\nWhat would 5-years-from-now you be grateful you started doing today?",
        "✨ **Spark:**\n\nName a constraint you're operating under. Now — what if that constraint wasn't real? What would you do differently?",
      ];

      const pick = sparks[Math.floor(Math.random() * sparks.length)];
      quickNotify(pick);
    },
  });

  // /aware checkin — Goal progress check
  pi.registerCommand("aware checkin", {
    description: "Check in on your goals and priorities",
    handler: async (_args, ctx) => {
      ctx.ui.notify("🎯 Goal check-in...", "info");
      await run("python3", [ENGAGE, "record", "checkin"]);

      // Check if there are active goals in state
      const stateResult = await run("python3", ["-c", `
import json
s = json.load(open("${AWARE}/state.json"))
goals = s.get("active_goals", [])
if goals:
    print("yes:" + ",".join(goals))
else:
    print("none")
      `]);

      if (stateResult.stdout.startsWith("yes:")) {
        const goals = stateResult.stdout.slice(4).split(",");
        quickNotify(
          `🎯 **Goal check-in!**\n\n` +
          `You've been tracking: **${goals.join(", ")}**\n\n` +
          `Quick pulse check:\n` +
          `• On track, stuck, or shifted priority?\n` +
          `• What's one small step that would move things forward?\n` +
          `• What's in the way right now?`
        );
      } else {
        quickNotify(
          `🎯 **Goal check-in!**\n\n` +
          `I don't see any active goals yet. Want to tell me what you're working towards?\n\n` +
          `Even a rough direction helps — we can refine over time. What matters to you right now?`
        );
      }
    },
  });

  // /aware reflect — Deep reflection session
  pi.registerCommand("aware reflect", {
    description: "Deep reflection — explore values, growth, and direction",
    handler: async (_args, ctx) => {
      ctx.ui.notify("🔮 Starting reflection...", "info");
      await run("python3", [ENGAGE, "record", "reflect"]);

      const reflections = [
        "🔮 **Reflection time.**\n\nYou're in what chapter of your life right now? Give it a title and a one-sentence summary. When you know the chapter you're in, you know what scenes to write.",
        "🔮 **Reflection.**\n\nThink about who you were 3 years ago. What's the biggest way you've grown since then that you don't give yourself enough credit for?",
        "🔮 **Reflection.**\n\nWhat version of you are you currently *becoming*? Not the version you're trying to be — the version your current habits, choices, and patterns are actually creating.",
        "🔮 **Reflection.**\n\nIf you lived the next 5 years exactly as you're living now — what would you have more of, less of, and wish you'd started sooner?",
      ];

      const pick = reflections[Math.floor(Math.random() * reflections.length)];
      quickNotify(pick);
    },
  });

  // /aware publish <idea> — Turn a thought into publishable content
  pi.registerCommand("aware publish", {
    description: "Turn your thoughts into ready-to-publish content",
    handler: async (args, ctx) => {
      const idea = args.trim();
      if (!idea) {
        quickNotify(
          "📝 **Turn an idea into content.**\n\n" +
          "Share a thought, insight, or story and I'll turn it into something publishable.\n\n" +
          "Try: `/aware publish I realized that the best decisions come from clarity, not certainty`\n\n" +
          "I'll generate social posts, threads, or whatever format you want."
        );
        return;
      }
      ctx.ui.notify("📝 Crafting your content...", "info");
      await run("python3", [ENGAGE, "record", "publish"]);

      // Send to LLM for content generation
      pi.sendUserMessage(
        `The user wants to turn this idea into publishable content: "${idea}"\n\n` +
        `Generate 3 ready-to-publish options:\n` +
        `1. A Twitter/X thread (3-5 tweets)\n` +
        `2. A LinkedIn post\n` +
        `3. A short-form note/reflection\n\n` +
        `Make them immediately publishable — just needs a quick review before posting. ` +
        `Use a natural, authentic voice that sounds like a real person sharing a genuine insight.` +
        `\n\nAfter generating, I'll save these to the content pipeline.`,
        { deliverAs: "followUp" }
      );
    },
  });

  // /aware process <goal> — Set up a new process/automation
  pi.registerCommand("aware process", {
    description: "Design a new process, habit, or automation",
    handler: async (args, ctx) => {
      const goal = args.trim();
      if (!goal) {
        quickNotify(
          "⚙️ **Design a new process.**\n\n" +
          "Tell me what you want to systemize, automate, or make into a habit.\n\n" +
          "Examples:\n" +
          "• \`/aware process daily standup for my projects\`\n" +
          "• \`/aware process content workflow from idea to post\`\n" +
          "• \`/aware process evening wind-down routine\`\n\n" +
          "I'll design the process and save it to your processes library."
        );
        return;
      }
      ctx.ui.notify("⚙️ Designing your process...", "info");
      await run("python3", [ENGAGE, "record", "process"]);

      pi.sendUserMessage(
        `The user wants to design a process for: "${goal}"\n\n` +
        `Design a simple, repeatable process. Include:\n` +
        `1. **Trigger** — When does this process start?\n` +
        `2. **Steps** — 3-7 clear steps in order\n` +
        `3. **Output** — What's produced or achieved?\n` +
        `4. **Tools needed** — What's required?\n` +
        `5. **Success signal** — How do we know it worked?\n\n` +
        `Keep it practical and minimal. Start with the smallest useful version.` +
        `\n\nAfter I share the design, save it in aware/processes/.`,
        { deliverAs: "followUp" }
      );
    },
  });

  // ═══════════════════════════════════════════════════════════
  // SYSTEM COMMANDS
  // ═══════════════════════════════════════════════════════════

  // /aware — System status and today's overview
  pi.registerCommand("aware", {
    description: "Show Aware system status and overview",
    handler: async (_args, ctx) => {
      const statusResult = await run("python3", [ENGAGE, "status"]);
      const state = JSON.parse(
        (await run("python3", ["-c", `import json; print(json.dumps(json.load(open("${AWARE}/state.json")), indent=2))`])).stdout
      );

      ctx.ui.notify(`${statusResult.stdout}\n\n` +
        `Use /aware <category> to engage:\n` +
        `  /aware morning    — Set intentions\n` +
        `  /aware evening    — Reflect on your day\n` +
        `  /aware notice     — Log an observation\n` +
        `  /aware spark      — Get inspired\n` +
        `  /aware checkin    — Goal progress\n` +
        `  /aware reflect    — Deep reflection\n` +
        `  /aware publish    — Create content from ideas\n` +
        `  /aware process    — Design a new system\n` +
        `  /aware journal    — Browse entries\n` +
        `  /aware patterns   — See what I've noticed\n` +
        `  /aware insight    — Get a life insight\n` +
        `  /aware digest     — Daily/weekly summary`, "info");
    },
  });

  // /aware journal — Browse journal entries
  pi.registerCommand("aware journal", {
    description: "Browse your journal entries",
    handler: async (args, ctx) => {
      const query = args.trim();
      if (query) {
        const result = await run("python3", [JOURNAL, "search", query]);
        ctx.ui.notify(result.stdout || `No matches for "${query}".`, "info");
      } else {
        const result = await run("python3", [JOURNAL, "list", "14"]);
        ctx.ui.notify(result.stdout || "No journal entries yet. Start with `/aware notice` or `/aware morning`", "info");
      }
    },
  });

  // /aware patterns — See detected patterns
  pi.registerCommand("aware patterns", {
    description: "See patterns I've noticed across your journal entries",
    handler: async (_args, ctx) => {
      const result = await run("python3", [JOURNAL, "patterns"]);
      ctx.ui.notify(result.stdout || "Not enough data for pattern analysis yet. Keep journaling!", "info");
    },
  });

  // /aware insight — Get a life insight
  pi.registerCommand("aware insight", {
    description: "Get a life insight based on your patterns",
    handler: async (_args, ctx) => {
      ctx.ui.notify("🔮 Generating insight...", "info");

      const state = JSON.parse(
        (await run("python3", ["-c", `import json; print(json.dumps(json.load(open("${AWARE}/state.json"))))`])).stdout
      );

      const themes = state.get("recurring_themes", []);
      const totalEntries = state.get("total_journal_entries", 0);

      if (totalEntries < 3) {
        quickNotify(
          "🔮 I don't have enough data to generate meaningful insights yet.\n\n" +
          "Keep journaling! Try:\n" +
          "• `/aware morning` — Start your day with intention\n" +
          "• `/aware notice 'something you observed'` — Log observations\n" +
          "• `/aware evening` — Reflect on your day\n\n" +
          "After a few entries, patterns will start to emerge."
        );
        return;
      }

      pi.sendUserMessage(
        `The user wants a life insight based on their journal patterns.\n\n` +
        `Here's what I know:\n` +
        `- Total journal entries: ${totalEntries}\n` +
        `- Recurring themes detected: ${themes.join(", ") || "None yet"}\n` +
        `- Active goals: ${state.get("active_goals", []).join(", ") || "None set"}\n\n` +
        `Generate a thoughtful, genuine insight. Something that feels observant but not presumptuous. ` +
        `Aim for: "I noticed this pattern... you might want to explore..." rather than "you should...".` +
        `\n\nKeep it to 3-4 sentences. Make it feel like a real observation from someone paying attention.`,
        { deliverAs: "followUp" }
      );
    },
  });

  // /aware digest — Generate daily/weekly digest
  pi.registerCommand("aware digest", {
    description: "Generate a daily or weekly life digest",
    handler: async (_args, ctx) => {
      ctx.ui.notify("📊 Compiling digest...", "info");
      await run("python3", [ENGAGE, "record", "digest"]);

      const state = JSON.parse(
        (await run("python3", ["-c", `import json; print(json.dumps(json.load(open("${AWARE}/state.json"))))`])).stdout
      );

      pi.sendUserMessage(
        `Generate a personal digest based on the user's current Aware state.\n\n` +
        `State: ${JSON.stringify(state, null, 2)}\n\n` +
        `Include:\n` +
        `1. 📊 **Engagement Stats** — How many reflections, what types\n` +
        `2. 🎯 **Active Goals** — Current focus areas\n` +
        `3. 🔍 **Recent Themes** — What's been coming up\n` +
        `4. 📝 **Content Pipeline** — Drafts ready to publish\n` +
        `5. 💡 **One Suggestion** — A small, actionable idea for today\n\n` +
        `Keep it light and encouraging. This is a friendly summary, not a report card.`,
        { deliverAs: "followUp" }
      );
    },
  });

  // /aware toggle — Toggle proactive mode
  pi.registerCommand("aware toggle", {
    description: "Toggle proactive engagement mode on/off",
    handler: async (_args, ctx) => {
      const state = JSON.parse(
        (await run("python3", ["-c", `import json; print(json.dumps(json.load(open("${AWARE}/state.json"))))`])).stdout
      );
      state["proactive_mode"] = !state["proactive_mode"];
      const mode = state["proactive_mode"] ? "ON 🟢" : "OFF 🔴";
      await run("python3", ["-c", `import json; json.dump(${JSON.stringify(state)}, open("${AWARE}/state.json", "w"))`]);
      ctx.ui.notify(`Aware proactive mode is now ${mode}`, "info");
    },
  });

  // /aware goals — Manage active goals
  pi.registerCommand("aware goals", {
    description: "View or set your active goals",
    handler: async (args, ctx) => {
      const input = args.trim();
      const state = JSON.parse(
        (await run("python3", ["-c", `import json; print(json.dumps(json.load(open("${AWARE}/state.json"))))`])).stdout
      );

      if (!input && state["active_goals"].length === 0) {
        quickNotify(
          "🎯 **No active goals set.**\n\n" +
          "Tell me what you're working towards:\n" +
          "• \`/aware goals build a daily writing habit\`\n" +
          "• \`/aware goals launch my project, get fit, learn piano\`\n\n" +
          "Even rough directions help me track your progress."
        );
      } else if (!input) {
        quickNotify(
          `🎯 **Your active goals:**\n  ${state["active_goals"].map((g: string) => `• ${g}`).join("\n  ")}\n\n` +
          `To update: \`/aware goals new goal here\`\n` +
          `To clear: \`/aware goals clear\``
        );
      } else if (input === "clear") {
        state["active_goals"] = [];
        await run("python3", ["-c", `import json; json.dump(${JSON.stringify(state)}, open("${AWARE}/state.json", "w"))`]);
        ctx.ui.notify("🎯 Active goals cleared.", "info");
      } else {
        state["active_goals"] = input.split(",").map((g: string) => g.trim()).filter(Boolean);
        await run("python3", ["-c", `import json; json.dump(${JSON.stringify(state)}, open("${AWARE}/state.json", "w"))`]);
        ctx.ui.notify(`🎯 Goals updated: ${state["active_goals"].join(", ")}`, "info");
      }
    },
  });

  // ═══════════════════════════════════════════════════════════
  // ORCHESTRATION COMMANDS
  // ═══════════════════════════════════════════════════════════

  const ORCHESTRATOR = `${PROJECT_ROOT}/automations/aware/orchestrator.py`;
  const CHANNELS = `${PROJECT_ROOT}/automations/aware/channels.py`;
  const TRACKER = `${PROJECT_ROOT}/automations/aware/tracker.py`;

  // /aware schedule — Show the full engagement schedule
  pi.registerCommand("aware schedule", {
    description: "Show the day/week/month engagement schedule across all agents",
    handler: async (_args, ctx) => {
      const result = await run("python3", [ORCHESTRATOR, "schedule"]);
      ctx.ui.notify(result.stdout || "No schedule configured.", "info");
    },
  });

  // /aware agents — Show the agent network
  pi.registerCommand("aware agents", {
    description: "Show the agent network — each agent's role, tone, and channels",
    handler: async (_args, ctx) => {
      const result = await run("python3", [ORCHESTRATOR, "status"]);
      ctx.ui.notify(result.stdout || "No agents configured.", "info");
    },
  });

  // /aware channels — Check channel availability
  pi.registerCommand("aware channels", {
    description: "Check which engagement channels are currently available",
    handler: async (_args, ctx) => {
      const result = await run("python3", [CHANNELS, "status"]);
      ctx.ui.notify(result.stdout || "Channel status unavailable.", "info");
    },
  });

  // /aware stats — View engagement statistics
  pi.registerCommand("aware stats", {
    description: "View engagement statistics and response rates",
    handler: async (args, ctx) => {
      const days = args.trim() || "7";
      const result = await run("python3", [TRACKER, "stats", days]);
      const stats = JSON.parse(result.stdout || "{}");
      
      const lines = [
        `📊 Engagement Stats (last ${days} days)`,
        `  Sent: ${stats.engagements_sent || 0}`,
        `  Responses: ${stats.responses || 0}`,
        `  Response Rate: ${stats.response_rate || 0}%`,
        `  Content Posted: ${stats.content_posted || 0}`,
      ];
      
      if (stats.by_agent && Object.keys(stats.by_agent).length) {
        lines.push(`\n  By Agent:`);
        for (const [agent, count] of Object.entries(stats.by_agent)) {
          lines.push(`    ${agent}: ${count}`);
        }
      }
      
      if (stats.by_channel && Object.keys(stats.by_channel).length) {
        lines.push(`\n  By Channel:`);
        for (const [ch, count] of Object.entries(stats.by_channel)) {
          lines.push(`    ${ch}: ${count}`);
        }
      }
      
      ctx.ui.notify(lines.join("\n"), "info");
    },
  });

  // /aware trends — Compare this week to last week
  pi.registerCommand("aware trends", {
    description: "Show engagement trends — compare this week to last week",
    handler: async (_args, ctx) => {
      const result = await run("python3", [TRACKER, "trends"]);
      ctx.ui.notify(result.stdout || "Not enough data for trends yet.", "info");
    },
  });

  // /aware tick — Manually check and fire due engagements
  pi.registerCommand("aware tick", {
    description: "Manually check and fire any due scheduled engagements",
    handler: async (_args, ctx) => {
      ctx.ui.notify("🔄 Checking scheduler...", "info");
      const result = await run("python3", [ORCHESTRATOR, "tick"]);
      ctx.ui.notify(result.stdout || "Tick complete.", "info");
    },
  });

  // /aware route <agent> <type> <message> [channels] — Route a custom message through an agent
  pi.registerCommand("aware route", {
    description: "Route a custom message through an agent profile to specific channels",
    handler: async (args, ctx) => {
      const parts = args.trim().split(" ");
      if (parts.length < 2) {
        quickNotify(
          "📡 **Route a message through an agent.**\n\n" +
          "Usage: `/aware route <agent> <type> <message>`\n" +
          "\nAgents: nexus, echo, press, shield, signal, aware" +
          "\nTypes: morning, evening, spark, checkin, reflect, notice, publish, digest" +
          "\n\nExample: `/aware route echo spark \"What if you had zero constraints?\"`" +
          "\nExample: `/aware route nexus digest discord,email`"
        );
        return;
      }
      
      const agent = parts[0].toLowerCase();
      const ptype = parts[1].toLowerCase();
      const remaining = parts.slice(2).join(" ");
      
      // If remaining has commas, treat as channel list
      let channels = ["direct"];
      let message = remaining;
      if (remaining.includes(",")) {
        channels = remaining.split(",").map((s: string) => s.trim());
        message = "";
      }
      
      ctx.ui.notify(`📡 Routing through ${agent}...`, "info");
      
      // Generate the engagement and dispatch
      const result = await run("python3", [ORCHESTRATOR, "test", agent, ptype, channels.join(",")]);
      ctx.ui.notify(result.stdout || "Route dispatched.", "info");
    },
  });

  // /aware who <agent> — Show agent personality and details
  pi.registerCommand("aware who", {
    description: "Learn about an agent — their role, personality, and communication style",
    handler: async (args, ctx) => {
      const agent = args.trim().toLowerCase();
      if (!agent) {
        quickNotify(
          "🧠 **Available Agents:**\n\n" +
          "🎯 **Nexus** — Communications Coordinator\n" +
          "  Routes information, coordinates agents, handles digests\n\n" +
          "📣 **Echo** — Social Media Manager\n" +
          "  Creates content, schedules posts, tracks engagement\n\n" +
          "📰 **Press** — PR Specialist\n" +
          "  Drafts press releases, pitches, key messages\n\n" +
          "🛡️ **Shield** — Crisis Communications\n" +
          "  Crisis response, holding statements, reputation management\n\n" +
          "📡 **Signal** — Media Relations\n" +
          "  Journalist outreach, coverage tracking, media lists\n\n" +
          "🧠 **Aware** — Life Engagement System\n" +
          "  Your personal growth engine — prompts, journal, insights"
        );
        return;
      }
      const result = await run("python3", [ORCHESTRATOR, "agent", agent]);
      ctx.ui.notify(result.stdout || `Unknown agent: ${agent}`, "info");
    },
  });

  // /aware automate — Check and manage Automate integration
  pi.registerCommand("aware automate", {
    description: "Check Automate status and get setup instructions",
    handler: async (args, ctx) => {
      const subcmd = args.trim().toLowerCase();

      if (subcmd === "status" || subcmd === "") {
        const statusResult = await run("bash", ["~Athena/.automate/status.sh"]);
        ctx.ui.notify(statusResult.stdout || "Status check failed.", "info");
        return;
      }

      if (subcmd === "install" || subcmd === "import" || subcmd === "flo") {
        quickNotify(
          "📦 **Automate Flow Import**\n\n" +
          "The flow file is ready at:\n" +
          "`/sdcard/Download/athena_autostart.flo`\n\n" +
          "**To import:**\n" +
          "1. Open Files app → Downloads folder\n" +
          "2. Tap `athena_autostart.flo`\n" +
          "3. Choose **Automate** from the picker\n" +
          "4. Tap ▶️ Play to start the flow\n\n" +
          "The flow auto-starts Pi + Discord bot on every boot, " +
          "and checks every 5 minutes that everything is alive."
        );
        return;
      }

      if (subcmd === "start" || subcmd === "run") {
        ctx.ui.notify("🔥 Running Automate startup script...", "info");
        const result = await run("bash", ["~Athena/.automate/startup.sh"]);
        ctx.ui.notify(result.stdout || "Startup complete.", "info");
        return;
      }

      if (subcmd === "fix" || subcmd === "repair") {
        const result = await run("bash", ["~Athena/.automate/status.sh", "--fix"]);
        ctx.ui.notify(result.stdout || "Fix attempted.", "info");
        return;
      }

      quickNotify(
        "🤖 **Automate Commands:**\n\n" +
        "`/aware automate` or `/aware automate status` — Check all services\n" +
        "`/aware automate install` — Install the Automate flow (import .flo)\n" +
        "`/aware automate start` — Run startup script now\n" +
        "`/aware automate fix` — Restart any down services\n" +
        "`/aware automate help` — This message"
      );
    },
  });
}
