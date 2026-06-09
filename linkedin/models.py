# linkedin/models.py
from __future__ import annotations

import logging
from datetime import date

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

logger = logging.getLogger(__name__)

# action_type → daily_limit_field
_RATE_LIMIT_FIELDS = {
    "connect": "connect_daily_limit",
    "follow_up": "follow_up_daily_limit",
}


class SiteConfig(models.Model):
    """Singleton model for global site configuration (LLM keys, etc.)."""

    class LLMProvider(models.TextChoices):
        OPENAI = "openai", "OpenAI"
        ANTHROPIC = "anthropic", "Anthropic"
        GOOGLE = "google", "Google"
        GROQ = "groq", "Groq"
        MISTRAL = "mistral", "Mistral"
        COHERE = "cohere", "Cohere"
        OPENAI_COMPATIBLE = "openai_compatible", "OpenAI-compatible"

    llm_provider = models.CharField(
        max_length=32,
        choices=LLMProvider.choices,
        default=LLMProvider.OPENAI,
    )
    llm_api_key = models.CharField(max_length=500, blank=True, default="")
    ai_model = models.CharField(max_length=200, blank=True, default="")
    llm_api_base = models.CharField(max_length=500, blank=True, default="")

    class Meta:
        app_label = "linkedin"
        verbose_name = "Site Configuration"
        verbose_name_plural = "Site Configuration"

    def __str__(self):
        return "Site Configuration"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls) -> "SiteConfig":
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class Campaign(models.Model):
    name = models.CharField(max_length=200, unique=True)
    users = models.ManyToManyField(User, blank=True, related_name="campaigns")
    product_docs = models.TextField(blank=True)
    campaign_objective = models.TextField(blank=True)
    booking_link = models.URLField(max_length=500, blank=True)
    is_job_hunt = models.BooleanField(default=False)
    action_fraction = models.FloatField(default=0.2)
    seed_public_ids = models.JSONField(default=list, blank=True)
    model_blob = models.BinaryField(null=True, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        app_label = "linkedin"


class LinkedInProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="linkedin_profile",
    )
    self_lead = models.ForeignKey(
        "crm.Lead",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    linkedin_username = models.CharField(max_length=200)
    linkedin_password = models.CharField(max_length=200)
    subscribe_newsletter = models.BooleanField(default=True)
    active = models.BooleanField(default=True)
    connect_daily_limit = models.PositiveIntegerField(default=20)
    follow_up_daily_limit = models.PositiveIntegerField(default=25)
    legal_accepted = models.BooleanField(default=False)
    cookie_data = models.JSONField(null=True, blank=True)
    newsletter_processed = models.BooleanField(default=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._exhausted: dict[str, date] = {}

    def can_execute(self, action_type: str) -> bool:
        """Check if the action is allowed under the daily rate limit."""
        # Reset exhaustion flag on a new day
        exhausted_date = self._exhausted.get(action_type)
        if exhausted_date is not None and exhausted_date != date.today():
            del self._exhausted[action_type]
        if action_type in self._exhausted:
            return False

        daily_field = _RATE_LIMIT_FIELDS[action_type]
        self.refresh_from_db(fields=[daily_field])

        daily_limit = getattr(self, daily_field)
        if daily_limit is not None and self._daily_count(action_type) >= daily_limit:
            return False

        return True

    def record_action(self, action_type: str, campaign: Campaign) -> None:
        """Persist a rate-limited action."""
        ActionLog.objects.create(
            linkedin_profile=self, campaign=campaign, action_type=action_type,
        )

    def mark_exhausted(self, action_type: str) -> None:
        """Mark the action type as externally exhausted for today."""
        self._exhausted[action_type] = date.today()
        logger.warning("Rate limit: %s externally exhausted for today", action_type)

    def _daily_count(self, action_type: str) -> int:
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        return ActionLog.objects.filter(
            linkedin_profile=self, action_type=action_type,
            created_at__gte=today_start,
        ).count()

    def __str__(self):
        return f"{self.user.username} ({self.linkedin_username})"

    class Meta:
        app_label = "linkedin"


class SearchKeyword(models.Model):
    campaign = models.ForeignKey(
        Campaign,
        on_delete=models.CASCADE,
        related_name="search_keywords",
    )
    keyword = models.CharField(max_length=500)
    used = models.BooleanField(default=False)
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = "linkedin"
        unique_together = [("campaign", "keyword")]

    def __str__(self):
        return self.keyword


class ActionLog(models.Model):
    class ActionType(models.TextChoices):
        CONNECT = "connect", "Connect"
        FOLLOW_UP = "follow_up", "Follow Up"

    linkedin_profile = models.ForeignKey(
        LinkedInProfile,
        on_delete=models.CASCADE,
        related_name="action_logs",
    )
    campaign = models.ForeignKey(
        Campaign,
        on_delete=models.CASCADE,
        related_name="action_logs",
    )
    action_type = models.CharField(max_length=20, choices=ActionType.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "linkedin"
        indexes = [
            models.Index(fields=["linkedin_profile", "action_type", "created_at"]),
        ]

    def __str__(self):
        return f"{self.action_type} by {self.linkedin_profile} at {self.created_at}"


class TaskQuerySet(models.QuerySet):
    def pending(self):
        return self.filter(status=Task.Status.PENDING).order_by("scheduled_at")

    def claim_next(self) -> "Task | None":
        return self.pending().filter(scheduled_at__lte=timezone.now()).first()

    def seconds_to_next(self) -> float | None:
        """Seconds until the next pending task, or None if queue is empty."""
        next_task = self.pending().only("scheduled_at").first()
        if next_task is None:
            return None
        return max((next_task.scheduled_at - timezone.now()).total_seconds(), 0)


class Task(models.Model):
    class TaskType(models.TextChoices):
        CONNECT = "connect"
        CHECK_PENDING = "check_pending"
        FOLLOW_UP = "follow_up"

    class Status(models.TextChoices):
        PENDING = "pending"
        RUNNING = "running"
        COMPLETED = "completed"
        FAILED = "failed"

    task_type = models.CharField(max_length=20, choices=TaskType.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    scheduled_at = models.DateTimeField()
    payload = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    objects = TaskQuerySet.as_manager()

    class Meta:
        app_label = "linkedin"
        indexes = [
            models.Index(fields=["status", "scheduled_at"]),
        ]

    def __str__(self):
        return f"{self.task_type} [{self.status}] scheduled={self.scheduled_at}"

    def mark_running(self):
        self.status = self.Status.RUNNING
        self.started_at = timezone.now()
        self.save(update_fields=["status", "started_at"])

    def mark_completed(self):
        self.status = self.Status.COMPLETED
        self.completed_at = timezone.now()
        self.save(update_fields=["status", "completed_at"])

    def mark_failed(self):
        self.status = self.Status.FAILED
        self.save(update_fields=["status"])


class JobHuntProfile(models.Model):
    campaign = models.OneToOneField(Campaign, on_delete=models.CASCADE, related_name="job_hunt_profile")
    target_roles = models.JSONField(default=list, help_text="List of target job roles")
    resume_url = models.URLField(max_length=500, blank=True)
    years_experience = models.CharField(max_length=100, blank=True)
    current_role = models.CharField(max_length=300, blank=True)
    current_company = models.CharField(max_length=300, blank=True)
    skills = models.TextField(blank=True, help_text="Key skills and technologies")
    target_companies = models.JSONField(default=list, blank=True)
    target_locations = models.JSONField(default=list, blank=True)
    standout_points = models.TextField(blank=True)
    message_tone = models.CharField(max_length=100, default="professional")
    education = models.TextField(blank=True)
    experience_details = models.TextField(blank=True)
    achievements = models.TextField(blank=True)
    additional_context = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Job Hunt: {', '.join(self.target_roles)}"

    def to_context(self) -> dict:
        """Return all fields as a flat dict for prompt rendering."""
        return {
            "target_roles": ", ".join(self.target_roles),
            "resume_url": self.resume_url,
            "years_experience": self.years_experience,
            "current_role": self.current_role,
            "current_company": self.current_company,
            "skills": self.skills,
            "target_companies": ", ".join(self.target_companies),
            "target_locations": ", ".join(self.target_locations),
            "standout_points": self.standout_points,
            "message_tone": self.message_tone,
            "education": self.education,
            "experience_details": self.experience_details,
            "achievements": self.achievements,
            "additional_context": self.additional_context,
        }

    class Meta:
        app_label = "linkedin"
