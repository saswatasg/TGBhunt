# linkedin/agents/job_hunt.py
"""Job Hunt agent: reads conversation, returns a structured decision.

Single LLM call with structured output — no tool-calling loop.
The handler in tasks/follow_up.py executes the decision when
campaign.is_job_hunt is True.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Literal

import jinja2
from pydantic import BaseModel, Field, model_validator
from pydantic_ai import Agent

from linkedin.conf import PROMPTS_DIR
from linkedin.llm import get_llm_model, run_agent_sync

logger = logging.getLogger(__name__)


class JobHuntDecision(BaseModel):
    """Structured output from the job hunt agent."""

    action: Literal["send_message", "mark_completed", "wait"] = Field(
        description="What to do next for this connection.",
    )
    message: str | None = Field(
        default=None,
        description="The message to send. Required when action='send_message'.",
    )
    outcome: Literal[
        "converted", "not_interested", "wrong_fit", "unresponsive", "max_reached",
    ] | None = Field(
        default=None,
        description="Why the conversation ended. Required when action='mark_completed'.",
    )
    follow_up_hours: float = Field(
        description="Hours until next follow-up. Always required.",
    )

    @model_validator(mode="after")
    def _check_required_fields(self):
        if self.action == "send_message" and not self.message:
            raise ValueError("message is required when action='send_message'")
        if self.action == "mark_completed" and not self.outcome:
            raise ValueError("outcome is required when action='mark_completed'")
        return self


RECENT_MESSAGES_WINDOW = 6


def _humanize_age(when: datetime, now: datetime) -> str:
    delta = now - when
    if delta < timedelta(hours=1):
        return f"{max(int(delta.total_seconds() // 60), 1)}m ago"
    if delta < timedelta(days=1):
        return f"{int(delta.total_seconds() // 3600)}h ago"
    return f"{delta.days}d ago"


def _format_recent_messages(messages: list, now: datetime) -> str:
    if not messages:
        return "No recent messages."
    lines = []
    for m in messages:
        content = (m.content or "").strip()
        if not content:
            continue
        speaker = "Me" if m.is_outgoing else "Lead"
        prefix = f"{speaker} ({_humanize_age(m.creation_date, now)})" if m.creation_date else speaker
        lines.append(f"{prefix}: {content}")
    return "\n".join(lines) or "No recent messages."


def _days_since_last_outgoing(messages: list, now: datetime) -> int | None:
    timestamps = [m.creation_date for m in messages if m.is_outgoing and m.creation_date]
    if not timestamps:
        return None
    return max((now - max(timestamps)).days, 0)


def _count_unanswered_outgoing(messages: list) -> int:
    count = 0
    for m in reversed(messages):
        if m.is_outgoing:
            count += 1
        else:
            break
    return count


def _format_facts(summary: dict | None) -> str:
    facts = (summary or {}).get("facts") or []
    if not facts:
        return "(none yet)"
    return "\n".join(f"- {f}" for f in facts)


def _load_recent_messages(deal, limit: int = RECENT_MESSAGES_WINDOW) -> list:
    from chat.models import ChatMessage
    from django.contrib.contenttypes.models import ContentType

    ct = ContentType.objects.get_for_model(deal.lead.__class__)
    qs = (
        ChatMessage.objects
        .filter(content_type=ct, object_id=deal.lead_id)
        .order_by("-creation_date", "-pk")[:limit]
    )
    return list(reversed(list(qs)))


def _render_system_prompt(session, deal, recent_messages: list) -> str:
    from django.utils import timezone

    env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(PROMPTS_DIR)))
    template = env.get_template("job_hunt_agent.j2")

    campaign = deal.campaign
    self_prof = session.self_profile
    self_name = f"{self_prof.get('first_name', '')} {self_prof.get('last_name', '')}".strip() or session.django_user.username

    jhp = campaign.job_hunt_profile
    ctx = jhp.to_context() if jhp else {}

    now = timezone.now()
    return template.render(
        self_name=self_name,
        profile_summary=_format_facts(deal.profile_summary),
        chat_summary=_format_facts(deal.chat_summary),
        recent_messages=_format_recent_messages(recent_messages, now),
        today=now.strftime("%Y-%m-%d"),
        days_since_last_outgoing=_days_since_last_outgoing(recent_messages, now),
        unanswered_outgoing=_count_unanswered_outgoing(recent_messages),
        **ctx,
    )


def run_job_hunt_agent(session, deal) -> JobHuntDecision:
    """Read conversation and return a structured job hunt decision."""
    from linkedin.db.chat import sync_conversation

    public_id = deal.lead.public_identifier
    sync_conversation(session, public_id)
    deal.refresh_from_db(fields=["chat_summary", "profile_summary"])

    recent = _load_recent_messages(deal)
    system_prompt = _render_system_prompt(session, deal, recent)

    agent = Agent(
        get_llm_model(),
        output_type=JobHuntDecision,
        model_settings={"temperature": 0.7, "timeout": 60},
    )
    decision = run_agent_sync(agent.run(system_prompt)).output
    if decision is None:
        raise RuntimeError(f"LLM returned unparseable response for job hunt follow-up of {public_id}")

    logger.info("job_hunt agent for %s: %s", public_id, decision.action)
    return decision
