# فیلدهای تخصصی اپتیک/مونتاژ لنز + ارتقای «نسبت کانونی» به «کلاس نوری لنز»
from django.db import migrations, models


FOCAL_MAP = {
    "معمولی": "معمولی IR",
    "استارلایت": "استارلایت Starlight",
    "دارک لایت": "بلک‌لایت Blacklight",
}
FOCAL_MAP_REVERSE = {v: k for k, v in FOCAL_MAP.items()}


def map_focal(apps, schema_editor):
    Product = apps.get_model("catalog", "Product")
    for old, new in FOCAL_MAP.items():
        Product.objects.filter(focal_ratio=old).update(focal_ratio=new)


def unmap_focal(apps, schema_editor):
    Product = apps.get_model("catalog", "Product")
    for new, old in FOCAL_MAP_REVERSE.items():
        Product.objects.filter(focal_ratio=new).update(focal_ratio=old)


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0040_amp_checkbox_cleanup"),
    ]

    operations = [
        migrations.AlterField(
            model_name="product",
            name="focal_ratio",
            field=models.CharField(
                blank=True, max_length=60, verbose_name="کلاس نوری لنز",
                choices=[("معمولی IR", "معمولی IR"), ("استارلایت Starlight", "استارلایت Starlight"),
                         ("وارم‌لایت / فول‌کالر Warm Light", "وارم‌لایت / فول‌کالر Warm Light"),
                         ("بلک‌لایت Blacklight", "بلک‌لایت Blacklight"), ("پلاک‌خوان LPR", "پلاک‌خوان LPR")],
            ),
        ),
        migrations.AddField(
            model_name="product", name="lens_aperture",
            field=models.CharField(blank=True, max_length=30, verbose_name="ضریب دیافراگم (Aperture)",
                                   help_text="مثل F1.0 یا F1.2"),
        ),
        migrations.AddField(
            model_name="product", name="lens_image_size",
            field=models.CharField(blank=True, max_length=30, verbose_name="سایز سنسور سازگار (Image Size)",
                                   help_text="مثل 1/2.8 اینچ"),
        ),
        migrations.AddField(
            model_name="product", name="lens_mount",
            field=models.CharField(blank=True, max_length=30, verbose_name="نوع مانت / رزوه (Mount Type)",
                                   help_text="M12 / D14 / CS-Mount"),
        ),
        migrations.AddField(
            model_name="product", name="lens_kit",
            field=models.CharField(blank=True, max_length=60, verbose_name="اقلام همراه و نگهدارنده",
                                   help_text="فقط لنز / لنز + هولدر ثابت / لنز + فیلتر IR-Cut / فقط هولدر/IR-Cut"),
        ),
        migrations.AddField(
            model_name="product", name="lens_holder_pitch",
            field=models.CharField(blank=True, max_length=40, verbose_name="فاصله پیچ نصب هولدر",
                                   help_text="استاندارد رایج 20mm"),
        ),
        migrations.AddField(
            model_name="product", name="lens_fov",
            field=models.CharField(blank=True, max_length=60, verbose_name="زاویه دید افقی (FOV)",
                                   help_text="مثل 91.3° یا 30~100° برای وریفوکال"),
        ),
        migrations.RunPython(map_focal, unmap_focal),
    ]
