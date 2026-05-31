# Aware — Proactive Life Engagement System

**Turn this assistant into your personal growth engine.**

Aware is a system that makes me (this assistant) proactively engage you with meaningful prompts, generate publishable content from your thoughts, notice patterns in your life, and help you continuously improve.

## How It Works

```
You engage with prompts ← → I generate content & insights
        ↓                           ↑
  Your responses stored       Patterns detected
        ↓                           ↑
  Processes triggered    →   Life improvements noticed
```

### Three Core Flows

#### 1. Prompt Flow (Proactive Engagement)
I check the prompt library and engage you at appropriate times:
- **/morning** — Start your day with intention
- **/evening** — Reflect on your day
- **/notice** — Share what you noticed
- **/spark** — Creative inspiration
- **/checkin** — Goal progress
- **/reflect** — Deep reflection
- **/process** — Set up a new process/automation
- **/publish** — Turn thoughts into publishable content

#### 2. Response Flow (Your Input → Output)
When you respond to a prompt:
1. Your response is saved to `journal/entries/` (dated, searchable)
2. I process it and generate corresponding output:
   - **/publish** → Ready-to-post social content in `content/social/`
   - **/process** → Automation scripts in `processes/`
   - **/reflect** → Insights stored in `journal/insights/`
   - **/notice** → Pattern data for analysis
3. Patterns are analyzed over time in `journal/patterns/`

#### 3. Notice Flow (Life Improvement)
I track patterns across your entries to notice:
- Recurring themes (what keeps coming up)
- Energy patterns (when you're most/least energized)
- Goal progress (forward or stuck)
- Improvement opportunities (repeated challenges)
- Wins and growth (what's working)

## Directory Structure

```
aware/
├── README.md                  # This file
├── prompts/                   # Prompt library
│   ├── morning.md             # Morning intention prompts
│   ├── evening.md             # Evening reflection prompts
│   ├── notice.md              # "What I noticed" prompts
│   ├── spark.md               # Creative inspiration prompts
│   ├── checkin.md             # Goal check-in prompts
│   ├── reflect.md             # Deep reflection prompts
│   ├── process.md             # Process/automation setup prompts
│   └── publish.md             # Content creation prompts
├── journal/
│   ├── entries/               # Dated journal entries (YYYY-MM-DD.md)
│   ├── patterns/              # Pattern analysis files
│   └── insights/              # Life insights and observations
├── content/
│   ├── social/                # Ready-to-publish social posts
│   ├── notes/                 # Personal notes and ideas
│   └── voice/                 # Voice note scripts
├── processes/                 # Generated process scripts
├── scheduler.json             # Prompt scheduling config
└── state.json                 # Current system state
```

## Commands

| Command | Description |
|---------|-------------|
| `/aware` | Show Aware system status and today's overview |
| `/aware morning` | Start morning reflection |
| `/aware evening` | Start evening reflection |
| `/aware notice <thing>` | Log something you noticed |
| `/aware publish <idea>` | Turn an idea into publishable content |
| `/aware process <goal>` | Set up a new process/automation |
| `/aware spark` | Get a creative prompt |
| `/aware checkin` | Goal progress check-in |
| `/aware reflect` | Deep reflection session |
| `/aware journal` | Browse your journal |
| `/aware patterns` | See what patterns I've noticed |
| `/aware insight` | Get a life insight based on your patterns |
| `/aware digest` | Get a daily/weekly digest |

## Getting Started

Just start using the commands above. I'll begin engaging you proactively based on:
- **Time of day** — Morning prompts in the AM, evening prompts later
- **Frequency** — Not too often, not too rarely
- **Context** — Based on what we've been discussing
- **Patterns** — When I notice something worth exploring

Try: `/aware spark` to get started right now.
