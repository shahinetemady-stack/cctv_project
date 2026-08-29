"""
بک‌فیل پرمیشن‌های فرمول قیمت (pricing_rate_view, pricing_costs_view)
برای نقش‌هایی که products_edit دارند تا رفتار فعلی بدون تغییر بماند.
"""
from django.db import migrations


NEW_PERMS = ('pricing_rate_view', 'pricing_costs_view')


def backfill(apps, schema_editor):
    Role = apps.get_model('users', 'Role')
    for role in Role.objects.all():
        perms = list(role.permissions or [])
        if 'products_edit' not in perms:
            continue
        changed = False
        for p in NEW_PERMS:
            if p not in perms:
                perms.append(p)
                changed = True
        if changed:
            role.permissions = perms
            role.save(update_fields=['permissions'])


def revert(apps, schema_editor):
    Role = apps.get_model('users', 'Role')
    for role in Role.objects.all():
        perms = [p for p in (role.permissions or []) if p not in NEW_PERMS]
        if perms != role.permissions:
            role.permissions = perms
            role.save(update_fields=['permissions'])


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0008_role_allowed_contact_types'),
    ]

    operations = [
        migrations.RunPython(backfill, revert),
    ]
