from django.contrib import admin
from django.utils.html import format_html
from .models import Order, OrderItem, StockReservation


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    fields = ["variant", "quantity", "unit_price", "confirmed_unit_price"]
    readonly_fields = ["unit_price"]


# ─── Order Admin ──────────────────────────────────────────────
from apps.orders.models import Order

try:
    admin.site.unregister(Order)
except Exception:
    pass

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display   = ["order_number", "get_customer_name", "get_customer_phone",
                      "status", "delivery_status", "courier_company",
                      "tracking_code", "total_amount", "created_at"]
    list_filter    = ["status", "delivery_status", "created_at"]
    list_editable  = ["delivery_status", "courier_company"]
    search_fields  = ["order_number", "user__phone", "user__first_name",
                      "user__last_name", "tracking_code"]
    readonly_fields = ["order_number", "created_at", "updated_at"]

    def get_customer_name(self, obj):
        name = obj.user.get_full_name()
        return name.strip() if name.strip() else "—"
    get_customer_name.short_description = "نام مشتری"

    def get_customer_phone(self, obj):
        return obj.user.phone or "—"
    get_customer_phone.short_description = "موبایل"

    fieldsets = (
        ("اطلاعات سفارش", {"fields": (
            "order_number", "user", "order_type", "status",
            "total_amount", "confirmed_amount", "paid_amount", "payment_method",
        )}),
        ("اطلاعات ارسال", {"fields": (
            "shipping_address",
            "courier_company", "tracking_code", "delivery_status",
            "shipped_at", "delivered_at",
        )}),
        ("یادداشت‌ها", {"fields": ("admin_notes", "customer_notes")}),
        ("تاریخ‌ها", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )
