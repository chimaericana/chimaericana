# Automations

Reusable scripts for repeatable actions across PR and general workflows.

## Structure

```
automations/
├── pr/          # Public Relations automations
├── general/     # General purpose automations
└── utils/       # Shared utilities and helpers
```

## Usage

```bash
# Run any script
bash automations/pr/draft_release.sh
python automations/pr/monitor_coverage.py
npx tsx automations/pr/social_draft.ts

# Make scripts executable
chmod +x automations/**/*.sh
chmod +x automations/**/*.py
```

## Scripts

### PR Automations (`pr/`)
| Script | Language | Description |
|--------|----------|-------------|
| `draft_release.sh` | Bash | Generate press release from template + briefing |
| `monitor_coverage.py` | Python | Fetch and summarize media mentions from RSS feeds |
| `media_list.sh` | Bash | Manage and search media contacts database |
| `social_draft.ts` | TypeScript | Generate platform-specific social posts from a briefing |
| `crisis_checklist.sh` | Bash | Generate crisis communication checklist |
| `sentiment.py` | Python | Analyze text sentiment for media coverage |

### General Automations (`general/`)
| Script | Language | Description |
|--------|----------|-------------|
| `notes.sh` | Bash | Quick note-taking with date and tags |
| `research.sh` | Bash | Save research findings with source metadata |
| `organize.py` | Python | Organize files by type, date, or custom rules |
| `summary.ts` | TypeScript | Generate text summaries from files or stdin |
| `todo.sh` | Bash | Simple todo list with priorities and status |
| `export_session.sh` | Bash | Export Pi session notes to a document |

### Utilities (`utils/`)
| Script | Language | Description |
|--------|----------|-------------|
| `text_utils.py` | Python | Common text manipulation helpers |
| `file_utils.sh` | Bash | File and directory utility functions |
| `config.ts` | TypeScript | Config loader for automation scripts |
| `logger.py` | Python | Structured logging for all Python scripts |

## Adding New Scripts

1. Place the script in the appropriate folder
2. Make it executable: `chmod +x automations/<category>/<script>`
3. If it has dependencies, add a `requirements.txt` (Python) or `package.json` (TS) in the same folder
4. Document it in this README

## Guidelines

- Scripts should be **idempotent** — safe to run multiple times
- Accept **stdin or file arguments** when processing text
- Output should be **machine-readable** (JSON) or **clean human-readable** format
- Use **consistent logging** via `utils/logger.py` or `utils/file_utils.sh`
- Include a **`--help` flag** in every script
- Keep dependencies minimal — prefer standard library where possible
