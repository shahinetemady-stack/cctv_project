"""
Migration: inventory app — 0001_initial
جداول: inventory_stock_movement, inventory_stock_alert
"""
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        ("catalog", "0001_initial"),
        ("orders", "0001_initial"),
        ("users", "0001_initial"),
    ]
    operations = [
        migrations.CreateModel(
            name="StockMovement",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")),
                ("movement_type", models.CharField(choices=[("purchase","خرید / دریافت کالا"),("sale","فروش"),("reservation","رزرو"),("reservation_release","آزادسازی رزرو"),("adjustment","تعدیل دستی"),("return","مرجوعی"),("damage","ضایعات")], max_length=25, verbose_name="نوع حرکت موجودی")),
                ("quantity_change", models.IntegerField(help_text="مثبت = افزایش، منفی = کاهش", verbose_name="تغییر تعداد")),
                ("stock_before", models.PositiveIntegerField(verbose_name="موجودی قبل")),
                ("stock_after", models.PositiveIntegerField(verbose_name="موجودی بعد")),
                ("note", models.CharField(blank=True, max_length=500, verbose_name="یادداشت")),
                ("order", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="stock_movements", to="orders.order", verbose_name="سفارش مرتبط")),
                ("performed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="stock_movements", to=settings.AUTH_USER_MODEL, verbose_name="انجام شده توسط")),
                ("variant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="stock_movements", to="catalog.productvariant", verbose_name="نسخه محصول")),
            ],
            options={"verbose_name": "حرکت موجودی", "verbose_name_plural": "حرکات موجودی", "db_table": "inventory_stock_movement", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="StockAlert",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")),
                ("stock_at_alert", models.PositiveIntegerField(verbose_name="موجودی در لحظه هشدار")),
                ("threshold", models.PositiveSmallIntegerField(verbose_name="آستانه هشدار")),
                ("email_sent", models.BooleanField(default=False, verbose_name="ایمیل ارسال شد")),
                ("email_sent_at", models.DateTimeField(blank=True, null=True, verbose_name="زمان ارسال ایمیل")),
                ("is_resolved", models.BooleanField(db_index=True, default=False, verbose_name="برطرف شده")),
                ("resolved_at", models.DateTimeField(blank=True, null=True, verbose_name="زمان برطرف شدن")),
                ("variant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="stock_alerts", to="catalog.productvariant", verbose_name="نسخه محصول")),
            ],
            options={"verbose_name": "هشدار موجودی کم", "verbose_name_plural": "هشدارهای موجودی کم", "db_table": "inventory_stock_alert", "ordering": ["-created_at"]},
        ),
        migrations.AddIndex(model_name="stockalert", index=models.Index(fields=["is_resolved", "email_sent"], name="idx_alert_unresolved")),
    ]
