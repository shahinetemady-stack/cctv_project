from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings

class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0001_initial_warehouse"),
        ("catalog", "0008_partner_price"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.CreateModel(
            name="StockMovement",
            fields=[
                ("id", models.BigAutoField(primary_key=True)),
                ("warehouse", models.ForeignKey("inventory.Warehouse", on_delete=django.db.models.deletion.PROTECT, related_name="movements", verbose_name="انبار")),
                ("variant", models.ForeignKey("catalog.ProductVariant", on_delete=django.db.models.deletion.PROTECT, related_name="movements", verbose_name="محصول")),
                ("movement_type", models.CharField(max_length=20, verbose_name="نوع حرکت",
                    choices=[("purchase","خرید"),("sale","فروش"),("transfer_in","انتقال ورودی"),
                             ("transfer_out","انتقال خروجی"),("adjustment","تعدیل"),("return","مرجوعی")])),
                ("quantity", models.IntegerField(verbose_name="تعداد")),
                ("unit_price", models.PositiveBigIntegerField(default=0, verbose_name="قیمت واحد")),
                ("balance_after", models.PositiveIntegerField(default=0, verbose_name="موجودی بعد")),
                ("reference", models.CharField(max_length=100, blank=True, verbose_name="مرجع")),
                ("note", models.TextField(blank=True, verbose_name="توضیحات")),
                ("created_by", models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=django.db.models.deletion.SET_NULL, null=True, blank=True, verbose_name="ثبت کننده")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"db_table": "inventory_stock_movement", "verbose_name": "کاردکس", "ordering": ["-created_at"]},
        ),
    ]
