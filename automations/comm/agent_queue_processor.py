#!/usr/bin/env python3
"""
Agent Queue Processor — Watches the agent_queue.jsonl and dispatches
messages to the Pi agent system for processing, then sends responses back to Discord.

This is the bridge between Discord messages and the Pi agent profile system.

Usage:
    python3 agent_queue_processor.py          # Run as daemon (watch queue)
    python3 agent_queue_processor.py --once   # Process one batch and exit
    python3 agent_queue_processor.py --dry    # Show what would be processed
"""

import asyncio
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PROJEX_ROOT = Path(__file__).parent.parent.parent
QUEUE_FILE = PROJEX_ROOT / "automations" / "comm" / "agent_queue.jsonl"
PROCESSED_FILE = PROJEX_ROOT / "automations" / "comm" / "agent_processed.jsonl"
PROFILES_DIR = PROJEX_ROOT / "profiles"

sys.path.insert(0, str(PROFILES_DIR))
from profile_manager import ProfileManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [AGENT_QUEUE] %(levelname)s: %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger('projex.agent_queue')


class AgentQueueProcessor:
    """Processes the agent queue and dispatches to Pi agent system."""

    def __init__(self):
        self.pm = ProfileManager()
        self.running = False
        self.processed_count = 0

    def read_queue(self) -> list[dict]:
        """Read pending items from the queue."""
        if not QUEUE_FILE.exists():
            return []

        items = []
        try:
            with open(QUEUE_FILE) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        items.append(json.loads(line))
            return items
        except Exception as e:
            logger.error(f"Failed to read queue: {e}")
            return []

    def clear_queue(self):
        """Clear the queue file."""
        if QUEUE_FILE.exists():
            QUEUE_FILE.unlink()

    def mark_processed(self, item: dict, result: str = ''):
        """Mark an item as processed."""
        item['processed_at'] = datetime.now(timezone.utc).isoformat()
        item['result_length'] = len(result)
        try:
            with open(PROCESSED_FILE, 'a') as f:
                f.write(json.dumps(item) + '\n')
        except Exception as e:
            logger.error(f"Failed to write processed log: {e}")

    def load_agent_context(self, agent_id: str) -> dict:
        """Load an agent's full profile context."""
        profile = self.pm.get(agent_id)
        if not profile:
            return {'error': f'Agent {agent_id} not found'}

        return {
            'id': profile['id'],
            'name': profile['name'],
            'role': profile['role'],
            'system_prompt': profile.get('_system_prompt_content', ''),
            'personality': profile.get('personality', {}),
            'processing': profile.get('processing', {}),
            'tools': [t for t in profile.get('tools', []) if t.get('enabled', True)],
            'memory_path': str(Path(profile['_path']).parent / profile['memory']['path']),
        }

    def build_agent_prompt(self, item: dict) -> dict:
        """Build a complete prompt package for Pi agent invocation."""
        agent_id = item.get('agent_id', 'nexus')
        context = item.get('context', {})
        message = context.get('user_prompt', '') or item.get('message', '')

        agent = self.load_agent_context(agent_id)
        if 'error' in agent:
            return agent

        prompt_package = {
            'agent_profile': {
                'id': agent['id'],
                'name': agent['name'],
                'role': agent['role'],
            },
            'system_prompt': agent['system_prompt'],
            'personality': agent['personality'],
            'user_message': message,
            'source': item.get('type', 'command'),
            'discord': {
                'channel': item.get('discord_channel', ''),
                'user': item.get('discord_user', ''),
            },
            'available_tools': agent['tools'],
            'memory_path': agent['memory_path'],
            'timestamp': datetime.now(timezone.utc).isoformat(),
        }

        return prompt_package

    def save_prompt_package(self, item: dict, prompt: dict):
        """Save the prompt package for Pi agent to pick up."""
        prompt_dir = PROJEX_ROOT / "automations" / "comm" / "agent_prompts"
        prompt_dir.mkdir(exist_ok=True)

        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
        agent_id = item.get('agent_id', 'nexus')
        prompt_file = prompt_dir / f"{agent_id}_{timestamp}.json"

        with open(prompt_file, 'w') as f:
            json.dump(prompt, f, indent=2)

        logger.info(f"Prompt package saved: {prompt_file}")
        return prompt_file

    def log_to_agent_memory(self, agent_id: str, item: dict, result: str = ''):
        """Append the interaction to the agent's memory."""
        profile = self.pm.get(agent_id)
        if not profile:
            return

        mem_path = Path(profile['_path']).parent / profile['memory']['path']
        conversation_file = mem_path / 'conversations.jsonl'

        entry = {
            'type': 'discord_interaction',
            'source': item.get('type', 'command'),
            'message': item.get('context', {}).get('user_prompt', '') or item.get('message', ''),
            'response_length': len(result),
            'discord_user': item.get('discord_user', ''),
            'discord_channel': item.get('discord_channel', ''),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

        try:
            with open(conversation_file, 'a') as f:
                f.write(json.dumps(entry) + '\n')
            logger.info(f"Logged to {agent_id} memory")
        except Exception as e:
            logger.error(f"Failed to log to agent memory: {e}")

    def process_item(self, item: dict, dry_run: bool = False) -> str:
        """Process a single queue item."""
        agent_id = item.get('agent_id', 'nexus')
        prompt = self.build_agent_prompt(item)

        if 'error' in prompt:
            logger.error(f"Cannot process: {prompt['error']}")
            self.mark_processed(item, result=f"Error: {prompt['error']}")
            return f"❌ {prompt['error']}"

        if dry_run:
            logger.info(f"[DRY] Would process: {agent_id} ← {(item.get('context', {}).get('user_prompt', '') or item.get('message', ''))[:80]}...")
            self.mark_processed(item, result='dry_run')
            return "✅ Dry run — prompt would be generated"

        # Save prompt package for Pi agent to pick up
        prompt_file = self.save_prompt_package(item, prompt)

        # Log to agent memory
        self.log_to_agent_memory(agent_id, item)

        self.mark_processed(item, result=f"prompt_saved:{prompt_file}")
        self.processed_count += 1

        return f"✅ Queued for Pi processing → {prompt_file}"

    def process_all(self, dry_run: bool = False) -> list[str]:
        """Process all pending queue items."""
        items = self.read_queue()
        if not items:
            logger.info("Queue is empty")
            return []

        results = []
        logger.info(f"Processing {len(items)} queue items...")

        for item in items:
            result = self.process_item(item, dry_run)
            results.append(result)

        if not dry_run:
            self.clear_queue()
            logger.info(f"Queue cleared. {self.processed_count} total processed.")

        return results

    async def run_daemon(self, interval: int = 10):
        """Run as a daemon, checking queue periodically."""
        self.running = True
        logger.info(f"Agent queue processor started (interval: {interval}s)")

        while self.running:
            try:
                results = self.process_all()
                if results:
                    for r in results:
                        logger.info(f"  {r}")
            except Exception as e:
                logger.error(f"Error processing queue: {e}")

            await asyncio.sleep(interval)


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Agent Queue Processor')
    parser.add_argument('--once', action='store_true', help='Process once and exit')
    parser.add_argument('--dry', action='store_true', help='Dry run — show what would happen')
    parser.add_argument('--interval', type=int, default=10, help='Daemon check interval (seconds)')
    args = parser.parse_args()

    processor = AgentQueueProcessor()

    if args.once or args.dry:
        results = processor.process_all(dry_run=args.dry)
        if results:
            for r in results:
                print(r)
        else:
            print("Queue is empty")
    else:
        try:
            asyncio.run(processor.run_daemon(args.interval))
        except KeyboardInterrupt:
            logger.info("Agent queue processor stopped")


if __name__ == '__main__':
    main()
