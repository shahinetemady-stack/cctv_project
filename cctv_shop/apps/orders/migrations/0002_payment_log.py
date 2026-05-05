"""
Migration: orders — 0002
جدول: orders_payment_log
لاگ تمام تراکنش‌های درگاه برای audit trail
"""
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("orders", "0001_initial"),
        ("users", "0001_initial"),
    ]
    operations = [
        migrations.CreateModel(
            name="PaymentLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")),
                ("step", models.CharField(
                    max_length=20,
                    choices=[("request", "درخواست پرداخت"), ("verify", "تأیید پرداخت"), ("settle", "تسویه")],
                    verbose_name="مرحله",
                )),
                ("status", models.CharField(
                    max_length=10,
                    choices=[("success", "موفق"), ("failed", "ناموفق"), ("pending", "در انتظار")],
                    default="pending",
                    verbose_name="وضعیت",
                )),
                ("bank_ref_id", models.CharField(max_length=100, blank=True, verbose_name="شناسه مرجع بانک")),
                ("res_code", models.CharField(max_length=10, blank=True, verbose_name="کد پاسخ")),
                ("amount", models.PositiveBigIntegerField(default=0, verbose_name="مبلغ (تومان)")),
                ("raw_request", models.TextField(blank=True, verbose_name="درخواست خام")),
                ("raw_response", models.TextField(blank=True, verbose_name="پاسخ خام")),
                ("error_message", models.TextField(blank=True, verbose_name="پیام خطا")),
                ("ip_address", models.GenericIPAddressField(null=True, blank=True, verbose_name="IP")),
                ("order", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="payment_logs",
                    to="orders.order",
                    verbose_name="سفارش",
                )),
                ("user", models.ForeignKey(
                    null=True, blank=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="payment_logs",
                    to=settings.AUTH_USER_MODEL,
                    verbose_name="کاربر",
                )),
            ],
            options={
                "verbose_name": "لاگ پرداخت",
                "verbose_name_plural": "لاگ‌های پرداخت",
                "db_table": "orders_payment_log",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="paymentlog",
            index=models.Index(fields=["order", "step"], name="idx_paylog_order_step"),
        ),
    ]
