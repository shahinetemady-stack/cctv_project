import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

admin_path = os.path.join('apps', 'orders', 'admin.py')
with open(admin_path, encoding='utf-8') as f:
    old = f.read()

# پیدا کردن و حذف OrderAdmin قدیمی
idx = old.find('class OrderAdmin')
if idx >= 0:
    # حذف از unregister تا آخر OrderAdmin
    unregister_idx = old.rfind('try:\n    admin.site.unregister(Order)', 0, idx)
    if unregister_idx < 0:
        unregister_idx = old.rfind('from apps.orders.models import Order', 0, idx)
    if unregister_idx < 0:
        unregister_idx = idx
    # برش قبل از OrderAdmin
    before = old[:unregister_idx].rstrip()
    print(f"Removing OrderAdmin from position {unregister_idx}")
else:
    before = old.rstrip()
    print("No OrderAdmin found, appending")

new_admin = before + '''

# ─── Order Admin ──────────────────────────────────────────────
from apps.orders.models import Order

try:
    admin.site.unregister(Order)
except Exception:
    pass

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display   = ["order_number", "get_customer_name", "get_customer_phone",
                      "status", "get_delivery_status", "tracking_code",
                      "total_amount", "created_at"]
    list_filter    = ["status", "created_at"]
    search_fields  = ["order_number", "user__phone", "user__first_name",
                      "user__last_name", "tracking_code"]
    readonly_fields = ["order_number", "created_at", "updated_at"]

    def get_customer_name(self, obj):
        name = obj.user.get_full_name()
        return name if name.strip() else "—"
    get_customer_name.short_description = "نام مشتری"

    def get_customer_phone(self, obj):
        return obj.user.phone or "—"
    get_customer_phone.short_description = "موبایل"

    def get_delivery_status(self, obj):
        mapping = {
            "pending":    "⏳ در انتظار",
            "shipped":    "📦 ارسال شده",
            "in_transit": "🚚 در مسیر",
            "delivered":  "✅ تحویل شده",
            "returned":   "↩️ مرجوع",
        }
        val = getattr(obj, "delivery_status", "pending") or "pending"
        return mapping.get(val, val)
    get_delivery_status.short_description = "وضعیت ارسال"

    fieldsets = (
        ("اطلاعات سفارش", {"fields": (
            "order_number", "user", "order_type", "status",
            "total_amount", "confirmed_amount", "paid_amount",
            "payment_method",
        )}),
        ("اطلاعات ارسال", {"fields": (
            "freight_company", "freight_name", "tracking_code",
            "courier_company", "delivery_status",
            "shipped_at", "delivered_at",
            "shipping_address",
        )}),
        ("یادداشت‌ها", {"fields": ("admin_notes", "customer_notes")}),
        ("تاریخ‌ها", {"fields": ("created_at", "updated_at"),
                      "classes": ("collapse",)}),
    )
'''

with open(admin_path, 'w', encoding='utf-8') as f:
    f.write(new_admin)
print("✓ admin.py بازنویسی شد")

import subprocess, sys
r = subprocess.run([sys.executable, 'manage.py', 'check', '--verbosity=0'],
                   capture_output=True, text=True)
print("✓ check موفق" if r.returncode == 0 else r.stderr[-400:])
print("سرور را restart کنید")
