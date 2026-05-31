#!/usr/bin/env python3
"""
Athena Discord Notifier — Quick script to send messages to Discord.
Usage:
  python3 athena_notify.py "Hello from Athena!"
  python3 athena_notify.py --channel alerts "System notification"
  python3 athena_notify.py --ping "I need your help with something"
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

import discord

CONFIG_PATH = Path(__file__).parent / "config.json"


def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)


async def send_message(message: str, category: str = "general", ping_owner: bool = False):
    config = load_config()
    token_env = config.get("discord", {}).get("token_env", "DISCORD_BOT_TOKEN")
    token = os.environ.get(token_env)
    if not token:
        env_path = Path(__file__).parent / ".env"
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())
        token = os.environ.get(token_env)
    if not token or "YOUR_" in token:
        print("❌ Discord token not configured")
        sys.exit(1)

    channels = config.get("discord", {}).get("channels", {})
    owner_id = config.get("discord", {}).get("owner_id", "")

    channel_id = channels.get(category, channels.get("general"))

    intents = discord.Intents.default()
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        try:
            if channel_id and "YOUR_" not in str(channel_id):
                channel = await client.fetch_channel(int(channel_id))
                if ping_owner and owner_id:
                    msg = f"<@{owner_id}> ⚡ **Athena says:** {message}"
                else:
                    msg = f"⚡ **Athena says:** {message}"
                await channel.send(msg)
                print(f"✅ Message sent to #{category}")
            else:
                print(f"⚠️ No channel configured for category: {category}")
        except Exception as e:
            print(f"❌ Failed: {e}")
        finally:
            await client.close()

    await client.start(token)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Send a Discord notification from Athena")
    parser.add_argument("message", help="Message to send")
    parser.add_argument("--channel", "-c", default="general", help="Channel category (general/alerts/social/pr)")
    parser.add_argument("--ping", "-p", action="store_true", help="Ping the owner")
    args = parser.parse_args()

    asyncio.run(send_message(args.message, args.channel, args.ping))
