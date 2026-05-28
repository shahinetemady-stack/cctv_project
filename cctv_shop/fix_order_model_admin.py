import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

# ─── 1. بررسی Order model ─────────────────────────────────────
models_path = os.path.join('apps', 'orders', 'models.py')
with open(models_path, encoding='utf-8') as f:
    content = f.read()

print("delivery_status in model:", 'delivery_status' in content)
print("courier_company in model:", 'courier_company' in content)

# ─── 2. اضافه کردن فیلدها به Order model ─────────────────────
if 'delivery_status' not in content:
    # پیدا کردن کلاس Order
    idx = content.find('class Order(')
    if idx < 0:
        idx = content.find('class Order(models')

    # پیدا کردن Meta class داخل Order
    meta_idx = content.find('    class Meta', idx)

    tracking_fields = '''
    # ─── فیلدهای رهگیری ──────────────────────────────────────
    courier_company = models.CharField(
        max_length=20, blank=True, default='',
        choices=[
            ('post', 'پست'), ('tipax', 'تیپاکس'),
            ('chapar', 'چاپار'), ('snap', 'اسنپ‌باکس'), ('other', 'سایر'),
        ],
        verbose_name='شرکت حمل'
    )
    delivery_status = models.CharField(
        max_length=20, blank=True, default='pending',
        choices=[
            ('pending', 'در انتظار ارسال'), ('shipped', 'ارسال شده'),
            ('in_transit', 'در مسیر'), ('delivered', 'تحویل داده شده'),
            ('returned', 'مرجوع شده'),
        ],
        verbose_name='وضعیت ارسال'
    )
    shipped_at = models.DateTimeField(null=True, blank=True, verbose_name='تاریخ ارسال')
    delivered_at = models.DateTimeField(null=True, blank=True, verbose_name='تاریخ تحویل')

'''
    if meta_idx > idx:
        content = content[:meta_idx] + tracking_fields + content[meta_idx:]
        with open(models_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print("✓ فیلدهای رهگیری به Order اضافه شد")
    else:
        print("✗ Meta پیدا نشد")
else:
    print("✓ قبلاً در model موجود بود")

# ─── 3. Migration ─────────────────────────────────────────────
import subprocess, sys

# چون فیلدها را با SQL اضافه کردیم، باید fake migrate کنیم
r = subprocess.run(
    [sys.executable, 'manage.py', 'makemigrations', 'orders', '--name', 'add_tracking_fields'],
    capture_output=True, text=True
)
print(r.stdout[-300:] if r.stdout else "")
if r.returncode != 0:
    print("خطا migration:", r.stderr[-300:])

# چون دیتابیس قبلاً آپدیت شده، fake migrate
r2 = subprocess.run(
    [sys.executable, 'manage.py', 'migrate', 'orders', '--fake-initial'],
    capture_output=True, text=True
)
print(r2.stdout[-200:] if r2.stdout else "")

r3 = subprocess.run(
    [sys.executable, 'manage.py', 'migrate', 'orders'],
    capture_output=True, text=True
)
print(r3.stdout[-200:] if r3.stdout else "")
if r3.returncode != 0:
    print("migrate error:", r3.stderr[-300:])

# ─── 4. Fix Admin ─────────────────────────────────────────────
admin_path = os.path.join('apps', 'orders', 'admin.py')
with open(admin_path, encoding='utf-8') as f:
    admin_content = f.read()

# حذف OrderAdmin فعلی و جایگزینی با نسخه صحیح
idx = admin_content.find('# ─── Order Admin')
if idx < 0:
    idx = admin_content.find('from apps.orders.models import Order')

if idx >= 0:
    admin_content = admin_content[:idx]

admin_content += '''
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
'''

with open(admin_path, 'w', encoding='utf-8') as f:
    f.write(admin_content)
print("✓ OrderAdmin بازنویسی شد")

r4 = subprocess.run([sys.executable, 'manage.py', 'check', '--verbosity=0'],
                    capture_output=True, text=True)
print("✓ check موفق" if r4.returncode == 0 else r4.stderr[-400:])
print("\nسرور را restart کنید")
