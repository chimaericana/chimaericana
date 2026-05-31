#!/usr/bin/env python3
"""
Pi Subagent Spawner — Spawns pi subprocesses with agent profiles.
Mirrors the Pi subagent extension behavior for use from Python.
"""

import asyncio
import json
import os
import signal
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

AGENT_DIR = Path.home() / ".pi" / "agent" / "agents"

PI_COMMAND = "pi"

DISCOVERABLE_TOOLS = ["read", "bash", "grep", "find", "ls", "write", "edit"]


def discover_agents() -> list[dict]:
    """Discover all agent .md files in ~/.pi/agent/agents/"""
    agents = []
    if not AGENT_DIR.exists():
        return agents

    for md_file in sorted(AGENT_DIR.glob("*.md")):
        content = md_file.read_text()
        # Parse YAML frontmatter
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                frontmatter = parts[1].strip()
                system_prompt = parts[2].strip()

                agent = {
                    "name": md_file.stem,
                    "file": str(md_file),
                    "system_prompt": system_prompt,
                    "model": None,
                    "tools": [],
                }

                for line in frontmatter.split("\n"):
                    line = line.strip()
                    if line.startswith("name:"):
                        agent["name"] = line.split(":", 1)[1].strip()
                    elif line.startswith("model:"):
                        agent["model"] = line.split(":", 1)[1].strip()
                    elif line.startswith("tools:"):
                        tools_str = line.split(":", 1)[1].strip()
                        agent["tools"] = [t.strip() for t in tools_str.split(",")]

                agents.append(agent)

    return agents


def find_agent(name: str) -> Optional[dict]:
    """Find an agent by name."""
    agents = discover_agents()
    for agent in agents:
        if agent["name"] == name:
            return agent
    return None


async def run_subagent(
    agent_name: str,
    task: str,
    cwd: str = None,
    timeout: int = 120,
    on_progress=None,
) -> dict:
    """
    Spawn a pi subprocess with the agent's profile.

    Returns:
        {
            "exit_code": 0,
            "output": "Final agent output",
            "messages": [...],
            "usage": {"input": 0, "output": 0, ...},
            "model": "...",
            "stderr": "",
        }
    """
    agent = find_agent(agent_name)
    if not agent:
        return {
            "exit_code": 1,
            "output": f"Unknown agent: {agent_name}",
            "messages": [],
            "usage": {},
            "stderr": f"Available agents: {', '.join(a['name'] for a in discover_agents())}",
        }

    # Build pi command
    args = [
        PI_COMMAND,
        "--mode", "json",
        "-p",
        "--no-session",
    ]

    if agent.get("model"):
        args.extend(["--model", agent["model"]])

    if agent.get("tools"):
        args.extend(["--tools", ",".join(agent["tools"])])

    # Write system prompt to temp file
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", delete=False, prefix=f"pi-agent-{agent_name}-"
    ) as f:
        f.write(agent["system_prompt"])
        prompt_file = f.name

    try:
        args.extend(["--append-system-prompt", prompt_file])
        args.append(f"Task: {task}")

        proc = await asyncio.create_subprocess_exec(
            *args,
            cwd=cwd or str(Path.home() / "Projex"),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        messages = []
        buffer = ""
        stderr_output = ""

        async def read_stdout():
            nonlocal buffer
            while True:
                data = await proc.stdout.read(4096)
                if not data:
                    break
                buffer += data.decode("utf-8", errors="replace")
                lines = buffer.split("\n")
                buffer = lines.pop() or ""
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        event = json.loads(line)
                        if event.get("type") == "message_end" and event.get("message"):
                            messages.append(event["message"])
                            if on_progress:
                                on_progress(messages, event)
                        elif event.get("type") == "tool_result_end" and event.get("message"):
                            messages.append(event["message"])
                            if on_progress:
                                on_progress(messages, event)
                    except json.JSONDecodeError:
                        pass

        async def read_stderr():
            nonlocal stderr_output
            while True:
                data = await proc.stderr.read(4096)
                if not data:
                    break
                stderr_output += data.decode("utf-8", errors="replace")

        try:
            await asyncio.wait_for(
                asyncio.gather(read_stdout(), read_stderr()),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            proc.kill()
            return {
                "exit_code": -1,
                "output": "Subagent timed out",
                "messages": messages,
                "usage": {},
                "stderr": stderr_output,
            }

        await proc.wait()
        exit_code = proc.returncode or 0

        # Extract final output from messages
        output = ""
        usage = {}
        model = agent.get("model", "")

        for msg in reversed(messages):
            if msg.get("role") == "assistant":
                for part in msg.get("content", []):
                    if part.get("type") == "text":
                        output = part.get("text", "")
                        break
                if msg.get("usage"):
                    usage = {
                        "input": msg["usage"].get("input", 0),
                        "output": msg["usage"].get("output", 0),
                        "cache_read": msg["usage"].get("cacheRead", 0),
                        "cache_write": msg["usage"].get("cacheWrite", 0),
                        "cost": msg["usage"].get("cost", {}).get("total", 0)
                        if isinstance(msg["usage"].get("cost"), dict)
                        else msg["usage"].get("cost", 0),
                        "turns": len(messages) // 2,
                    }
                if msg.get("model"):
                    model = msg["model"]
                break

        return {
            "exit_code": exit_code,
            "output": output,
            "messages": messages,
            "usage": usage,
            "model": model,
            "stderr": stderr_output,
            "agent": agent_name,
        }

    finally:
        # Clean up temp file
        try:
            os.unlink(prompt_file)
        except OSError:
            pass


# CLI test
if __name__ == "__main__":
    import sys

    agents = discover_agents()
    print(f"Discovered {len(agents)} agents:")
    for a in agents:
        tools = ", ".join(a["tools"]) if a["tools"] else "default"
        print(f"  {a['name']:10} | model: {a['model'] or 'default'} | tools: {tools}")

    if len(sys.argv) > 1:
        agent_name = sys.argv[1]
        task = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else "Hello, who are you?"

        print(f"\nRunning: {agent_name} ← {task}")

        async def test():
            result = await run_subagent(agent_name, task)
            print(f"\nExit code: {result['exit_code']}")
            print(f"Model: {result['model']}")
            print(f"Usage: {result['usage']}")
            print(f"\nOutput:\n{result['output'][:1000]}")
            if result["stderr"]:
                print(f"\nStderr: {result['stderr'][:500]}")

        asyncio.run(test())
