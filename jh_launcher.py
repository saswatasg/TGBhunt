#!/usr/bin/env python3
"""Job Hunt Assistant — tray app launcher. Double-click and go.

Starts the web server in a background thread, shows a menu bar icon
(via rumps), opens the browser to the setup wizard, and lets the user
start/stop the daemon from the menu or dashboard.
"""
from __future__ import annotations

import os
import sys
import threading
import time
from pathlib import Path


def main():
    root = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
    data_dir = root / "jh_data"
    data_dir.mkdir(parents=True, exist_ok=True)

    os.environ["JH_DATA_DIR"] = str(data_dir)
    os.environ["JH_MODE"] = "1"
    os.environ["DJANGO_SETTINGS_MODULE"] = "linkedin.jh_settings"
    os.chdir(root)

    import django
    django.setup()

    from django.core.management import call_command as dj
    dj("migrate", "--no-input", verbosity=0)

    import logging
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    host = os.environ.get("JH_HOST", "127.0.0.1")
    port = os.environ.get("JH_PORT", "8000")
    url = f"http://{host}:{port}/"

    # ── Background web server ──
    def _run_server():
        from django.core.management import execute_from_command_line
        sys.argv = ["manage.py", "runserver", "--noreload", f"{host}:{port}"]
        try:
            execute_from_command_line(sys.argv)
        except SystemExit:
            pass

    threading.Thread(target=_run_server, daemon=True).start()

    # ── Wait for server to come up ──
    import urllib.request
    for _ in range(40):
        try:
            urllib.request.urlopen(url, timeout=1)
            break
        except Exception:
            time.sleep(1)

    # ── Menu bar icon (rumps) ──
    import rumps
    from linkedin.daemon_controller import (
        is_running as daemon_running,
        start as daemon_start,
        stop as daemon_stop,
    )

    app = rumps.App("JH Assistant", title="🧠")
    _start_item = rumps.MenuItem("Start Automation")

    def _open_dashboard(_):
        import webbrowser
        webbrowser.open(f"{url}dashboard/job-hunt/")

    def _toggle_daemon(_):
        if daemon_running():
            daemon_stop()
            _start_item.title = "Start Automation"
        else:
            daemon_start()
            _start_item.title = "Stop Automation"

    _start_item.set_callback(_toggle_daemon)

    def _quit(_):
        daemon_stop()
        time.sleep(0.5)
        rumps.quit_application()

    app.menu = [
        rumps.MenuItem("Open Dashboard", callback=_open_dashboard),
        None,
        _start_item,
        None,
        rumps.MenuItem("Quit", callback=_quit),
    ]

    # ── Open browser ──
    import webbrowser
    webbrowser.open(url)

    # ── Run tray loop ──
    app.run()


if __name__ == "__main__":
    main()
