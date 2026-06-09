# Job Hunt Assistant

> **Self-hosted LinkedIn automation for job seekers.** Connect with recruiters and hiring managers at your target companies, powered by AI.

<div align="center">

[![License: GPLv3](https://img.shields.io/badge/License-GPLv3-blue.svg?style=flat-square)](LICENCE.md)

</div>

---

## How it works

1. **Tell it about you** — target roles, skills, experience, target companies
2. **It finds the right people** — searches LinkedIn for recruiters, hiring managers, and teams at your target companies
3. **AI crafts messages** — personalized intros that start genuine conversations
4. **You get interviews** — the bot handles the outreach, you focus on preparing

The AI agent manages up to 4 messages per connection (intro → discuss → pitch → close). You can monitor all conversations from the web dashboard.

---

## What you need

| # | What | Example |
|---|------|---------|
| 1 | **A LinkedIn account** | Your email + password |
| 2 | **An LLM API key** | Groq (free), OpenAI, Anthropic |

That's it. No lead lists, no CRM setup, no complex configuration.

---

## Quick Start

### Prerequisites

- Python 3.9+
- [Playwright browsers](https://playwright.dev/python/docs/install)

### Setup

```bash
# Clone the repo
git clone <your-repo-url>
cd TGBconnect

# Install dependencies
pip install django scikit-learn scipy jinja2 pydantic pydantic-ai termcolor

# Install Playwright browsers
playwright install chromium

# Run migrations
python manage.py migrate

# Start the web setup
python manage.py runserver
```

Open **http://localhost:8000/** in your browser and complete the 3-step setup wizard:

1. **LinkedIn credentials + AI provider** — your login and LLM API key
2. **Target roles** — what jobs you want (e.g., "Senior Software Engineer, Engineering Manager")
3. **Your story** — achievements, skills, target companies, resume link

### Run the daemon

Once setup is complete:

```bash
# Start the automation daemon
python manage.py rundaemon
```

The daemon logs into LinkedIn, starts finding relevant people, sends connection requests, and manages follow-up conversations.

### View your dashboard

Keep the web UI running in another terminal:

```bash
python manage.py runserver
```

Visit **http://localhost:8000/dashboard/job-hunt/** to see your progress.

---

## Project Structure

```
├── linkedin/
│   ├── agents/              # AI agents (job hunt conversations)
│   ├── browser/             # LinkedIn browser automation
│   ├── daemon.py            # Task queue worker loop
│   ├── jh_dashboard.py      # Job hunt web dashboard
│   ├── jh_settings.py       # Django settings
│   ├── jh_urls.py           # URL routing
│   ├── models.py            # Campaign, JobHuntProfile, etc.
│   ├── pipeline/            # Candidate search (job hunt pool)
│   ├── tasks/               # Connect, follow-up, check pending
│   └── views/jh_setup.py    # Setup wizard
├── build.py                 # Build single executable (PyInstaller)
├── jh_launcher.py           # Entry point for the executable
├── manage.py                # Entry point (dev)
└── README.md
```

---

## Single Executable (for friends)

You can build a standalone executable for macOS (no Python required):

```bash
# Install Playwright + Chromium first
pip install playwright
playwright install chromium

# Build the executable
python build.py

# The executable is at dist/jh_assistant/jh_assistant (~205MB)
# Your friends can run it directly — it starts a web server
# and opens their browser to the setup wizard.
```

Windows/Linux builds: change `build.py` to match your platform's Chromium path, or build directly on the target OS.

---

## FAQ

**Is this undetectable?**
The bot uses Playwright with stealth plugins to mimic real user behavior. It respects LinkedIn's rate limits and operates within your daily connection limit.

**Can I get banned?**
LinkedIn's ToS prohibit automation. Use at your own risk. Keep daily limits low (20 connects/day) and the bot uses human-like timing to minimize risk.

**What LLM providers are supported?**
Groq, OpenAI, Anthropic, Google, Mistral, Cohere, or any OpenAI-compatible endpoint. Groq offers generous free tier access.

**Does the bot apply to jobs for me?**
No. It connects you with people (recruiters, hiring managers, team leads) so you can have conversations and find opportunities. You handle the actual interviews.

---

## License

[GNU GPLv3](LICENCE.md)

## Legal

Not affiliated with LinkedIn. Use at your own risk — no liability assumed.
