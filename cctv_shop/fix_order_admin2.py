import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

admin_path = os.path.join('apps', 'orders', 'admin.py')
with open(admin_path, encoding='utf-8') as f:
    content = f.read()

# اضافه کردن unregister قبل از register
if 'admin.site.unregister(Order)' not in content and 'class OrderAdmin' in content:
    content = content.replace(
        '@admin.register(Order)\nclass OrderAdmin',
        'try:\n    admin.site.unregister(Order)\nexcept Exception:\n    pass\n\n@admin.register(Order)\nclass OrderAdmin'
    )
    with open(admin_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("✓ unregister اضافه شد")
elif 'class OrderAdmin' not in content:
    # اضافه کردن کامل
    content += '''

from apps.orders.models import Order

try:
    admin.site.unregister(Order)
except Exception:
    pass

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display  = ["order_number", "get_customer_name", "get_customer_phone",
                     "status", "get_delivery_status", "get_courier",
                     "tracking_code", "total_amount", "created_at"]
    list_filter   = ["status", "created_at"]
    list_editable = []
    search_fields = ["order_number", "user__phone", "user__first_name",
                     "user__last_name", "tracking_code"]
    readonly_fields = ["order_number", "created_at", "updated_at"]

    def get_customer_name(self, obj):
        return obj.user.get_full_name() or "—"
    get_customer_name.short_description = "نام مشتری"

    def get_customer_phone(self, obj):
        return obj.user.phone or "—"
    get_customer_phone.short_description = "موبایل"

    def get_delivery_status(self, obj):
        choices = {
            "pending": "⏳ در انتظار ارسال",
            "shipped": "📦 ارسال شده",
            "in_transit": "🚚 در مسیر",
            "delivered": "✅ تحویل داده شده",
            "returned": "↩️ مرجوع شده",
        }
        val = getattr(obj, "delivery_status", "pending") or "pending"
        return choices.get(val, val)
    get_delivery_status.short_description = "وضعیت ارسال"

    def get_courier(self, obj):
        choices = {"post": "پست", "tipax": "تیپاکس",
                   "chapar": "چاپار", "snap": "اسنپ‌باکس", "other": "سایر"}
        val = getattr(obj, "courier_company", "") or ""
        return choices.get(val, val or "—")
    get_courier.short_description = "شرکت حمل"

    fieldsets = (
        ("اطلاعات سفارش", {"fields": (
            "order_number", "user", "status", "total_amount",
        )}),
        ("اطلاعات ارسال", {"fields": (
            "courier_company", "tracking_code", "delivery_status",
            "shipped_at", "delivered_at", "shipping_address",
        )}),
        ("یادداشت‌ها", {"fields": ("admin_notes",)}),
        ("تاریخ‌ها", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )
'''
    with open(admin_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("✓ OrderAdmin اضافه شد")

import subprocess, sys
r = subprocess.run([sys.executable, 'manage.py', 'check', '--verbosity=0'],
                   capture_output=True, text=True)
print("✓ check موفق" if r.returncode == 0 else r.stderr[-300:])
print("سرور را restart کنید")
