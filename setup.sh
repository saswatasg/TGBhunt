#!/usr/bin/env bash
set -e

# ──────────────────────────────────────────────
#  Job Hunt Assistant – one‑click setup
#  Paste this whole block into your terminal.
# ──────────────────────────────────────────────

cd "$(dirname "$0")"

echo "=== 1/6 Installing Python packages ==="
pip3 install -r requirements.txt -q
pip3 install playwright -q

echo "=== 2/6 Installing Chromium browser (for LinkedIn automation) ==="
playwright install chromium 2>/dev/null || python3 -m playwright install chromium

echo "=== 3/6 Creating database ==="
python3 manage.py migrate --no-input

echo "=== 4/6 Starting web server ==="
echo ""
echo "  ┌──────────────────────────────────────────────────┐"
echo "  │                                                  │"
echo "  │   ✅ Open this URL in your browser:              │"
echo "  │   →  http://localhost:8000/                      │"
echo "  │                                                  │"
echo "  │   Complete the 3‑step setup wizard.              │"
echo "  │   After that, close this window and run:         │"
echo "  │   →  python3 manage.py rundaemon                 │"
echo "  │                                                  │"
echo "  └──────────────────────────────────────────────────┘"
echo ""

python3 manage.py runserver
