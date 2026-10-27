# فیلد «جستجو و رکورد بر اساس چهره/پلاک» برای بردهای IP
# تمایز تشخیص ساده (detection) از جستجوی ساختیافته با دیتابیس/لیست سفید/سیاه
from django.db import migrations


NEW_FIELDS = [
    ("جستجو-چهره-پلاک", "جستجو و رکورد بر اساس چهره/پلاک", "select",
     "ندارد,چهره,پلاک,چهره و پلاک", 6, True),
    # ولتاژ کاری و حفاظت صاعقه برای بردهای IP هم معنا دارد (مثل MC800 با حفاظت 6KV)
    ("محدوده-ولتاژ-کاری", "محدوده ولتاژ کاری (مثل DC 6-15V)", "text", "", 11, False),
    ("حفاظت-صاعقه", "حفاظت در برابر صاعقه (مثل 6KV)", "text", "", 12, False),
]


def forwards(apps, schema_editor):
    Category = apps.get_model("catalog", "Category")
    CategorySpecField = apps.get_model("catalog", "CategorySpecField")
    try:
        cat = Category.objects.get(slug="ip-camera-board")
    except Category.DoesNotExist:
        return
    for key, label, ftype, choices, sort, filterable in NEW_FIELDS:
        CategorySpecField.objects.get_or_create(
            category=cat, key=key,
            defaults=dict(label=label, field_type=ftype, choices=choices,
                          sort_order=sort, is_filterable=filterable),
        )


def backwards(apps, schema_editor):
    CategorySpecField = apps.get_model("catalog", "CategorySpecField")
    CategorySpecField.objects.filter(
        category__slug="ip-camera-board",
        key__in=[f[0] for f in NEW_FIELDS],
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0037_board_spec_fields"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
