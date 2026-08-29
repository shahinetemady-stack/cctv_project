"""
واحد نرخ یوان از تومان به ریال تغییر کرد — مقدار موجود × ۱۰ می‌شود تا قیمت‌ها تغییر نکنند.
"""
from django.db import migrations, models


def convert_rate_to_rial(apps, schema_editor):
    ExchangeRateSetting = apps.get_model('catalog', 'ExchangeRateSetting')
    ExchangeRateSetting.objects.all().update(rate_cny_to_irt=models.F('rate_cny_to_irt') * 10)


def revert_rate_to_toman(apps, schema_editor):
    ExchangeRateSetting = apps.get_model('catalog', 'ExchangeRateSetting')
    ExchangeRateSetting.objects.all().update(rate_cny_to_irt=models.F('rate_cny_to_irt') / 10)


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0015_category_field_overrides'),
    ]

    operations = [
        migrations.AlterField(
            model_name='exchangeratesetting',
            name='rate_cny_to_irt',
            field=models.PositiveBigIntegerField(
                default=85000,
                help_text='هر یوان چینی چند ریال؟',
                verbose_name='نرخ یوان (ریال)',
            ),
        ),
        migrations.RunPython(convert_rate_to_rial, revert_rate_to_toman),
    ]
