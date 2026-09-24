# Generated manually — مشابه خروجی makemigrations

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0027_userprofile_parent_account_phonechangerequest'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProfileChangeRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('field', models.CharField(choices=[('first_name', 'نام'), ('last_name', 'نام خانوادگی'), ('company_name', 'نام شرکت'), ('national_id', 'کد ملی'), ('address', 'آدرس')], max_length=20, verbose_name='فیلد')),
                ('new_value', models.CharField(max_length=300, verbose_name='مقدار جدید')),
                ('reason', models.CharField(blank=True, max_length=300, verbose_name='دلیل')),
                ('status', models.CharField(choices=[('pending', 'در انتظار تأیید'), ('approved', 'تأیید شده'), ('rejected', 'رد شده')], default='pending', max_length=10, verbose_name='وضعیت')),
                ('reviewed_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('reviewed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reviewed_profile_requests', to=settings.AUTH_USER_MODEL, verbose_name='بررسی\u200cکننده')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='profile_change_requests', to=settings.AUTH_USER_MODEL, verbose_name='کاربر')),
            ],
            options={
                'verbose_name': 'درخواست تغییر مشخصات',
                'verbose_name_plural': 'درخواست\u200cهای تغییر مشخصات',
                'db_table': 'users_profile_change_request',
                'ordering': ['-created_at'],
            },
        ),
    ]
