"""
Migration: catalog — 0003
اضافه کردن فیلدهای SEO به Product و جدول SeoSettings
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0002_alter_category_icon_alter_category_id_and_more"),
    ]

    operations = [
        # فیلدهای SEO به Product
        migrations.AddField(
            model_name="product",
            name="keywords",
            field=models.CharField(
                blank=True, max_length=500,
                verbose_name="کلمات کلیدی",
                help_text="جدا شده با کاما — اگر خالی باشد خودکار ساخته می‌شود",
            ),
        ),
        migrations.AddField(
            model_name="product",
            name="geo_tags",
            field=models.CharField(
                blank=True, max_length=300,
                verbose_name="شهرهای هدف (Geo Tags)",
            ),
        ),
        migrations.AlterField(
            model_name="product",
            name="meta_title",
            field=models.CharField(
                blank=True, max_length=60,
                verbose_name="Meta Title",
                help_text="اگر خالی باشد خودکار ساخته می‌شود",
            ),
        ),
        migrations.AlterField(
            model_name="product",
            name="meta_description",
            field=models.CharField(
                blank=True, max_length=160,
                verbose_name="Meta Description",
                help_text="اگر خالی باشد خودکار ساخته می‌شود",
            ),
        ),
        # جدول SeoSettings
        migrations.CreateModel(
            name="SeoSettings",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")),
                ("target_cities", models.CharField(
                    default="تهران، مشهد، اصفهان، شیراز، تبریز، کرج",
                    max_length=500,
                    verbose_name="شهرهای هدف",
                    help_text="با کاما جدا کنید",
                )),
                ("site_name", models.CharField(
                    default="فروشگاه قطعات دوربین مداربسته",
                    max_length=100,
                    verbose_name="نام سایت",
                )),
            ],
            options={
                "verbose_name": "تنظیمات سئو",
                "verbose_name_plural": "تنظیمات سئو",
                "db_table": "catalog_seo_settings",
            },
        ),
    ]
