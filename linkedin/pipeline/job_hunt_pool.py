# linkedin/pipeline/job_hunt_pool.py
"""Job hunt candidate pool — finds relevant people to connect with.

Searches LinkedIn for people relevant to the user's target roles:
- Recruiters and hiring managers at target companies
- People in similar roles at target companies
- People with titles matching the target role
"""
from __future__ import annotations

import logging
import random

from linkedin_cli.exceptions import ReachedConnectionLimit

logger = logging.getLogger(__name__)


def _search_query_for(jhp) -> str:
    """Build a LinkedIn search query from the job hunt profile."""
    target_roles = jhp.target_roles or []
    target_companies = jhp.target_companies or []

    def quoted(items):
        return ' OR '.join(f'"{x}"' for x in items)

    def recruiter_quoted(items):
        return ' OR '.join(f'"recruiter {x}"' for x in items)

    def talent_quoted(items):
        return ' OR '.join(f'"talent {x}"' for x in items)

    patterns = []

    if target_companies:
        patterns.append(lambda: f'"recruiter" {quoted(target_companies[:3])}')

    if target_roles:
        patterns.extend([
            lambda: f'({recruiter_quoted(target_roles[:3])})',
            lambda: f'({talent_quoted(target_roles[:3])})',
            lambda: f'"hiring manager" {quoted(target_roles[:2])}',
            lambda: f'({quoted(target_roles[:3])})',
        ])
        if target_companies:
            patterns.append(
                lambda: f'({quoted(target_companies[:3])}) {quoted(target_roles[:2])}'
            )

    if not patterns:
        return ""

    used = getattr(_search_query_for, "_pattern_index", 0)
    _search_query_for._pattern_index = (used + 1) % len(patterns)
    return patterns[used]()


def _already_connected(session, public_id: str) -> bool:
    """Check if we already have a deal/lead for this profile."""
    from crm.models import Deal, Lead

    lead = Lead.objects.filter(public_identifier=public_id).first()
    if not lead:
        return False
    return Deal.objects.filter(lead=lead, campaign=session.campaign).exists()


def _create_lead_and_deal(session, public_id: str, profile_data: dict | None = None):
    """Create a Lead and Deal for a job hunt connection target."""
    from crm.models import Deal, Lead
    from linkedin_cli.enums import ProfileState

    lead, _ = Lead.objects.get_or_create(
        public_identifier=public_id,
        defaults={
            "linkedin_url": f"https://www.linkedin.com/in/{public_id}/",
            "urn": (profile_data or {}).get("urn", ""),
        },
    )
    deal, created = Deal.objects.get_or_create(
        lead=lead,
        campaign=session.campaign,
        defaults={"state": ProfileState.READY_TO_CONNECT},
    )
    if created:
        logger.info("[job_hunt] created deal for %s", public_id)
    return deal


def find_job_hunt_candidate(session, campaign) -> dict | None:
    """Find one person relevant to the job hunt to connect with."""
    from linkedin_cli.actions.search import search_people
    from linkedin_cli.api.client import enrich_profile

    jhp = getattr(campaign, "job_hunt_profile", None)
    if not jhp:
        logger.warning("[job_hunt] no JobHuntProfile for campaign %s", campaign)
        return None

    query = _search_query_for(jhp)
    logger.info("[job_hunt] searching: %s", query)

    try:
        profile_urls = search_people(session, query)
    except ReachedConnectionLimit:
        logger.warning("[job_hunt] search rate limited")
        return None
    except Exception as e:
        logger.warning("[job_hunt] search failed: %s", e)
        return None

    if not profile_urls:
        logger.info("[job_hunt] no results for: %s", query)
        return None

    from linkedin_cli.url_utils import url_to_public_id

    # Pick a random unseen candidate
    random.shuffle(profile_urls)
    for url in profile_urls:
        public_id = url_to_public_id(url)
        if not public_id:
            continue
        if _already_connected(session, public_id):
            continue

        # Create Lead + Deal for this candidate
        _create_lead_and_deal(session, public_id)

        return {"public_identifier": public_id}

    logger.info("[job_hunt] all candidates already connected")
    return None
