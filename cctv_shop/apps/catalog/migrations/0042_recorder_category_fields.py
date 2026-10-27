# نوع جدید «برد دستگاه ضبط» (recorder) + ویژگی‌های تخصصی DVR/NVR
# بر اساس دیتاشیت‌های RUISION (سری AT64xxM-V2 و N216-S1)
from django.db import migrations, models


# ویژگی‌های مشترک ریشه «برد دستگاه ضبط تصاویر» (به هر دو زیردسته می‌رسد)
COMMON_FIELDS = [
    # (key, label, field_type, choices, sort_order, is_filterable)
    ("تعداد-کانال", "تعداد کانال", "select", "4 کانال,8 کانال,10 کانال,16 کانال,32 کانال", 1, True),
    ("حداکثر-رزولوشن-ورودی", "حداکثر رزولوشن ورودی", "select", "2MP (1080P),4MP,5MP,8MP (4K)", 2, True),
    ("پردازنده-اصلی", "پردازنده اصلی", "text", "", 3, True),
    ("فشرده-سازی-ویدئو", "فشرده‌سازی ویدئو", "select",
     "H.264,H.265 / H.264,H.265+ / H.265 / H.264", 4, True),
    ("خروجی-hdmi", "حداکثر خروجی HDMI", "select", "1080P,2K,4K", 5, True),
    ("تعداد-پورت-sata", "تعداد پورت SATA", "select", "1,2,4", 6, True),
    ("حداکثر-ظرفیت-هارد", "حداکثر ظرفیت هر هارد", "select", "تا 8TB,تا 10TB,تا 16TB", 7, True),
    ("مکالمه-دوطرفه", "مکالمه دوطرفه (Intercom)", "checkbox", "", 8, True),
    ("پشتیبانی-onvif", "پشتیبانی ONVIF", "checkbox", "", 9, True),
    ("کنترل-ptz", "کنترل PTZ", "checkbox", "", 10, True),
    ("اپلیکیشن-موبایل", "اپلیکیشن موبایل", "text", "", 11, False),
    ("پورت-شبکه", "پورت شبکه", "select", "RJ45 10/100Mbps,RJ45 گیگابیت (10/100/1000)", 12, False),
    ("تغذیه", "تغذیه", "text", "", 13, False),
]

# مخصوص بردهای DVR/HVR (ورودی کواکسیال)
DVR_FIELDS = [
    ("ورودی-پنج-کاره", "ورودی 5in1 (AHD/TVI/CVI/CVBS/IP)", "checkbox", "", 1, True),
    ("صدای-کواکسیال", "صدای کواکسیال (Coax Audio)", "checkbox", "", 2, True),
    ("پشتیبانی-utc", "کنترل UTC (تنظیم منوی دوربین)", "checkbox", "", 3, True),
    ("دانگل-4g", "پشتیبانی دانگل 4G USB", "checkbox", "", 4, False),
    ("پشتیبانی-دوال-لایت", "پشتیبانی دوال‌لایت هوشمند", "checkbox", "", 5, True),
    ("حصار-الکترونیکی", "حصار الکترونیکی (E-Fence)", "checkbox", "", 6, False),
    ("تشخیص-عبور-از-خط", "تشخیص عبور از خط (Cross-Line)", "checkbox", "", 7, False),
    ("آمار-تردد", "آمار تردد (Passenger Flow)", "checkbox", "", 8, False),
]

# مخصوص بردهای NVR (ورودی شبکه)
NVR_FIELDS = [
    ("پهنای-باند-ورودی", "پهنای باند ورودی", "text", "", 1, False),
    ("تشخیص-انسان-خودرو", "تشخیص انسان و خودرو", "checkbox", "", 2, True),
    ("پخش-هوشمند", "پخش هوشمند رویدادها (Smart Playback)", "checkbox", "", 3, False),
    ("خروجی-صدا-اکتیو", "خروجی صدای 3.5mm / بلندگوی آمپلی‌فایردار", "checkbox", "", 4, False),
]


def forwards(apps, schema_editor):
    Category = apps.get_model("catalog", "Category")
    CategorySpecField = apps.get_model("catalog", "CategorySpecField")

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

    # ریشه و زیردسته‌ها به نوع recorder تغییر می‌کنند تا گروه‌های فیلد برد دوربین
    # (سنسور، سیستم AHD/IP و…) در فرمشان نمایش داده نشود
    Category.objects.filter(
        slug__in=["recorder-board", "dvr-board", "nvr-recorder-pcb-board"]
    ).update(category_type="recorder")

    add_fields("recorder-board", COMMON_FIELDS)
    add_fields("dvr-board", DVR_FIELDS)
    add_fields("nvr-recorder-pcb-board", NVR_FIELDS)


def backwards(apps, schema_editor):
    Category = apps.get_model("catalog", "Category")
    CategorySpecField = apps.get_model("catalog", "CategorySpecField")
    Category.objects.filter(
        slug__in=["recorder-board", "dvr-board", "nvr-recorder-pcb-board"]
    ).update(category_type="board")
    for slug, fields in (("recorder-board", COMMON_FIELDS), ("dvr-board", DVR_FIELDS),
                         ("nvr-recorder-pcb-board", NVR_FIELDS)):
        CategorySpecField.objects.filter(
            category__slug=slug, key__in=[f[0] for f in fields]
        ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0041_lens_optics_fields'),
    ]

    operations = [
        migrations.AlterField(
            model_name='category',
            name='category_type',
            field=models.CharField(choices=[('board', 'برد دوربین مداربسته'), ('lens', 'لنز دوربین مداربسته'), ('modem', 'مودم و ماژول'), ('housing', 'بدنه دوربین مداربسته'), ('accessory', 'لوازم جانبی'), ('recorder', 'برد دستگاه ضبط'), ('other', 'سایر')], db_index=True, default='other', max_length=20, verbose_name='نوع دسته'),
        ),
        migrations.RunPython(forwards, backwards),
    ]
