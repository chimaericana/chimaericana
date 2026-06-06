#!/usr/bin/env python3
"""
Agent Engine — Calls OpenRouter API directly instead of spawning `pi` subprocess.
Replaces pi_subagent.py for cloud deployment (Railway/Render).

Reads agent system prompts from the profiles/ directory and sends them
as system messages to the configured OpenRouter model.
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Optional

import aiohttp

logger = logging.getLogger('athena.agent_engine')

# ─── Paths ───────────────────────────────────────────────────────────────────

DEPLOY_ROOT = Path(__file__).parent
PROFILES_DIR = DEPLOY_ROOT / "profiles"

# ─── Agent Registry ──────────────────────────────────────────────────────────

AGENT_REGISTRY = {
    "nexus": {
        "name": "Metis",
        "emoji": "🎯",
        "color": 0x3498db,
        "footer": "Metis — Communications Coordinator",
        "profile_path": PROFILES_DIR / "comm" / "nexus" / "system_prompt.md",
    },
    "press": {
        "name": "Calliope",
        "emoji": "📰",
        "color": 0xe74c3c,
        "footer": "Calliope — PR Specialist",
        "profile_path": PROFILES_DIR / "comm" / "press" / "system_prompt.md",
    },
    "echo": {
        "name": "Clio",
        "emoji": "📣",
        "color": 0xf39c12,
        "footer": "Clio — Social Media Manager",
        "profile_path": PROFILES_DIR / "comm" / "echo" / "system_prompt.md",
    },
    "shield": {
        "name": "Pallas",
        "emoji": "🛡️",
        "color": 0x9b59b6,
        "footer": "Pallas — Crisis Communications",
        "profile_path": PROFILES_DIR / "comm" / "shield" / "system_prompt.md",
    },
    "signal": {
        "name": "Iris",
        "emoji": "📡",
        "color": 0x1abc9c,
        "footer": "Iris — Media Relations",
        "profile_path": PROFILES_DIR / "comm" / "signal" / "system_prompt.md",
    },
}

# ─── Message Router (keyword-based) ──────────────────────────────────────────

AGENT_TRIGGERS = {
    "nexus": ["nexus", "coord", "route", "broadcast", "status", "bridge", "coordinate", "notify all"],
    "press": ["press", "pr", "release", "pitch", "media kit", "boilerplate", "statement"],
    "echo": ["echo", "social", "post", "schedule", "engage", "twitter", "linkedin", "instagram", "thread", "hashtag"],
    "shield": ["shield", "crisis", "incident", "emergency", "breach", "urgent", "alert"],
    "signal": ["signal", "media", "journalist", "coverage", "outlet", "reporter"],
}


def route_message(message: str) -> str:
    """Determine which agent should handle a message. Returns agent_id."""
    msg_lower = message.lower().strip()

    for agent_id, triggers in AGENT_TRIGGERS.items():
        for trigger in triggers:
            if msg_lower.startswith(trigger) or msg_lower.startswith(f"/{trigger}"):
                return agent_id

    return "nexus"


def get_agent_info(agent_id: str) -> dict:
    return AGENT_REGISTRY.get(agent_id, AGENT_REGISTRY["nexus"])


def get_branding(agent_id: str) -> dict:
    info = get_agent_info(agent_id)
    return {
        "emoji": info["emoji"],
        "color": info["color"],
        "footer": info["footer"],
        "name": info["name"],
    }


# ─── OpenRouter Client ──────────────────────────────────────────────────────

async def call_openrouter(
    system_prompt: str,
    user_message: str,
    model: str,
    api_key: str,
    base_url: str = "https://openrouter.ai/api/v1",
    timeout: int = 90,
) -> dict:
    """
    Call OpenRouter chat completions API.

    Returns: { "output": str, "model": str, "usage": dict, "error": str|None }
    """
    url = f"{base_url}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/chimaericana/athena-bot",
        "X-Title": "Athena Discord Bot",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "max_tokens": 2048,
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=timeout),
            ) as resp:
                if resp.status == 429:
                    return {"output": "", "model": model, "usage": {}, "error": "rate_limit"}
                if resp.status == 401:
                    return {"output": "", "model": model, "usage": {}, "error": "invalid_api_key"}
                if resp.status >= 400:
                    body = await resp.text()
                    return {"output": "", "model": model, "usage": {}, "error": f"http_{resp.status}: {body[:200]}"}

                data = await resp.json()
                choices = data.get("choices", [])
                if not choices:
                    return {"output": "", "model": model, "usage": {}, "error": "no_choices"}

                output = choices[0].get("message", {}).get("content", "")
                return {
                    "output": output,
                    "model": data.get("model", model),
                    "usage": data.get("usage", {}),
                    "error": None,
                }

    except asyncio.TimeoutError:
        return {"output": "", "model": model, "usage": {}, "error": "timeout"}
    except Exception as e:
        return {"output": "", "model": model, "usage": {}, "error": str(e)[:200]}


async def call_agent(
    agent_id: str,
    user_message: str,
    api_key: str,
    config: dict,
    timeout: int = 90,
) -> dict:
    """
    Call an agent by ID. Loads system prompt from profile, tries models with fallback.

    Returns: { "output": str, "model": str, "agent_id": str, "agent_name": str,
               "branding": dict, "usage": dict, "error": str|None, "tried": list }
    """
    info = get_agent_info(agent_id)
    branding = get_branding(agent_id)

    # Load system prompt
    system_prompt = ""
    if info["profile_path"].exists():
        system_prompt = info["profile_path"].read_text()
    else:
        logger.warning(f"System prompt not found: {info['profile_path']}")
        system_prompt = f"You are {info['name']}, a communication agent."

    # Build fallback chain
    openrouter_config = config.get("openrouter", {})
    default_model = openrouter_config.get("default_model", "z-ai/glm-4.5-air:free")
    fallback_models = openrouter_config.get("fallback_models", [default_model])
    base_url = openrouter_config.get("base_url", "https://openrouter.ai/api/v1")

    models = [default_model]
    for m in fallback_models:
        if m not in models:
            models.append(m)

    tried = []
    last_error = None

    for model in models:
        tried.append(model)
        logger.info(f"Agent {agent_id}: trying model {model}")

        result = await call_openrouter(
            system_prompt=system_prompt,
            user_message=user_message,
            model=model,
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
        )

        if result["output"] and not result["error"]:
            return {
                "output": result["output"],
                "model": result["model"],
                "agent_id": agent_id,
                "agent_name": info["name"],
                "branding": branding,
                "usage": result["usage"],
                "error": None,
                "tried": tried,
            }

        last_error = result["error"]
        logger.warning(f"Model {model} failed: {result['error']}, trying next...")

    return {
        "output": "",
        "model": "",
        "agent_id": agent_id,
        "agent_name": info["name"],
        "branding": branding,
        "usage": {},
        "error": last_error or "all_models_failed",
        "tried": tried,
    }
