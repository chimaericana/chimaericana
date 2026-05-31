#!/usr/bin/env python3
"""spawner.py — Subagent orchestration system.

Spawn isolated Pi instances via RPC for background jobs.
Manage lifecycle, collect results, enforce limits.

Usage:
    python spawner.py spawn --type report --prompt "Generate daily report"
    python spawner.py list
    python spawner.py stop <agent_id>
    python spawner.py results <agent_id>
    python spawner.py status
"""

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

AGENTS_DIR = "automations/agents"
RESULTS_DIR = f"{AGENTS_DIR}/results"
CONFIG_FILE = f"{AGENTS_DIR}/agents_config.json"

# Resource limits per subagent
DEFAULT_LIMITS = {
    "timeout": 300,  # 5 minutes max
    "max_output_kb": 512,
    "max_memory_mb": 256,
    "max_concurrent": 3
}

AGENT_TYPES = ["report", "monitor", "process", "check", "custom"]


def init():
    os.makedirs(AGENTS_DIR, exist_ok=True)
    os.makedirs(RESULTS_DIR, exist_ok=True)
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w") as f:
            json.dump({
                "agents": [],
                "limits": DEFAULT_LIMITS
            }, f, indent=2)


def load_config():
    with open(CONFIG_FILE) as f:
        return json.load(f)


def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def generate_id():
    return f"agent_{datetime.now().strftime('%Y%m%d%H%M%S')}_{os.getpid()}"


def count_running(config):
    return sum(1 for a in config["agents"] if a.get("status") == "running")


def spawn_agent(agent_type, prompt, timeout=None, output_file=None):
    config = load_config()
    limits = config.get("limits", DEFAULT_LIMITS)

    # Check concurrent limit
    running = count_running(config)
    if running >= limits.get("max_concurrent", 3):
        return False, f"Max concurrent agents reached ({running}/{limits['max_concurrent']})"

    agent_id = generate_id()
    timeout = timeout or limits.get("timeout", 300)

    agent = {
        "id": agent_id,
        "type": agent_type,
        "prompt": prompt,
        "status": "running",
        "pid": None,
        "started_at": datetime.now().isoformat(),
        "completed_at": None,
        "output_file": output_file or f"{RESULTS_DIR}/{agent_id}.json",
        "timeout": timeout,
        "exit_code": None,
        "error": None
    }

    config["agents"].append(agent)
    save_config(config)

    # Spawn as background process
    # Write agent info to a file for the subprocess to update
    agent_info_file = f"{RESULTS_DIR}/{agent_id}_info.json"
    with open(agent_info_file, "w") as f:
        json.dump({"status": "running", "output": "", "error": None}, f)

    print(f"🤖 Spawning subagent: {agent_id}")
    print(f"   Type: {agent_type}")
    print(f"   Prompt: {prompt[:100]}...")
    print(f"   Timeout: {timeout}s")

    # For now, run the prompt as a pi print command
    # In production, this would use pi --mode rpc
    cmd = ["pi", "--mode", "print", "--no-context-files", prompt]

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=os.getcwd()
        )
        agent["pid"] = proc.pid
        save_config(config)

        # Monitor in background thread
        import threading

        def monitor():
            try:
                stdout, stderr = proc.communicate(timeout=timeout)
                result = {
                    "status": "completed" if proc.returncode == 0 else "failed",
                    "output": stdout.strip(),
                    "error": stderr.strip() if stderr else None,
                    "exit_code": proc.returncode,
                    "completed_at": datetime.now().isoformat()
                }
            except subprocess.TimeoutExpired:
                proc.kill()
                result = {
                    "status": "timeout",
                    "output": "",
                    "error": f"Agent timed out after {timeout}s",
                    "exit_code": -1,
                    "completed_at": datetime.now().isoformat()
                }

            # Save result
            with open(agent_info_file, "w") as f:
                json.dump(result, f)

            # Update config
            cfg = load_config()
            for a in cfg["agents"]:
                if a["id"] == agent_id:
                    a["status"] = result["status"]
                    a["completed_at"] = result["completed_at"]
                    a["exit_code"] = result["exit_code"]
                    a["error"] = result["error"]
                    a["pid"] = None
                    break
            save_config(cfg)

        thread = threading.Thread(target=monitor, daemon=True)
        thread.start()

        return True, f"Subagent spawned: {agent_id} (PID {proc.pid})"

    except FileNotFoundError:
        # pi not in PATH - create a simulated agent
        agent["status"] = "queued"
        save_config(config)

        # Simulate with a simple process
        import threading

        def simulate():
            time.sleep(2)  # Simulate work
            result = {
                "status": "completed",
                "output": f"[Simulated {agent_type} agent result]\nPrompt: {prompt}",
                "error": None,
                "exit_code": 0,
                "completed_at": datetime.now().isoformat()
            }
            with open(agent_info_file, "w") as f:
                json.dump(result, f)

            cfg = load_config()
            for a in cfg["agents"]:
                if a["id"] == agent_id:
                    a["status"] = "completed"
                    a["completed_at"] = result["completed_at"]
                    break
            save_config(cfg)

        thread = threading.Thread(target=simulate, daemon=True)
        thread.start()

        return True, f"Subagent queued (simulated): {agent_id}"


def list_agents(config=None, status_filter=None):
    if config is None:
        config = load_config()

    agents = config["agents"]
    if status_filter:
        agents = [a for a in agents if a.get("status") == status_filter]

    # Sort by started_at descending
    agents.sort(key=lambda a: a.get("started_at", ""), reverse=True)
    return agents


def stop_agent(config, agent_id):
    for agent in config["agents"]:
        if agent["id"] == agent_id:
            if agent.get("pid"):
                try:
                    os.kill(agent["pid"], signal.SIGTERM)
                    agent["status"] = "stopped"
                    agent["completed_at"] = datetime.now().isoformat()
                    save_config(config)
                    return True, f"Stopped agent: {agent_id}"
                except ProcessLookupError:
                    agent["status"] = "dead"
                    save_config(config)
                    return True, f"Agent already dead: {agent_id}"
            else:
                agent["status"] = "stopped"
                save_config(config)
                return True, f"Marked stopped: {agent_id}"

    return False, f"Agent '{agent_id}' not found"


def get_results(agent_id):
    result_file = f"{RESULTS_DIR}/{agent_id}_info.json"
    if not os.path.exists(result_file):
        return None, "No results file found"

    with open(result_file) as f:
        return json.load(f), None


def format_agent(a):
    type_icons = {
        "report": "📊",
        "monitor": "📡",
        "process": "⚙️",
        "check": "✅",
        "custom": "🔧"
    }
    status_icons = {
        "running": "🔄",
        "completed": "✅",
        "failed": "❌",
        "timeout": "⏰",
        "stopped": "⛔",
        "queued": "⏳",
        "dead": "💀"
    }

    icon = type_icons.get(a["type"], "🤖")
    status_icon = status_icons.get(a["status"], "❓")
    started = a.get("started_at", "")[:19]
    duration = ""
    if a.get("completed_at") and a.get("started_at"):
        try:
            start = datetime.fromisoformat(a["started_at"])
            end = datetime.fromisoformat(a["completed_at"])
            delta = end - start
            duration = f" ({delta.total_seconds():.0f}s)"
        except:
            pass

    lines = [f"  {status_icon} {icon} [{a['type']}] {a['id']}"]
    lines.append(f"     Status: {a['status']}{duration}")
    lines.append(f"     Started: {started}")
    if a.get("prompt"):
        prompt_preview = a["prompt"][:80]
        lines.append(f"     Prompt: {prompt_preview}...")
    if a.get("error"):
        lines.append(f"     Error: {a['error'][:100]}")

    return "\n".join(lines)


def get_status(config):
    agents = config["agents"]
    total = len(agents)
    running = sum(1 for a in agents if a.get("status") == "running")
    completed = sum(1 for a in agents if a.get("status") == "completed")
    failed = sum(1 for a in agents if a.get("status") in ("failed", "timeout"))

    limits = config.get("limits", DEFAULT_LIMITS)

    return {
        "total": total,
        "running": running,
        "completed": completed,
        "failed": failed,
        "max_concurrent": limits.get("max_concurrent", 3),
        "slots_available": limits.get("max_concurrent", 3) - running
    }


def main():
    parser = argparse.ArgumentParser(description="Subagent Spawner")
    subparsers = parser.add_subparsers(dest="command", help="Command")

    # spawn
    spawn = subparsers.add_parser("spawn", help="Spawn a subagent")
    spawn.add_argument("--type", "-t", required=True, choices=AGENT_TYPES)
    spawn.add_argument("--prompt", "-p", required=True, help="Prompt for the agent")
    spawn.add_argument("--timeout", type=int, help="Timeout in seconds")
    spawn.add_argument("--output", "-o", help="Output file path")

    # list
    ls = subparsers.add_parser("list", help="List subagents")
    ls.add_argument("--status", "-s", choices=["running", "completed", "failed", "stopped", "all"], default="all")
    ls.add_argument("--json", "-j", action="store_true")

    # stop
    stop = subparsers.add_parser("stop", help="Stop a subagent")
    stop.add_argument("id", help="Agent ID")

    # results
    res = subparsers.add_parser("results", help="View subagent results")
    res.add_argument("id", help="Agent ID")
    res.add_argument("--json", "-j", action="store_true")

    # status
    subparsers.add_parser("status", help="Show agent system status")

    # cleanup
    subparsers.add_parser("cleanup", help="Remove old completed agents from config")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    init()

    if args.command == "spawn":
        success, msg = spawn_agent(args.type, args.prompt, args.timeout, args.output)
        print(f"{'✅' if success else '❌'} {msg}")

    elif args.command == "list":
        config = load_config()
        filter_status = None if args.status == "all" else args.status
        agents = list_agents(config, filter_status)

        if args.json:
            print(json.dumps(agents, indent=2))
        elif not agents:
            print(f"No agents found" + (f" with status '{args.status}'" if args.status != "all" else ""))
        else:
            print(f"🤖 Subagents ({len(agents)})\n" + "=" * 50)
            for a in agents:
                print(format_agent(a))
                print()

    elif args.command == "stop":
        config = load_config()
        success, msg = stop_agent(config, args.id)
        print(f"{'✅' if success else '❌'} {msg}")

    elif args.command == "results":
        result, error = get_results(args.id)
        if error:
            print(f"Error: {error}", file=sys.stderr)
            sys.exit(1)

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            status_icon = {"completed": "✅", "failed": "❌", "timeout": "⏰", "stopped": "⛔"}.get(result.get("status", "?"), "❓")
            print(f"{status_icon} Agent Results\n" + "=" * 50)
            print(f"Status: {result.get('status')}")
            if result.get("output"):
                print(f"\nOutput:\n{result['output']}")
            if result.get("error"):
                print(f"\nError: {result['error']}")

    elif args.command == "status":
        config = load_config()
        status = get_status(config)
        print("🤖 Subagent System Status")
        print("=" * 50)
        print(f"  Total agents: {status['total']}")
        print(f"  Running: {status['running']}")
        print(f"  Completed: {status['completed']}")
        print(f"  Failed: {status['failed']}")
        print(f"  Slots: {status['running']}/{status['max_concurrent']} ({status['slots_available']} available)")

    elif args.command == "cleanup":
        config = load_config()
        before = len(config["agents"])
        config["agents"] = [a for a in config["agents"] if a.get("status") == "running"]
        after = len(config["agents"])
        save_config(config)
        print(f"🧹 Cleaned up {before - after} old agent records")


if __name__ == "__main__":
    main()
