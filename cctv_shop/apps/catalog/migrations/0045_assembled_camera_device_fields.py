# بهینه‌سازی فیلدهای دسته «دوربین و دستگاه ضبط» (محصولات مونتاژشده)
# دوربین مونتاژی = بدنه + لنز + برد → فیلدها بر اساس معیارهای انتخاب نصاب:
# سیستم تصویر، سنسور، پردازنده، کلاس نوری، برد دید در شب، استاندارد حفاظتی و…
from django.db import migrations


# (key, label, field_type, choices, sort_order, is_filterable)
CAMERA_FIELDS = [
    ("سیستم-تصویر", "سیستم تصویر", "select", "AHD,IP", 1, True),
    ("رزولوشن", "رزولوشن", "select", "2MP,4MP,5MP,8MP,12MP", 2, True),
    ("سنسور", "سنسور تصویر", "text", "", 3, True),
    ("پردازنده", "پردازنده (ISP)", "text", "", 4, True),
    ("نوع-لنز", "نوع لنز", "select", "ثابت (فیکس),وریفوکال دستی,موتورایز", 5, True),
    ("فاصله-کانونی", "فاصله کانونی", "text", "", 6, False),
    ("دید-در-شب", "دید در شب", "checkbox", "", 7, True),
    ("فرم-بدنه", "فرم بدنه", "select", "بولت,دام,باکس", 8, True),
    ("جنس-بدنه", "جنس بدنه", "select", "فلز,پلاستیک,فلز و پلاستیک", 9, True),
    ("کلاس-نوری", "کلاس نوری", "select",
     "معمولی IR,استارلایت Starlight,وارم‌لایت / فول‌کالر Warm Light,بلک‌لایت Blacklight", 10, True),
    ("برد-دید-در-شب", "برد دید در شب (متر)", "text", "", 11, False),
    ("استاندارد-حفاظت", "استاندارد حفاظتی", "select", "IP66,IP67,داخلی", 12, True),
    ("خروجی-چهارحالته", "خروجی 4in1 (AHD/TVI/CVI/CVBS)", "checkbox", "", 13, False),
    ("utc-osd", "کنترل UTC / منوی OSD", "checkbox", "", 14, False),
    ("میکروفون-داخلی", "میکروفون داخلی", "checkbox", "", 15, False),
    ("تغذیه", "تغذیه", "select", "12V DC,PoE,12V DC / PoE", 16, False),
    ("wdr", "WDR", "checkbox", "", 17, False),
]

DEVICE_FIELDS = [
    ("نوع-ضبط", "نوع ضبط", "select", "DVR,NVR,XVR", 1, True),
    ("تعداد-کانال", "تعداد کانال", "select", "4 کانال,8 کانال,16 کانال,32 کانال", 2, True),
    ("حداکثر-ظرفیت-هارد", "حداکثر ظرفیت هر هارد", "select", "تا 8TB,تا 10TB,تا 16TB", 3, True),
    ("تعداد-پورت-sata", "تعداد پورت SATA", "select", "1,2,4", 4, True),
    ("فشرده-سازی-ویدئو", "فشرده‌سازی ویدئو", "select",
     "H.264,H.265 / H.264,H.265+ / H.265 / H.264", 5, True),
    ("خروجی-hdmi", "حداکثر خروجی HDMI", "select", "1080P,2K,4K", 6, True),
    ("پشتیبانی-onvif", "پشتیبانی ONVIF", "checkbox", "", 7, True),
    ("تشخیص-انسان-خودرو", "تشخیص انسان و خودرو", "checkbox", "", 8, True),
    ("مکالمه-دوطرفه", "مکالمه دوطرفه (Intercom)", "checkbox", "", 9, False),
    ("اپلیکیشن-موبایل", "اپلیکیشن موبایل", "text", "", 10, False),
    ("تغذیه", "تغذیه", "text", "", 11, False),
]


def upsert_fields(CategorySpecField, cat, fields):
    for key, label, ftype, choices, sort, filterable in fields:
        CategorySpecField.objects.update_or_create(
            category=cat, key=key,
            defaults=dict(label=label, field_type=ftype, choices=choices,
                          sort_order=sort, is_filterable=filterable, is_active=True),
        )


def forwards(apps, schema_editor):
    Category = apps.get_model("catalog", "Category")
    CategorySpecField = apps.get_model("catalog", "CategorySpecField")

    cam = Category.objects.filter(slug="mvntazhi").first()
    if cam:
        upsert_fields(CategorySpecField, cam, CAMERA_FIELDS)

    dev = Category.objects.filter(slug="dvr-nvr-dstgah-zbt").first()
    if dev:
        upsert_fields(CategorySpecField, dev, DEVICE_FIELDS)
        # فیلد متنی قدیمی «ظرفیت هارد» با فیلد ساخت‌یافته جایگزین شد
        CategorySpecField.objects.filter(category=dev, key="ظرفیت-هارد").delete()


def backwards(apps, schema_editor):
    Category = apps.get_model("catalog", "Category")
    CategorySpecField = apps.get_model("catalog", "CategorySpecField")
    cam = Category.objects.filter(slug="mvntazhi").first()
    if cam:
        CategorySpecField.objects.filter(
            category=cam, key__in=[f[0] for f in CAMERA_FIELDS]).delete()
    dev = Category.objects.filter(slug="dvr-nvr-dstgah-zbt").first()
    if dev:
        CategorySpecField.objects.filter(
            category=dev, key__in=[f[0] for f in DEVICE_FIELDS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0044_remove_product_housing_type"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
