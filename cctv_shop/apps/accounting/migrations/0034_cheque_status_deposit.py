from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("accounting", "0033_cheque_lifecycle"),
    ]

    operations = [
        migrations.AlterField(
            model_name="cheque",
            name="status",
            field=models.CharField(
                choices=[
                    ("in_hand", "در صندوق"),
                    ("deposited", "خوابانده به حساب بانکی"),
                    ("endorsed", "واگذار شده"),
                    ("returned", "برگشت داده شده به مشتری"),
                    ("bounced", "برگشتی از بانک"),
                    ("issued", "صادر شده"),
                ],
                default="in_hand", max_length=10, verbose_name="وضعیت",
            ),
        ),
        migrations.AddField(
            model_name="cheque",
            name="deposited_account",
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="deposited_cheques",
                to="accounting.account",
                verbose_name="حساب بانکی خوابانده‌شده",
            ),
        ),
    ]
