from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    initial = True
    dependencies = [
        ("catalog", "0008_partner_price"),
        ("inventory", "0002_alter_stockalert_id_alter_stockalert_threshold_and_more"),
    ]
    operations = [
        migrations.CreateModel(
            name="Warehouse",
            fields=[
                ("id", models.BigAutoField(primary_key=True)),
                ("name", models.CharField(max_length=100, verbose_name="نام انبار")),
                ("code", models.CharField(max_length=20, unique=True, verbose_name="کد انبار")),
                ("warehouse_type", models.CharField(
                    max_length=20, verbose_name="نوع انبار",
                    choices=[
                        ("air_transit", "در راه هوایی"),
                        ("sea_transit", "در راه دریایی"),
                        ("shop1", "فروشگاه یک"),
                        ("shop2", "فروشگاه دو"),
                        ("assembly", "انبار مونتاژ"),
                    ]
                )),
                ("is_public", models.BooleanField(default=False, verbose_name="نمایش به مشتری")),
                ("is_active", models.BooleanField(default=True, verbose_name="فعال")),
                ("address", models.TextField(blank=True, verbose_name="آدرس")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "inventory_warehouse", "verbose_name": "انبار", "verbose_name_plural": "انبارها"},
        ),
        migrations.CreateModel(
            name="WarehouseStock",
            fields=[
                ("id", models.BigAutoField(primary_key=True)),
                ("warehouse", models.ForeignKey("inventory.Warehouse", on_delete=django.db.models.deletion.CASCADE, related_name="stocks", verbose_name="انبار")),
                ("variant", models.ForeignKey("catalog.ProductVariant", on_delete=django.db.models.deletion.CASCADE, related_name="warehouse_stocks", verbose_name="محصول")),
                ("quantity", models.PositiveIntegerField(default=0, verbose_name="موجودی")),
                ("min_quantity", models.PositiveIntegerField(default=0, verbose_name="حداقل موجودی")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "inventory_warehouse_stock", "verbose_name": "موجودی انبار", "verbose_name_plural": "موجودی‌های انبار", "unique_together": {("warehouse", "variant")}},
        ),
        migrations.CreateModel(
            name="StockTransfer",
            fields=[
                ("id", models.BigAutoField(primary_key=True)),
                ("from_warehouse", models.ForeignKey("inventory.Warehouse", on_delete=django.db.models.deletion.PROTECT, related_name="transfers_out", verbose_name="از انبار")),
                ("to_warehouse", models.ForeignKey("inventory.Warehouse", on_delete=django.db.models.deletion.PROTECT, related_name="transfers_in", verbose_name="به انبار")),
                ("variant", models.ForeignKey("catalog.ProductVariant", on_delete=django.db.models.deletion.PROTECT, related_name="transfers", verbose_name="محصول")),
                ("quantity", models.PositiveIntegerField(verbose_name="تعداد")),
                ("status", models.CharField(max_length=20, default="pending", choices=[("pending","در انتظار"),("done","انجام شده"),("cancelled","لغو شده")], verbose_name="وضعیت")),
                ("note", models.TextField(blank=True, verbose_name="توضیحات")),
                ("transferred_by", models.ForeignKey("users.User", on_delete=django.db.models.deletion.SET_NULL, null=True, blank=True, verbose_name="انتقال دهنده")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "inventory_stock_transfer", "verbose_name": "انتقال موجودی", "verbose_name_plural": "انتقال‌های موجودی", "ordering": ["-created_at"]},
        ),
    ]
