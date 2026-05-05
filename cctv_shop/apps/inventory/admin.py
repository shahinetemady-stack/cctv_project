
from django.contrib import admin
from django.utils.html import format_html
from .models import StockAlert, StockMovement


@admin.register(StockAlert)
class StockAlertAdmin(admin.ModelAdmin):
    list_display = ["variant", "stock_at_alert", "is_resolved", "created_at"]
    list_filter = ["is_resolved"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ["variant", "movement_type", "quantity_change", "created_at"]
    list_filter = ["movement_type"]
    readonly_fields = ["created_at"]
    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
