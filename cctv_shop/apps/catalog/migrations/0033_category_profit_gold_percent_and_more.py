# Generated manually — ستون‌های قیمت مجزا برای مشتری گلد و سیلور
from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import migrations, models


def backfill_tier_profits(apps, schema_editor):
    """گلد تا امروز از ستون توحسابی و سیلور از ستون یکماهه قیمت می‌گرفت —
    مقدار فعلی همان ستون‌ها کپی می‌شود تا هیچ قیمتی تغییر نکند.
    صفر (ارث از والد) صفر باقی می‌ماند تا زنجیره ارث‌بری دست‌نخورده بماند."""
    Category = apps.get_model("catalog", "Category")
    for c in Category.objects.all().iterator():
        c.profit_gold_percent = c.profit_credit_percent
        c.profit_silver_percent = c.profit_month1_percent
        c.save(update_fields=["profit_gold_percent", "profit_silver_percent"])


def unbackfill_tier_profits(apps, schema_editor):
    Category = apps.get_model("catalog", "Category")
    Category.objects.update(profit_gold_percent=Decimal("0"), profit_silver_percent=Decimal("0"))


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0032_alter_productpricehistory_price_irr"),
    ]

    operations = [
        migrations.AddField(
            model_name="category",
            name="profit_gold_percent",
            field=models.DecimalField(
                decimal_places=2, default=Decimal("0"), max_digits=5,
                validators=[MinValueValidator(Decimal("0"))],
                verbose_name="سود مشتری گلد (%)",
            ),
        ),
        migrations.AddField(
            model_name="category",
            name="profit_silver_percent",
            field=models.DecimalField(
                decimal_places=2, default=Decimal("0"), max_digits=5,
                validators=[MinValueValidator(Decimal("0"))],
                verbose_name="سود مشتری سیلور (%)",
            ),
        ),
        migrations.RunPython(backfill_tier_profits, unbackfill_tier_profits),
    ]
