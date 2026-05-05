"""
Migration: catalog app — 0001_initial
جداول: catalog_exchange_rate, catalog_category, catalog_product,
       catalog_product_image, catalog_product_variant
"""
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        ("users", "0001_initial"),
    ]
    operations = [
        migrations.CreateModel(
            name="ExchangeRateSetting",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")),
                ("rate_usd_to_irt", models.PositiveBigIntegerField(default=60000, verbose_name="نرخ دلار (تومان)")),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL, verbose_name="بروزرسانی توسط")),
            ],
            options={"verbose_name": "نرخ ارز", "verbose_name_plural": "نرخ ارز", "db_table": "catalog_exchange_rate"},
        ),
        migrations.CreateModel(
            name="Category",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")),
                ("name", models.CharField(max_length=150, verbose_name="نام دسته‌بندی")),
                ("slug", models.SlugField(allow_unicode=True, max_length=160, unique=True, verbose_name="اسلاگ")),
                ("icon", models.CharField(blank=True, max_length=100, verbose_name="آیکون")),
                ("image", models.ImageField(blank=True, null=True, upload_to="categories/", verbose_name="تصویر دسته")),
                ("is_active", models.BooleanField(default=True, verbose_name="فعال")),
                ("sort_order", models.PositiveSmallIntegerField(default=0, verbose_name="ترتیب نمایش")),
                ("parent", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="children", to="catalog.category", verbose_name="دسته‌بندی والد")),
            ],
            options={"verbose_name": "دسته‌بندی", "verbose_name_plural": "دسته‌بندی‌ها", "db_table": "catalog_category", "ordering": ["sort_order", "name"]},
        ),
        migrations.CreateModel(
            name="Product",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")),
                ("name", models.CharField(max_length=255, verbose_name="نام محصول")),
                ("slug", models.SlugField(allow_unicode=True, max_length=270, unique=True, verbose_name="اسلاگ")),
                ("brand", models.CharField(blank=True, max_length=100, verbose_name="برند / سازنده")),
                ("model_number", models.CharField(blank=True, max_length=100, verbose_name="شماره مدل")),
                ("description", models.TextField(blank=True, verbose_name="توضیحات")),
                ("short_description", models.CharField(blank=True, max_length=500, verbose_name="توضیح کوتاه")),
                ("part_type", models.CharField(choices=[("sensor","سنسور"),("lens","لنز"),("board","برد"),("isp","پردازنده تصویر (ISP)"),("housing","پوشش و کیس"),("ir_cut","فیلتر IR-Cut"),("motor","موتور"),("fpc","کابل FPC"),("power","منبع تغذیه"),("other","سایر")], db_index=True, default="other", max_length=20, verbose_name="نوع قطعه")),
                ("chipset", models.CharField(blank=True, db_index=True, max_length=150, verbose_name="چیپست")),
                ("voltage", models.CharField(blank=True, db_index=True, max_length=50, verbose_name="ولتاژ")),
                ("lens_mount", models.CharField(choices=[("m12","M12 (S-Mount)"),("cs","CS-Mount"),("c","C-Mount"),("m16","M16"),("none","بدون مانت"),("other","سایر")], db_index=True, default="none", max_length=10, verbose_name="مانت لنز")),
                ("resolution", models.CharField(blank=True, max_length=50, verbose_name="رزولوشن")),
                ("extra_specs", models.JSONField(blank=True, default=dict, verbose_name="مشخصات اضافی")),
                ("datasheet_pdf", models.FileField(blank=True, null=True, upload_to="datasheets/%Y/%m/", verbose_name="دیتاشیت PDF")),
                ("whatsapp_link", models.URLField(blank=True, verbose_name="لینک واتساپ")),
                ("bale_link", models.URLField(blank=True, verbose_name="لینک بله")),
                ("is_active", models.BooleanField(db_index=True, default=True, verbose_name="فعال")),
                ("is_featured", models.BooleanField(default=False, verbose_name="ویژه / پیشنهادی")),
                ("meta_title", models.CharField(blank=True, max_length=255, verbose_name="Meta Title")),
                ("meta_description", models.CharField(blank=True, max_length=500, verbose_name="Meta Description")),
                ("category", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="products", to="catalog.category", verbose_name="دسته‌بندی")),
                ("compatible_with", models.ManyToManyField(blank=True, symmetrical=True, to="catalog.product", verbose_name="محصولات سازگار")),
            ],
            options={"verbose_name": "محصول", "verbose_name_plural": "محصولات", "db_table": "catalog_product", "ordering": ["-created_at"]},
        ),
        migrations.AddIndex(model_name="product", index=models.Index(fields=["part_type", "chipset"], name="idx_product_type_chip")),
        migrations.AddIndex(model_name="product", index=models.Index(fields=["is_active", "is_featured"], name="idx_product_active_feat")),
        migrations.CreateModel(
            name="ProductImage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")),
                ("image", models.ImageField(upload_to="products/%Y/%m/", verbose_name="تصویر")),
                ("alt_text", models.CharField(blank=True, max_length=255, verbose_name="متن جایگزین")),
                ("is_primary", models.BooleanField(default=False, verbose_name="تصویر اصلی")),
                ("sort_order", models.PositiveSmallIntegerField(default=0, verbose_name="ترتیب")),
                ("product", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="images", to="catalog.product", verbose_name="محصول")),
            ],
            options={"verbose_name": "تصویر محصول", "verbose_name_plural": "تصاویر محصول", "db_table": "catalog_product_image", "ordering": ["-is_primary", "sort_order"]},
        ),
        migrations.CreateModel(
            name="ProductVariant",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")),
                ("sku", models.CharField(max_length=100, unique=True, verbose_name="کد SKU")),
                ("name_suffix", models.CharField(blank=True, max_length=100, verbose_name="پسوند نام")),
                ("stock_quantity", models.PositiveIntegerField(default=0, verbose_name="موجودی کل")),
                ("reserved_qty", models.PositiveIntegerField(default=0, verbose_name="رزرو شده")),
                ("purchase_price_usd", models.DecimalField(decimal_places=2, max_digits=10, verbose_name="قیمت خرید (دلار)")),
                ("shipping_cost", models.PositiveBigIntegerField(default=0, verbose_name="هزینه حمل (تومان)")),
                ("profit_margin", models.PositiveBigIntegerField(default=0, verbose_name="سود (تومان)")),
                ("is_active", models.BooleanField(default=True, verbose_name="فعال")),
                ("product", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="variants", to="catalog.product", verbose_name="محصول")),
            ],
            options={"verbose_name": "نسخه محصول (Variant)", "verbose_name_plural": "نسخه‌های محصول", "db_table": "catalog_product_variant", "ordering": ["product", "sku"]},
        ),
    ]
