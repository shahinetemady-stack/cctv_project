# Generated manually for legacy_id fields + alignment with doorbinkar.com category tree

from django.db import migrations, models


def align_categories_with_legacy(apps, schema_editor):
    Category = apps.get_model("catalog", "Category")

    # ── دسته‌های ریشه: نگاشت به id سایت قدیمی + یکسان‌سازی نام/اسلاگ ──
    root_map = {
        # slug فعلی: (legacy_id, slug جدید, نام جدید)
        "camera-board":    (1,  "cctv-camera-board",      "برد دوربین مدار بسته"),
        "recorder-board":  (2,  "recorder-board",         "برد دستگاه ضبط تصاویر"),
        "lens-holder":     (3,  "lens-holder",            "لنز و نگهدارنده"),
        "camera-housing":  (4,  "camera-device-housing",  "بدنه دوربین و دستگاه"),
        "accessories":     (21, "accessories-modem",      "لوازم جانبی و مودم"),
    }
    for old_slug, (legacy_id, new_slug, name) in root_map.items():
        Category.objects.filter(slug=old_slug, parent__isnull=True).update(
            legacy_id=legacy_id, slug=new_slug, name=name,
        )

    # ── زیردسته‌های موجود ──
    child_map = {
        "ahd-board":       (8,  "ahd-camera-board",       "برد دوربین AHD"),
        "ip-board":        (9,  "ip-camera-board",        "برد دوربین تحت شبکه (IP)"),
        "dvr-board":       (10, "dvr-board",              "برد دستگاه DVR (دی وی آر)"),
        "nvr-board":       (18, "nvr-recorder-pcb-board", "برد دستگاه NVR (ان وی آر)"),
        "bullet-housing":  (15, "bullet-camera-housing",  "بدنه دوربین مداربسته بولت"),
        "dome-housing":    (16, "dome-camera-housing",    "بدنه دوربین مداربسته دام"),
        "cctv-cable":      (13, "cctv-cable",             "کابل دوربین مداربسته"),
        "modem":           (22, "modem-cctv",             "مودم 4G"),
    }
    for old_slug, (legacy_id, new_slug, name) in child_map.items():
        Category.objects.filter(slug=old_slug, parent__isnull=False).update(
            legacy_id=legacy_id, slug=new_slug, name=name,
        )

    # ── حذف «لنز استارلایت» — در سایت قدیمی وجود ندارد (استارلایت ویژگی لنز است) ──
    Category.objects.filter(slug="starlight-lens", products__isnull=True).delete()

    # ── ساخت زیردسته‌های جدید (نوع از والد به ارث می‌رسد) ──
    def parent_by_legacy(legacy_id):
        return Category.objects.get(legacy_id=legacy_id, parent__isnull=True)

    new_children = [
        # (legacy والد, legacy_id, slug, نام, ترتیب)
        (1,  19, "wifi-camera-board",  "برد دوربین وای فای",        30),
        (3,  11, "cw-lens-holder",     "لنز و نگهدارنده CW",        10),
        (3,  12, "ytot-lens-holder",   "لنز و نگهدارنده YTOT",      20),
        (21, 14, "cctv-accessories",   "لوازم جانبی",               30),
        (21, 17, "assembly-tools",     "ابزار مونتاژ",              40),
        (21, 20, "cctv-led",           "ال ای دی دوربین مداربسته",  50),
    ]
    for parent_legacy, legacy_id, slug, name, sort_order in new_children:
        parent = parent_by_legacy(parent_legacy)
        Category.objects.get_or_create(
            slug=slug,
            defaults={
                "name": name,
                "parent_id": parent.pk,
                "category_type": parent.category_type,
                "legacy_id": legacy_id,
                "is_active": True,
                "sort_order": sort_order,
            },
        )

    # ── متاهای SEO دسته‌ها (فقط جاهای خالی) ──
    for cat in Category.objects.all():
        updates = {}
        if not cat.meta_title:
            updates["meta_title"] = f"خرید {cat.name} | دوربینکار"[:60]
        if not cat.meta_description:
            updates["meta_description"] = (
                f"خرید {cat.name} با بهترین قیمت همکار از دوربینکار؛ "
                "تامین قطعات دوربین مداربسته با ضمانت کیفیت و ارسال سریع."
            )[:160]
        if updates:
            Category.objects.filter(pk=cat.pk).update(**updates)


def reverse_alignment(apps, schema_editor):
    # فقط legacy_idها پاک می‌شوند؛ تغییر نام/اسلاگ برگشت‌پذیر نیست
    Category = apps.get_model("catalog", "Category")
    Category.objects.all().update(legacy_id=None)


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0018_category_seo_and_tree"),
    ]

    operations = [
        migrations.AddField(
            model_name="category",
            name="legacy_id",
            field=models.PositiveIntegerField(
                blank=True, db_index=True, null=True, unique=True,
                verbose_name="شناسه در سایت قدیمی",
                help_text="برای ریدایرکت ۳۰۱ از doorbinkar.com",
            ),
        ),
        migrations.AddField(
            model_name="product",
            name="legacy_id",
            field=models.PositiveIntegerField(
                blank=True, db_index=True, null=True, unique=True,
                verbose_name="شناسه در سایت قدیمی",
                help_text="برای ریدایرکت ۳۰۱ از doorbinkar.com",
            ),
        ),
        migrations.RunPython(align_categories_with_legacy, reverse_alignment),
    ]
