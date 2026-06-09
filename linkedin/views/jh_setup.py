# linkedin/views/jh_setup.py
"""Combined setup wizard for job-hunt-only mode.

Collects LinkedIn credentials, LLM config, and job hunt profile
in a single multi-step flow. Supports resume PDF upload + LLM parsing.
"""
from __future__ import annotations

import logging
from pathlib import Path

from django.conf import settings
from django.contrib.auth import login as auth_login
from django.contrib.auth.models import User
from django.db import transaction
from django.shortcuts import redirect, render
from django.urls import path

from linkedin.conf import DEFAULT_CONNECT_DAILY_LIMIT, DEFAULT_FOLLOW_UP_DAILY_LIMIT
from linkedin.models import Campaign, JobHuntProfile, LinkedInProfile, SiteConfig

logger = logging.getLogger(__name__)


def _needs_setup() -> bool:
    return not JobHuntProfile.objects.exists()


def _parse_resume_pdf(file_bytes: bytes, session=None) -> dict:
    """Parse uploaded PDF and return structured data dict."""
    from linkedin.resume_parser import (
        cleanup_pdf,
        extract_text_from_pdf,
        parse_resume_with_llm,
        save_uploaded_pdf,
    )

    data_root = Path(settings.DATABASES["default"]["NAME"]).parent
    pdf_path = save_uploaded_pdf(file_bytes, data_root)
    if not pdf_path:
        return {}

    raw_text = extract_text_from_pdf(str(pdf_path))
    cleanup_pdf(pdf_path)

    if not raw_text:
        return {}

    llm_kwargs = {}
    if session:
        llm_kwargs = {
            "llm_provider": session.get("jh_llm_provider"),
            "llm_api_key": session.get("jh_llm_api_key"),
            "ai_model": session.get("jh_llm_model"),
        }
    result = parse_resume_with_llm(raw_text, **llm_kwargs)
    result["_resume_text"] = raw_text
    return result


def _fill_session_from_parsed(session, parsed: dict) -> None:
    """Pre-fill session with parsed resume data (only non-empty values)."""
    mapping = {
        "jh_target_roles": "target_roles",
        "jh_current_role": "current_role",
        "jh_years_experience": "years_experience",
        "jh_skills": "skills",
        "jh_education": "education",
        "jh_achievements": "achievements",
        "jh_standout_points": "standout_points",
        "jh_target_companies": "target_companies",
        "jh_target_locations": "target_locations",
        "jh_company": "current_company",
        "jh_resume_text": "_resume_text",
    }
    for session_key, parse_key in mapping.items():
        val = parsed.get(parse_key)
        if val not in (None, "", [], {}):
            session[session_key] = val


def _render_step(request, step, extra=None):
    ctx = {
        "step": step,
        "total_steps": 3,
        "provider_choices": SiteConfig.LLMProvider.choices,
    }
    if extra:
        ctx.update(extra)
    return render(request, "setup/jh_setup.html", ctx)


def setup_wizard(request):
    if not _needs_setup():
        return redirect("/dashboard/job-hunt/")

    if request.method == "GET":
        return _render_step(request, 1)

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
            return _render_step(request, 1, {"errors": errors, "values": request.POST})

        request.session["jh_linkedin_email"] = linkedin_email
        request.session["jh_linkedin_password"] = linkedin_password
        request.session["jh_llm_provider"] = llm_provider or SiteConfig.LLMProvider.GROQ
        request.session["jh_llm_model"] = llm_model or "llama-3.3-70b-versatile"
        request.session["jh_llm_api_key"] = llm_api_key

        return _render_step(request, 2)

    elif step == 2:
        has_pdf = bool(request.FILES.get("resume_pdf"))

        if has_pdf:
            pdf_file = request.FILES["resume_pdf"]
            if not pdf_file.name.lower().endswith(".pdf"):
                return _render_step(request, 2, {
                    "errors": {"resume_pdf": "File must be a PDF."},
                    "values": request.POST,
                })

            parsed = _parse_resume_pdf(pdf_file.read(), request.session)
            if parsed:
                _fill_session_from_parsed(request.session, parsed)
                logger.info("Resume parsed: %d fields extracted", len(parsed))
            else:
                logger.warning("Resume parsing failed — falling back to manual entry")

        target_roles = [r.strip() for r in request.POST.get("target_roles", "").split(",") if r.strip()]
        if not target_roles:
            existing = request.session.get("jh_target_roles", [])
            if isinstance(existing, list) and existing:
                target_roles = existing
            else:
                errors = {"target_roles": "At least one target role is required."}
                if has_pdf:
                    errors["resume_pdf"] = "Could not extract target roles from PDF — enter them manually."
                return _render_step(request, 2, {"errors": errors, "values": request.POST})

        resume_url = request.POST.get("resume_url", "").strip()
        current_role = request.POST.get("current_role", "").strip() or request.session.get("jh_current_role", "")
        years_exp = request.POST.get("years_experience", "").strip() or request.session.get("jh_years_experience", "")
        skills = request.POST.get("skills", "").strip() or request.session.get("jh_skills", "")

        request.session["jh_target_roles"] = target_roles
        request.session["jh_resume_url"] = resume_url
        request.session["jh_current_role"] = current_role
        request.session["jh_years_experience"] = years_exp
        request.session["jh_skills"] = skills

        return _render_step(request, 3)

    elif step == 3:
        request.session["jh_achievements"] = request.POST.get("achievements", "").strip() or request.session.get("jh_achievements", "")
        request.session["jh_standout_points"] = request.POST.get("standout_points", "").strip() or request.session.get("jh_standout_points", "")
        request.session["jh_education"] = request.POST.get("education", "").strip() or request.session.get("jh_education", "")
        request.session["jh_company"] = request.POST.get("current_company", "").strip() or request.session.get("jh_company", "")
        target_companies_str = request.POST.get("target_companies", "").strip()
        if target_companies_str:
            target_companies = [c.strip() for c in target_companies_str.split(",") if c.strip()]
        else:
            target_companies = request.session.get("jh_target_companies", [])
        target_locations_str = request.POST.get("target_locations", "").strip()
        if target_locations_str:
            target_locations = [l.strip() for l in target_locations_str.split(",") if l.strip()]
        else:
            target_locations = request.session.get("jh_target_locations", [])
        request.session["jh_target_companies"] = target_companies
        request.session["jh_target_locations"] = target_locations
        request.session["jh_additional_context"] = request.POST.get("additional_context", "").strip() or request.session.get("jh_additional_context", "")

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
                    resume_text=request.session.get("jh_resume_text", ""),
                )

            auth_login(request, user)

            temp_password = request.session.pop("jh_temp_password", None)

            for k in list(request.session.keys()):
                if k.startswith("jh_"):
                    del request.session[k]

            return render(request, "setup/jh_success.html", {"temp_password": temp_password})

        except Exception as e:
            return _render_step(request, 3, {
                "errors": {"__all__": f"Setup failed: {e}"},
                "values": request.POST,
            })

    return redirect("/setup/")


urlpatterns = [
    path("", setup_wizard, name="jh_setup"),
]
