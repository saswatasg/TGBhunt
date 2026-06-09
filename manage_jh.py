#!/usr/bin/env python3
"""Job Hunt Assistant — entry point.

Usage:
    python3 manage_jh.py                # run the automation daemon
    python3 manage_jh.py runserver      # start the web UI
    python3 manage_jh.py migrate        # run migrations
"""
import os
import sys

os.environ["JH_MODE"] = "1"
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "linkedin.jh_settings")

if __name__ == "__main__":
    from django.core.management import execute_from_command_line

    if len(sys.argv) == 1:
        sys.argv = [sys.argv[0], "rundaemon"]

    execute_from_command_line(sys.argv)
