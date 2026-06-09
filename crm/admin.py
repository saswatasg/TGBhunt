# crm/admin.py
from django.contrib import admin
from django.utils.html import format_html

from crm.models import Deal, Lead


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = (
        "public_identifier", "linkedin_url_link",
        "disqualified", "has_embedding", "creation_date",
    )
    list_filter = ("disqualified",)
    search_fields = ("public_identifier", "linkedin_url", "urn")
    readonly_fields = ("creation_date", "update_date", "embedding")
    actions = ("mark_disqualified", "mark_eligible")

    def linkedin_url_link(self, obj):
        if not obj.linkedin_url:
            return ""
        return format_html('<a href="{}" target="_blank">{}</a>', obj.linkedin_url, obj.linkedin_url)
    linkedin_url_link.short_description = "LinkedIn URL"

    def has_embedding(self, obj):
        return obj.embedding is not None
    has_embedding.boolean = True

    @admin.action(description="Mark selected as DISQUALIFIED (won't requalify)")
    def mark_disqualified(self, request, queryset):
        n = queryset.update(disqualified=True)
        self.message_user(request, f"Marked {n} leads as disqualified.")

    @admin.action(description="Mark selected as ELIGIBLE (can requalify)")
    def mark_eligible(self, request, queryset):
        n = queryset.update(disqualified=False)
        self.message_user(request, f"Marked {n} leads as eligible.")


@admin.register(Deal)
class DealAdmin(admin.ModelAdmin):
    list_display = (
        "id", "lead_handle", "campaign", "state", "outcome",
        "connect_attempts", "backoff_hours", "update_date",
    )
    list_filter = ("state", "outcome", "campaign")
    search_fields = ("lead__public_identifier", "lead__linkedin_url", "reason")
    readonly_fields = ("creation_date", "update_date", "profile_summary", "chat_summary")
    raw_id_fields = ("lead", "campaign")
    actions = ("mark_failed", "mark_qualified", "reset_backoff")

    def lead_handle(self, obj):
        if obj.lead and obj.lead.linkedin_url:
            return format_html(
                '<a href="{}" target="_blank">{}</a>',
                obj.lead.linkedin_url, obj.lead.public_identifier,
            )
        return obj.lead.public_identifier if obj.lead else ""
    lead_handle.short_description = "LinkedIn Handle"

    @admin.action(description="Force state = Failed (skip outreach)")
    def mark_failed(self, request, queryset):
        n = queryset.update(state="Failed")
        self.message_user(request, f"Set state=Failed on {n} deals.")

    @admin.action(description="Force state = Qualified (re-queue for connect)")
    def mark_qualified(self, request, queryset):
        n = queryset.update(state="Qualified")
        self.message_user(request, f"Set state=Qualified on {n} deals.")

    @admin.action(description="Reset connect backoff (allow immediate retry)")
    def reset_backoff(self, request, queryset):
        n = queryset.update(backoff_hours=0, connect_attempts=0)
        self.message_user(request, f"Reset backoff on {n} deals.")
