import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";

export default function (pi: ExtensionAPI) {
  // Helper: send PR task to LLM
  function sendPrTask(message: string, ctx: any) {
    ctx.ui.notify("Processing your PR request...", "info");
    pi.sendUserMessage(message, { deliverAs: "followUp" });
  }

  // /pr release - Draft a press release from briefing notes
  pi.registerCommand("pr release", {
    description: "Draft a press release from briefing notes",
    handler: async (args, ctx) => {
      const briefing = args || "the following briefing notes";
      sendPrTask(
        `Draft a professional press release based on ${briefing}.\n\nFollow AP style and use the inverted pyramid structure. Include:\n- FOR IMMEDIATE RELEASE header\n- Strong, active headline under 100 characters\n- Dateline (CITY, State — Date)\n- Lead paragraph covering who, what, when, where, why\n- Body with supporting details and context\n- Quote from key stakeholder\n- About/boilerplate section\n- Media contact placeholder\n\nKeep it newsworthy, not promotional. Focus on facts and significance.`,
        ctx
      );
    },
  });

  // /pr pitch - Create a media pitch
  pi.registerCommand("pr pitch", {
    description: "Create a media pitch for a specific story or outlet",
    handler: async (args, ctx) => {
      const details = args || "the following story details";
      sendPrTask(
        `Write a targeted media pitch based on ${details}.\n\nThe pitch should:\n- Be under 200 words\n- Open with a strong hook in the first sentence\n- Personalize for the journalist/outlet\n- Present a clear news angle\n- Explain why it matters to the outlet's audience\n- Include a clear call to action\n- Reference relevant data, trends, or timing that makes this newsworthy now\n\nMake it conversational, not corporate.`,
        ctx
      );
    },
  });

  // /pr crisis - Develop crisis communication materials
  pi.registerCommand("pr crisis", {
    description: "Develop crisis communication materials and response plan",
    handler: async (args, ctx) => {
      const situation = args || "the following crisis situation";
      sendPrTask(
        `Develop crisis communication materials for ${situation}.\n\nInclude:\n1. **Holding Statement** — A brief initial response acknowledging the situation\n2. **Key Messages** — 3-5 core messages for all communications\n3. **Response Plan** — Immediate actions, timeline, and responsible parties\n4. **Stakeholder Communications** — Tailored messages for employees, customers, media, regulators\n5. **Q&A Document** — Anticipated questions with approved responses\n6. **Social Media Response** — Guidelines for social media monitoring and response\n\nTone: serious, transparent, empathetic, and accountable. Avoid speculation and legal jargon.`,
        ctx
      );
    },
  });

  // /pr messages - Generate key messages and talking points
  pi.registerCommand("pr messages", {
    description: "Generate key messages and talking points",
    handler: async (args, ctx) => {
      const topic = args || "the following topic";
      sendPrTask(
        `Generate key messages and talking points for ${topic}.\n\nCreate:\n1. **Core Message** — One-sentence summary of the main point\n2. **Supporting Messages** — 3-5 key messages, each concise and memorable\n3. **Supporting Facts** — Data, evidence, or examples for each message\n4. **Audience Adaptations** — How to tailor messages for media, public, employees, and executives\n5. **Sound Bites** — 3-5 quotable, shareable phrases\n\nEach message should be: concise, memorable, repeatable, and backed by facts.`,
        ctx
      );
    },
  });

  // /pr campaign - Build a PR campaign strategy
  pi.registerCommand("pr campaign", {
    description: "Build a PR campaign strategy outline",
    handler: async (args, ctx) => {
      const campaign = args || "the following campaign goal";
      sendPrTask(
        `Build a comprehensive PR campaign strategy for ${campaign}.\n\nInclude:\n1. **Campaign Objective** — Clear, measurable goals\n2. **Target Audiences** — Primary and secondary audiences with personas\n3. **Key Messages** — Core messaging framework\n4. **Channels & Tactics** — Media relations, social, events, influencer partnerships, owned media\n5. **Timeline** — Phased rollout with key milestones\n6. **Media Strategy** — Target outlets, angles, and pitching approach\n7. **Content Calendar** — Key content pieces and publication schedule\n8. **Measurement** — KPIs and success metrics\n9. **Budget Considerations** — Resource allocation\n10. **Risk Management** — Potential challenges and mitigation`,
        ctx
      );
    },
  });

  // /pr social - Draft social media content
  pi.registerCommand("pr social", {
    description: "Draft social media content from a press release or announcement",
    handler: async (args, ctx) => {
      const source = args || "the following announcement or press release";
      sendPrTask(
        `Draft social media content based on ${source}.\n\nCreate platform-specific posts for:\n1. **X/Twitter** — Short, punchy post with relevant hashtags (under 280 characters)\n2. **LinkedIn** — Professional post with context and call to action\n3. **Facebook** — Engaging post with visual suggestions\n4. **Instagram** — Caption with hashtag strategy and visual direction\n\nFor each platform include:\n- Post copy\n- Suggested hashtags\n- Visual/media recommendations\n- Optimal posting time\n- Engagement prompt (question or CTA)\n\nAdapt tone appropriately per platform while maintaining message consistency.`,
        ctx
      );
    },
  });

  // /pr qa - Create spokesperson Q&A document
  pi.registerCommand("pr qa", {
    description: "Create spokesperson Q&A document for interviews",
    handler: async (args, ctx) => {
      const topic = args || "the following interview topic";
      sendPrTask(
        `Create a comprehensive Q&A document for a spokesperson interview about ${topic}.\n\nInclude:\n1. **Background Brief** — Key facts, context, and narrative the spokesperson should know\n2. **Expected Questions** — 15-20 likely questions with approved answers\n3. **Tough Questions** — 5-10 challenging or adversarial questions with bridge responses\n4. **Talking Points** — Key messages to weave into every answer\n5. **Bridging Techniques** — Phrases to pivot from tough questions back to key messages\n6. **Body Language & Delivery Tips** — Non-verbal guidance\n7. **Don't Say List** — Topics, words, or phrases to avoid\n8. **Follow-up Resources** — Where to send journalists for more information\n\nAnswers should be concise, factual, and message-driven. Include bridging examples.`,
        ctx
      );
    },
  });

  // /pr monitor - Analyze media coverage
  pi.registerCommand("pr monitor", {
    description: "Analyze media coverage or mentions you provide",
    handler: async (args, ctx) => {
      const coverage = args || "the following media coverage or mentions";
      sendPrTask(
        `Analyze the following media coverage and provide insights:\n\n${coverage}\n\nProvide:\n1. **Coverage Summary** — Volume, reach, and key outlets\n2. **Sentiment Analysis** — Positive, neutral, and negative coverage breakdown\n3. **Message Pull-Through** — Which key messages were picked up\n4. **Top Quotes & Mentions** — Notable quotes and how they were used\n5. **Influencer Impact** — Which journalists or outlets drove the most engagement\n6. **Narrative Analysis** — Dominant storylines and frames\n7. **Gaps & Opportunities** — What's missing and how to address it\n8. **Competitive Context** — How this compares to competitor coverage\n9. **Recommendations** — Actionable next steps based on analysis`,
        ctx
      );
    },
  });

  // /pr stakeholder - Draft stakeholder communication
  pi.registerCommand("pr stakeholder", {
    description: "Draft stakeholder or internal communication",
    handler: async (args, ctx) => {
      const details = args || "the following communication details";
      sendPrTask(
        `Draft a stakeholder communication based on ${details}.\n\nSpecify:\n1. **Audience** — Who is receiving this (employees, investors, partners, community, regulators)\n2. **Purpose** — What we need them to know, feel, or do\n3. **Key Messages** — What must be communicated\n4. **Tone** — Appropriate for the audience and situation\n\nCreate:\n- Primary communication (email, memo, or letter format as appropriate)\n- Executive summary version for leadership\n- FAQ for likely questions\n- Follow-up communication plan\n\nTone should match the situation: informative for routine updates, empathetic for sensitive topics, inspiring for announcements.`,
        ctx
      );
    },
  });

  // /pr strategy - Develop overall PR strategy
  pi.registerCommand("pr strategy", {
    description: "Develop an overall PR strategy for a goal or situation",
    handler: async (args, ctx) => {
      const goal = args || "the following PR goal or situation";
      sendPrTask(
        `Develop a comprehensive PR strategy for ${goal}.\n\nInclude:\n1. **Situation Analysis** — Current landscape, SWOT, and key challenges\n2. **Objectives** — SMART goals (Specific, Measurable, Achievable, Relevant, Time-bound)\n3. **Target Audiences** — Primary and secondary with audience insights\n4. **Positioning** — How we want to be perceived\n5. **Messaging Framework** — Core messages and proof points\n6. **Channel Strategy** — Earned, owned, shared, and paid media approach\n7. **Tactics & Activities** — Specific actions and initiatives\n8. **Timeline** — Phased approach with milestones\n9. **Measurement Framework** — KPIs, metrics, and reporting cadence\n10. **Budget & Resources** — Investment and team requirements\n11. **Risk Assessment** — Potential challenges and contingency plans\n12. **Success Criteria** — What "good" looks like`,
        ctx
      );
    },
  });
}
