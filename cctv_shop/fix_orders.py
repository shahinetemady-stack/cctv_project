"""
python fix_orders.py
"""
import os, subprocess, sys

print("اضافه کردن فیلدهای ارسال و رهگیری ...")

# ─── 1. migration ─────────────────────────────────────────
migration = '''from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ("orders", "0002_payment_log"),
    ]
    operations = [
        migrations.AddField(
            model_name="order",
            name="shipping_method",
            field=models.CharField(
                max_length=20, blank=True, default="",
                verbose_name="روش ارسال",
                choices=[
                    ("post", "پست"),
                    ("courier", "پیک"),
                    ("freight", "باربری"),
                ],
            ),
        ),
        migrations.AddField(
            model_name="order",
            name="freight_company",
            field=models.CharField(
                max_length=200, blank=True,
                verbose_name="نام باربری",
            ),
        ),
        migrations.AddField(
            model_name="order",
            name="tracking_code",
            field=models.CharField(
                max_length=100, blank=True,
                verbose_name="کد رهگیری",
            ),
        ),
        migrations.AddField(
            model_name="order",
            name="paid_amount",
            field=models.PositiveBigIntegerField(
                null=True, blank=True,
                verbose_name="مبلغ پرداخت شده (تومان)",
            ),
        ),
        migrations.AddField(
            model_name="order",
            name="payment_method",
            field=models.CharField(
                max_length=50, blank=True,
                verbose_name="روش پرداخت",
                choices=[
                    ("cash", "نقد"),
                    ("transfer", "کارت به کارت"),
                    ("online", "آنلاین"),
                    ("check", "چک"),
                ],
            ),
        ),
    ]
'''

mig_path = os.path.join('apps','orders','migrations','0003_shipping_tracking.py')
with open(mig_path, 'w', encoding='utf-8') as f:
    f.write(migration)
print("  OK - migration")

# ─── 2. orders/models.py ─────────────────────────────────
orders_model = os.path.join('apps','orders','models.py')
with open(orders_model, encoding='utf-8') as f:
    content = f.read()

# اضافه کردن فیلدها به Order model
old = '''    shipping_address = models.TextField(blank=True, verbose_name="آدرس ارسال")
    customer_notes   = models.TextField(blank=True, verbose_name="یادداشت مشتری")
    admin_notes      = models.TextField(blank=True, verbose_name="یادداشت ادمین")'''

new = '''    shipping_address = models.TextField(blank=True, verbose_name="آدرس ارسال")
    shipping_method  = models.CharField(
        max_length=20, blank=True, default="",
        verbose_name="روش ارسال",
        choices=[("post","پست"),("courier","پیک"),("freight","باربری")],
    )
    freight_company  = models.CharField(max_length=200, blank=True, verbose_name="نام باربری")
    tracking_code    = models.CharField(max_length=100, blank=True, verbose_name="کد رهگیری")
    paid_amount      = models.PositiveBigIntegerField(null=True, blank=True, verbose_name="مبلغ پرداخت شده (تومان)")
    payment_method   = models.CharField(
        max_length=50, blank=True,
        verbose_name="روش پرداخت",
        choices=[("cash","نقد"),("transfer","کارت به کارت"),("online","آنلاین"),("check","چک")],
    )
    customer_notes   = models.TextField(blank=True, verbose_name="یادداشت مشتری")
    admin_notes      = models.TextField(blank=True, verbose_name="یادداشت ادمین")'''

content = content.replace(old, new)
with open(orders_model, 'w', encoding='utf-8') as f:
    f.write(content)
print("  OK - orders/models.py")

# ─── 3. orders/admin.py با قابلیت ثبت پرداخت ─────────────
orders_admin = '''from django.contrib import admin
from django.utils.html import format_html
from django.http import HttpResponse
from .models import Order, OrderItem, StockReservation


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    fields = ["variant", "quantity", "unit_price", "confirmed_unit_price"]
    readonly_fields = ["unit_price"]


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ["order_number", "user_display", "status_display",
                    "shipping_display", "total_amount_display", "tracking_display", "created_at"]
    list_filter  = ["status", "order_type", "shipping_method",
                    ("created_at", admin.DateFieldListFilter)]
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
        return obj.user.phone or obj.user.email or "—"
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
            '<span style="background:{};color:white;padding:2px 8px;border-radius:4px;font-size:11px">{}</span>',
            color, label
        )
    status_display.short_description = "وضعیت"

    def shipping_display(self, obj):
        labels = {"post": "📮 پست", "courier": "🛵 پیک", "freight": "🚛 باربری"}
        method = labels.get(obj.shipping_method, "—")
        if obj.shipping_method == "freight" and obj.freight_company:
            method += f" ({obj.freight_company})"
        return method
    shipping_display.short_description = "ارسال"

    def total_amount_display(self, obj):
        amount = obj.confirmed_amount or obj.total_amount or 0
        return format_html("<b>{:,}</b> ت", amount)
    total_amount_display.short_description = "مبلغ"

    def tracking_display(self, obj):
        if obj.tracking_code:
            return format_html(
                '<span style="font-family:monospace;color:#00C896">{}</span>',
                obj.tracking_code
            )
        return "—"
    tracking_display.short_description = "کد رهگیری"

    @admin.action(description="✅ آماده ارسال")
    def mark_as_ready(self, request, queryset):
        updated = queryset.update(status="ready_to_ship")
        self.message_user(request, f"{updated} سفارش به آماده ارسال تغییر یافت.")

    @admin.action(description="💰 ثبت پرداخت دستی")
    def mark_as_paid(self, request, queryset):
        updated = queryset.update(status="paid")
        self.message_user(request, f"{updated} سفارش پرداخت شده ثبت شد.")


@admin.register(StockReservation)
class StockReservationAdmin(admin.ModelAdmin):
    list_display = ["variant", "order", "quantity", "reserved_until", "is_released"]
    list_filter  = ["is_released"]
    readonly_fields = ["released_at", "created_at", "updated_at"]
'''

with open(os.path.join('apps','orders','admin.py'), 'w', encoding='utf-8') as f:
    f.write(orders_admin)
print("  OK - orders/admin.py")

# ─── 4. اضافه کردن status های جدید به Order model ─────────
with open(orders_model, encoding='utf-8') as f:
    content = f.read()

old_status = '''    class Status(models.TextChoices):
        PENDING          = "pending",          "در انتظار تأیید"
        CONFIRMED        = "confirmed",        "تأیید شده"
        AWAITING_PAYMENT = "awaiting_payment", "در انتظار پرداخت"
        PAID             = "paid",             "پرداخت شده"
        CANCELLED        = "cancelled",        "لغو شده"
        REFUNDED         = "refunded",         "مسترد شده"'''

new_status = '''    class Status(models.TextChoices):
        PENDING          = "pending",          "در انتظار تأیید"
        CONFIRMED        = "confirmed",        "تأیید شده"
        AWAITING_PAYMENT = "awaiting_payment", "در انتظار پرداخت"
        PAID             = "paid",             "پرداخت شده"
        READY_TO_SHIP    = "ready_to_ship",    "آماده ارسال"
        SHIPPED          = "shipped",          "ارسال شده"
        CANCELLED        = "cancelled",        "لغو شده"
        REFUNDED         = "refunded",         "مسترد شده"'''

if old_status in content:
    content = content.replace(old_status, new_status)
    with open(orders_model, 'w', encoding='utf-8') as f:
        f.write(content)
    print("  OK - status choices updated")

# ─── 5. migrate ──────────────────────────────────────────
r = subprocess.run([sys.executable,'manage.py','migrate','--verbosity=0'],
                   capture_output=True, text=True)
if r.returncode == 0:
    print("  OK - migrate موفق")
else:
    for line in (r.stdout+r.stderr).strip().split('\n')[-6:]:
        if line.strip(): print(" ", line)

r2 = subprocess.run([sys.executable,'manage.py','check','--verbosity=0'],
                    capture_output=True, text=True)
print("  OK - check" if r2.returncode == 0 else "  خطا در check")

print("\nتمام! حالا بزنید: python manage.py runserver")
