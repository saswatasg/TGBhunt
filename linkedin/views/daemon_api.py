"""REST API endpoints for daemon control from the dashboard."""

from __future__ import annotations

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods


@require_http_methods(["GET"])
def status_view(request):
    from linkedin.daemon_controller import is_running
    return JsonResponse({"running": is_running()})


@require_http_methods(["POST"])
def start_view(request):
    from django.contrib.auth.models import AnonymousUser
    if isinstance(request.user, AnonymousUser) or not request.user.is_authenticated:
        return JsonResponse({"error": "Not authenticated"}, status=403)

    from linkedin.daemon_controller import start as start_daemon

    session = getattr(request, "_linkedin_session", None)
    started = start_daemon(session=session)
    return JsonResponse({"running": started, "started": started})


@require_http_methods(["POST"])
def stop_view(request):
    from linkedin.daemon_controller import stop as stop_daemon

    stopped = stop_daemon()
    return JsonResponse({"running": False, "stopped": stopped})
