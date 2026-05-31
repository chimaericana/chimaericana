#!/usr/bin/env python3
"""
Discord Bot for Projex Communication Hub — Agent-Enabled
Integrates with the Agent Profile system for intelligent message routing.
Memory footprint: ~5 MB + agent overhead
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

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [DISCORD] %(levelname)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('projex.discord')

PROJEX_ROOT = Path(__file__).parent.parent.parent
CONFIG_PATH = PROJEX_ROOT / "automations" / "comm" / "config.json"
AGENT_ROUTER_PATH = PROJEX_ROOT / "automations" / "comm" / "agent_router.py"
PI_SETTINGS_PATH = Path.home() / ".pi" / "agent" / "settings.json"

# Import agent router
sys.path.insert(0, str(PROJEX_ROOT / "automations" / "comm"))
from agent_router import AgentRouter
from pi_subagent import run_subagent, discover_agents


class ProjexDiscordBot(discord.Client):
    """Agent-enabled Discord bot for Projex notifications and agent interactions."""

    def __init__(self, config: dict):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.members = True
        super().__init__(intents=intents)
        self.config = config.get("discord", {})
        self.channels = self.config.get("channels", {})
        self.tree = app_commands.CommandTree(self)
        self.router = None  # Initialized in setup_hook
        self._setup_commands()
        self._queue_file = Path(__file__).parent / "agent_queue.jsonl"
        self._queue_lock = asyncio.Lock()
        self._processed_entries = set()
        self._queue_task = None
        self.health_status = "healthy"
        self.uptime = datetime.now(timezone.utc)
        self.message_count = 0
        self.agent_invocations = 0

    def _setup_commands(self):
        """Register slash commands with agent integration."""

        # ─── System Commands ───

        @self.tree.command(name="status", description="Check Projex system status")
        async def status(interaction: discord.Interaction):
            embed = discord.Embed(
                title="🤖 Projex System Status",
                color=discord.Color.green() if self.health_status == "healthy" else discord.Color.red()
            )
            embed.add_field(name="Status", value=self.health_status.capitalize(), inline=True)
            embed.add_field(name="Messages Sent", value=str(self.message_count), inline=True)
            embed.add_field(name="Agent Invocations", value=str(self.agent_invocations), inline=True)
            uptime = datetime.now(timezone.utc) - self.uptime
            embed.add_field(name="Uptime", value=str(uptime).split('.')[0], inline=True)
            embed.set_footer(text=f"Last check: {datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}")
            await interaction.response.send_message(embed=embed)

        @self.tree.command(name="agents", description="List all available Projex agents")
        async def agents(interaction: discord.Interaction):
            if not self.router:
                await interaction.response.send_message("⚠️ Agent system not initialized", ephemeral=True)
                return

            embed_data = self.router.get_agent_list_embed()
            embed = discord.Embed.from_dict(embed_data)
            await interaction.response.send_message(embed=embed)

        @self.tree.command(name="agent_status", description="Show agent profiles and memory status")
        async def agent_status(interaction: discord.Interaction):
            if not self.router:
                await interaction.response.send_message("⚠️ Agent system not initialized", ephemeral=True)
                return

            embed_data = self.router.get_agent_status_embed()
            embed = discord.Embed.from_dict(embed_data)
            await interaction.response.send_message(embed=embed)

        @self.tree.command(name="report", description="Request latest Projex report")
        async def report(interaction: discord.Interaction):
            await interaction.response.send_message(
                "📋 Report requested. The Projex agent will compile and post it shortly.",
                ephemeral=True
            )
            bridge_file = Path(__file__).parent / "bridge_queue.jsonl"
            with open(bridge_file, "a") as f:
                f.write(json.dumps({
                    "action": "generate_report",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "requested_by": str(interaction.user.id)
                }) + "\n")

        @self.tree.command(name="help", description="Show available Projex commands")
        async def help(interaction: discord.Interaction):
            embed = discord.Embed(
                title="📡 Projex Communication Bot",
                description="**System Commands:**\n"
                            "`/status` — System health\n"
                            "`/agents` — Agent team roster\n"
                            "`/agent_status` — Agent memory & config\n"
                            "`/report` — Request system report\n"
                            "`/help` — This message\n\n"
                            "**Agent Commands:**\n"
                            "`/nexus <message>` — Route & coordinate\n"
                            "`/press <briefing>` — Draft PR content\n"
                            "`/echo <briefing>` — Social media tasks\n"
                            "`/shield <situation>` — Crisis response\n"
                            "`/signal <task>` — Media relations\n\n"
                            "**Or just mention me!**",
                color=discord.Color.blue()
            )
            embed.set_footer(text="Projex AI Agent Platform")
            await interaction.response.send_message(embed=embed)

        # ─── Agent Commands ───

        @self.tree.command(name="nexus", description="🎯 Send a message to Nexus (Communications Coordinator)")
        @app_commands.describe(message="Message for Nexus to route or act on")
        async def nexus_cmd(interaction: discord.Interaction, message: str):
            await self._handle_agent_command(interaction, 'nexus', message)

        @self.tree.command(name="press", description="📰 Send a briefing to Press (PR Specialist)")
        @app_commands.describe(briefing="PR briefing notes or request")
        async def press_cmd(interaction: discord.Interaction, briefing: str):
            await self._handle_agent_command(interaction, 'press', briefing)

        @self.tree.command(name="echo", description="📣 Send a request to Echo (Social Media Manager)")
        @app_commands.describe(request="Social media task or content request")
        async def echo_cmd(interaction: discord.Interaction, request: str):
            await self._handle_agent_command(interaction, 'echo', request)

        @self.tree.command(name="shield", description="🛡️ Report an incident to Shield (Crisis Comms)")
        @app_commands.describe(situation="Describe the situation or incident")
        async def shield_cmd(interaction: discord.Interaction, situation: str):
            await self._handle_agent_command(interaction, 'shield', situation)

        @self.tree.command(name="signal", description="📡 Send a task to Signal (Media Relations)")
        @app_commands.describe(task="Media relations task or request")
        async def signal_cmd(interaction: discord.Interaction, task: str):
            await self._handle_agent_command(interaction, 'signal', task)

    async def _handle_agent_command(self, interaction: discord.Interaction, agent_id: str, message: str):
        """Handle a slash command directed at a specific agent."""
        if not self.router:
            await interaction.response.send_message("⚠️ Agent system not initialized", ephemeral=True)
            return

        self.agent_invocations += 1

        # Build context
        context = self.router.build_spawn_context(
            agent_id, message,
            user_id=str(interaction.user.id),
            channel=str(interaction.channel)
        )

        # Log interaction
        self.router.log_interaction(agent_id, str(interaction.user.id), message)

        # Acknowledge immediately
        branding = self.router.get_branding(agent_id)
        await interaction.response.send_message(
            f"{branding['emoji']} **{context['agent']['name']}** received your message. "
            f"Processing via profile system...\n\n"
            f"📋 Context built: `{context['processing'].get('model', 'N/A')}`\n"
            f"💾 Memory path: `{context['memory_path']}`\n\n"
            f"_Full agent processing requires Pi agent invocation._",
            ephemeral=False
        )

        # Save context to queue for background Pi agent processing
        with open(self._queue_file, "a") as f:
            f.write(json.dumps({
                'agent_id': agent_id,
                'message': message,  # Original user message for direct task use
                'context': context,
                'channel_id': interaction.channel_id,  # Numeric ID for channel lookup
                'discord_user': str(interaction.user),
                'discord_user_id': str(interaction.user.id),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }) + '\n')

        logger.info(f"Agent command queued: {agent_id} ← {message[:100]}... [channel {interaction.channel_id}]")

    async def setup_hook(self):
        """Initialize agent router and sync commands."""
        try:
            self.router = AgentRouter()
            logger.info("Agent router initialized")
            for agent_id in self.router._agent_cache:
                logger.info(f"  → {agent_id} loaded")
        except Exception as e:
            logger.error(f"Failed to initialize agent router: {e}")
            self.router = None

        await self.tree.sync()
        logger.info("Slash commands synced")

        # Start queue processor background task
        self._queue_task = asyncio.create_task(self._queue_processor())
        logger.info("Queue processor background task started")

    async def on_ready(self):
        logger.info(f"Discord bot connected as {self.user}")
        logger.info(f"Guilds: {len(self.guilds)}")
        logger.info(f"Agent router: {'✅ Active' if self.router else '❌ Inactive'}")

        general_id = self.channels.get("general")
        if general_id and general_id not in ("GENERAL_CHANNEL_ID", ""):
            try:
                channel = self.get_channel(int(general_id))
                if channel:
                    agents_list = ""
                    if self.router:
                        agents_list = "\nAvailable agents: " + ", ".join(
                            f"{self.router.get_branding(a)['emoji']} {self.router._agent_cache[a]['name']}"
                            for a in self.router._agent_cache
                        )
                    await channel.send(
                        f"🟢 **Projex online** — Agent-enabled communication bot connected.{agents_list}"
                    )
            except (ValueError, TypeError):
                pass  # Placeholder channel ID, skip startup message

    async def on_message(self, message):
        """Handle messages — route to agents based on content."""
        if message.author == self.user:
            return

        # Check if bot is mentioned
        if self.user.mentioned_in(message):
            content = message.content.replace(self.user.mention, '').strip()
            if not content or content.lower() in ('hi', 'hello', 'hey', 'ping'):
                await message.channel.send(
                    "🤖 I'm here! Use `/help` for commands, or talk to an agent directly:\n"
                    "• `/nexus <message>` — Route & coordinate\n"
                    "• `/press <briefing>` — Draft PR content\n"
                    "• `/echo <request>` — Social media tasks\n"
                    "• `/shield <situation>` — Crisis response\n"
                    "• `/signal <task>` — Media relations"
                )
                return

            # Route the message content through agent router
            if self.router:
                result = self.router.route(content, str(message.author.id), str(message.channel))
                branding = result['branding']
                agent_id = result['agent_id']
                self.agent_invocations += 1

                # Log interaction
                self.router.log_interaction(agent_id, str(message.author.id), content)

                # Send thinking indicator
                thinking_msg = await message.channel.send(
                    f"{branding['emoji']} **{result['agent_name']}** is thinking..."
                )

                # Spawn Pi subagent
                try:
                    sub_result = await run_subagent(
                        agent_id,
                        content,
                        cwd=str(PROJEX_ROOT),
                        timeout=90,
                    )

                    # Delete thinking message
                    try:
                        await thinking_msg.delete()
                    except Exception:
                        pass

                    if sub_result['exit_code'] == 0 and sub_result['output']:
                        output = sub_result['output']
                        # Split long responses into chunks (Discord 2000 char limit)
                        chunks = [output[i:i+1900] for i in range(0, len(output), 1900)]
                        for i, chunk in enumerate(chunks):
                            embed = discord.Embed(
                                description=chunk,
                                color=branding['color'],
                            )
                            embed.set_footer(text=f"{branding['footer']} · Model: {sub_result.get('model', '')}")
                            await message.channel.send(embed=embed)
                            if i == 0 and len(chunks) > 1:
                                await message.channel.send(f"_({len(chunks)} messages total)_")

                        logger.info(f"Subagent response sent: {agent_id} → {len(output)} chars")
                    else:
                        error_msg = sub_result.get('output', 'No output') or sub_result.get('stderr', 'Unknown error')
                        await message.channel.send(
                            f"⚠️ **{result['agent_name']}** encountered an issue:\n```{error_msg[:500]}```"
                        )
                        logger.error(f"Subagent error: {agent_id}: {error_msg[:200]}")

                except Exception as e:
                    try:
                        await thinking_msg.delete()
                    except Exception:
                        pass
                    await message.channel.send(f"⚠️ Processing failed: {str(e)[:200]}")
                    logger.error(f"Subagent spawn failed: {e}")

    async def send_notification(self, category: str, title: str, body: str, urgency: str = "info"):
        """Send a notification to the appropriate channel."""
        channel_id = self.channels.get(category, self.channels.get("general"))
        if not channel_id:
            logger.warning(f"No channel configured for category: {category}")
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
            }

            embed = discord.Embed(
                title=f"{self._get_emoji(urgency)} {title}",
                description=body,
                color=color_map.get(urgency, discord.Color.blue()),
                timestamp=datetime.now(timezone.utc)
            )
            embed.set_footer(text=f"Category: {category} · Urgency: {urgency}")

            await channel.send(embed=embed)
            self.message_count += 1
            logger.info(f"Notification sent to {category} channel: {title}")

        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
            raise

    def _get_emoji(self, urgency: str) -> str:
        emoji_map = {
            "urgent": "🚨",
            "alert": "⚠️",
            "info": "ℹ️",
            "digest": "📊",
            "critical": "🔴",
            "warning": "🟡",
        }
        return emoji_map.get(urgency, "📢")

    def update_health(self, status: str):
        self.health_status = status

    # ─── Model Rotation ───

    def _load_pi_settings(self) -> dict:
        """Load full settings from ~/.pi/agent/settings.json."""
        try:
            with open(PI_SETTINGS_PATH) as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load Pi settings: {e}")
            return {}

    def _get_model_fallback_chain(self, agent_model: str) -> list:
        """Build ordered model fallback chain respecting settings.json hierarchy.

        Priority:
          1. settings.json defaultProvider/defaultModel (user's current preference)
          2. agent's hardcoded model
          3. remaining enabledModels in their configured order
        """
        settings = self._load_pi_settings()
        all_models = settings.get("enabledModels", [])

        if not all_models:
            return [agent_model] if agent_model else ["z-ai/glm-4.5-air:free"]

        default_provider = settings.get("defaultProvider", "")
        default_model = settings.get("defaultModel", "")
        settings_default = (
            f"{default_provider}/{default_model}"
            if default_provider and default_model
            else ""
        )

        ordered = []

        # 1. Settings default model first (user's configured preference gets priority)
        if settings_default and settings_default not in ordered:
            ordered.append(settings_default)

        # 2. Agent's hardcoded model
        if agent_model and agent_model not in ordered:
            ordered.append(agent_model)

        # 3. All remaining enabledModels in their configured order
        for m in all_models:
            if m not in ordered:
                ordered.append(m)

        logger.debug(f"Fallback chain ({len(ordered)} models): {ordered[:3]}...")
        return ordered

    # ─── Queue Processor ───

    async def _queue_processor(self):
        """Background task: polls the agent queue and dispatches to subagents."""
        logger.info("Queue processor loop started")
        while True:
            try:
                await self._process_queue()
            except Exception as e:
                logger.error(f"Queue processor error: {e}", exc_info=True)
            await asyncio.sleep(3)

    async def _process_queue(self):
        """Read and process all pending queue entries."""
        if not self._queue_file.exists():
            return

        async with self._queue_lock:
            # Read all entries atomically
            entries = []
            try:
                with open(self._queue_file, "r") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            entries.append(json.loads(line))
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Queue read error: {e}")
                return

            if not entries:
                return

            logger.info(f"Queue processor: {len(entries)} pending entries")

            # Process each entry
            for entry in entries:
                entry_key = f"{entry.get('timestamp', '')}:{entry.get('discord_user_id', '')}:{entry.get('agent_id', '')}"
                if entry_key in self._processed_entries:
                    continue

                await self._handle_queued_entry(entry)
                self._processed_entries.add(entry_key)
                # Keep set from growing unbounded
                if len(self._processed_entries) > 500:
                    self._processed_entries = set(list(self._processed_entries)[-200:])

            # Clear the queue file after processing
            with open(self._queue_file, "w") as f:
                pass

    async def _handle_queued_entry(self, entry: dict):
        """Process a single queued agent request: invoke pi directly, send response to Discord."""
        agent_id = entry.get('agent_id', 'nexus')
        message = entry.get('message', '')
        channel_id = entry.get('channel_id')
        user = entry.get('discord_user', 'Unknown')
        timestamp = entry.get('timestamp', '')

        if not message:
            logger.warning(f"Queue entry has no message: {entry}")
            return

        # Resolve channel
        channel = self.get_channel(int(channel_id)) if channel_id else None
        if not channel:
            try:
                channel = await self.fetch_channel(int(channel_id))
            except Exception as e:
                logger.error(f"Could not resolve channel {channel_id}: {e}")
                return

        branding = self.router.get_branding(agent_id) if self.router else {
            'emoji': '🤖', 'color': 0x3498db, 'footer': agent_id
        }

        logger.info(f"Processing queued entry: {agent_id} ← {message[:80]}... (channel {channel_id})")

        # Send thinking indicator
        thinking_msg = await channel.send(
            f"{branding['emoji']} **{agent_id}** is thinking..."
        )

        try:
            # Build pi command — use a temp file for the agent system prompt
            from pi_subagent import find_agent
            import subprocess

            agent = find_agent(agent_id)
            if not agent:
                await thinking_msg.delete()
                await channel.send(f"⚠️ Unknown agent: **{agent_id}**")
                return

            import tempfile
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".md", delete=False,
                prefix=f"pi-agent-{agent_id}-"
            ) as f:
                f.write(agent["system_prompt"])
                prompt_file = f.name

            try:
                # Get fallback chain: agent model first, then all models from settings.json
                agent_model = agent.get("model", "z-ai/glm-4.5-air:free")
                fallback_chain = self._get_model_fallback_chain(agent_model)
                
                output = ""
                model_used = ""
                error_detail = ""
                tried = []

                for model in fallback_chain:
                    tried.append(model)
                    args = [
                        "pi",
                        "--mode", "json",
                        "-p",
                        "--no-session",
                        "--model", model,
                        "--append-system-prompt", prompt_file,
                        message,
                    ]

                    logger.info(f"Trying model: {model} (attempt {len(tried)}/{len(fallback_chain)})")

                    try:
                        def _run_pi():
                            return subprocess.run(
                                args,
                                capture_output=True,
                                text=True,
                                cwd=str(PROJEX_ROOT),
                                timeout=90,
                            )

                        proc_result = await asyncio.get_event_loop().run_in_executor(
                            None, _run_pi
                        )

                        # Parse JSON-lines output
                        for line in proc_result.stdout.strip().split("\n"):
                            line = line.strip()
                            if not line:
                                continue
                            try:
                                event = json.loads(line)
                                # Detect 429 rate limit errors
                                if event.get("message", {}).get("stopReason") == "error":
                                    err_msg = event["message"].get("errorMessage", "")
                                    if "429" in err_msg or "rate limit" in err_msg.lower():
                                        logger.warning(f"Model {model} hit rate limit: {err_msg[:100]}")
                                        error_detail = err_msg
                                        break  # try next model
                                
                                if event.get("type") == "message_end" and event.get("message"):
                                    msg = event["message"]
                                    if msg.get("role") == "assistant":
                                        for part in msg.get("content", []):
                                            if part.get("type") == "text":
                                                output = part.get("text", "")
                                                break
                                    if msg.get("model"):
                                        model_used = msg["model"]
                                    if output:
                                        break
                            except json.JSONDecodeError:
                                pass

                        if output:
                            model_used = model
                            break  # success, stop trying

                    except subprocess.TimeoutExpired:
                        logger.warning(f"Model {model} timed out, trying next...")
                        continue

                # Delete thinking indicator
                try:
                    await thinking_msg.delete()
                except Exception:
                    pass

                if output:
                    # Split long responses (Discord 2000 char limit)
                    chunks = [output[i:i+1900] for i in range(0, len(output), 1900)]
                    for i, chunk in enumerate(chunks):
                        embed = discord.Embed(
                            description=chunk,
                            color=branding['color'],
                        )
                        embed.set_footer(
                            text=f"{branding['footer']} · Model: {model_used}"
                        )
                        await channel.send(embed=embed)
                        if i == 0 and len(chunks) > 1:
                            await channel.send(f"_({len(chunks)} messages total)_")

                    self.agent_invocations += 1
                    if self.router:
                        self.router.log_interaction(
                            agent_id, entry.get('discord_user_id', ''), message, output
                        )
                    logger.info(
                        f"Queued subagent response sent: {agent_id} → {len(output)} chars "
                        f"via {model_used} (channel {channel_id})"
                    )
                else:
                    # All models failed
                    tried_str = ", ".join(tried)
                    await channel.send(
                        f"⚠️ **{agent_id}** couldn't respond. All models failed.\n"
                        f"Tried: `{tried_str}`\n"
                        f"Last error: `{error_detail[:200]}`"
                    )
                    logger.error(
                        f"All models failed for {agent_id}. Tried: {tried_str}. Error: {error_detail[:200]}"
                    )

            finally:
                import os
                try:
                    os.unlink(prompt_file)
                except OSError:
                    pass

        except subprocess.TimeoutExpired:
            try:
                await thinking_msg.delete()
            except Exception:
                pass
            await channel.send(
                f"⏳ **{agent_id}** timed out while processing. Please try again."
            )
            logger.error(f"Subagent timed out for queued entry: {agent_id}")

        except Exception as e:
            try:
                await thinking_msg.delete()
            except Exception:
                pass
            await channel.send(f"⚠️ Processing failed: {str(e)[:200]}")
            logger.error(f"Subagent spawn failed for queued entry: {e}", exc_info=True)


def load_config() -> dict:
    with open(CONFIG_PATH) as f:
        return json.load(f)


async def main():
    config = load_config()
    token = config.get("discord", {}).get("token")

    if not token or token == "YOUR_DISCORD_BOT_TOKEN_HERE":
        logger.error("Discord token not configured. Update config.json with your bot token.")
        sys.exit(1)

    bot = ProjexDiscordBot(config)
    logger.info("Starting agent-enabled Discord bot...")
    await bot.start(token)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Discord bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
