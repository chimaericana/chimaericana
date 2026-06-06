# Communications Agents

Five specialized agents for managing all communication workflows.

## Team Roster

### 🎯 Metis — Communications Coordinator
- **Role**: Central hub, message routing, coordination
- **When to use**: Route messages, check bot status, escalate issues, coordinate agents
- **Trigger words**: `route`, `broadcast`, `status`, `notify all`, `coordinate`
- **System prompt**: `nexus/system_prompt.md`

### 📰 Press — PR Specialist
- **Role**: Press releases, media pitches, key messages, spokesperson prep
- **When to use**: Draft press releases, create media pitches, develop key messages
- **Trigger words**: `press release`, `media pitch`, `talking points`, `spokesperson`
- **System prompt**: `press/system_prompt.md`

### 📣 Clio — Social Media Manager
- **Role**: Social content creation, scheduling, engagement analysis
- **When to use**: Draft social posts, schedule content, analyze engagement
- **Trigger words**: `social post`, `schedule`, `engagement`, `content calendar`
- **System prompt**: `echo/system_prompt.md`

### 🛡️ Pallas — Crisis Communications
- **Role**: Crisis detection, response planning, holding statements, reputation management
- **When to use**: Crisis situations, negative press spikes, sentiment drops
- **Trigger words**: `crisis`, `breach`, `incident`, `negative press spike`
- **System prompt**: `shield/system_prompt.md`

### 📡 Iris — Media Relations
- **Role**: Journalist outreach, media lists, coverage monitoring, interview prep
- **When to use**: Pitch stories, build media lists, monitor coverage, prep for interviews
- **Trigger words**: `journalist`, `media pitch`, `coverage analysis`, `interview prep`
- **System prompt**: `signal/system_prompt.md`

## Workflow Examples

### Launching a Product
1. **Calliope** drafts the press release
2. **Iris** builds the media list and pitches journalists
3. **Clio** creates social media content across platforms
4. **Metis** coordinates the rollout timing and routes notifications
5. **Pallas** monitors for any negative reactions

### Handling a Crisis
1. **Pallas** takes the lead — detects, assesses, drafts holding statement
2. **Metis** routes the crisis alert to all channels
3. **Calliope** prepares the official statement (under Pallas's guidance)
4. **Iris** monitors media coverage and manages journalist inquiries
5. **Clio** prepares social media responses (using Pallas-approved messaging)

### Routine Communications
1. **Metis** routes incoming information to the right channel
2. **Clio** maintains the social content calendar
3. **Iris** monitors coverage and updates media relationships
4. **Calliope** works on upcoming announcements and campaigns

## Agent Memory

Each agent maintains isolated memory:

| Agent | Memory Capacity | Retention | Purpose |
|-------|----------------|-----------|---------|
| Metis | 500 entries | 60 days | Routing decisions, channel states, patterns |
| Calliope | 500 entries | 90 days | Releases, coverage, messaging effectiveness |
| Clio | 1000 entries | 90 days | Posts, engagement, trends, audience insights |
| Pallas | 200 entries | 365 days | Incidents, responses, lessons learned |
| Iris | 1000 entries | 365 days | Journalists, pitches, coverage history |

## Integration with Bot System

All agents connect through the communication bot infrastructure:

```
Agent Profile → profile_manager.py spawn
                     ↓
              System prompt + tools + memory
                     ↓
              Pi agent instance (isolated)
                     ↓
              Bot bridge → Discord / Mattermost
```

## Deployment

Current: Local Python execution via Pi agent
Future: Containerized deployment with isolated memory volumes and message queues
