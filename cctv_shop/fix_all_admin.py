"""
در پوشه cctv_shop اجرا کنید:
python fix_all_admin.py
"""
import os

print("\n" + "="*50)
print("  بازنویسی کامل فایل‌های admin")
print("="*50 + "\n")

# ─── orders/admin.py ─────────────────────────────────────
orders_admin = '''from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import Cart, CartItem, InquiryCart, InquiryCartItem, Order, OrderItem, StockReservation

STATUS_COLORS = {
    "pending": "#FF9500", "confirmed": "#0066FF",
    "awaiting_payment": "#8B5CF6", "paid": "#00C896",
    "cancelled": "#FF3B3B", "refunded": "#8892A4",
}

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ["unit_price", "subtotal_display", "reserved_until"]
    fields = ["variant", "quantity", "unit_price", "confirmed_unit_price", "subtotal_display", "reserved_until"]
    def subtotal_display(self, obj):
        return f"{obj.subtotal:,} تومان"
    subtotal_display.short_description = "جمع"

class StockReservationInline(admin.TabularInline):
    model = StockReservation
    extra = 0
    readonly_fields = ["variant", "quantity", "reserved_until", "is_released", "release_reason"]
    can_delete = False

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ["order_number", "user", "order_type_display", "status_display",
                    "total_amount_display", "created_at"]
    list_filter = ["status", "order_type", ("created_at", admin.DateFieldListFilter)]
    search_fields = ["order_number", "user__email"]
    readonly_fields = ["order_number", "created_at", "updated_at", "payment_link", "payment_ref_id", "paid_at"]
    inlines = [OrderItemInline, StockReservationInline]
    ordering = ["-created_at"]
    fieldsets = (
        ("اطلاعات سفارش", {"fields": ("order_number", "user", "order_type", "status")}),
        ("مالی", {"fields": ("total_amount", "confirmed_amount")}),
        ("پرداخت", {"fields": ("payment_link", "payment_deadline", "payment_ref_id", "paid_at")}),
        ("یادداشت‌ها", {"fields": ("shipping_address", "customer_notes", "admin_notes")}),
        ("تاریخ‌ها", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )
    def order_type_display(self, obj):
        colors = {"direct_purchase": "#00C896", "inquiry": "#0066FF"}
        return format_html('<span style="color:{};font-weight:bold">{}</span>',
                           colors.get(obj.order_type, "#888"), obj.get_order_type_display())
    order_type_display.short_description = "نوع"
    def status_display(self, obj):
        color = STATUS_COLORS.get(obj.status, "#888")
        return format_html('<span style="background:{};color:white;padding:2px 8px;border-radius:4px">{}</span>',
                           color, obj.get_status_display())
    status_display.short_description = "وضعیت"
    def total_amount_display(self, obj):
        return format_html("<b>{:,}</b> تومان", obj.effective_amount)
    total_amount_display.short_description = "مبلغ"

@admin.register(StockReservation)
class StockReservationAdmin(admin.ModelAdmin):
    list_display = ["variant", "order", "quantity", "reserved_until", "is_released"]
    list_filter = ["is_released"]
    search_fields = ["order__order_number", "variant__sku"]
    readonly_fields = ["released_at", "release_reason", "created_at", "updated_at"]
'''

path = os.path.join('apps', 'orders', 'admin.py')
with open(path, 'w', encoding='utf-8') as f:
    f.write(orders_admin)
print("[1/2] orders/admin.py بازنویسی شد")

# ─── بررسی syntax ────────────────────────────────────────
import ast
ok = True
for p in [path, os.path.join('apps', 'catalog', 'admin.py')]:
    try:
        ast.parse(open(p, encoding='utf-8').read())
        print(f"      OK: {os.path.basename(p)}")
    except SyntaxError as e:
        print(f"      ERROR: {os.path.basename(p)}: {e}")
        ok = False

print("\n" + "="*50)
if ok:
    print("  تمام! حالا بزنید:")
    print("  python manage.py migrate")
    print("  python manage.py runserver")
else:
    print("  هنوز خطا دارد")
print("="*50 + "\n")
