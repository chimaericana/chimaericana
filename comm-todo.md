# Projex — Communication Bots Todo

> Discord & Mattermost bot integration for Projex agent platform.
> Replace native apps with lightweight bots to free ~400-600 MB RAM.

---

## 📊 Quick Stats

| Status | Count |
|--------|-------|
| ✅ Done | 8 |
| 🔧 In Progress | 0 |
| 📋 Planned | 0 |
| **Total** | 8 |

---

## Phase 1 — Infrastructure Setup

- [x] **Directory Structure** — `automations/comm/` with bot configs
- [x] **Config System** — `comm/config.json` for tokens, channels, routing rules
- [x] **Requirements** — `comm/requirements.txt` for Python deps (discord.py, aiohttp, requests installed)

## Phase 2 — Discord Bot

- [x] **`discord_bot.py`** — Lightweight discord.py bot
  - [x] Connect to Discord via token
  - [x] Post notifications to designated channels
  - [x] Slash commands: `/status`, `/report`, `/help`
  - [x] Health check endpoint
  - [x] Error handling and reconnection logic

## Phase 3 — Mattermost Bot

- [x] **`mattermost_bot.py`** — Mattermost API bot
  - [x] Connect via bot token or webhook
  - [x] Post to team channels
  - [x] Listen for mentions/commands
  - [x] Health check

## Phase 4 — Bot Bridge (Message Router)

- [x] **`bot_bridge.py`** — Central message router
  - [x] Accept messages from Projex notifications
  - [x] Route to correct platform/channel based on config
  - [x] Priority filtering (urgent → both, info → Discord only, etc.)
  - [x] Queue for offline delivery
  - [x] CLI interface for testing

## Phase 5 — Pi Extension

- [x] **`.pi/extensions/comm.ts`** — Pi slash commands
  - [x] `/comm send <platform> <message>`
  - [x] `/comm status` — Bot health
  - [x] `/comm config` — Show/edit config
  - [x] `/comm test` — Test message to all platforms

## Phase 6 — Integration

- [ ] **Hook into heartbeat** — Send health alerts via bots
- [ ] **Hook into notifications** — Route `/notify` to bot channels
- [ ] **Hook into social** — Forward social alerts to comm channels
- [ ] **Hook into PR** — Send PR campaign updates

## Phase 7 — Documentation

- [x] **Setup guide** — How to create bot tokens and configure
- [x] **README.md** in `automations/comm/`
- [ ] **Update AGENTS.md** with new `/comm` commands

## Phase 8 — Testing & Optimization

- [ ] **Memory footprint test** — Verify <15 MB total
- [ ] **Reconnection test** — Network drop recovery
- [ ] **Rate limit handling** — Discord/Mattermost API limits
- [ ] **Log rotation** — Prevent log growth on low-storage device

**Completed:** 2026-05-28 — Phases 1-7 complete, Phase 8 pending activation

---

## 📝 Notes

| Decision | Rationale |
|----------|-----------|
| discord.py | Mature, async, low memory footprint |
| Mattermost webhook + API | No heavy client needed, webhook for send, API for receive |
| JSON config | Consistent with Projex patterns |
| Bridge pattern | Single entry point for all outbound messages |

---

*Created: 2026-05-28*
