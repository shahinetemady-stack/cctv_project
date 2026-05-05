"""
Migration: orders app — 0001_initial
جداول: orders_cart, orders_cart_item, orders_inquiry_cart,
       orders_inquiry_cart_item, orders_order, orders_order_item,
       orders_stock_reservation
"""
import apps.orders.models
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        ("catalog", "0001_initial"),
        ("users", "0001_initial"),
    ]
    operations = [
        # Cart
        migrations.CreateModel(
            name="Cart",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")),
                ("session_key", models.CharField(blank=True, max_length=40, null=True, verbose_name="کلید سشن")),
                ("user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="carts", to=settings.AUTH_USER_MODEL, verbose_name="کاربر")),
            ],
            options={"verbose_name": "سبد خرید", "verbose_name_plural": "سبدهای خرید", "db_table": "orders_cart"},
        ),
        migrations.CreateModel(
            name="CartItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")),
                ("quantity", models.PositiveSmallIntegerField(default=1, verbose_name="تعداد")),
                ("cart", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="items", to="orders.cart")),
                ("variant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="cart_items", to="catalog.productvariant", verbose_name="نسخه محصول")),
            ],
            options={"verbose_name": "آیتم سبد خرید", "verbose_name_plural": "آیتم‌های سبد خرید", "db_table": "orders_cart_item"},
        ),
        migrations.AddConstraint(
            model_name="cartitem",
            constraint=models.UniqueConstraint(fields=["cart", "variant"], name="unique_cart_variant"),
        ),
        # InquiryCart
        migrations.CreateModel(
            name="InquiryCart",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")),
                ("notes", models.TextField(blank=True, verbose_name="یادداشت مشتری")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="inquiry_carts", to=settings.AUTH_USER_MODEL, verbose_name="کاربر همکار")),
            ],
            options={"verbose_name": "سبد استعلام", "verbose_name_plural": "سبدهای استعلام", "db_table": "orders_inquiry_cart"},
        ),
        migrations.CreateModel(
            name="InquiryCartItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")),
                ("quantity", models.PositiveSmallIntegerField(default=1, verbose_name="تعداد")),
                ("cart", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="items", to="orders.inquirycart")),
                ("variant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="inquiry_items", to="catalog.productvariant", verbose_name="نسخه محصول")),
            ],
            options={"verbose_name": "آیتم سبد استعلام", "verbose_name_plural": "آیتم‌های سبد استعلام", "db_table": "orders_inquiry_cart_item"},
        ),
        migrations.AddConstraint(
            model_name="inquirycartitem",
            constraint=models.UniqueConstraint(fields=["cart", "variant"], name="unique_inquiry_cart_variant"),
        ),
        # Order
        migrations.CreateModel(
            name="Order",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")),
                ("order_number", models.CharField(default=apps.orders.models.generate_order_number, max_length=30, unique=True, verbose_name="شماره سفارش")),
                ("order_type", models.CharField(choices=[("direct_purchase","خرید مستقیم"),("inquiry","استعلام")], db_index=True, default="direct_purchase", max_length=20, verbose_name="نوع سفارش")),
                ("status", models.CharField(choices=[("pending","در انتظار بررسی"),("confirmed","تأیید شده توسط ادمین"),("awaiting_payment","در انتظار پرداخت"),("paid","پرداخت شده"),("cancelled","لغو شده"),("refunded","مسترد شده")], db_index=True, default="pending", max_length=20, verbose_name="وضعیت")),
                ("total_amount", models.PositiveBigIntegerField(default=0, verbose_name="مبلغ کل (تومان)")),
                ("confirmed_amount", models.PositiveBigIntegerField(default=0, verbose_name="مبلغ تأیید شده ادمین (تومان)")),
                ("payment_link", models.URLField(blank=True, verbose_name="لینک پرداخت")),
                ("payment_deadline", models.DateTimeField(blank=True, null=True, verbose_name="مهلت پرداخت")),
                ("payment_ref_id", models.CharField(blank=True, max_length=100, verbose_name="کد پیگیری پرداخت")),
                ("paid_at", models.DateTimeField(blank=True, null=True, verbose_name="زمان پرداخت")),
                ("shipping_address", models.TextField(blank=True, verbose_name="آدرس ارسال")),
                ("customer_notes", models.TextField(blank=True, verbose_name="یادداشت مشتری")),
                ("admin_notes", models.TextField(blank=True, verbose_name="یادداشت ادمین")),
                ("admin_confirm_deadline", models.DateTimeField(blank=True, null=True, verbose_name="مهلت تأیید ادمین")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="orders", to=settings.AUTH_USER_MODEL, verbose_name="کاربر")),
            ],
            options={"verbose_name": "سفارش", "verbose_name_plural": "سفارش‌ها", "db_table": "orders_order", "ordering": ["-created_at"]},
        ),
        migrations.AddIndex(model_name="order", index=models.Index(fields=["status", "order_type"], name="idx_order_status_type")),
        migrations.AddIndex(model_name="order", index=models.Index(fields=["user", "status"], name="idx_order_user_status")),
        # OrderItem
        migrations.CreateModel(
            name="OrderItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")),
                ("quantity", models.PositiveSmallIntegerField(default=1, verbose_name="تعداد")),
                ("unit_price", models.PositiveBigIntegerField(verbose_name="قیمت واحد (تومان) — snapshot")),
                ("confirmed_unit_price", models.PositiveBigIntegerField(default=0, verbose_name="قیمت تأیید شده ادمین")),
                ("reserved_until", models.DateTimeField(blank=True, null=True, verbose_name="رزرو تا")),
                ("order", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="items", to="orders.order", verbose_name="سفارش")),
                ("variant", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="order_items", to="catalog.productvariant", verbose_name="نسخه محصول")),
            ],
            options={"verbose_name": "آیتم سفارش", "verbose_name_plural": "آیتم‌های سفارش", "db_table": "orders_order_item"},
        ),
        # StockReservation
        migrations.CreateModel(
            name="StockReservation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")),
                ("quantity", models.PositiveSmallIntegerField(verbose_name="تعداد رزرو شده")),
                ("reserved_until", models.DateTimeField(verbose_name="رزرو تا")),
                ("is_released", models.BooleanField(db_index=True, default=False, verbose_name="آزاد شده")),
                ("released_at", models.DateTimeField(blank=True, null=True, verbose_name="زمان آزادسازی")),
                ("release_reason", models.CharField(blank=True, max_length=100, verbose_name="دلیل آزادسازی")),
                ("order", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="reservations", to="orders.order", verbose_name="سفارش")),
                ("variant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="reservations", to="catalog.productvariant", verbose_name="نسخه محصول")),
            ],
            options={"verbose_name": "رزرو موجودی", "verbose_name_plural": "رزروهای موجودی", "db_table": "orders_stock_reservation", "ordering": ["-created_at"]},
        ),
        migrations.AddIndex(model_name="stockreservation", index=models.Index(fields=["is_released", "reserved_until"], name="idx_reservation_active")),
    ]
