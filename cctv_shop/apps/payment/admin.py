
from django.contrib import admin
from django.utils.html import format_html
from .models import PaymentTransaction


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ["id", "order", "amount", "status", "created_at"]
    list_filter = ["status"]
    search_fields = ["order__order_number"]
    readonly_fields = ["created_at", "updated_at"]
    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
