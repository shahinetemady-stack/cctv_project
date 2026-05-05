"""
Migration: payment app — 0001_initial
جدول: payment_transaction
"""
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("orders", "0001_initial"),
        ("users",  "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="PaymentTransaction",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("created_at",   models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")),
                ("updated_at",   models.DateTimeField(auto_now=True,     verbose_name="تاریخ بروزرسانی")),
                ("bank_token",   models.BigIntegerField(null=True, blank=True, verbose_name="توکن بانکی")),
                ("amount",       models.PositiveBigIntegerField(verbose_name="مبلغ (ریال)")),
                ("res_code",     models.CharField(max_length=10,  blank=True, verbose_name="کد نتیجه بانک")),
                ("sale_ref_id",  models.CharField(max_length=50,  blank=True, verbose_name="شماره پیگیری فروش")),
                ("sale_order_id",models.CharField(max_length=30,  blank=True, verbose_name="شماره سفارش ارسالی")),
                ("status",       models.CharField(
                    max_length=10, db_index=True, default="initiated",
                    choices=[
                        ("initiated","شروع شده"),("success","موفق"),
                        ("failed","ناموفق"),("expired","منقضی"),
                    ],
                    verbose_name="وضعیت تراکنش",
                )),
                ("error_message", models.TextField(blank=True, verbose_name="پیام خطا")),
                ("raw_request",   models.JSONField(default=dict, blank=True, verbose_name="درخواست خام")),
                ("raw_callback",  models.JSONField(default=dict, blank=True, verbose_name="callback خام")),
                ("raw_verify",    models.JSONField(default=dict, blank=True, verbose_name="پاسخ verify خام")),
                ("order", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="payment_transactions",
                    to="orders.order",
                    verbose_name="سفارش",
                )),
                ("user", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="payment_transactions",
                    to=settings.AUTH_USER_MODEL,
                    verbose_name="کاربر",
                )),
            ],
            options={
                "verbose_name": "تراکنش پرداخت",
                "verbose_name_plural": "تراکنش‌های پرداخت",
                "db_table": "payment_transaction",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="paymenttransaction",
            index=models.Index(fields=["bank_token"], name="idx_pay_token"),
        ),
        migrations.AddIndex(
            model_name="paymenttransaction",
            index=models.Index(fields=["order", "status"], name="idx_pay_order_status"),
        ),
    ]
