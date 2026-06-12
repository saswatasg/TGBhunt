# CLAUDE.md

## Rules

- **Python env**: Always use `python3` (system Python 3.9).
- **Commits**: No `Co-Authored-By` lines. Single-line messages (no body).
- **Dependencies**: Managed in `requirements.txt` (root).
- **No memory**: Never use the auto-memory system (no MEMORY.md, no memory files). All persistent context belongs here.
- **Error handling**: App should crash on unexpected errors. `try/except` only for expected, recoverable errors.
- **No API backward compat**: Project has no external users yet — don't preserve old Python APIs, function signatures, or import paths. Rename, delete, and rewrite freely; no shims.

## Project Overview

Job Hunt Assistant — self-hosted LinkedIn automation for job seekers. Playwright + stealth for browser automation, LinkedIn Voyager API for profile data, Django + Django Admin for CRM.

## Commands

```bash
# Web server
python3 manage.py runserver

# Start daemon
python3 manage.py rundaemon

# Build executable
python build.py

# Testing
pytest tests/
```

## Architecture (quick reference)

- **`linkedin_cli/`**: Django-free library of LinkedIn platform mechanics (browser nav/login, Voyager API, profile/conversation scrape, connect/message/status/thread verbs). Exposes a JSON verb CLI.
- **Entry**: `manage.py` — stock Django management. `rundaemon` command (migrate → onboard → validate → task queue loop). No args defaults to `rundaemon`. Onboarding logic in `onboarding.py`.
- **State machine**: `ProfileState` — QUALIFIED → READY_TO_CONNECT → PENDING → CONNECTED → COMPLETED / FAILED.
- **Task queue**: `Task` model. Three types: `connect`, `check_pending`, `follow_up`. Handlers in `linkedin/tasks/`.
- **Job Hunt mode**: `Campaign.is_job_hunt` flag. Setup via wizard at `/setup/`. Uses `JobHuntProfile` model. Searches LinkedIn for recruiters/hiring managers. Uses `job_hunt_agent.j2` prompt template.
- **Config**: `SiteConfig` DB singleton. `conf.py` for defaults.
- **Django apps**: `linkedin` (main), `crm` (Lead/Deal), `chat` (ChatMessage).
- **Data dir**: `tgb_data/` next to the executable, or `data/` in development.
