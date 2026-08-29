
from django.contrib import admin
from .models import NotificationLog


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ["recipient_address", "channel", "status", "created_at"]
    list_filter = ["status", "channel"]
    readonly_fields = ["created_at", "updated_at"]
    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
