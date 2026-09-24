from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("accounting", "0029_contact_restriction_override"),
    ]

    operations = [
        migrations.AddField(
            model_name="payment",
            name="reversal_of",
            field=models.ForeignKey(
                blank=True,
                help_text="اگر این سند، برگشتِ سند دیگری است به آن لینک می‌شود — حذف انجام نمی‌شود، سند معکوس ثبت می‌شود تا سابقه حفظ شود",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="reversals",
                to="accounting.payment",
                verbose_name="برگشتِ سند",
            ),
        ),
    ]
