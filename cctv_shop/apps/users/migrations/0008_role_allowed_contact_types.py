"""
۱) افزودن فیلد allowed_contact_types به Role (خالی = همه نوع‌ها)
۲) بک‌فیل پرمیشن‌های جدید طرف حساب برای نقش‌هایی که contacts_edit دارند
   تا رفتار فعلی بدون تغییر بماند.
"""
from django.db import migrations, models


NEW_PERMS = ('contacts_create', 'partner_approve')


def backfill(apps, schema_editor):
    Role = apps.get_model('users', 'Role')
    for role in Role.objects.all():
        perms = list(role.permissions or [])
        if 'contacts_edit' not in perms:
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
        ('users', '0007_exchange_rate_perm_backfill'),
    ]

    operations = [
        migrations.AddField(
            model_name='role',
            name='allowed_contact_types',
            field=models.JSONField(blank=True, default=list,
                verbose_name='نوع‌های مجاز طرف حساب',
                help_text='لیست کدهای نوع طرف حساب — خالی = همه نوع‌ها'),
        ),
        migrations.RunPython(backfill, revert),
    ]
