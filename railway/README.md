# ⚡ Athena Discord Bot — Railway Deployment

Agent-enabled Discord communication hub. Routes messages to specialized AI agents via OpenRouter.

## Deploy to Railway

1. Push this repo to GitHub (if not already)
2. In Railway: **New Project → Deploy from GitHub repo**
3. Set the **root directory** to `railway/`
4. Add environment variables:
   - `DISCORD_BOT_TOKEN` — Your Discord bot token
   - `OPENROUTER_API_KEY` — Your OpenRouter API key
   - `DISCORD_GUILD_ID` — (optional) Guild ID for fast slash command sync
5. Update `config.json` with your Discord channel IDs
6. Deploy!

## Agents

| Agent | ID | Role | Emoji |
|-------|----|------|-------|
| Metis | `nexus` | Communications Coordinator | 🎯 |
| Calliope | `press` | PR Specialist | 📰 |
| Clio | `echo` | Social Media Manager | 📣 |
| Pallas | `shield` | Crisis Communications | 🛡️ |
| Iris | `signal` | Media Relations | 📡 |

## Commands

- `/status` — System health
- `/agents` — List available agents
- `/help` — Show all commands
- `/nexus <message>` — Route & coordinate
- `/press <briefing>` — Draft PR content
- `/echo <briefing>` — Social media tasks
- `/shield <situation>` — Crisis response
- `/signal <task>` — Media relations

Or just **@mention** the bot in any channel!
