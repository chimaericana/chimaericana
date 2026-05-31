# Projex Communication Bots + Agents

Lightweight Discord and Mattermost bots with **AI agent profiles** for intelligent message routing and specialized responses.

## Architecture

```
┌─────────────────────────────────────────────────┐
│                    Discord                       │
│  /nexus /press /echo /shield /signal @mention    │
└────────────────────┬────────────────────────────┘
                     ↓
            ┌────────────────┐
            │  discord_bot.py │ ← Agent-aware slash commands
            └────────┬───────┘
                     ↓
            ┌────────────────┐
            │  agent_router.py│ ← Routes to correct agent
            └────────┬───────┘
                     ↓
            ┌────────────────┐     ┌──────────────────┐
            │  agent_queue    │────→│  Profile Manager │
            │  .jsonl         │     │  profiles/comm/  │
            └────────┬───────┘     └──────────────────┘
                     ↓
            ┌────────────────┐
            │  agent_queue_   │ ← Dispatches to Pi agent
            │  processor.py   │
            └────────┬───────┘
                     ↓
            ┌────────────────┐
            │  bot_bridge.py  │ ← Routes to Discord/MM
            └────────────────┘
```

## Quick Start

### 1. Create Bot Tokens

**Discord:**
1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create New Application → "Projex Bot"
3. Go to "Bot" → Reset Token → Copy it
4. Enable **Message Content Intent** under Privileged Gateway Intents
5. Invite to your server using OAuth2 → URL Generator → `bot` + `applications.commands` scopes

### 2. Configure

Edit `config.json`:
```json
{
  "discord": {
    "token": "your-bot-token",
    "channels": {
      "alerts": "channel-id-here",
      "general": "channel-id-here"
    },
    "agent_channels": {
      "nexus": "channel-id",
      "press": "channel-id",
      "echo": "channel-id",
      "shield": "channel-id",
      "signal": "channel-id"
    }
  },
  "agents": {
    "enabled": true,
    "auto_route": true
  }
}
```

### 3. Run

```bash
# Start everything (bots + agent queue processor)
bash automations/comm/bot_manager.sh start

# Check status
bash automations/comm/bot_manager.sh status

# View agent profiles
bash automations/comm/bot_manager.sh agents

# Process pending agent queue
bash automations/comm/bot_manager.sh queue
```

## Agent Profiles

Five specialized agents with isolated memory, personality, and tools:

| Agent | Role | Slash Command | Triggers |
|-------|------|---------------|----------|
| 🎯 **Nexus** | Comm Coordinator | `/nexus <msg>` | route, broadcast, coordinate |
| 📰 **Press** | PR Specialist | `/press <brief>` | press release, pitch, messaging |
| 📣 **Echo** | Social Media Manager | `/echo <req>` | social, schedule, engagement |
| 🛡️ **Shield** | Crisis Comms | `/shield <sit>` | crisis, breach, incident |
| 📡 **Signal** | Media Relations | `/signal <task>` | journalist, coverage, media |

## Discord Commands

### System Commands
| Command | Description |
|---------|-------------|
| `/status` | System health with agent invocations |
| `/agents` | Show agent team roster |
| `/agent_status` | Agent memory & model config |
| `/report` | Request system report |
| `/help` | Show all commands |

### Agent Commands
| Command | Description |
|---------|-------------|
| `/nexus <message>` | Route messages, coordinate agents |
| `/press <briefing>` | Draft press releases, pitches, key messages |
| `/echo <request>` | Create social content, schedule posts |
| `/shield <situation>` | Crisis detection, holding statements |
| `/signal <task>` | Media lists, coverage analysis, journalist outreach |

### Natural Language
Just mention the bot with a task — it auto-routes to the right agent:
- "draft a press release for our launch" → 📰 Press
- "schedule a tweet about our funding" → 📣 Echo
- "we have a data breach" → 🛡️ Shield
- "find journalists covering AI" → 📡 Signal
- "route this update to everyone" → 🎯 Nexus

## Bot Manager Commands

```bash
bash automations/comm/bot_manager.sh start     # Start all services
bash automations/comm/bot_manager.sh stop      # Stop all services
bash automations/comm/bot_manager.sh restart   # Restart all
bash automations/comm/bot_manager.sh status    # Service + agent status
bash automations/comm/bot_manager.sh agents    # Agent profile tree
bash automations/comm/bot_manager.sh queue     # Process agent queue
bash automations/comm/bot_manager.sh logs 100  # Last 100 log lines
```

## Agent Queue Flow

When a Discord message hits an agent:
1. **Bot receives** message via slash command or mention
2. **Router matches** message content to agent profile
3. **Context built** with system prompt, personality, tools, memory path
4. **Queue written** to `agent_queue.jsonl`
5. **Queue processor** picks up and creates prompt package
6. **Prompt package** saved to `agent_prompts/` for Pi agent
7. **Pi agent** processes with full context
8. **Response** routed back to Discord channel

## Memory

Each agent maintains isolated memory:

| Agent | Entries | Retention | Tracks |
|-------|---------|-----------|--------|
| Nexus | 500 | 60 days | Routing decisions, patterns, escalations |
| Press | 500 | 90 days | Releases, coverage, messaging |
| Echo | 1000 | 90 days | Posts, engagement, trends |
| Shield | 200 | 365 days | Incidents, responses, lessons |
| Signal | 1000 | 365 days | Journalists, pitches, coverage |

## Files

| File | Purpose |
|------|---------|
| `discord_bot.py` | Agent-enabled Discord bot |
| `agent_router.py` | Message → Agent routing |
| `agent_queue_processor.py` | Queue dispatch to Pi agents |
| `bot_bridge.py` | Cross-platform message router |
| `bot_manager.sh` | Service management |
| `health_check.py` | Bot health monitoring |
| `config.json` | Bot + agent configuration |
| `profiles/comm/` | Agent profiles (separate directory) |

## Memory Footprint

| Component | RAM |
|-----------|-----|
| Discord Bot | ~5 MB |
| Agent Router | ~3 MB |
| Queue Processor | ~2 MB |
| **Total** | **~10 MB** |
