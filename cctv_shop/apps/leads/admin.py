"""
apps/leads/admin.py — ادمین جنگو برای مخاطبان و کمپین‌ها
"""
from django.contrib import admin

from .models import CampaignSend, Lead, LeadCampaign, LeadSettings, ScraperRun


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ["phone", "name", "city", "source", "category", "keyword", "status", "sms_count", "created_at"]
    list_filter = ["source", "category", "status", "city"]
    search_fields = ["phone", "name", "source_title"]
    readonly_fields = ["created_at", "updated_at", "last_sms_at"]


class CampaignSendInline(admin.TabularInline):
    model = CampaignSend
    extra = 0
    readonly_fields = ["lead", "ok", "error", "sent_at"]
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(LeadCampaign)
class LeadCampaignAdmin(admin.ModelAdmin):
    list_display = ["name", "status", "total_targets", "sent_count", "failed_count", "created_at"]
    list_filter = ["status"]
    inlines = [CampaignSendInline]
    readonly_fields = ["total_targets", "sent_count", "failed_count", "started_at", "finished_at"]


@admin.register(ScraperRun)
class ScraperRunAdmin(admin.ModelAdmin):
    list_display = ["source", "status", "new_count", "seen_count", "started_at", "finished_at"]
    list_filter = ["source", "status"]
    readonly_fields = ["source", "status", "new_count", "seen_count", "message", "started_at", "finished_at"]

    def has_add_permission(self, request):
        return False


@admin.register(LeadSettings)
class LeadSettingsAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return not LeadSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
