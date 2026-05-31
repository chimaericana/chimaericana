#!/usr/bin/env python3
"""
Profile Manager — Load, manage, and spawn agent profiles.
Provides profile discovery, validation, memory management, and deployment config.

Usage:
    python3 profile_manager.py list
    python3 profile_manager show <agent_id>
    python3 profile_manager validate <agent_id>
    python3 profile_manager memory <agent_id> [stats|clear|export|rotate]
    python3 profile_manager spawn <agent_id> --prompt "..."
    python3 profile_manager tree
"""

import json
import sys
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

PROJEX_ROOT = Path(__file__).parent.parent
PROFILES_ROOT = PROJEX_ROOT / "profiles"
SCHEMA_PATH = PROFILES_ROOT / "schemas" / "agent_profile.schema.json"


class ProfileManager:
    """Manages agent profiles across all domains."""

    def __init__(self):
        self.profiles_root = PROFILES_ROOT
        self._cache = {}

    def discover(self) -> list[dict]:
        """Discover all agent profiles."""
        profiles = []
        for domain_dir in sorted(self.profiles_root.iterdir()):
            if not domain_dir.is_dir() or domain_dir.name in ("schemas", "templates"):
                continue
            for agent_dir in sorted(domain_dir.iterdir()):
                profile_file = agent_dir / "profile.json"
                if profile_file.exists():
                    with open(profile_file) as f:
                        profile = json.load(f)
                    profile["_path"] = str(profile_file)
                    profile["_domain"] = domain_dir.name
                    profiles.append(profile)
        return profiles

    def get(self, agent_id: str) -> Optional[dict]:
        """Get a specific agent profile by ID."""
        if agent_id in self._cache:
            return self._cache[agent_id]

        for profile in self.discover():
            if profile["id"] == agent_id:
                # Load system prompt
                prompt_file = Path(profile["_path"]).parent / profile.get("system_prompt", "system_prompt.md")
                if prompt_file.exists():
                    profile["_system_prompt_content"] = prompt_file.read_text()
                self._cache[agent_id] = profile
                return profile

        return None

    def validate(self, agent_id: str) -> dict:
        """Validate an agent profile."""
        profile = self.get(agent_id)
        if not profile:
            return {"valid": False, "errors": [f"Profile '{agent_id}' not found"]}

        errors = []
        warnings = []

        # Required fields
        for field in ["id", "name", "role", "system_prompt", "personality", "memory"]:
            if field not in profile:
                errors.append(f"Missing required field: {field}")

        # Personality validation
        personality = profile.get("personality", {})
        for field in ["traits", "communication_style", "decision_framework"]:
            if field not in personality:
                warnings.append(f"Missing personality.{field}")

        # Memory validation
        memory = profile.get("memory", {})
        for field in ["type", "path"]:
            if field not in memory:
                errors.append(f"Missing memory.{field}")

        # Check system prompt file exists
        prompt_path = Path(profile["_path"]).parent / profile.get("system_prompt", "")
        if not prompt_path.exists():
            errors.append(f"System prompt file not found: {prompt_path}")

        # Check memory directory exists
        mem_path = Path(profile["_path"]).parent / memory.get("path", "memory")
        if not mem_path.exists():
            warnings.append(f"Memory directory does not exist: {mem_path}")

        # Check tools exist
        for tool in profile.get("tools", []):
            if tool.get("type") == "script" and tool.get("path"):
                tool_path = Path(profile["_path"]).parent / tool["path"]
                if not tool_path.exists():
                    warnings.append(f"Tool not found: {tool['name']} ({tool['path']})")

        # Check extensions exist
        for ext in profile.get("extensions", []):
            ext_path = Path(profile["_path"]).parent / ext
            if not ext_path.exists():
                warnings.append(f"Extension not found: {ext}")

        # Processing config
        processing = profile.get("processing", {})
        if processing.get("temperature", 0) > 1.0:
            warnings.append("Temperature > 1.0 may produce erratic results")

        # Deployment config
        deployment = profile.get("deployment", {})
        if deployment.get("type") not in ("local", "container", "modal", "lambda", None):
            errors.append(f"Invalid deployment type: {deployment.get('type')}")

        # Relationships
        relationships = profile.get("relationships", {})
        for field in ["collaborates_with", "delegates_to"]:
            for agent in relationships.get(field, []):
                other = self.get(agent)
                if not other:
                    warnings.append(f"Unknown agent in relationships.{field}: {agent}")

        return {
            "valid": len(errors) == 0,
            "agent_id": agent_id,
            "errors": errors,
            "warnings": warnings,
            "score": max(0, 100 - (len(errors) * 20) - (len(warnings) * 5))
        }

    def show(self, agent_id: str) -> str:
        """Display a formatted profile summary."""
        profile = self.get(agent_id)
        if not profile:
            return f"❌ Profile '{agent_id}' not found"

        validation = self.validate(agent_id)
        memory = profile.get("memory", {})
        processing = profile.get("processing", {})
        deployment = profile.get("deployment", {})
        relationships = profile.get("relationships", {})
        routing = profile.get("routing", {})

        valid_status = '✅ Valid' if validation['valid'] else f"❌ {len(validation['errors'])} errors"
        lines = [
            f"🤖 {profile['name']} — {profile['role']}",
            f"{'=' * 50}",
            f"ID:         {profile['id']}",
            f"Version:    {profile.get('version', '1.0.0')}",
            f"Domain:     {profile['_domain']}",
            f"Validation: {valid_status} (score: {validation['score']}/100)",
            "",
            "🧠 Personality",
            f"  Traits:     {', '.join(profile.get('personality', {}).get('traits', []))}",
            f"  Style:      {profile.get('personality', {}).get('communication_style', 'N/A')[:80]}...",
            "",
            "⚙️ Processing",
            f"  Model:      {processing.get('model', 'N/A')}",
            f"  Provider:   {processing.get('provider', 'N/A')}",
            f"  Thinking:   {processing.get('thinking_level', 'N/A')}",
            f"  Temperature: {processing.get('temperature', 'N/A')}",
            f"  Max tokens: {processing.get('max_tokens', 'N/A')}",
            "",
            "💾 Memory",
            f"  Type:       {memory.get('type', 'N/A')}",
            f"  Max entries: {memory.get('max_entries', 'N/A')}",
            f"  Retention:  {memory.get('retention_days', 'N/A')} days",
            f"  Categories: {', '.join(memory.get('categories', []))}",
            "",
            "🛠 Tools",
        ]

        for tool in profile.get("tools", []):
            status = "✅" if tool.get("enabled", True) else "❌"
            lines.append(f"  {status} {tool['name']} ({tool.get('type', 'unknown')})")

        lines += [
            "",
            "🔗 Relationships",
            f"  Reports to:   {relationships.get('reports_to', 'None')}",
            f"  Collaborates: {', '.join(relationships.get('collaborates_with', [])) or 'None'}",
            f"  Delegates to: {', '.join(relationships.get('delegates_to', [])) or 'None'}",
            "",
            "📡 Routing",
            f"  Auto-respond: {routing.get('auto_respond', False)}",
            f"  Channels:     {', '.join(routing.get('channels', []))}",
            f"  Triggers:     {', '.join(routing.get('triggers', []))}",
            "",
            "🚀 Deployment",
            f"  Type:         {deployment.get('type', 'local')}",
            f"  Memory:       {deployment.get('resource_limits', {}).get('memory_mb', 'N/A')} MB",
            f"  Scaling:      {deployment.get('scaling', {}).get('max_instances', 1)} instance(s)",
        ]

        if validation["warnings"]:
            lines += ["", "⚠️ Warnings"]
            for w in validation["warnings"]:
                lines.append(f"  • {w}")

        if validation["errors"]:
            lines += ["", "❌ Errors"]
            for e in validation["errors"]:
                lines.append(f"  • {e}")

        return "\n".join(lines)

    def tree(self) -> str:
        """Display the full profile tree."""
        profiles = self.discover()
        by_domain = {}
        for p in profiles:
            domain = p["_domain"]
            if domain not in by_domain:
                by_domain[domain] = []
            by_domain[domain].append(p)

        lines = ["📁 Profile Tree", "=" * 40]
        for domain, agents in sorted(by_domain.items()):
            lines.append(f"\n📂 {domain}/")
            for agent in agents:
                emoji = {"nexus": "🎯", "press": "📰", "echo": "📣", "shield": "🛡️", "signal": "📡"}.get(agent["id"], "🤖")
                lines.append(f"  {emoji} {agent['id']}/  ({agent['name']} — {agent['role']})")
                # Memory status
                mem_path = Path(agent["_path"]).parent / agent.get("memory", {}).get("path", "memory")
                if mem_path.exists():
                    files = list(mem_path.iterdir())
                    lines.append(f"     💾 {len(files)} memory file(s)")
                else:
                    lines.append(f"     💾 memory directory not created")
                # Tool count
                tools = agent.get("tools", [])
                lines.append(f"     🛠 {len(tools)} tool(s)")
                # Commands
                cmds = agent.get("commands", [])
                lines.append(f"     ⚡ {len(cmds)} command(s)")

        lines += [f"\nTotal: {len(profiles)} agent(s) across {len(by_domain)} domain(s)"]
        return "\n".join(lines)

    def memory_stats(self, agent_id: str) -> dict:
        """Get memory statistics for an agent."""
        profile = self.get(agent_id)
        if not profile:
            return {"error": f"Profile '{agent_id}' not found"}

        mem_path = Path(profile["_path"]).parent / profile["memory"]["path"]
        if not mem_path.exists():
            return {"status": "no_memory_directory"}

        stats = {"path": str(mem_path), "files": {}}
        total_entries = 0
        total_size = 0

        for f in mem_path.iterdir():
            if f.is_file():
                size = f.stat().st_size
                lines = 0
                if f.suffix == ".jsonl":
                    with open(f) as fh:
                        lines = sum(1 for _ in fh)
                    total_entries += lines
                stats["files"][f.name] = {
                    "size_kb": round(size / 1024, 1),
                    "entries": lines if f.suffix == ".jsonl" else "N/A"
                }
                total_size += size

        stats["total_size_kb"] = round(total_size / 1024, 1)
        stats["total_entries"] = total_entries
        stats["max_entries"] = profile["memory"].get("max_entries", "unlimited")
        stats["retention_days"] = profile["memory"].get("retention_days", "unlimited")
        return stats

    def memory_clear(self, agent_id: str) -> str:
        """Clear an agent's memory."""
        profile = self.get(agent_id)
        if not profile:
            return f"❌ Profile '{agent_id}' not found"

        mem_path = Path(profile["_path"]).parent / profile["memory"]["path"]
        if not mem_path.exists():
            return "⚠️ Memory directory does not exist"

        # Archive instead of delete
        archive_name = f"{agent_id}_memory_{datetime.now().strftime('%Y%m%d_%H%M%S')}.tar.gz"
        archive_path = mem_path.parent / archive_name

        shutil.make_archive(str(mem_path.parent / archive_name.replace('.tar.gz', '')), 'gztar', str(mem_path))
        
        # Clear memory files
        for f in mem_path.iterdir():
            if f.is_file():
                f.unlink()

        return f"✅ Memory archived to {archive_path} and cleared"

    def memory_rotate(self, agent_id: str) -> str:
        """Rotate memory if it exceeds max_entries."""
        profile = self.get(agent_id)
        if not profile:
            return f"❌ Profile '{agent_id}' not found"

        stats = self.memory_stats(agent_id)
        if "error" in stats:
            return f"❌ {stats['error']}"

        max_entries = profile["memory"].get("max_entries", 999999)
        if stats["total_entries"] <= max_entries:
            return f"✅ Memory within limits ({stats['total_entries']}/{max_entries})"

        # Keep only the most recent entries
        mem_path = Path(profile["_path"]).parent / profile["memory"]["path"]
        for f in mem_path.iterdir():
            if f.suffix == ".jsonl" and f.is_file():
                with open(f) as fh:
                    lines = fh.readlines()
                if len(lines) > max_entries:
                    keep = lines[-max_entries:]
                    with open(f, "w") as fh:
                        fh.writelines(keep)
                    removed = len(lines) - max_entries
                    return f"🔄 Rotated {f.name}: removed {removed} entries, kept {max_entries}"

        return "✅ No files needed rotation"

    def spawn_context(self, agent_id: str, user_prompt: str = "") -> dict:
        """Build a complete context package for spawning an agent."""
        profile = self.get(agent_id)
        if not profile:
            return {"error": f"Profile '{agent_id}' not found"}

        return {
            "agent": {
                "id": profile["id"],
                "name": profile["name"],
                "role": profile["role"],
            },
            "system_prompt": profile.get("_system_prompt_content", ""),
            "personality": profile.get("personality", {}),
            "processing": profile.get("processing", {}),
            "tools": [t for t in profile.get("tools", []) if t.get("enabled", True)],
            "skills": [s for s in profile.get("skills", []) if s.get("enabled", True)],
            "user_prompt": user_prompt,
            "memory_path": str(Path(profile["_path"]).parent / profile["memory"]["path"]),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


def main():
    pm = ProfileManager()

    if len(sys.argv) < 2:
        print(pm.tree())
        print("\nUsage:")
        print("  profile_manager.py list              — List all profiles")
        print("  profile_manager.py show <id>         — Show profile details")
        print("  profile_manager.py validate <id>     — Validate profile")
        print("  profile_manager.py tree              — Show profile tree")
        print("  profile_manager.py memory <id> stats — Memory statistics")
        print("  profile_manager.py memory <id> clear — Clear memory (archive first)")
        print("  profile_manager.py memory <id> rotate — Rotate if over limit")
        print("  profile_manager.py spawn <id> \"...\"  — Build spawn context")
        sys.exit(0)

    command = sys.argv[1].lower()

    if command == "list":
        profiles = pm.discover()
        for p in profiles:
            emoji = {"nexus": "🎯", "press": "📰", "echo": "📣", "shield": "🛡️", "signal": "📡"}.get(p["id"], "🤖")
            print(f"  {emoji} {p['id']:10} — {p['name']:12} | {p['role']}")

    elif command == "show":
        if len(sys.argv) < 3:
            print("Usage: profile_manager.py show <agent_id>")
            sys.exit(1)
        print(pm.show(sys.argv[2]))

    elif command == "validate":
        if len(sys.argv) < 3:
            print("Usage: profile_manager.py validate <agent_id>")
            sys.exit(1)
        result = pm.validate(sys.argv[2])
        emoji = "✅" if result["valid"] else "❌"
        print(f"{emoji} {sys.argv[2]} — Score: {result['score']}/100")
        if result["errors"]:
            print(f"  Errors: {len(result['errors'])}")
            for e in result["errors"]:
                print(f"    • {e}")
        if result["warnings"]:
            print(f"  Warnings: {len(result['warnings'])}")
            for w in result["warnings"]:
                print(f"    • {w}")

    elif command == "tree":
        print(pm.tree())

    elif command == "memory":
        if len(sys.argv) < 4:
            print("Usage: profile_manager.py memory <agent_id> <stats|clear|rotate>")
            sys.exit(1)
        agent_id = sys.argv[2]
        action = sys.argv[3].lower()

        if action == "stats":
            stats = pm.memory_stats(agent_id)
            if "error" in stats:
                print(f"❌ {stats['error']}")
            else:
                print(f"💾 Memory: {agent_id}")
                print(f"  Path: {stats.get('path', 'N/A')}")
                print(f"  Total: {stats.get('total_entries', 0)} entries, {stats.get('total_size_kb', 0)} KB")
                print(f"  Limit: {stats.get('max_entries', 'unlimited')} entries, {stats.get('retention_days', 'unlimited')} days")
                for fname, fstats in stats.get("files", {}).items():
                    print(f"    📄 {fname}: {fstats['size_kb']} KB, {fstats['entries']} entries")

        elif action == "clear":
            print(pm.memory_clear(agent_id))

        elif action == "rotate":
            print(pm.memory_rotate(agent_id))

    elif command == "spawn":
        if len(sys.argv) < 4:
            print("Usage: profile_manager.py spawn <agent_id> \"prompt\"")
            sys.exit(1)
        context = pm.spawn_context(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "")
        print(json.dumps(context, indent=2))

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
