# ۱) چک‌باکس «آمپلی‌فایر داخلی» (کنار مکالمه دوطرفه، روی دسته ریشه برد)
# ۲) غیرفعال‌کردن فیلتر سایت برای چک‌باکس قدیمی «پشتیبانی از کارت حافظه»
#    (جایگزین: دراپ‌داون «حداکثر ظرفیت کارت حافظه» با گزینه «ندارد»)
from django.db import migrations


def forwards(apps, schema_editor):
    Category = apps.get_model("catalog", "Category")
    CategorySpecField = apps.get_model("catalog", "CategorySpecField")
    try:
        board_root = Category.objects.get(slug="cctv-camera-board")
    except Category.DoesNotExist:
        return
    CategorySpecField.objects.get_or_create(
        category=board_root, key="امپلی-فایر-داخلی",
        defaults=dict(
            label="آمپلی‌فایر داخلی (اتصال مستقیم اسپیکر)",
            field_type="checkbox", sort_order=0, is_filterable=True,
        ),
    )
    CategorySpecField.objects.filter(
        category=board_root, key="پشتیبانی-از-کارت-حافظه"
    ).update(is_filterable=False)


def backwards(apps, schema_editor):
    CategorySpecField = apps.get_model("catalog", "CategorySpecField")
    CategorySpecField.objects.filter(
        category__slug="cctv-camera-board", key="امپلی-فایر-داخلی"
    ).delete()
    CategorySpecField.objects.filter(
        category__slug="cctv-camera-board", key="پشتیبانی-از-کارت-حافظه"
    ).update(is_filterable=True)


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0039_board_fps_and_labels"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
