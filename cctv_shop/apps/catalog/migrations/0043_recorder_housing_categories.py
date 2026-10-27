# زیردسته‌های «بدنه دستگاه DVR» و «بدنه دستگاه NVR» زیر «بدنه دوربین و دستگاه»
# + فیلدهای تخصصی کیس دستگاه ضبط (بر اساس مشخصات رایج کیس‌های DVR/NVR در بازار:
# تعداد جای هارد، فن، پاور داخلی، قفل، نوع نصب رومیزی/رک‌مونت و رنگ)
from django.db import migrations


HOUSING_FIELDS = [
    # (key, label, field_type, choices, sort_order, is_filterable)
    ("سازگار-با-برد", "سازگار با برد (مثلاً DVR چهار/هشت کانال)", "text", "", 1, False),
    ("تعداد-هارد-قابل-نصب", "تعداد هارد قابل نصب", "select", "1 هارد,2 هارد,4 هارد", 2, True),
    ("فن-خنک-کننده", "فن خنک‌کننده", "checkbox", "", 3, True),
    ("پاور-داخلی", "منبع تغذیه داخلی", "select", "بدون پاور,با پاور 12V", 4, True),
    ("قفل-محافظ", "قفل محافظ (Lock Box)", "checkbox", "", 5, False),
    ("نوع-نصب", "نوع نصب", "select", "رومیزی,رک‌مونت", 6, True),
    ("رنگ", "رنگ", "select", "مشکی,طوسی,سفید", 7, False),
]

NEW_CATS = [
    # (slug, name, sort_order, meta_title, meta_description, لیبل فیلد سازگاری برد)
    ("dvr-housing", "بدنه دستگاه DVR (دی وی آر)", 30,
     "بدنه و کیس دستگاه DVR | قیمت و خرید",
     "خرید بدنه و کیس دستگاه ضبط DVR (دی وی آر) برای مونتاژ و تعمیر؛ فلزی و پلاستیکی با جای هارد، فن خنک‌کننده و پاور داخلی. ارسال سریع از دوربینکار.",
     "سازگار با برد (مثلاً DVR چهار/هشت کانال)"),
    ("nvr-housing", "بدنه دستگاه NVR (ان وی آر)", 40,
     "بدنه و کیس دستگاه NVR | قیمت و خرید",
     "خرید بدنه و کیس دستگاه ضبط NVR (ان وی آر) تحت شبکه برای مونتاژ و تعمیر؛ فلزی با جای هارد، فن و پاور داخلی. قیمت همکار و ارسال سریع از دوربینکار.",
     "سازگار با برد (مثلاً NVR نه/شانزده کانال)"),
]


def forwards(apps, schema_editor):
    Category = apps.get_model("catalog", "Category")
    CategorySpecField = apps.get_model("catalog", "CategorySpecField")

    parent = Category.objects.filter(slug="camera-device-housing").first()
    if parent is None:
        return
    for slug, name, sort, meta_t, meta_d, compat_label in NEW_CATS:
        cat, _ = Category.objects.get_or_create(
            slug=slug,
            defaults=dict(
                name=name, parent=parent, category_type="housing",
                is_active=True, sort_order=sort,
                meta_title=meta_t, meta_description=meta_d,
            ),
        )
        for key, label, ftype, choices, s, filterable in HOUSING_FIELDS:
            if key == "سازگار-با-برد":
                label = compat_label
            CategorySpecField.objects.get_or_create(
                category=cat, key=key,
                defaults=dict(label=label, field_type=ftype, choices=choices,
                              sort_order=s, is_filterable=filterable),
            )


def backwards(apps, schema_editor):
    Category = apps.get_model("catalog", "Category")
    Category.objects.filter(
        slug__in=[c[0] for c in NEW_CATS], products__isnull=True
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0042_recorder_category_fields"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
