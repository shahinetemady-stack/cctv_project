# ویژگی‌های تخصصی جدید بردهای IP و AHD + بک‌فیل board_system محصولات زیردسته IP
from django.db import migrations


IP_FIELDS = [
    # (key, label, field_type, choices, sort_order, is_filterable)
    ("npu-tops", "توان پردازشی NPU", "text", "", 1, True),
    ("حصار-الکترونیکی", "حصار الکترونیکی (Electronic Fence)", "checkbox", "", 2, True),
    ("تشخیص-عبور-از-مرز", "تشخیص عبور از مرز (Cross-border)", "checkbox", "", 3, True),
    ("ردیابی-خودکار", "ردیابی خودکار (Auto Tracking)", "checkbox", "", 4, True),
    ("ظرفیت-کارت-حافظه", "حداکثر ظرفیت کارت حافظه", "select",
     "ندارد,تا 128GB,تا 256GB,تا 512GB", 5, True),
]

AHD_FIELDS = [
    ("محدوده-ولتاژ-کاری", "محدوده ولتاژ کاری (مثل DC 6-15V)", "text", "", 11, False),
    ("حفاظت-صاعقه", "حفاظت در برابر صاعقه (مثل 6KV)", "text", "", 12, False),
]


def forwards(apps, schema_editor):
    Category = apps.get_model("catalog", "Category")
    CategorySpecField = apps.get_model("catalog", "CategorySpecField")
    Product = apps.get_model("catalog", "Product")

    def add_fields(slug, fields):
        try:
            cat = Category.objects.get(slug=slug)
        except Category.DoesNotExist:
            return
        for key, label, ftype, choices, sort, filterable in fields:
            CategorySpecField.objects.get_or_create(
                category=cat, key=key,
                defaults=dict(label=label, field_type=ftype, choices=choices,
                              sort_order=sort, is_filterable=filterable),
            )

    add_fields("ip-camera-board", IP_FIELDS)
    add_fields("ahd-camera-board", AHD_FIELDS)

    # چند محصول زیردسته IP بدون سیستم برد مانده بودند — مثل بقیه همان دسته IP شوند
    try:
        ip_cat = Category.objects.get(slug="ip-camera-board")
        Product.objects.filter(category=ip_cat, board_system="").update(board_system="IP")
    except Category.DoesNotExist:
        pass


def backwards(apps, schema_editor):
    Category = apps.get_model("catalog", "Category")
    CategorySpecField = apps.get_model("catalog", "CategorySpecField")
    for slug, fields in (("ip-camera-board", IP_FIELDS), ("ahd-camera-board", AHD_FIELDS)):
        CategorySpecField.objects.filter(
            category__slug=slug, key__in=[f[0] for f in fields]
        ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0036_productreview"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
