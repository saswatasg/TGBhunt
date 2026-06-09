# linkedin/views/jh_setup.py
"""Combined setup wizard for job-hunt-only mode.

Collects LinkedIn credentials, LLM config, and job hunt profile
in a single multi-step flow.
"""
from __future__ import annotations

from django.contrib.auth import login as auth_login
from django.contrib.auth.models import User
from django.db import transaction
from django.shortcuts import redirect, render
from django.urls import path

from linkedin.conf import DEFAULT_CONNECT_DAILY_LIMIT, DEFAULT_FOLLOW_UP_DAILY_LIMIT
from linkedin.models import Campaign, JobHuntProfile, LinkedInProfile, SiteConfig


def _needs_setup() -> bool:
    return not JobHuntProfile.objects.exists()


def setup_wizard(request):
    if not _needs_setup():
        return redirect("/dashboard/job-hunt/")

    if request.method == "GET":
        return render(request, "setup/jh_setup.html", {
            "step": 1,
            "total_steps": 3,
            "provider_choices": SiteConfig.LLMProvider.choices,
        })

    step = int(request.POST.get("step", 1))

    if step == 1:
        linkedin_email = request.POST.get("linkedin_email", "").strip()
        linkedin_password = request.POST.get("linkedin_password", "")
        llm_provider = request.POST.get("llm_provider", "").strip()
        llm_model = request.POST.get("llm_model", "").strip()
        llm_api_key = request.POST.get("llm_api_key", "").strip()

        errors = {}
        if not linkedin_email:
            errors["linkedin_email"] = "LinkedIn email is required."
        if not linkedin_password:
            errors["linkedin_password"] = "LinkedIn password is required."
        if not llm_api_key:
            errors["llm_api_key"] = "LLM API key is required."
        if errors:
            return render(request, "setup/jh_setup.html", {
                "step": 1, "total_steps": 3,
                "errors": errors, "values": request.POST,
                "provider_choices": SiteConfig.LLMProvider.choices,
            })

        request.session["jh_linkedin_email"] = linkedin_email
        request.session["jh_linkedin_password"] = linkedin_password
        request.session["jh_llm_provider"] = llm_provider or SiteConfig.LLMProvider.GROQ
        request.session["jh_llm_model"] = llm_model or "llama-3.3-70b-versatile"
        request.session["jh_llm_api_key"] = llm_api_key

        return render(request, "setup/jh_setup.html", {
            "step": 2, "total_steps": 3,
            "provider_choices": SiteConfig.LLMProvider.choices,
        })

    elif step == 2:
        target_roles = [r.strip() for r in request.POST.get("target_roles", "").split(",") if r.strip()]
        resume_url = request.POST.get("resume_url", "").strip()
        current_role = request.POST.get("current_role", "").strip()
        years_exp = request.POST.get("years_experience", "").strip()
        skills = request.POST.get("skills", "").strip()

        if not target_roles:
            return render(request, "setup/jh_setup.html", {
                "step": 2, "total_steps": 3,
                "errors": {"target_roles": "At least one target role is required."},
                "values": request.POST,
                "provider_choices": SiteConfig.LLMProvider.choices,
            })

        request.session["jh_target_roles"] = target_roles
        request.session["jh_resume_url"] = resume_url
        request.session["jh_current_role"] = current_role
        request.session["jh_years_experience"] = years_exp
        request.session["jh_skills"] = skills

        return render(request, "setup/jh_setup.html", {
            "step": 3, "total_steps": 3,
            "provider_choices": SiteConfig.LLMProvider.choices,
        })

    elif step == 3:
        request.session["jh_achievements"] = request.POST.get("achievements", "").strip()
        request.session["jh_standout_points"] = request.POST.get("standout_points", "").strip()
        request.session["jh_education"] = request.POST.get("education", "").strip()
        request.session["jh_company"] = request.POST.get("current_company", "").strip()
        target_companies = [c.strip() for c in request.POST.get("target_companies", "").split(",") if c.strip()]
        target_locations = [l.strip() for l in request.POST.get("target_locations", "").split(",") if l.strip()]
        request.session["jh_target_companies"] = target_companies
        request.session["jh_target_locations"] = target_locations
        request.session["jh_additional_context"] = request.POST.get("additional_context", "").strip()

        try:
            with transaction.atomic():
                campaign = Campaign.objects.create(
                    name="Job Hunt",
                    is_job_hunt=True,
                )

                handle = request.session["jh_linkedin_email"].split("@")[0].lower()
                user, created = User.objects.get_or_create(
                    username=handle,
                    defaults={"is_staff": True, "is_active": True},
                )
                if created or not user.has_usable_password():
                    import secrets
                    pw = secrets.token_urlsafe(16)
                    user.set_password(pw)
                    user.save()
                    request.session["jh_temp_password"] = pw

                LinkedInProfile.objects.create(
                    user=user,
                    linkedin_username=request.session["jh_linkedin_email"],
                    linkedin_password=request.session["jh_linkedin_password"],
                    subscribe_newsletter=False,
                    connect_daily_limit=DEFAULT_CONNECT_DAILY_LIMIT,
                    follow_up_daily_limit=DEFAULT_FOLLOW_UP_DAILY_LIMIT,
                    legal_accepted=True,
                )
                campaign.users.add(user)

                cfg = SiteConfig.load()
                cfg.llm_provider = request.session.get("jh_llm_provider", SiteConfig.LLMProvider.GROQ)
                cfg.ai_model = request.session.get("jh_llm_model", "llama-3.3-70b-versatile")
                cfg.llm_api_key = request.session["jh_llm_api_key"]
                cfg.save()

                JobHuntProfile.objects.create(
                    campaign=campaign,
                    target_roles=request.session.get("jh_target_roles", []),
                    resume_url=request.session.get("jh_resume_url", ""),
                    current_role=request.session.get("jh_current_role", ""),
                    current_company=request.session.get("jh_company", ""),
                    years_experience=request.session.get("jh_years_experience", ""),
                    skills=request.session.get("jh_skills", ""),
                    target_companies=request.session.get("jh_target_companies", []),
                    target_locations=request.session.get("jh_target_locations", []),
                    standout_points=request.session.get("jh_standout_points", ""),
                    education=request.session.get("jh_education", ""),
                    achievements=request.session.get("jh_achievements", ""),
                    additional_context=request.session.get("jh_additional_context", ""),
                )

            auth_login(request, user)

            temp_password = request.session.pop("jh_temp_password", None)

            for k in list(request.session.keys()):
                if k.startswith("jh_"):
                    del request.session[k]

            return render(request, "setup/jh_success.html", {"temp_password": temp_password})

        except Exception as e:
            return render(request, "setup/jh_setup.html", {
                "step": 3, "total_steps": 3,
                "errors": {"__all__": f"Setup failed: {e}"},
                "values": request.POST,
                "provider_choices": SiteConfig.LLMProvider.choices,
            })

    return redirect("/setup/")


urlpatterns = [
    path("", setup_wizard, name="jh_setup"),
]
