"""
بک‌فیل پرمیشن «ویرایش نرخ یوان روز» (exchange_rate_edit) برای نقش‌های ادمین و حسابدار.
"""
from django.db import migrations


TARGET_ROLES = ('ادمین', 'حسابدار')
PERM = 'exchange_rate_edit'


def backfill(apps, schema_editor):
    Role = apps.get_model('users', 'Role')
    for role in Role.objects.filter(name__in=TARGET_ROLES):
        perms = list(role.permissions or [])
        if PERM not in perms:
            perms.append(PERM)
            role.permissions = perms
            role.save(update_fields=['permissions'])


def revert(apps, schema_editor):
    Role = apps.get_model('users', 'Role')
    for role in Role.objects.filter(name__in=TARGET_ROLES):
        perms = [p for p in (role.permissions or []) if p != PERM]
        if perms != role.permissions:
            role.permissions = perms
            role.save(update_fields=['permissions'])


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0006_alter_user_created_at_alter_user_updated_at_and_more'),
    ]

    operations = [
        migrations.RunPython(backfill, revert),
    ]
