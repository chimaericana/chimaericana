import type { BunFile } from "bun";

/**
 * social_draft.ts — Generate platform-specific social media posts from a briefing.
 * Usage: bun run social_draft.ts --brief "Your briefing text here"
 *        bun run social_draft.ts --file briefing.md
 *        echo "Announcement text" | bun run social_draft.ts
 */

interface SocialPost {
  platform: string;
  copy: string;
  hashtags: string[];
  visual: string;
  bestTime: string;
  engagement: string;
  charCount: number;
}

interface BriefingInput {
  title: string;
  body: string;
  cta?: string;
  audience?: string;
}

function parseArgs(args: string[]): BriefingInput {
  let title = "";
  let body = "";
  let cta = "";
  let audience = "";

  for (let i = 0; i < args.length; i++) {
    switch (args[i]) {
      case "--title":
        title = args[++i] || "";
        break;
      case "--brief":
      case "--body":
        body = args[++i] || "";
        break;
      case "--cta":
        cta = args[++i] || "";
        break;
      case "--audience":
        audience = args[++i] || "";
        break;
      case "--help":
        console.log(`Usage: bun run social_draft.ts --brief "text" [--title "title"] [--cta "action"] [--audience "target"]`);
        Deno.exit(0);
    }
  }

  if (!body && process.stdin.isTTY === false) {
    // Will read from stdin
  }

  return { title, body, cta, audience };
}

async function readStdin(): Promise<string> {
  let data = "";
  for await (const chunk of Deno.stdin.readable) {
    data += new TextDecoder().decode(chunk);
  }
  return data;
}

function generatePosts(input: BriefingInput): SocialPost[] {
  const keyMessage = input.body || input.title || "No briefing provided";
  const cta = input.cta || "Learn more at our website";
  const brand = input.audience ? ` for ${input.audience}` : "";

  // Extract key words for hashtags
  const hashtags = keyMessage
    .toLowerCase()
    .replace(/[^\w\s]/g, "")
    .split(/\s+/)
    .filter((w) => w.length > 3)
    .slice(0, 5)
    .map((w) => `#${w}`);

  const posts: SocialPost[] = [
    {
      platform: "X (Twitter)",
      copy: `${input.title || "Breaking"} — ${keyMessage.slice(0, 180)}${keyMessage.length > 180 ? "..." : ""} ${hashtags.join(" ")} ${cta}`,
      hashtags: [...hashtags, "#Breaking", "#News"],
      visual: "Clean graphic with headline and key stat. Max 2 lines of text on image.",
      bestTime: "9-10 AM or 12-1 PM weekdays",
      engagement: "What's your take on this? Reply below.",
      charCount: 0,
    },
    {
      platform: "LinkedIn",
      copy: `${input.title || "Announcement"}\n\n${keyMessage}\n\nThis matters because${brand}: it represents a significant step forward for our industry and the people we serve.\n\nKey takeaways:\n• What this means for you\n• Why it matters now\n• What's next\n\n${cta}\n\n#BusinessNews #Innovation`,
      hashtags: [...hashtags, "#Leadership", "#Innovation"],
      visual: "Professional photo or branded carousel post (3-5 slides summarizing key points).",
      bestTime: "8-10 AM Tuesday-Thursday",
      engagement: "How do you see this impacting your work? Share your thoughts.",
      charCount: 0,
    },
    {
      platform: "Facebook",
      copy: `${input.title || "Big news!"} 📢\n\n${keyMessage}\n\nWe're excited to share this with our community. ${input.audience ? `This is especially relevant for ${input.audience}.` : ""}\n\n👉 ${cta}\n\n${hashtags.join(" ")}`,
      hashtags: [...hashtags, "#Community"],
      visual: "Engaging photo or short video (30-60 sec) showing the announcement in action.",
      bestTime: "1-3 PM weekdays, 9-11 AM weekends",
      engagement: "Tag someone who needs to see this! 👇",
      charCount: 0,
    },
    {
      platform: "Instagram",
      copy: `${input.title || "New"} ✨\n\n${keyMessage.slice(0, 200)}${keyMessage.length > 200 ? "..." : ""}\n\nSwipe to learn more →\n\n${hashtags.slice(0, 15).join(" ")}`,
      hashtags: [...hashtags, "#instanews", "#update", "#announcement"],
      visual: "Carousel post (5-7 slides) with bold typography, brand colors, and key stats. First slide = hook.",
      bestTime: "11 AM-1 PM weekdays, 7-9 PM evenings",
      engagement: "Double tap if you're excited and tell us what you think! 💬",
      charCount: 0,
    },
  ];

  // Calculate char counts
  posts.forEach((p) => {
    p.charCount = p.copy.length;
  });

  return posts;
}

function formatOutput(posts: SocialPost[]): string {
  let output = "📱 SOCIAL MEDIA DRAFTS\n";
  output += "═".repeat(45) + "\n\n";

  for (const post of posts) {
    const charWarning = post.charCount > 280 ? " ⚠️  OVER LIMIT" : "";
    output += `── ${post.platform} ──${charWarning}\n\n`;
    output += `📝 Copy:\n${post.copy}\n\n`;
    output += `📊 Character count: ${post.charCount}\n`;
    output += `🏷️  Hashtags: ${post.hashtags.join(" ")}\n`;
    output += `🖼️  Visual: ${post.visual}\n`;
    output += `⏰ Best time: ${post.bestTime}\n`;
    output += `💬 Engagement: ${post.engagement}\n`;
    output += "\n" + "─".repeat(45) + "\n\n";
  }

  return output;
}

async function main() {
  const args = process.argv.slice(2);
  const input = parseArgs(args);

  // Read from stdin if no body provided
  if (!input.body && process.stdin.isTTY === false) {
    input.body = await readStdin();
  }

  if (!input.body && !input.title) {
    console.error("Error: Provide --brief text or pipe input via stdin");
    console.error("Usage: bun run social_draft.ts --brief \"text\"");
    Deno.exit(1);
  }

  const posts = generatePosts(input);
  const output = formatOutput(posts);

  console.log(output);

  // Save to file
  const timestamp = new Date().toISOString().slice(0, 10);
  const filename = `social_drafts_${timestamp}.md`;
  const path = `automations/pr/outputs/${filename}`;

  try {
    await Deno.mkdir("automations/pr/outputs", { recursive: true });
    await Deno.writeTextFile(path, output);
    console.log(`\n💾 Saved to: ${path}`);
  } catch {
    console.log(`\n💾 Tip: Save manually to automations/pr/outputs/${filename}`);
  }
}

main();
