#!/usr/bin/env python3
"""
Athena Discord Bot — Agent-Enabled Communication Hub
Cloud-deployable version (Railway/Render) using OpenRouter API.

Environment variables:
    DISCORD_BOT_TOKEN     — Discord bot token
    OPENROUTER_API_KEY    — OpenRouter API key
    DISCORD_GUILD_ID      — (optional) Guild ID for faster command sync
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import discord
from discord import app_commands

from agent_engine import (
    AGENT_REGISTRY,
    call_agent,
    get_branding,
    route_message,
)

# ─── Logging ─────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [BOT] %(levelname)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("athena.discord")

# ─── Config ──────────────────────────────────────────────────────────────────

CONFIG_PATH = Path(__file__).parent / "config.json"


def load_config() -> dict:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return json.load(f)
    return {}


CONFIG = load_config()

# ─── Bot ─────────────────────────────────────────────────────────────────────


class AthenaBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.members = True
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self._setup_commands()
        self.health_status = "healthy"
        self.uptime = datetime.now(timezone.utc)
        self.message_count = 0
        self.agent_invocations = 0
        self.api_key = os.environ.get("OPENROUTER_API_KEY", "")
        self.guild_id = os.environ.get("DISCORD_GUILD_ID", "")

    # ── Slash Commands ────────────────────────────────────────────────────

    def _setup_commands(self):
        @self.tree.command(name="status", description="Check system status")
        async def status_cmd(interaction: discord.Interaction):
            uptime = datetime.now(timezone.utc) - self.uptime
            embed = discord.Embed(
                title="⚡ Athena System Status",
                color=discord.Color.green() if self.health_status == "healthy" else discord.Color.red(),
            )
            embed.add_field(name="Status", value=self.health_status.capitalize(), inline=True)
            embed.add_field(name="Messages Sent", value=str(self.message_count), inline=True)
            embed.add_field(name="Agent Invocations", value=str(self.agent_invocations), inline=True)
            embed.add_field(name="Uptime", value=str(uptime).split(".")[0], inline=True)
            embed.set_footer(text=f"Checked: {datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}")
            await interaction.response.send_message(embed=embed)

        @self.tree.command(name="agents", description="List available agents")
        async def agents_cmd(interaction: discord.Interaction):
            embed = discord.Embed(
                title="🤖 Athena Agent Team",
                description="Each agent has a specialized role. Use their trigger words or direct commands.",
                color=0x2ECC71,
            )
            for agent_id, info in AGENT_REGISTRY.items():
                embed.add_field(
                    name=f"{info['emoji']} {info['name']}",
                    value=f"Command: `/{agent_id} <message>`",
                    inline=False,
                )
            await interaction.response.send_message(embed=embed)

        @self.tree.command(name="help", description="Show available commands")
        async def help_cmd(interaction: discord.Interaction):
            embed = discord.Embed(
                title="⚡ Athena Communication Bot",
                description=(
                    "**System Commands:**\n"
                    "`/status` — System health\n"
                    "`/agents` — Agent team roster\n"
                    "`/help` — This message\n\n"
                    "**Agent Commands:**\n"
                    "`/nexus <message>` — Route & coordinate\n"
                    "`/press <briefing>` — Draft PR content\n"
                    "`/echo <briefing>` — Social media tasks\n"
                    "`/shield <situation>` — Crisis response\n"
                    "`/signal <task>` — Media relations\n\n"
                    "**Or just mention me!**"
                ),
                color=discord.Color.blue(),
            )
            await interaction.response.send_message(embed=embed)

        # Agent slash commands
        agent_descriptions = {
            "nexus": "🎯 Send a message to Metis (Communications Coordinator)",
            "press": "📰 Send a briefing to Calliope (PR Specialist)",
            "echo": "📣 Send a request to Clio (Social Media Manager)",
            "shield": "🛡️ Report an incident to Pallas (Crisis Comms)",
            "signal": "📡 Send a task to Iris (Media Relations)",
        }

        for agent_id, desc in agent_descriptions.items():

            def make_handler(aid):
                async def handler(interaction: discord.Interaction, message: str):
                    await self._handle_agent_command(interaction, aid, message)
                return handler

            self.tree.command(name=agent_id, description=desc)(make_handler(agent_id))

    async def _handle_agent_command(self, interaction: discord.Interaction, agent_id: str, message: str):
        """Handle an agent slash command."""
        if not self.api_key:
            await interaction.response.send_message(
                "⚠️ OpenRouter API key not configured.",
                ephemeral=True,
            )
            return

        branding = get_branding(agent_id)
        self.agent_invocations += 1

        await interaction.response.send_message(
            f"{branding['emoji']} **{branding['name']}** received your message. Thinking..."
        )

        result = await call_agent(
            agent_id=agent_id,
            user_message=message,
            api_key=self.api_key,
            config=CONFIG,
            timeout=90,
        )

        await self._send_agent_result(interaction, result, followup=True)

    async def _send_agent_result(self, interaction, result: dict, followup: bool = False):
        """Send agent result to Discord channel."""
        branding = result["branding"]
        output = result.get("output", "")
        error = result.get("error")
        model = result.get("model", "unknown")
        tried = result.get("tried", [])

        if output:
            chunks = [output[i : i + 1900] for i in range(0, len(output), 1900)]
            for i, chunk in enumerate(chunks):
                embed = discord.Embed(description=chunk, color=branding["color"])
                embed.set_footer(text=f"{branding['footer']} · Model: {model}")
                if followup:
                    await interaction.followup.send(embed=embed)
                else:
                    await interaction.channel.send(embed=embed)
                if i == 0 and len(chunks) > 1:
                    msg = f"_(Response: {len(chunks)} parts)_"
                    if followup:
                        await interaction.followup.send(msg)
                    else:
                        await interaction.channel.send(msg)

            logger.info(f"Agent {result['agent_id']} responded: {len(output)} chars via {model}")
        else:
            tried_str = ", ".join(tried) if tried else "none"
            err_msg = (
                f"⚠️ **{result['agent_name']}** couldn't respond.\n"
                f"Tried models: `{tried_str}`\n"
                f"Error: `{str(error)[:200]}`"
            )
            if followup:
                await interaction.followup.send(err_msg)
            else:
                await interaction.channel.send(err_msg)
            logger.error(f"Agent {result['agent_id']} failed. Tried: {tried_str}. Error: {error}")

    # ── Events ─────────────────────────────────────────────────────────────

    async def setup_hook(self):
        guild_id = self.guild_id
        if guild_id:
            guild = discord.Object(id=int(guild_id))
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            logger.info(f"Slash commands synced to guild {guild_id}")
        else:
            await self.tree.sync()
            logger.info("Slash commands synced globally (can take up to 1 hour)")

    async def on_ready(self):
        logger.info(f"Connected as {self.user} (ID: {self.user.id})")
        logger.info(f"Guilds: {len(self.guilds)}")

        # Announce to general channel
        channels_config = CONFIG.get("discord", {}).get("channels", {})
        general_id = channels_config.get("general")
        if general_id and general_id not in ("GENERAL_CHANNEL_ID", ""):
            try:
                channel = self.get_channel(int(general_id))
                if channel:
                    agents_list = ", ".join(
                        f"{info['emoji']} {info['name']}" for info in AGENT_REGISTRY.values()
                    )
                    await channel.send(
                        f"⚡ **Athena online** — Agent-enabled communication bot connected.\n"
                        f"Agents: {agents_list}"
                    )
            except (ValueError, TypeError):
                pass

    async def on_message(self, message):
        if message.author == self.user:
            return

        if not self.user.mentioned_in(message):
            return

        if not self.api_key:
            await message.channel.send("⚠️ OpenRouter API key not configured.")
            return

        content = message.content.replace(self.user.mention, "").strip()
        if not content or content.lower() in ("hi", "hello", "hey", "ping"):
            agents_list = "\n".join(
                f"• `/{aid}` — {info['name']}" for aid, info in AGENT_REGISTRY.items()
            )
            await message.channel.send(
                f"⚡ I'm here! Use `/help` for commands, or talk to an agent:\n{agents_list}"
            )
            return

        # Route to agent
        agent_id = route_message(content)
        branding = get_branding(agent_id)
        self.agent_invocations += 1

        thinking_msg = await message.channel.send(
            f"{branding['emoji']} **{branding['name']}** is thinking..."
        )

        # Remove trigger prefix for cleaner agent input
        user_message = content
        for trigger in ["nexus", "press", "echo", "shield", "signal", "/", "@"]:
            if user_message.lower().startswith(trigger):
                user_message = user_message[len(trigger):].strip()
                break

        result = await call_agent(
            agent_id=agent_id,
            user_message=user_message or content,
            api_key=self.api_key,
            config=CONFIG,
            timeout=90,
        )

        try:
            await thinking_msg.delete()
        except Exception:
            pass

        if result.get("output"):
            output = result["output"]
            model = result.get("model", "unknown")
            chunks = [output[i : i + 1900] for i in range(0, len(output), 1900)]
            for i, chunk in enumerate(chunks):
                embed = discord.Embed(description=chunk, color=branding["color"])
                embed.set_footer(text=f"{branding['footer']} · Model: {model}")
                await message.channel.send(embed=embed)
                if i == 0 and len(chunks) > 1:
                    await message.channel.send(f"_(Response: {len(chunks)} parts)_")
        else:
            tried_str = ", ".join(result.get("tried", []))
            await message.channel.send(
                f"⚠️ **{result['agent_name']}** couldn't respond.\n"
                f"Tried: `{tried_str}`\n"
                f"Error: `{str(result.get('error', 'unknown'))[:200]}`"
            )

    # ── Notification API ───────────────────────────────────────────────────

    async def send_notification(self, category: str, title: str, body: str, urgency: str = "info"):
        """Send a notification to the configured channel."""
        channels_config = CONFIG.get("discord", {}).get("channels", {})
        channel_id = channels_config.get(category, channels_config.get("general"))
        if not channel_id or channel_id in ("GENERAL_CHANNEL_ID", ""):
            logger.warning(f"No channel configured for: {category}")
            return

        try:
            channel = self.get_channel(int(channel_id))
            if not channel:
                channel = await self.fetch_channel(int(channel_id))

            color_map = {
                "urgent": discord.Color.red(),
                "alert": discord.Color.orange(),
                "info": discord.Color.blue(),
                "digest": discord.Color.green(),
                "critical": discord.Color.dark_red(),
                "warning": discord.Color.gold(),
            }
            emoji_map = {
                "urgent": "🚨",
                "alert": "⚠️",
                "info": "ℹ️",
                "digest": "📊",
                "critical": "🔴",
                "warning": "🟡",
            }

            embed = discord.Embed(
                title=f"{emoji_map.get(urgency, '📢')} {title}",
                description=body,
                color=color_map.get(urgency, discord.Color.blue()),
                timestamp=datetime.now(timezone.utc),
            )
            embed.set_footer(text=f"{category} · {urgency}")

            await channel.send(embed=embed)
            self.message_count += 1
            logger.info(f"Notification → {category}: {title}")

        except Exception as e:
            logger.error(f"Failed to send notification: {e}")


# ─── Main ────────────────────────────────────────────────────────────────────


async def main():
    token = os.environ.get("DISCORD_BOT_TOKEN")
    api_key = os.environ.get("OPENROUTER_API_KEY")

    if not token:
        logger.error("DISCORD_BOT_TOKEN not set")
        sys.exit(1)

    if not api_key:
        logger.error("OPENROUTER_API_KEY not set")
        sys.exit(1)

    bot = AthenaBot()
    logger.info("Starting Athena bot...")

    try:
        await bot.start(token)
    except KeyboardInterrupt:
        logger.info("Stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
