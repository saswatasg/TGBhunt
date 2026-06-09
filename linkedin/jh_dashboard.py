# linkedin/jh_dashboard.py
"""Job-hunt-only dashboard views."""
from __future__ import annotations

from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.urls import path
from django.utils import timezone


def _humanize_time(dt, now) -> str:
    delta = now - dt
    if delta < timedelta(hours=1):
        return f"{max(int(delta.total_seconds() // 60), 1)}m ago"
    if delta < timedelta(days=1):
        return f"{int(delta.total_seconds() // 3600)}h ago"
    return f"{delta.days}d ago"


@login_required(login_url="/admin/login/")
def job_hunt_dashboard(request):
    from chat.models import ChatMessage
    from crm.models import Deal, Outcome
    from django.contrib.contenttypes.models import ContentType
    from linkedin.models import JobHuntProfile

    profile = JobHuntProfile.objects.filter(
        campaign__users=request.user,
    ).select_related("campaign").first()
    if not profile:
        return render(request, "dashboard/job_hunt.html", {"profile": None, "stats": {}, "deals": [], "filter": "all"})

    campaign = profile.campaign
    filter_param = request.GET.get("filter", "all")

    qs = Deal.objects.filter(campaign=campaign).select_related("lead").order_by("-update_date")
    if filter_param == "pending":
        qs = qs.filter(state="Pending")
    elif filter_param == "connected":
        qs = qs.filter(state="Connected")
    elif filter_param == "completed":
        qs = qs.filter(state="Completed")

    now = timezone.now()
    ct = ContentType.objects.get_for_model(Deal._meta.get_field("lead").related_model())

    deals = []
    for d in qs[:50]:
        messages = ChatMessage.objects.filter(
            content_type=ct,
            object_id=d.lead_id,
        ).order_by("-creation_date")[:6]

        deals.append({
            "public_id": d.lead.public_identifier if d.lead else "?",
            "url": d.lead.linkedin_url if d.lead else "#",
            "state": d.state,
            "outcome": d.outcome or "",
            "updated": _humanize_time(d.update_date, now) if d.update_date else "",
            "messages": [
                {
                    "content": m.content or "",
                    "is_outgoing": m.is_outgoing,
                    "age": _humanize_time(m.creation_date, now) if m.creation_date else "",
                }
                for m in reversed(messages)
            ],
        })

    total = qs.count()
    stats = {
        "total": total,
        "messaged": qs.filter(state="Messaged").count(),
        "replied": qs.filter(state="Replied").count(),
        "converted": qs.filter(outcome=Outcome.CONVERTED).count(),
        "completed": qs.filter(state="Completed").count(),
    }

    return render(request, "dashboard/job_hunt.html", {
        "profile": profile,
        "stats": stats,
        "deals": deals,
        "filter": filter_param,
    })


urlpatterns = [
    path("", job_hunt_dashboard, name="dashboard_job_hunt"),
]
