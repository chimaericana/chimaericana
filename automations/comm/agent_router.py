#!/usr/bin/env python3
"""
Agent Router — Connects Discord messages to Agent Profiles.
Routes incoming messages to the correct agent based on commands, triggers, or content analysis.

Flow: Discord message → AgentRouter → Agent Profile → Response → Discord embed
"""

import json
import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Add profiles to path
PROJEX_ROOT = Path(__file__).parent.parent.parent
PROFILES_DIR = PROJEX_ROOT / "profiles"
sys.path.insert(0, str(PROFILES_DIR))

from profile_manager import ProfileManager

logger = logging.getLogger('projex.agent_router')

# Agent command prefixes
AGENT_COMMANDS = {
    'nexus': ['nexus', 'coord', 'route', 'broadcast'],
    'press': ['press', 'pr', 'release', 'pitch', 'release'],
    'echo': ['echo', 'social', 'post', 'schedule', 'engage'],
    'shield': ['shield', 'crisis', 'incident', 'emergency', 'breach'],
    'signal': ['signal', 'media', 'journalist', 'pitch', 'coverage'],
}

# Agent display config for Discord embeds
AGENT_BRANDING = {
    'nexus': {
        'emoji': '🎯',
        'color': 0x3498db,  # Blue
        'footer': 'Nexus — Communications Coordinator'
    },
    'press': {
        'emoji': '📰',
        'color': 0xe74c3c,  # Red
        'footer': 'Press — PR Specialist'
    },
    'echo': {
        'emoji': '📣',
        'color': 0xf39c12,  # Orange
        'footer': 'Echo — Social Media Manager'
    },
    'shield': {
        'emoji': '🛡️',
        'color': 0x9b59b6,  # Purple
        'footer': 'Shield — Crisis Communications'
    },
    'signal': {
        'emoji': '📡',
        'color': 0x1abc9c,  # Teal
        'footer': 'Signal — Media Relations'
    }
}


class AgentRouter:
    """Routes Discord messages to the appropriate agent profile."""

    def __init__(self):
        self.pm = ProfileManager()
        self._agent_cache = {}
        self._load_agents()
        self.interaction_log = PROJEX_ROOT / "automations" / "comm" / "agent_interactions.jsonl"

    def _load_agents(self):
        """Cache all comm agent profiles."""
        for agent_id in AGENT_COMMANDS:
            profile = self.pm.get(agent_id)
            if profile:
                self._agent_cache[agent_id] = profile
                logger.info(f"Loaded agent: {agent_id} ({profile['name']})")

    def match_agent(self, message: str) -> Optional[str]:
        """Determine which agent should handle a message."""
        msg_lower = message.lower().strip()

        # 1. Direct command match: /agent_name or @agent
        for agent_id, commands in AGENT_COMMANDS.items():
            for cmd in commands:
                # Match /command or @command at start
                if re.match(rf'^[/@]?\s*{cmd}\b', msg_lower):
                    return agent_id

        # 2. Trigger keyword match from profile routing config
        for agent_id, profile in self._agent_cache.items():
            triggers = profile.get('routing', {}).get('triggers', [])
            for trigger in triggers:
                if trigger.lower() in msg_lower:
                    return agent_id

        # 3. Default to Nexus for unmatched messages
        return 'nexus'

    def get_branding(self, agent_id: str) -> dict:
        """Get Discord embed branding for an agent."""
        return AGENT_BRANDING.get(agent_id, AGENT_BRANDING['nexus'])

    def build_embed_data(self, agent_id: str, title: str, content: str, fields: list = None) -> dict:
        """Build Discord embed data for an agent response."""
        branding = self.get_branding(agent_id)
        embed = {
            'title': f"{branding['emoji']} {title}",
            'description': content[:4096],  # Discord limit
            'color': branding['color'],
            'footer': {'text': branding['footer']},
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        if fields:
            embed['fields'] = fields[:25]  # Discord limit
        return embed

    def build_spawn_context(self, agent_id: str, user_message: str, user_id: str = None, channel: str = None) -> dict:
        """Build complete context for spawning an agent from Discord."""
        context = self.pm.spawn_context(agent_id, user_message)
        context['source'] = 'discord'
        context['user_id'] = user_id
        context['channel'] = channel
        context['timestamp'] = datetime.now(timezone.utc).isoformat()
        return context

    def log_interaction(self, agent_id: str, user_id: str, message: str, response: str = ''):
        """Log agent interaction for memory tracking."""
        entry = {
            'agent': agent_id,
            'user_id': user_id,
            'message': message[:500],  # Truncate
            'response_length': len(response),
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'source': 'discord'
        }
        try:
            with open(self.interaction_log, 'a') as f:
                f.write(json.dumps(entry) + '\n')
        except Exception as e:
            logger.error(f"Failed to log interaction: {e}")

    def get_agent_list_embed(self) -> dict:
        """Build embed showing all available agents."""
        fields = []
        for agent_id, profile in self._agent_cache.items():
            branding = self.get_branding(agent_id)
            routing = profile.get('routing', {})
            triggers = routing.get('triggers', [])[:3]
            fields.append({
                'name': f"{branding['emoji']} {profile['name']}",
                'value': f"**{profile['role']}**\n"
                         f"Triggers: `{', '.join(triggers)}`\n"
                         f"Auto-respond: {'Yes' if routing.get('auto_respond') else 'No'}",
                'inline': False
            })

        return {
            'title': '🤖 Projex Agent Team',
            'description': 'Each agent has a specialized role. Mention them by name or use their trigger words.',
            'color': 0x2ecc71,
            'fields': fields,
            'footer': {'text': 'Projex AI Agent Platform'},
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

    def get_agent_status_embed(self) -> dict:
        """Build embed showing agent status."""
        fields = []
        for agent_id, profile in self._agent_cache.items():
            branding = self.get_branding(agent_id)
            memory_stats = self.pm.memory_stats(agent_id)
            entries = memory_stats.get('total_entries', 0)
            max_entries = memory_stats.get('max_entries', '∞')
            processing = profile.get('processing', {})

            fields.append({
                'name': f"{branding['emoji']} {profile['name']}",
                'value': f"Model: `{processing.get('model', 'N/A')}`\n"
                         f"Memory: `{entries}/{max_entries}` entries\n"
                         f"Temp: `{processing.get('temperature', 'N/A')}`",
                'inline': True
            })

        return {
            'title': '📊 Agent Status',
            'description': 'Current status of all comm agents.',
            'color': 0x3498db,
            'fields': fields,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

    def route(self, message: str, user_id: str = None, channel: str = None) -> dict:
        """Route a message and return routing decision."""
        agent_id = self.match_agent(message)
        profile = self._agent_cache.get(agent_id, {})
        context = self.build_spawn_context(agent_id, message, user_id, channel)

        return {
            'agent_id': agent_id,
            'agent_name': profile.get('name', agent_id),
            'agent_role': profile.get('role', ''),
            'matched': agent_id != 'nexus' or self.match_agent(message) == 'nexus',
            'context': context,
            'branding': self.get_branding(agent_id)
        }


# CLI testing
if __name__ == '__main__':
    router = AgentRouter()

    if len(sys.argv) < 2:
        print("Usage: python3 agent_router.py <message>")
        print("\nTest messages:")
        tests = [
            "press release for our new product launch",
            "schedule a social post for Twitter",
            "we have a data breach incident",
            "pitch this story to TechCrunch",
            "route this to all channels",
            "hello there",
        ]
        for test in tests:
            result = router.route(test)
            branding = result['branding']
            print(f"  {branding['emoji']} {result['agent_name']:8} ← \"{test}\"")
        sys.exit(0)

    message = ' '.join(sys.argv[1:])
    result = router.route(message)
    branding = result['branding']
    print(f"Agent: {branding['emoji']} {result['agent_name']}")
    print(f"Role:  {result['agent_role']}")
    print(f"Match: {result['matched']}")
    print(json.dumps(result['context'], indent=2)[:500])
