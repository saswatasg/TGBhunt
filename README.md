# TGB Hunt

> **Self-hosted LinkedIn automation for job seekers.** Connect with recruiters and hiring managers at your target companies, powered by AI.

[![License: GPLv3](https://img.shields.io/badge/License-GPLv3-blue.svg?style=flat-square)](LICENCE.md)

---

## How it works

1. **Tell it about you** — target roles, skills, experience, target companies
2. **It finds the right people** — searches LinkedIn for recruiters and hiring managers
3. **AI crafts messages** — personalized intros that start genuine conversations
4. **You get interviews** — the bot handles outreach, you focus on preparing

---

## Download & Run

[Download the latest release](https://github.com/saswatasg/TGBhunt/releases/latest)

1. Download `tgb-hunt-macos.zip`
2. Unzip → **right-click** `TGB Hunt.app` → **Open** (first launch only)
3. Browser opens — complete the 3-step wizard
4. Click **Start** on the dashboard
5. Done — the bot runs silently in the background

> **macOS security**: On first launch, right-click the app and choose *Open* instead of double-clicking. This is because the app isn't signed with an Apple Developer certificate (ad-hoc signed only).
>
> **First run**: The app may prompt you to run `playwright install chromium` in Terminal. This installs the browser engine (~350 MB, one-time).

**No terminal. No Python. No setup.**

---

## What you need

- **LinkedIn account** — email + password
- **API key** — [Groq](https://console.groq.com/keys) (free) or [OpenAI](https://platform.openai.com/api-keys)

---

## For developers

Clone the repo and run from source:

```bash
git clone https://github.com/saswatasg/TGBhunt
cd TGBhunt
pip3 install -r requirements.txt
pip3 install playwright
python3 -m playwright install chromium
python3 manage.py migrate
python3 manage.py runserver
```

| Command | What |
|---------|------|
| `python3 manage.py runserver` | Web UI |
| `python3 manage.py rundaemon` | Start bot |
| `python3 manage.py migrate` | Apply DB changes |
| `python build.py` | Build executable |

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
│   ├── tgb_dashboard.py
│   ├── tgb_settings.py
│   ├── tgb_urls.py
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
