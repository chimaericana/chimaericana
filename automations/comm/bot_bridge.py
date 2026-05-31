#!/usr/bin/env python3
"""
Bot Bridge — Central Message Router for Projex
Routes notifications to Discord, Mattermost, or both based on config.
Provides a queue for offline delivery and retry logic.
"""

import asyncio
import json
import logging
import sys
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

PROJEX_ROOT = Path(__file__).parent.parent.parent
CONFIG_PATH = PROJEX_ROOT / "automations" / "comm" / "config.json"
QUEUE_FILE = PROJEX_ROOT / "automations" / "comm" / "bridge_queue.jsonl"
LOG_FILE = PROJEX_ROOT / "automations" / "comm" / "bot.log"

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [BRIDGE] %(levelname)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('projex.bridge')


class MessageQueue:
    """Persistent message queue with retry logic."""

    def __init__(self, config: dict):
        queue_config = config.get("queue", {})
        self.enabled = queue_config.get("enabled", True)
        self.max_retries = queue_config.get("max_retries", 3)
        self.retry_delay = queue_config.get("retry_delay_seconds", 30)
        self.max_size = queue_config.get("max_queue_size", 100)
        self._queue: deque = deque(maxlen=self.max_size)

    def enqueue(self, message: dict):
        message["queued_at"] = datetime.now(timezone.utc).isoformat()
        message["retries"] = 0
        self._queue.append(message)
        self._persist()
        logger.info(f"Message queued: {message.get('title', 'untitled')}")

    def dequeue(self) -> Optional[dict]:
        if self._queue:
            msg = self._queue.popleft()
            self._persist()
            return msg
        return None

    def retry(self, message: dict):
        message["retries"] = message.get("retries", 0) + 1
        if message["retries"] < self.max_retries:
            message["retry_after"] = (
                datetime.now(timezone.utc).timestamp() + self.retry_delay
            )
            self._queue.append(message)
            logger.warning(f"Retrying message (attempt {message['retries']}): {message.get('title')}")
        else:
            logger.error(f"Message dropped after {self.max_retries} retries: {message.get('title')}")
        self._persist()

    def pending_count(self) -> int:
        return len(self._queue)

    def _persist(self):
        if not self.enabled:
            return
        try:
            with open(QUEUE_FILE, "w") as f:
                for msg in self._queue:
                    f.write(json.dumps(msg) + "\n")
        except Exception as e:
            logger.error(f"Failed to persist queue: {e}")

    def load(self):
        if not self.enabled or not QUEUE_FILE.exists():
            return
        try:
            with open(QUEUE_FILE) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        self._queue.append(json.loads(line))
            logger.info(f"Loaded {len(self._queue)} pending messages from queue")
        except Exception as e:
            logger.error(f"Failed to load queue: {e}")


class BotBridge:
    """Central router that sends messages to configured platforms."""

    def __init__(self):
        self.config = self._load_config()
        self.queue = MessageQueue(self.config)
        self.routing = self.config.get("routing", {})
        self.discord_bot = None
        self.mm_bot = None
        self.stats = {
            "sent": 0,
            "failed": 0,
            "queued": 0,
            "started": datetime.now(timezone.utc).isoformat()
        }

    def _load_config(self) -> dict:
        with open(CONFIG_PATH) as f:
            return json.load(f)

    def set_discord_bot(self, bot):
        self.discord_bot = bot

    def set_mattermost_bot(self, bot):
        self.mm_bot = bot

    def route(self, category: str, title: str, body: str, urgency: str = "info"):
        """Route a message to the appropriate platforms."""
        platforms = self.routing.get(category, self.routing.get(urgency, ["discord"]))

        message = {
            "category": category,
            "title": title,
            "body": body,
            "urgency": urgency,
            "platforms": platforms,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        logger.info(f"Routing '{title}' to: {', '.join(platforms)}")

        for platform in platforms:
            if platform == "discord" and self.discord_bot:
                self._send_discord(message)
            elif platform == "mattermost" and self.mm_bot:
                self._send_mattermost(message)
            else:
                logger.warning(f"Platform '{platform}' not available, queuing")
                self.queue.enqueue(message)
                self.stats["queued"] += 1

    def _send_discord(self, message: dict):
        try:
            if self.discord_bot:
                asyncio.create_task(
                    self.discord_bot.send_notification(
                        message["category"],
                        message["title"],
                        message["body"],
                        message["urgency"]
                    )
                )
                self.stats["sent"] += 1
                logger.info(f"Sent to Discord: {message['title']}")
            else:
                self.queue.enqueue(message)
        except Exception as e:
            logger.error(f"Discord send failed: {e}")
            self.stats["failed"] += 1
            self.queue.enqueue(message)

    def _send_mattermost(self, message: dict):
        try:
            if self.mm_bot:
                success = self.mm_bot.send_notification(
                    message["category"],
                    message["title"],
                    message["body"],
                    message["urgency"]
                )
                if success:
                    self.stats["sent"] += 1
                else:
                    self.queue.enqueue(message)
            else:
                self.queue.enqueue(message)
        except Exception as e:
            logger.error(f"Mattermost send failed: {e}")
            self.stats["failed"] += 1
            self.queue.enqueue(message)

    def get_status(self) -> dict:
        return {
            **self.stats,
            "queue_pending": self.queue.pending_count(),
            "discord_connected": self.discord_bot is not None,
            "mattermost_connected": self.mm_bot is not None
        }

    def reload_config(self):
        self.config = self._load_config()
        self.routing = self.config.get("routing", {})
        logger.info("Configuration reloaded")


# CLI interface for testing
def cli_send(category: str, title: str, body: str, urgency: str = "info"):
    """Send a test message via CLI."""
    bridge = BotBridge()
    bridge.route(category, title, body, urgency)
    status = bridge.get_status()
    print(json.dumps(status, indent=2))


def cli_status():
    """Show bridge status."""
    bridge = BotBridge()
    status = bridge.get_status()
    print(json.dumps(status, indent=2))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 bot_bridge.py <send|status>")
        print("  send <category> <title> <body> [urgency]")
        print("  status")
        sys.exit(1)

    command = sys.argv[1]
    if command == "send" and len(sys.argv) >= 5:
        cli_send(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5] if len(sys.argv) > 5 else "info")
    elif command == "status":
        cli_status()
    else:
        print("Invalid command or missing arguments")
        sys.exit(1)
