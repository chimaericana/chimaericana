#!/usr/bin/env python3
"""
Mattermost Bot for Projex Communication Hub
Lightweight bot using Mattermost API and webhooks.
Memory footprint: ~3 MB
"""

import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import requests

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [MATTERMOST] %(levelname)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('projex.mattermost')

PROJEX_ROOT = Path(__file__).parent.parent.parent
CONFIG_PATH = PROJEX_ROOT / "automations" / "comm" / "config.json"


class MattermostBot:
    """Lightweight Mattermost bot for Projex notifications."""

    def __init__(self, config: dict):
        mm_config = config.get("mattermost", {})
        self.url = mm_config.get("url", "").rstrip("/")
        self.token = mm_config.get("token", "")
        self.webhook_url = mm_config.get("webhook_url", "")
        self.channels = mm_config.get("channels", {})
        self.enabled = mm_config.get("enabled", False)
        self.message_count = 0
        self.health_status = "healthy"
        self.uptime = datetime.now(timezone.utc)
        self._channel_ids: dict = {}

        if self.enabled:
            if not self.url and not self.webhook_url:
                logger.error("Mattermost URL or webhook URL not configured")
                self.enabled = False

    def _get_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    def _ensure_channel_id(self, channel_name: str) -> Optional[str]:
        """Get channel ID by name, caching the result."""
        if channel_name in self._channel_ids:
            return self._channel_ids[channel_name]

        if not self.token:
            logger.warning("No token — cannot resolve channel IDs. Using webhook only.")
            return None

        try:
            # Find the team first
            teams_resp = requests.get(
                f"{self.url}/api/v4/users/me/teams",
                headers=self._get_headers()
            )
            teams_resp.raise_for_status()
            teams = teams_resp.json()
            if not teams:
                logger.error("Bot is not on any teams")
                return None

            team_id = teams[0]["id"]

            # Get channels for the team
            channels_resp = requests.get(
                f"{self.url}/api/v4/teams/{team_id}/channels",
                headers=self._get_headers()
            )
            channels_resp.raise_for_status()
            channels = channels_resp.json()

            for ch in channels:
                if ch["name"] == channel_name:
                    self._channel_ids[channel_name] = ch["id"]
                    return ch["id"]

            logger.warning(f"Channel '{channel_name}' not found")
            return None

        except Exception as e:
            logger.error(f"Failed to resolve channel '{channel_name}': {e}")
            return None

    def send_message(self, channel_name: str, message: str, **kwargs) -> bool:
        """Send a message to a Mattermost channel."""
        if not self.enabled:
            logger.warning("Mattermost bot is disabled")
            return False

        # Try webhook first (simpler, no token needed)
        if self.webhook_url:
            return self._send_via_webhook(message)

        # Fall back to API (requires token and channel resolution)
        return self._send_via_api(channel_name, message)

    def _send_via_webhook(self, message: str) -> bool:
        """Send via incoming webhook."""
        try:
            payload = {
                "text": message,
                "username": "Projex Bot",
                "icon_url": ""  # Set to a bot avatar URL if desired
            }
            resp = requests.post(self.webhook_url, json=payload, timeout=10)
            resp.raise_for_status()
            self.message_count += 1
            logger.info("Message sent via webhook")
            return True
        except Exception as e:
            logger.error(f"Webhook send failed: {e}")
            return False

    def _send_via_api(self, channel_name: str, message: str) -> bool:
        """Send via Mattermost API v4."""
        if not self.token:
            return False

        channel_id = self._ensure_channel_id(channel_name)
        if not channel_id:
            return False

        try:
            payload = {
                "channel_id": channel_id,
                "message": message
            }
            resp = requests.post(
                f"{self.url}/api/v4/posts",
                headers=self._get_headers(),
                json=payload,
                timeout=10
            )
            resp.raise_for_status()
            self.message_count += 1
            logger.info(f"Message sent to channel '{channel_name}'")
            return True
        except Exception as e:
            logger.error(f"API send failed: {e}")
            return False

    def send_notification(self, category: str, title: str, body: str, urgency: str = "info"):
        """Send a formatted notification."""
        emoji_map = {
            "urgent": "🚨",
            "alert": "⚠️",
            "info": "ℹ️",
            "digest": "📊",
            "critical": "🔴",
            "warning": "🟡",
        }
        emoji = emoji_map.get(urgency, "📢")
        channel = self.channels.get(category, self.channels.get("general", "town-square"))

        message = f"{emoji} **{title}**\n\n{body}\n\n---\n*Category: {category} · Urgency: {urgency}*"
        return self.send_message(channel, message)

    def update_health(self, status: str):
        self.health_status = status

    def get_status(self) -> dict:
        uptime = datetime.now(timezone.utc) - self.uptime
        return {
            "platform": "Mattermost",
            "enabled": self.enabled,
            "health": self.health_status,
            "messages_sent": self.message_count,
            "uptime": str(uptime).split('.')[0],
            "using_webhook": bool(self.webhook_url),
            "using_api": bool(self.token)
        }


def load_config() -> dict:
    with open(CONFIG_PATH) as f:
        return json.load(f)


if __name__ == "__main__":
    config = load_config()
    bot = MattermostBot(config)

    if not bot.enabled:
        logger.info("Mattermost bot is disabled in config. Set 'enabled: true' to activate.")
        sys.exit(0)

    # Test connection
    logger.info("Testing Mattermost connection...")
    success = bot.send_notification(
        "general",
        "Projex Bot Test",
        "Mattermost bot is online and connected.",
        "info"
    )

    if success:
        logger.info("✅ Mattermost bot test successful")
    else:
        logger.error("❌ Mattermost bot test failed")
        sys.exit(1)
