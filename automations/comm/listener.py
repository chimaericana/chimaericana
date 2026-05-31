#!/usr/bin/env python3
"""
Lightweight Discord Listener — Minimal process that watches for @Goode mentions.
When someone mentions the bot, it triggers the wake script to start the full agent bot.
Memory footprint: ~2 MB (vs ~35 MB for full bot with agents).
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import discord

logging.basicConfig(
    level=logging.WARNING,  # Minimal logging
    format='%(asctime)s [LISTENER] %(levelname)s: %(message)s'
)
logger = logging.getLogger('projex.listener')

PROJEX_ROOT = Path(__file__).parent.parent.parent
CONFIG_PATH = PROJEX_ROOT / "automations" / "comm" / "config.json"
WAKE_SCRIPT = PROJEX_ROOT / "automations" / "comm" / "wake.sh"
PID_FILE = PROJEX_ROOT / "automations" / "comm" / ".pids" / "listener.pid"
WAKE_QUEUE = PROJEX_ROOT / "automations" / "comm" / "wake_queue.jsonl"

BOT_WAKING = False  # Flag to prevent multiple wake triggers


def is_bot_running():
    """Check if the full bot is already running."""
    try:
        result = subprocess.run(
            ['pgrep', '-f', 'discord_bot.py'],
            capture_output=True, text=True, timeout=5
        )
        return result.returncode == 0
    except Exception:
        return False


def trigger_wake():
    """Trigger the wake script to start the full bot."""
    global BOT_WAKING
    if BOT_WAKING:
        return False

    BOT_WAKING = True
    logger.info("Triggering wake script...")

    try:
        subprocess.Popen(
            ['bash', str(WAKE_SCRIPT)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
        logger.info("Wake script triggered")
        return True
    except Exception as e:
        logger.error(f"Failed to trigger wake: {e}")
        return False


def queue_message(user: str, channel: str, content: str):
    """Queue the triggering message for the full bot to handle."""
    entry = {
        'trigger': True,
        'user': user,
        'channel': channel,
        'content': content[:500],
        'timestamp': datetime.now(timezone.utc).isoformat()
    }
    try:
        with open(WAKE_QUEUE, 'a') as f:
            f.write(json.dumps(entry) + '\n')
    except Exception as e:
        logger.error(f"Failed to queue message: {e}")


class WakeListener(discord.Client):
    """Minimal Discord client that only watches for bot mentions."""

    def __init__(self, token: str):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        super().__init__(intents=intents)
        self.token = token
        self.wake_triggered = False

    async def on_ready(self):
        logger.info(f"Listener active as {self.user}")
        # Write PID
        with open(PID_FILE, 'w') as f:
            f.write(str(os.getpid()))

    async def on_message(self, message):
        if message.author == self.user:
            return

        # Check if bot is mentioned
        if self.user.mentioned_in(message):
            content = message.content.replace(self.user.mention, '').strip()

            if is_bot_running():
                logger.info(f"Bot already running, ignoring mention from {message.author}")
                return

            logger.info(f"Mention detected: {message.author} in {message.channel}")
            queue_message(str(message.author), str(message.channel), content or "(mention only)")

            if trigger_wake():
                # Send a quick acknowledgment
                try:
                    await message.channel.send(
                        "⏳ **Goode is waking up...** Give me ~10 seconds to fully start, then try your command again."
                    )
                except Exception:
                    pass
                logger.info("Wake triggered, listener will exit when bot starts")

                # Wait for bot to start, then exit (bot takes over)
                await asyncio.sleep(15)

                # Check if bot is running now
                if is_bot_running():
                    logger.info("Full bot is running, listener shutting down")
                    await self.close()
                else:
                    logger.warning("Bot didn't start, listener staying alive for retry")
                    BOT_WAKING = False


def load_config() -> str:
    with open(CONFIG_PATH) as f:
        config = json.load(f)
    return config.get("discord", {}).get("token", "")


async def main():
    token = load_config()
    if not token or token == "YOUR_DISCORD_BOT_TOKEN_HERE":
        logger.error("No token configured")
        sys.exit(1)

    listener = WakeListener(token)
    logger.info("Starting lightweight listener...")
    await listener.start(token)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Listener stopped")
    except Exception as e:
        logger.error(f"Fatal: {e}")
        sys.exit(1)
