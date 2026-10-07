"""
apps/publisher/admin.py
────────────────────────
مدیریت پلتفرم‌ها، اعتبارنامه‌ها، پست‌ها و لاگ‌های انتشار.
اعتبارنامه رمزنگاری‌شده هرگز به‌صورت معنادار نمایش داده نمی‌شود (readonly).
"""

from django.contrib import admin

from .models import ChannelCredential, ChannelPost, ContentIdea, MusicTrack, Platform, PublishJob, PublishLog


@admin.register(ContentIdea)
class ContentIdeaAdmin(admin.ModelAdmin):
    list_display = ["title", "category", "source", "status", "product", "created_at"]
    list_filter = ["category", "source", "status"]
    search_fields = ["title", "description"]
    readonly_fields = ["created_at"]


@admin.register(MusicTrack)
class MusicTrackAdmin(admin.ModelAdmin):
    list_display = ["title", "mood", "is_active", "created_at"]
    list_filter = ["is_active", "mood"]
    search_fields = ["title"]


@admin.register(Platform)
class PlatformAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "is_active", "sort_order"]
    list_filter = ["is_active"]
    list_editable = ["is_active", "sort_order"]


@admin.register(ChannelCredential)
class ChannelCredentialAdmin(admin.ModelAdmin):
    list_display = ["platform", "chat_id", "is_active", "updated_at"]
    list_filter = ["is_active", "platform"]
    # متن رمزنگاری‌شده قابل ویرایش دستی نیست — از API ذخیره/ویرایش شود
    readonly_fields = ["credentials_encrypted", "created_at", "updated_at"]


class PublishLogInline(admin.TabularInline):
    model = PublishLog
    extra = 0
    readonly_fields = [
        "platform", "status", "error_message", "attempt_count",
        "external_message_id", "created_at", "updated_at",
    ]
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(ChannelPost)
class ChannelPostAdmin(admin.ModelAdmin):
    list_display = ["title", "content_type", "approval_status", "created_by", "created_at"]
    list_filter = ["content_type", "approval_status", "created_at"]
    search_fields = ["title", "body"]
    readonly_fields = ["created_at"]


@admin.register(PublishJob)
class PublishJobAdmin(admin.ModelAdmin):
    list_display = ["id", "post", "status", "created_by", "created_at"]
    list_filter = ["status"]
    readonly_fields = ["post", "status", "created_by", "created_at", "updated_at"]
    inlines = [PublishLogInline]

    def has_add_permission(self, request):
        return False


@admin.register(PublishLog)
class PublishLogAdmin(admin.ModelAdmin):
    list_display = ["job", "platform", "status", "attempt_count", "updated_at"]
    list_filter = ["status", "platform"]
    readonly_fields = [
        "job", "platform", "status", "response_data", "error_message",
        "attempt_count", "next_attempt_at", "external_message_id",
        "created_at", "updated_at",
    ]

    def has_add_permission(self, request):
        return False
