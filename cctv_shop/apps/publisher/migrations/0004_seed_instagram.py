"""
ساخت پلتفرم اینستاگرام — idempotent (get_or_create).
"""

from django.db import migrations


def seed_instagram(apps, schema_editor):
    Platform = apps.get_model("publisher", "Platform")
    Platform.objects.get_or_create(
        slug="instagram",
        defaults={"name": "اینستاگرام", "sort_order": 6},
    )


def unseed_instagram(apps, schema_editor):
    Platform = apps.get_model("publisher", "Platform")
    Platform.objects.filter(slug="instagram").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("publisher", "0003_musictrack_channelpost_approval_status_and_more"),
    ]

    operations = [
        migrations.RunPython(seed_instagram, unseed_instagram, elidable=False),
    ]
