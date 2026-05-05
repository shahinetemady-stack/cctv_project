"""
Migration: notifications app — 0001_initial
جدول: notifications_log
"""
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        ("orders", "0001_initial"),
        ("users", "0001_initial"),
    ]
    operations = [
        migrations.CreateModel(
            name="NotificationLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")),
                ("channel", models.CharField(choices=[("sms","پیامک"),("email","ایمیل"),("push","اعلان Push")], max_length=10, verbose_name="کانال")),
                ("recipient_type", models.CharField(choices=[("admin","ادمین"),("user","کاربر")], max_length=10, verbose_name="نوع گیرنده")),
                ("recipient_address", models.CharField(max_length=255, verbose_name="آدرس گیرنده")),
                ("subject", models.CharField(blank=True, max_length=255, verbose_name="موضوع")),
                ("message", models.TextField(verbose_name="متن پیام")),
                ("status", models.CharField(choices=[("sent","ارسال شد"),("failed","شکست خورد"),("pending","در صف")], default="pending", max_length=10, verbose_name="وضعیت ارسال")),
                ("sent_at", models.DateTimeField(blank=True, null=True, verbose_name="زمان ارسال")),
                ("provider_response", models.TextField(blank=True, verbose_name="پاسخ سرویس‌دهنده")),
                ("error_message", models.TextField(blank=True, verbose_name="پیام خطا")),
                ("order", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="notifications", to="orders.order", verbose_name="سفارش")),
                ("user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="notifications", to=settings.AUTH_USER_MODEL, verbose_name="کاربر")),
            ],
            options={"verbose_name": "لاگ اعلان", "verbose_name_plural": "لاگ اعلان‌ها", "db_table": "notifications_log", "ordering": ["-created_at"]},
        ),
    ]
