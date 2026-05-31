# Agent Profiles

Self-contained AI agent profiles with isolated configuration, personality, memory, and tools.

## Architecture

Each agent profile is a **fully independent unit** that can:
- Run with its own system prompt and personality
- Access specific tools and skills
- Maintain isolated memory
- Be deployed independently (local → container → serverless)

### Directory Structure

```
profiles/
├── profile_manager.py          # Core manager: list, show, validate, spawn
├── schemas/
│   └── agent_profile.schema.json  # JSON schema for profile validation
├── templates/                   # Template for creating new profiles
│   ├── profile.json
│   └── system_prompt.md
├── comm/                        # Communications domain
│   ├── nexus/                   # 🎯 Communications Coordinator
│   ├── press/                   # 📰 PR Specialist
│   ├── echo/                    # 📣 Social Media Manager
│   ├── shield/                  # 🛡️ Crisis Communications
│   └── signal/                  # 📡 Media Relations
└── <domain>/                    # Future domains (devops, research, etc.)
    └── <agent>/
        ├── profile.json         # Agent configuration
        ├── system_prompt.md     # System prompt
        ├── memory/              # Isolated memory store
        ├── skills/              # Agent-specific skills
        └── extensions/          # Agent-specific extensions
```

## Profile Anatomy

### profile.json
The core configuration file:
- **id/name/role** — Identity
- **personality** — Traits, communication style, decision framework, perspectives, core beliefs
- **memory** — Storage type, path, retention, categories
- **skills** — Enabled skills with config
- **tools** — Scripts, APIs, builtins with permissions
- **extensions** — Custom extensions
- **commands** — Agent-specific commands
- **processing** — LLM provider, model, temperature, context window
- **deployment** — Local/container/modal/lambda with resource limits
- **relationships** — Reports to, collaborates with, delegates to
- **routing** — Trigger keywords, channels, auto-respond

### system_prompt.md
The agent's behavioral specification:
- Identity and core mandate
- Operating frameworks and decision trees
- Writing standards and tone rules
- Delegation and escalation protocols
- Memory tracking and learning goals
- Boundaries (what they DON'T do)

## Usage

```bash
# List all profiles
python3 profiles/profile_manager.py list

# Show full profile tree
python3 profiles/profile_manager.py tree

# Show detailed profile
python3 profiles/profile_manager.py show nexus

# Validate a profile
python3 profiles/profile_manager.py validate press

# Memory management
python3 profiles/profile_manager.py memory nexus stats
python3 profiles/profile_manager.py memory nexus rotate
python3 profiles/profile_manager.py memory nexus clear

# Build spawn context (for agent invocation)
python3 profiles/profile_manager.py spawn nexus "Route this message to Discord"
```

## Communication Agents

| Agent | Role | Speciality | Model Temp | Memory |
|-------|------|-----------|-----------|--------|
| **Nexus** 🎯 | Comm Coordinator | Routing, coordination, escalation | 0.3 | 500 entries, 60 days |
| **Press** 📰 | PR Specialist | Press releases, pitches, messaging | 0.4 | 500 entries, 90 days |
| **Echo** 📣 | Social Media Manager | Content, scheduling, engagement | 0.7 | 1000 entries, 90 days |
| **Shield** 🛡️ | Crisis Comms | Crisis response, holding statements | 0.2 | 200 entries, 365 days |
| **Signal** 📡 | Media Relations | Journalist outreach, coverage | 0.5 | 1000 entries, 365 days |

## Agent Hierarchy

```
                    ┌─────────────┐
                    │   NEXUS     │
                    │ Coordinator │
                    └──────┬──────┘
                           │ delegates to
           ┌───────────────┼───────────────┐
           │               │               │
    ┌──────┴──────┐ ┌──────┴──────┐ ┌──────┴──────┐
    │   PRESS     │ │    ECHO     │ │   SHIELD    │
    │ PR Specialist│ │ Social Mgr  │ │ Crisis Comms│
    └──────┬──────┘ └──────┬──────┘ └──────┬──────┘
           │               │               │
           └───────────────┼───────────────┘
                           │
                    ┌──────┴──────┐
                    │   SIGNAL    │
                    │ Media Relations
                    └─────────────┘
```

Nexus coordinates and delegates. Specialist agents handle their domains and report back. Signal supports both Press and Shield with media intelligence.

## Future Deployment

Profiles are designed for eventual serverless deployment:

### Current (Local)
- Python scripts on Termux
- JSONL memory files
- Direct tool execution

### Phase 2 (Container)
- Dockerfile per agent
- Isolated memory volumes
- Inter-agent communication via message queue

### Phase 3 (Serverless)
- Modal/Lambda deployment
- Auto-scaling based on queue depth
- Shared memory store (S3, DynamoDB)
- Event-driven invocation

### Migration Path
```
profiles/<agent>/
├── Dockerfile              # Container config (future)
├── modal_config.py         # Modal deployment (future)
├── profile.json            # Shared config (current)
└── ...
```

## Creating New Agents

1. Copy template: `cp profiles/templates/* profiles/<domain>/<agent>/`
2. Edit `profile.json` — set id, name, role, personality, tools
3. Write `system_prompt.md` — define behavior, frameworks, boundaries
4. Initialize memory: `mkdir profiles/<domain>/<agent>/memory`
5. Validate: `python3 profiles/profile_manager.py validate <agent_id>`

## Memory System

Each agent has isolated memory with configurable:
- **Storage type**: jsonl, sqlite, vector, hybrid
- **Max entries**: Auto-rotation when exceeded
- **Retention days**: Automatic cleanup of old entries
- **Summary interval**: Periodic summarization for context compression
- **Categories**: Organized memory by type (decisions, context, relationships, etc.)

Memory files:
- `conversations.jsonl` — All agent interactions
- `context.json` — Current context and state
- `<category>.jsonl` — Category-specific memory entries
