# ۱) فیلد board_fps + آزادسازی choices ابعاد برد (برای ابعاد دو تکه)
# ۲) تغییر لیبل «تشخیص چهره» به «تشخیص انسان / چهره»
from django.db import migrations, models


def rename_face_label(apps, schema_editor):
    CategorySpecField = apps.get_model("catalog", "CategorySpecField")
    CategorySpecField.objects.filter(
        category__slug="ip-camera-board", key="تشخیص-چهره"
    ).update(label="تشخیص انسان / چهره")


def revert_face_label(apps, schema_editor):
    CategorySpecField = apps.get_model("catalog", "CategorySpecField")
    CategorySpecField.objects.filter(
        category__slug="ip-camera-board", key="تشخیص-چهره"
    ).update(label="تشخیص چهره")


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0038_ip_face_plate_search"),
    ]

    operations = [
        migrations.AlterField(
            model_name="product",
            name="board_dimensions",
            field=models.CharField(
                blank=True, max_length=100, verbose_name="ابعاد (برد)",
                help_text="مثل ۳۸*۳۸ — برای بردهای دو تکه مثل پلاک‌خوان: ۳۸*۳۸ + ۶۰*۵۱",
            ),
        ),
        migrations.AddField(
            model_name="product",
            name="board_fps",
            field=models.CharField(
                blank=True, max_length=50, verbose_name="نرخ فریم (FPS)",
                help_text="مثل 25fps یا 20fps@5MP",
            ),
        ),
        migrations.RunPython(rename_face_label, revert_face_label),
    ]
