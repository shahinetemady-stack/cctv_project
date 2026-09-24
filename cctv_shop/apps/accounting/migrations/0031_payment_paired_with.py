from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("accounting", "0030_payment_reversal_of"),
    ]

    operations = [
        migrations.AddField(
            model_name="payment",
            name="paired_with",
            field=models.ForeignKey(
                blank=True,
                help_text="دو رکورد «سند انتقال بین دو طرف حساب» با این فیلد جفت می‌شوند — ویرایش مبلغ/برگشت/حذف همیشه دوطرفه اعمال می‌شود",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="paired_by",
                to="accounting.payment",
                verbose_name="طرف مقابل سند انتقال",
            ),
        ),
    ]
