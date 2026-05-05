
from django.contrib import admin
from django.utils.html import format_html
from .models import Order, OrderItem, StockReservation


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    fields = ["variant", "quantity", "unit_price", "confirmed_unit_price"]
    readonly_fields = ["unit_price"]


class StockReservationInline(admin.TabularInline):
    model = StockReservation
    extra = 0
    readonly_fields = ["variant", "quantity", "reserved_until", "is_released"]
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ["order_number", "user", "status", "order_type", "total_amount", "created_at"]
    list_filter = ["status", "order_type"]
    search_fields = ["order_number", "user__email"]
    readonly_fields = ["order_number", "created_at", "updated_at", "payment_ref_id", "paid_at"]
    inlines = [OrderItemInline, StockReservationInline]
    ordering = ["-created_at"]


@admin.register(StockReservation)
class StockReservationAdmin(admin.ModelAdmin):
    list_display = ["variant", "order", "quantity", "reserved_until", "is_released"]
    list_filter = ["is_released"]
    readonly_fields = ["released_at", "created_at", "updated_at"]
