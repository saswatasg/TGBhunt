"""Shared daemon lifecycle — used by launcher tray and web API views.

Provides thread-safe start/stop/status for the background daemon loop.
The launcher imports this to control the daemon from the menu bar.
The web views import it to control the daemon from the dashboard.
"""
from __future__ import annotations

import logging
import threading

logger = logging.getLogger(__name__)

_daemon_thread: threading.Thread | None = None
_stop_event = threading.Event()


def is_running() -> bool:
    return _daemon_thread is not None and _daemon_thread.is_alive()


def start(session=None) -> bool:
    """Start the daemon in a background thread. No-op if already running."""
    global _daemon_thread
    if is_running():
        return False
    _stop_event.clear()

    from linkedin.daemon import run_daemon

    def _target():
        try:
            run_daemon(session=session, stop_event=_stop_event)
        except Exception:
            logger.exception("Daemon thread crashed")

    _daemon_thread = threading.Thread(target=_target, daemon=True, name="jh-daemon")
    _daemon_thread.start()
    logger.info("Daemon started in background thread")
    return True


def stop() -> bool:
    """Signal the daemon to stop. Returns True if it was running."""
    if not is_running():
        return False
    _stop_event.set()
    logger.info("Daemon stop signaled")
    return True


def wait_for_stop(timeout: float | None = None) -> bool:
    """Block until daemon stops. Returns True if stopped cleanly."""
    global _daemon_thread
    if _daemon_thread is None:
        return True
    _daemon_thread.join(timeout=timeout)
    if _daemon_thread.is_alive():
        return False
    _daemon_thread = None
    return True
