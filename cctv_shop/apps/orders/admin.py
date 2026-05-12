from django.contrib import admin
from django.utils.html import format_html
from .models import Order, OrderItem, StockReservation


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    fields = ["variant", "quantity", "unit_price", "confirmed_unit_price"]
    readonly_fields = ["unit_price"]


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ["order_number", "user_display", "status_display",
                    "shipping_display", "total_display", "tracking_display", "created_at"]
    list_filter  = ["status", "order_type", ("created_at", admin.DateFieldListFilter)]
    search_fields = ["order_number", "user__phone", "user__email", "tracking_code"]
    readonly_fields = ["order_number", "created_at", "updated_at", "payment_ref_id", "paid_at"]
    inlines = [OrderItemInline]
    ordering = ["-created_at"]
    list_per_page = 25
    actions = ["mark_as_ready", "mark_as_paid"]

    fieldsets = (
        ("اطلاعات سفارش", {
            "fields": ("order_number", "user", "order_type", "status"),
        }),
        ("مالی", {
            "fields": ("total_amount", "confirmed_amount", "paid_amount", "payment_method"),
        }),
        ("ارسال و رهگیری", {
            "fields": ("shipping_method", "freight_company", "tracking_code", "shipping_address"),
        }),
        ("یادداشت‌ها", {
            "fields": ("customer_notes", "admin_notes"),
        }),
        ("پرداخت آنلاین", {
            "fields": ("payment_link", "payment_deadline", "payment_ref_id", "paid_at"),
            "classes": ("collapse",),
        }),
        ("تاریخ‌ها", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    def user_display(self, obj):
        try:
            return str(obj.user.phone or obj.user.email or obj.user.pk)
        except Exception:
            return "-"
    user_display.short_description = "کاربر"

    def status_display(self, obj):
        colors = {
            "pending": "#FF9500", "confirmed": "#0066FF",
            "awaiting_payment": "#8B5CF6", "paid": "#00C896",
            "ready_to_ship": "#00C896", "shipped": "#0066FF",
            "cancelled": "#FF3B3B",
        }
        labels = {
            "pending": "در انتظار",
            "confirmed": "تأیید شده",
            "awaiting_payment": "در انتظار پرداخت",
            "paid": "پرداخت شده",
            "ready_to_ship": "آماده ارسال",
            "shipped": "ارسال شده",
            "cancelled": "لغو شده",
        }
        color = colors.get(obj.status, "#888")
        label = labels.get(obj.status, obj.status)
        return format_html(
            '<span style="background:{};color:white;padding:2px 8px;'
            'border-radius:4px;font-size:11px">{}</span>',
            color, label
        )
    status_display.short_description = "وضعیت"

    def shipping_display(self, obj):
        labels = {"post": "پست", "courier": "پیک", "freight": "باربری"}
        method = getattr(obj, 'shipping_method', '') or ''
        label = labels.get(method, method or "-")
        freight = getattr(obj, 'freight_company', '') or ''
        if method == "freight" and freight:
            label = label + " (" + freight + ")"
        return label
    shipping_display.short_description = "ارسال"

    def total_display(self, obj):
        amount = int(obj.confirmed_amount or obj.total_amount or 0)
        return str(amount) + " ت"
    total_display.short_description = "مبلغ"

    def tracking_display(self, obj):
        code = getattr(obj, 'tracking_code', '') or ''
        if code:
            return format_html(
                '<span style="font-family:monospace;color:#00C896">{}</span>',
                code
            )
        return "-"
    tracking_display.short_description = "کد رهگیری"

    @admin.action(description="آماده ارسال")
    def mark_as_ready(self, request, queryset):
        updated = queryset.update(status="ready_to_ship")
        self.message_user(request, str(updated) + " سفارش به آماده ارسال تغییر یافت.")

    @admin.action(description="ثبت پرداخت دستی")
    def mark_as_paid(self, request, queryset):
        updated = queryset.update(status="paid")
        self.message_user(request, str(updated) + " سفارش پرداخت شده ثبت شد.")


@admin.register(StockReservation)
class StockReservationAdmin(admin.ModelAdmin):
    list_display = ["variant", "order", "quantity", "reserved_until", "is_released"]
    list_filter  = ["is_released"]
    readonly_fields = ["released_at", "created_at", "updated_at"]
