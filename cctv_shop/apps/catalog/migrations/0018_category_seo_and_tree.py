# Generated manually for category SEO fields + fixed category tree

from django.db import migrations, models


def seed_category_tree(apps, schema_editor):
    Category = apps.get_model("catalog", "Category")

    # ── آپدیت دسته‌های ریشهٔ موجود (بدون تغییر id، چون محصولات لینک شده‌اند) ──
    root_updates = {
        1: {"name": "برد دوربین مداربسته", "slug": "camera-board", "category_type": "board", "sort_order": 10},
        2: {"name": "لنز و نگهدارنده", "slug": "lens-holder", "category_type": "lens", "sort_order": 30},
        3: {"name": "بدنه دوربین", "slug": "camera-housing", "category_type": "housing", "sort_order": 40},
        4: {"name": "متعلقات و لوازم", "slug": "accessories", "category_type": "modem", "sort_order": 50},
    }
    for pk, data in root_updates.items():
        Category.objects.filter(pk=pk).update(**data)

    # ── آپدیت اسلاگ انگلیسی زیردستهٔ موجود ──
    Category.objects.filter(pk=8).update(slug="starlight-lens", sort_order=5)

    # ── ساخت دستهٔ ریشهٔ جدید: برد دستگاه ضبط ──
    recorder_board, _ = Category.objects.get_or_create(
        slug="recorder-board",
        defaults={
            "name": "برد دستگاه ضبط",
            "category_type": "board",
            "is_active": True,
            "sort_order": 20,
        },
    )

    # ── ساخت زیردسته‌ها ──
    children = [
        # زیردسته‌های برد دوربین مداربسته
        (1, "ahd-board", "برد AHD", "board", 10),
        (1, "ip-board", "برد IP", "board", 20),
        # زیردسته‌های برد دستگاه ضبط
        (recorder_board.pk, "dvr-board", "برد DVR", "board", 10),
        (recorder_board.pk, "nvr-board", "برد NVR", "board", 20),
        # زیردسته‌های بدنه دوربین
        (3, "bullet-housing", "بدنه بولت", "housing", 10),
        (3, "dome-housing", "بدنه دام", "housing", 20),
        # زیردسته‌های متعلقات و لوازم
        (4, "cctv-cable", "کابل", "modem", 10),
        (4, "modem", "مودم", "modem", 20),
    ]

    for parent_id, slug, name, cat_type, sort_order in children:
        Category.objects.get_or_create(
            slug=slug,
            defaults={
                "name": name,
                "parent_id": parent_id,
                "category_type": cat_type,
                "is_active": True,
                "sort_order": sort_order,
            },
        )


def reverse_seed(apps, schema_editor):
    # حذف زیردسته‌هایی که توسط این مایگریشن ساخته شده‌اند
    Category = apps.get_model("catalog", "Category")
    created_slugs = {
        "recorder-board",
        "ahd-board", "ip-board", "wifi-board",
        "dvr-board", "nvr-board",
        "bullet-housing", "dome-housing",
        "cctv-cable", "assembly-tools", "cctv-led", "modem",
    }
    Category.objects.filter(slug__in=created_slugs).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0017_subcategory_fields_to_parent"),
    ]

    operations = [
        migrations.AddField(
            model_name="category",
            name="description",
            field=models.TextField(blank=True, verbose_name="توضیحات دسته"),
        ),
        migrations.AddField(
            model_name="category",
            name="meta_title",
            field=models.CharField(blank=True, max_length=60, verbose_name="Meta Title"),
        ),
        migrations.AddField(
            model_name="category",
            name="meta_description",
            field=models.CharField(blank=True, max_length=160, verbose_name="Meta Description"),
        ),
        migrations.RunPython(seed_category_tree, reverse_seed),
    ]
