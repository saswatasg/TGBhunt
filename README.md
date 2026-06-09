# Job Hunt Assistant

> **Self-hosted LinkedIn automation for job seekers.** Connect with recruiters and hiring managers at your target companies, powered by AI.

[![License: GPLv3](https://img.shields.io/badge/License-GPLv3-blue.svg?style=flat-square)](LICENCE.md)

---

## How it works

1. **Tell it about you** — target roles, skills, experience, target companies
2. **It finds the right people** — searches LinkedIn for recruiters and hiring managers
3. **AI crafts messages** — personalized intros that start genuine conversations
4. **You get interviews** — the bot handles outreach, you focus on preparing

---

## What you need

- **LinkedIn account** — email + password
- **API key** — [Groq](https://console.groq.com/keys) (free) or [OpenAI](https://platform.openai.com/api-keys)
- **Python 3** installed — [download](https://www.python.org/downloads/)

---

## Quick Start

### 1. Download & install

Open **Terminal** (Mac) or **Command Prompt** (Windows) and paste:

```bash
# Download the code
git clone https://github.com/saswatasg/TGBhunt
cd TGBhunt

# Install everything
pip3 install -r requirements.txt
pip3 install playwright
python3 -m playwright install chromium
python3 manage.py migrate
```

### 2. Start the setup wizard

```bash
python3 manage.py runserver
```

Open **http://localhost:8000/** in your browser and complete the 3-step wizard.

### 3. Start the bot

Press **Ctrl+C** in the terminal, then run:

```bash
python3 manage.py rundaemon
```

The bot logs into LinkedIn, searches for relevant people, sends connection requests with AI-written messages, and follows up automatically.

### 4. Check progress

Open a **second terminal window** and run:

```bash
cd TGBhunt && python3 manage.py runserver
```

Visit **http://localhost:8000/dashboard/job-hunt/** to see your conversations.

> **Tip:** Keep the daemon running 24/7 for best results. Stop anytime with Ctrl+C — progress is saved.

---

## Commands cheat sheet

| What | Command |
|------|---------|
| Web UI | `python3 manage.py runserver` |
| Start the bot | `python3 manage.py rundaemon` |
| Apply DB changes | `python3 manage.py migrate` |
| Create admin login | `python3 manage.py createsuperuser` |

---

## FAQ

**Is this undetectable?**
The bot uses Playwright with stealth plugins and respects LinkedIn's rate limits to minimize risk.

**Can I get banned?**
LinkedIn's ToS prohibit automation. Use at your own risk. Keep daily limits low (20 connects/day).

**What AI providers work?**
Groq (free tier), OpenAI, Anthropic, Google, Mistral, Cohere, or any OpenAI-compatible endpoint.

**Does the bot apply to jobs?**
No. It connects you with people (recruiters, hiring managers, team leads) so you can have conversations. You handle interviews.

---

## Project Structure

```
├── linkedin/          # Main Django app
│   ├── agents/        # AI conversation agents
│   ├── browser/       # LinkedIn browser automation
│   ├── daemon.py      # Background task worker
│   ├── jh_dashboard.py
│   ├── jh_settings.py
│   ├── jh_urls.py
│   ├── models.py      # Campaign, JobHuntProfile
│   ├── pipeline/      # Candidate search
│   ├── tasks/         # Connect, follow-up, check pending
│   └── views/         # Setup wizard
├── crm/               # Lead & Deal models
├── chat/              # Message models
├── linkedin_cli/      # LinkedIn platform library
├── manage.py          # Entry point
├── setup.sh           # One-click install script
├── build.py           # Build single executable
├── requirements.txt
└── README.md
```

---

## License

[GNU GPLv3](LICENCE.md) — Not affiliated with LinkedIn. Use at your own risk.
