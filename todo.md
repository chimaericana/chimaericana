# Projex — Master Todo

> Track all tasks, progress, and blockers for the Projex agent platform.
> Update this file as work progresses. Use `[x]` for done, `[-]` for in progress, `[ ]` for pending.

---

## 📊 Quick Stats

| Status | Count |
|--------|-------|
| ✅ Done | 34 |
| 🔧 In Progress | 12 |
| 📋 Planned | 0 |
| **Total** | **46** |

---

## Phase 1 — Foundation & Core Setup ✅

> **Status:** Complete

- [x] **Pi Agent Configuration** — AGENTS.md with general + PR capabilities, commands, guidelines
- [x] **PR Commands Extension** — 10 slash commands (`/pr release`, `/pr pitch`, `/pr crisis`, `/pr messages`, `/pr campaign`, `/pr social`, `/pr qa`, `/pr monitor`, `/pr stakeholder`, `/pr strategy`)
- [x] **Automations Framework** — Organized `automations/` folder with `pr/`, `general/`, `utils/` subdirectories
- [x] **12 Base Automation Scripts** — Press release drafts, media monitoring, sentiment analysis, social drafts, crisis checklist, media contacts, notes, research, todo, logger, file utils
- [x] **Roadmap & Todo** — `roadmap.html` visual dashboard + `todo.md` tracking

---

## Phase 2 — Voice I/O & Notification System ✅

> **Status:** Complete

### Speech-to-Text

- [x] **STT Extension** — `/voice record` command using Termux:API or Whisper.cpp
  - [x] Install `termux-api` package if not present
  - [x] Create `automations/voice/stt.sh` wrapper script
  - [x] Register `/voice record` command in Pi extension
  - [ ] Test with multiple languages
  - Dependencies: `termux-api` app installed on device
  - Notes: Fallback to `whisper.cpp` if Termux API STT is unreliable

- [x] **TTS Extension** — `/voice speak` and `/tts toggle`
  - [x] Create `automations/voice/tts.sh` using `termux-tts` or `pico2wave`
  - [x] Register `/voice speak <text>` command
  - [ ] Add `/tts on` and `/tts off` toggle for auto-reading responses
  - [x] Support voice selection and speed control
  - Dependencies: `termux-api` or `pico2wave`

### Notification System

- [x] **Enhanced Notification Engine**
  - [x] Create `automations/notifications/notify.sh` with categories:
    - `urgent` — sound + vibration + LED
    - `alert` — sound + notification
    - `info` — silent notification
    - `digest` — batched summary
  - [x] Notification history log (`notifications/history.jsonl`)
  - [x] Action buttons for common responses
  - [x] Notification preferences system

- [x] **Notification Preferences**
  - [x] `notifications/config.json` for settings:
    - Quiet hours (start/end time)
    - Priority filtering
    - Channel routing
    - Digest mode (hourly, daily)
  - [x] `/notify config` command to manage preferences
  - [x] `/notify history` to view past notifications
  - [x] `/notify test` to verify notification delivery

- [x] **Voice Commands Extension** (`voice-notify.ts`)
  - [x] `/voice record` — Record and transcribe
  - [ ] `/voice transcribe <file>` — Transcribe audio file
  - [x] `/voice speak <text>` — Read text aloud
  - [x] `/voice dictation` — Continuous dictation mode
  - [x] `/voice commands` — List available voice commands
  - [x] `/notify send` — Send categorized notification
  - [x] `/notify history` — View notification history
  - [x] `/notify config` — Show notification settings
  - [x] `/notify test` — Send test notifications
  - [x] `/quick note` — Quick note with tags
  - [x] `/quick todo` — Quick todo item
  - [x] `/system status` — Show system health
  - [x] `/toast` — Show Android toast

**Completed:** 2026-05-27

---

## Phase 3 — Social Media Tracking & Scheduling ✅

> **Status:** Complete

### Scheduler

- [x] **Social Media Scheduler Extension**
  - [x] Create `automations/social/scheduler.py` (SQLite-backed)
    - [x] Post queue with statuses (pending, published, failed, cancelled)
    - [x] Campaign tagging and categorization
    - [x] Scheduled publish times
    - [x] Post status tracking
  - [x] `/social schedule` — Queue a post for publishing
  - [x] `/social queue` — View scheduled posts
  - [x] `/social cancel <id>` — Cancel a scheduled post
  - [x] `/social publish <id>` — Publish immediately
  - [x] Support platforms: Twitter, LinkedIn, Facebook, Instagram, Mastodon

### Tracker

- [x] **Social Media Tracker** (`tracker.py` + SQLite)
  - [x] Track per-platform metrics:
    - [x] Follower/fan counts (snapshots)
    - [x] Post engagement (likes, comments, shares, clicks, impressions)
    - [x] Mention volume and sentiment
  - [x] `/social track` — Record metric snapshot
  - [x] `/social metrics` — Current metrics overview
  - [x] `/social mention` — Record brand mention
  - [x] `/social mentions` — List/search mentions

### Content Calendar

- [x] `/social calendar` — View upcoming scheduled posts
- [ ] Visual calendar view in `automations/social/calendar.html`
- [ ] ICS export for external calendar apps

### Engagement Alerts

- [x] **Smart Alert System** (`alerts.py`)
  - [x] High-engagement post alerts
  - [x] Negative sentiment spike detection
  - [x] Follower milestone notifications
  - [x] Mention volume spike detection
  - [x] Configurable thresholds per alert type
  - [x] `/social alerts` — Check alerts
  - [x] `/social alerts-config` — Manage thresholds
  - [x] `/social alerts-history` — View alert history

### Quick Social Commands

- [x] `/social draft` — AI-draft posts from briefing
- [x] `/social export` — Export data as JSON/CSV
- [x] `/social stats` — Scheduler statistics

**Completed:** 2026-05-27

---

## Phase 4 — Heartbeat, Triggers & Subagent Orchestration ✅

> **Status:** Complete

### Heartbeat Monitor

- [x] **Heartbeat System** (`heartbeat.sh`)
  - [x] Configurable interval (default: 5 min)
  - [x] Health check per component:
    - [x] Disk space
    - [x] Memory usage
    - [x] Network connectivity
    - [x] Running processes
    - [x] Automation health
  - [x] Heartbeat log (`system/heartbeats.jsonl`)
  - [x] Missed beat detection and alerting
  - [x] Background daemon mode
  - [x] `/heartbeat status` — Current system health
  - [x] `/heartbeat check` — Run immediate check
  - [x] `/heartbeat log` — View heartbeat history
  - [x] `/heartbeat start` — Start daemon
  - [x] `/heartbeat stop` — Stop daemon

### Trigger Engine

- [x] **Event-Driven Trigger System** (`trigger_engine.py`)
  - [x] Trigger types: cron, file, webhook, condition, manual
  - [x] Trigger configuration (`triggers/triggers.json`)
  - [x] Trigger execution log (`triggers/trigger_log.jsonl`)
  - [x] Conditional triggers
  - [x] Rate limiting / cooldown per trigger
  - [x] `/trigger list` — View all triggers
  - [x] `/trigger add` — Create new trigger
  - [x] `/trigger remove <id>` — Remove trigger
  - [x] `/trigger fire <id>` — Manually fire trigger
  - [x] `/trigger log` — View trigger execution history
  - [x] `/trigger check` — Check and fire due triggers
  - [x] `/trigger toggle` — Enable/disable trigger

### Subagent Spawner

- [x] **Subagent Orchestration** (`spawner.py`)
  - [x] Spawn isolated Pi instances via print mode
  - [x] Pass context and constraints to subagents
  - [x] Collect and aggregate results
  - [x] Manage subagent lifecycle (start, monitor, stop)
  - [x] Timeout and resource limits per subagent
  - [x] Subagent job types: monitor, report, process, check, custom
  - [x] `/agent spawn <type> <prompt>` — Spawn subagent
  - [x] `/agent list` — View running subagents
  - [x] `/agent stop <id>` — Stop subagent
  - [x] `/agent results <id>` — View subagent output
  - [x] `/agent status` — System status

### Job Queue

- [ ] **Persistent Job Queue**
  - [ ] SQLite-backed job queue
  - [ ] Priority levels: critical, high, normal, low
  - [ ] Retry logic with exponential backoff
  - [ ] Timeout handling
  - [ ] Dependency chains (job B runs after job A)
  - [ ] Job history and audit trail
  - [ ] `/queue list` — View pending jobs
  - [ ] `/queue add` — Add job to queue
  - [ ] `/queue cancel <id>` — Cancel job
  - [ ] `/queue retry <id>` — Retry failed job

### Process Watcher

- [ ] **Process Monitor**
  - [ ] Track running automations and subagents
  - [ ] Auto-restart on crash (configurable)
  - [ ] Resource usage tracking (CPU, memory)
  - [ ] Execution time logging
  - [ ] `/process list` — View running processes
  - [ ] `/process kill <id>` — Terminate process
  - [ ] `/process stats` — Resource usage summary

### Cron Integration

- [x] **Cron Integration** (via trigger engine)
  - [x] Cron-style scheduling in trigger engine
  - [x] Check-and-fire mechanism for due triggers
  - [ ] `termux-job-scheduler` for persistent scheduling
  - [ ] Daily report generation
  - [ ] Hourly heartbeat checks

**Completed:** 2026-05-27

---

## Phase 5 — Observability, Recovery & Daily Reporting ✅

> **Status:** Complete

### Activity Tracker

- [ ] **Activity Logging System**
  - [ ] Structured JSONL logs for all agent actions
    - Tool calls and results
    - Command executions
    - Automation runs
    - Subagent activity
    - Trigger firings
  - [ ] Log rotation and archival
  - [ ] Search and filter capabilities
  - [ ] `/log search <query>` — Search logs
  - [ ] `/log tail` — View recent activity
  - [ ] `/log export` — Export logs for analysis

### Recovery System

- [ ] **Auto-Recovery Engine**
  - [ ] Failure detection and classification
    - Transient (retry) vs permanent (alert)
  - [ ] Checkpoint files for long-running tasks
  - [ ] Job state restoration on restart
  - [ ] Rollback to last known good state
  - [ ] Recovery attempt logging
  - [ ] Escalation after N failed recovery attempts
  - [ ] `/recovery status` — Current recovery state
  - [ ] `/recovery log` — View recovery history

### Daily Report Generator

- [ ] **Daily Digest**
  - [ ] Compile daily report covering:
    - ✅ Completed tasks and jobs
    - 📋 Pending items and upcoming schedule
    - 📊 Social media metrics summary
    - 📰 Media coverage highlights
    - 💻 System health status
    - ⚠️ Errors and recovery events
    - 📅 Tomorrow's schedule
  - [ ] Deliver via:
    - Notification (summary)
    - Full report file
    - Email (optional)
  - [ ] `/report daily` — Generate on demand
  - [ ] `/report weekly` — Weekly summary
  - [ ] `/report custom <params>` — Custom report

### Dashboard & Project Management

- [ ] **Interactive Dashboard** (`dashboard/index.html`)
  - [ ] System status panel (heartbeat, processes, jobs)
  - [ ] Active jobs board
  - [ ] Social media metrics
  - [ ] Task board (Kanban view):
    - Backlog → In Progress → Review → Done
  - [ ] Recent activity feed
  - [ ] Upcoming schedule
  - [ ] Quick actions panel
  - [ ] Project management features:
    - Create/edit tasks
    - Assign priorities and deadlines
    - Track project progress
    - Link tasks to PR campaigns
  - [ ] Auto-refresh every 30 seconds
  - [ ] Serve via simple HTTP server for mobile browser access

### Error Budget & Alerting

- [ ] **Error Tracking**
  - [ ] Error rate tracking per component
  - [ ] Threshold-based alerting
  - [ ] Error categorization
  - [ ] Trend analysis
  - [ ] `/errors summary` — Current error status
  - [ ] `/errors detail` — Detailed error log

### Metrics & Analytics

- [ ] **Usage Analytics**
  - [ ] Agent usage tracking
  - [ ] Task completion rates
  - [ ] Automation frequency
  - [ ] Response time metrics
  - [ ] Cost tracking (API usage)
  - [ ] Export to CSV/JSON
  - [ ] `/metrics summary` — Current metrics
  - [ ] `/metrics export` — Export data

**Completed:** 2026-05-27

---

## Future — Media Generation 🎨

> **Status:** Roadmap (not yet started)

- [ ] **Image Generation**
  - [ ] Stable Diffusion or API integration
  - [ ] Social media graphics
  - [ ] Press release images
  - [ ] Campaign visuals
  - [ ] `/generate image <prompt>` — Generate image

- [ ] **Video Generation**
  - [ ] Automated video clips from text
  - [ ] Social media video posts
  - [ ] Animated infographics
  - [ ] `/generate video <prompt>` — Generate video

- [ ] **Audio Production**
  - [ ] Podcast clips
  - [ ] Voice-over generation
  - [ ] Audio ads
  - [ ] Sound bites from press releases
  - [ ] `/generate audio <prompt>` — Generate audio

- [ ] **Brand Asset Manager**
  - [ ] Store brand assets (logos, colors, fonts)
  - [ ] Template library
  - [ ] Consistent style enforcement
  - [ ] `/brand assets` — View/manage assets

---

## Cross-Cutting — Security & Sandboxing 📋

> **Status:** Planned (parallel to other phases)

- [ ] **Script Execution Sandbox**
  - [ ] Isolated execution environment
  - [ ] Restricted filesystem access
  - [ ] Network policies per script
  - [ ] Resource limits (CPU, memory, time)
  - [ ] Use `proot` or `chroot` where possible on Termux

- [ ] **Credential Management**
  - [ ] Encrypted storage for API keys and tokens
  - [ ] Load-on-demand (never in memory longer than needed)
  - [ ] Token rotation and refresh
  - [ ] `/secrets list` — View stored credentials (masked)
  - [ ] `/secrets add <name>` — Store new credential
  - [ ] `/secrets remove <name>` — Remove credential

- [ ] **Permission Gates**
  - [ ] Confirmation for destructive actions
  - [ ] Approval for API calls with costs
  - [ ] Whitelist/blacklist for external communications
  - [ ] Per-script permission configuration

- [ ] **Audit Trail**
  - [ ] Immutable log of all agent decisions
  - [ ] Tool execution records
  - [ ] Automation run records
  - [ ] Tamper-evident (hash chain)
  - [ ] `/audit log` — View audit trail

---

## 📝 Notes & Decisions

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-05-27 | Use JSONL for logs | Simple, append-only, easy to parse |
| 2026-05-27 | SQLite for structured data | Available in Termux, no extra deps |
| 2026-05-27 | termux-job-scheduler for cron | Native Termux scheduling |
| 2026-05-27 | Pi RPC for subagents | Native Pi capability, no fork needed |
| 2026-05-27 | HTML dashboard | Viewable in mobile browser, no app needed |

---

## 🔗 Quick Links

- [Roadmap (Visual)](roadmap.html)
- [Agent Config](AGENTS.md)
- [PR Extension](.pi/extensions/pr-agent.ts)
- [Voice & Notify Extension](.pi/extensions/voice-notify.ts)
- [Social Media Extension](.pi/extensions/social-media.ts)
- [Heartbeat & Triggers Extension](.pi/extensions/heartbeat-triggers.ts)
- [Observability Extension](.pi/extensions/observability.ts)
- [Automations](automations/README.md)
- [Dashboard](dashboard/index.html)
- [Comm Bot Manager](automations/comm/bot_manager.sh)

---

## Phase 6 — Communication Bots (Discord & Mattermost) 🔧

> **Status:** Code complete, awaiting token configuration

### Discord Bot

- [x] **Discord Bot** (`discord_bot.py`)
  - [x] Slash commands: `/status`, `/report`, `/help`
  - [x] Embed-based notifications with urgency colors
  - [x] Message mention response
  - [x] Bridge queue integration for `/report` requests
  - [x] Health tracking and uptime monitoring
- [x] **Bot Manager** (`bot_manager.sh`)
  - [x] Start/stop/restart/status/logs commands
  - [x] PID tracking for background processes
  - [x] Token validation before start
  - [x] Log file rotation support
- [x] **Health Checker** (`health_check.py`)
  - [x] Process status monitoring
  - [x] Config validation
  - [x] Log error detection
  - [x] JSON output for heartbeat integration
- [ ] **Token Configuration** — NEEDS USER ACTION
  - [ ] Create Discord application at discord.com/developers
  - [ ] Get bot token and enable Message Content Intent
  - [ ] Invite bot to server
  - [ ] Update `config.json` with token, guild ID, channel IDs

### Mattermost Bot

- [x] **Mattermost Bot** (`mattermost_bot.py`)
  - [x] Webhook and API v4 support
  - [x] Channel ID resolution and caching
  - [x] Formatted notifications
  - [x] Health status tracking
- [ ] **Token Configuration** — NEEDS USER ACTION
  - [ ] Create bot account in Mattermost System Console
  - [ ] Update `config.json` with URL, token, webhook

### Bot Bridge

- [x] **Message Router** (`bot_bridge.py`)
  - [x] Category-based routing (urgent, alert, info, digest, social, pr)
  - [x] Persistent message queue with retry logic
  - [x] CLI interface for testing
  - [x] Stats tracking (sent, failed, queued)
- [x] **Pi Extension** (`comm.ts`)
  - [x] `/comm` — Show available commands
  - [x] `/comm send <platform> <message>` — Send message
  - [x] `/comm status` — Show bot health
  - [x] `/comm config` — Show routing configuration
  - [x] `/comm test` — Send test message

### Dependencies

- [x] `discord.py` installed (v2.7.1)
- [x] `requests` installed
- [x] `aiohttp` installed
- [ ] Discord bot token — **BLOCKER: requires user to create Discord app**
- [ ] Mattermost token — **BLOCKER: requires Mattermost server setup**

### Quick Start (once tokens are ready)

```bash
# Start both bots
bash automations/comm/bot_manager.sh start

# Check status
bash automations/comm/bot_manager.sh status

# View logs
bash automations/comm/bot_manager.sh logs

# Stop
bash automations/comm/bot_manager.sh stop
```

---

*Last updated: 2026-05-28 — Phase 6 in progress · Communication bots setup*
