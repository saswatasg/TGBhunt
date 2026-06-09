#!/usr/bin/env python3
"""Job Hunt Assistant — single executable entry point."""
import os
import sys
import webbrowser
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

    from django.core.management import call_command
    call_command("migrate", "--no-input", verbosity=0)

    host = os.environ.get("JH_HOST", "127.0.0.1")
    port = os.environ.get("JH_PORT", "8000")
    url = f"http://{host}:{port}/"

    print(f"\n  Job Hunt Assistant running at {url}")
    print(f"  Data directory: {data_dir}\n")
    webbrowser.open(url)

    from django.core.management import execute_from_command_line
    sys.argv = ["manage.py", "runserver", "--noreload", f"{host}:{port}"]
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
