"""
python fix_everything.py
"""
import os, sys

print("\n" + "="*55)
print("  رفع مشکل نهایی - همه فایل‌ها")
print("="*55 + "\n")

# ─── 1. پاک کردن کامل orders/admin.py ──────────────────
print("[1/3] بازنویسی orders/admin.py ...")

orders_admin = """from django.contrib import admin
from django.utils.html import format_html
from .models import Order, OrderItem, StockReservation


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ["unit_price"]
    fields = ["variant", "quantity", "unit_price", "confirmed_unit_price"]


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
"""

with open(os.path.join('apps', 'orders', 'admin.py'), 'w', encoding='utf-8') as f:
    f.write(orders_admin)
print("      OK")

# ─── 2. پاک کردن payments/admin.py (اگر در INSTALLED_APPS نیست) ──
print("[2/3] بررسی apps/payments ...")
settings_path = os.path.join('config', 'settings.py')
with open(settings_path, encoding='utf-8') as f:
    settings_content = f.read()

if '"apps.payments"' not in settings_content and "'apps.payments'" not in settings_content:
    # payments در INSTALLED_APPS نیست - admin.py را خالی کن
    payments_admin_path = os.path.join('apps', 'payments', 'admin.py')
    if os.path.exists(payments_admin_path):
        with open(payments_admin_path, 'w', encoding='utf-8') as f:
            f.write("# این app در INSTALLED_APPS نیست\n")
        print("      OK - payments/admin.py خالی شد")
    else:
        print("      OK - فایل وجود نداشت")
else:
    print("      OK - payments در INSTALLED_APPS است")

# ─── 3. بررسی syntax همه admin فایل‌ها ─────────────────
print("[3/3] بررسی syntax ...")
import ast
all_ok = True
admin_files = []
for root, dirs, files in os.walk('apps'):
    for f in files:
        if f == 'admin.py':
            admin_files.append(os.path.join(root, f))

for path in admin_files:
    try:
        ast.parse(open(path, encoding='utf-8').read())
        print(f"      OK: {path}")
    except SyntaxError as e:
        print(f"      ERROR: {path}: {e}")
        all_ok = False

print("\n" + "="*55)
if all_ok:
    print("  تمام! حالا بزنید:")
    print("  python manage.py migrate")
    print("  python manage.py runserver")
else:
    print("  هنوز خطا دارد")
print("="*55 + "\n")
