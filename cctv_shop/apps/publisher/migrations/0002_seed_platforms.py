"""
ساخت پنج پلتفرم پیش‌فرض از PLATFORMS_SEED — idempotent (get_or_create).
"""

from django.db import migrations


def seed_platforms(apps, schema_editor):
    Platform = apps.get_model("publisher", "Platform")
    from apps.publisher.services import PLATFORMS_SEED
    for item in PLATFORMS_SEED:
        Platform.objects.get_or_create(
            slug=item["slug"],
            defaults={"name": item["name"], "sort_order": item["sort_order"]},
        )


def unseed_platforms(apps, schema_editor):
    Platform = apps.get_model("publisher", "Platform")
    from apps.publisher.services import PLATFORMS_SEED
    Platform.objects.filter(slug__in=[item["slug"] for item in PLATFORMS_SEED]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("publisher", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_platforms, unseed_platforms, elidable=False),
    ]
