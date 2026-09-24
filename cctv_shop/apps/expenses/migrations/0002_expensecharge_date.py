# افزودن فیلد date به ExpenseCharge + بازپر از آخرین روز سال/ماه موجود
import calendar
from datetime import date

from django.db import migrations, models


def _backfill(apps, schema_editor):
    ExpenseCharge = apps.get_model("expenses", "ExpenseCharge")
    for c in ExpenseCharge.objects.all():
        if c.source == "general":
            # تاریخ واقعی ثبت از timestamp ساخته‌شدن
            c.date = c.created_at.date()
        else:
            c.date = date(c.year, c.month, calendar.monthrange(c.year, c.month)[1])
        c.save(update_fields=["date"])


class Migration(migrations.Migration):

    dependencies = [
        ("expenses", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="expensecharge",
            name="date",
            field=models.DateField(default=date(2000, 1, 1),
                                   verbose_name="تاریخ هزینه"),
        ),
        migrations.RunPython(_backfill, migrations.RunPython.noop),
    ]
