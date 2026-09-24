from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("accounting", "0032_cheque_payment_type_choices"),
    ]

    operations = [
        migrations.AddField(
            model_name="cheque",
            name="kind",
            field=models.CharField(
                choices=[("received", "دریافتی از مشتری"), ("issued", "صادره از حساب ما")],
                default="received", max_length=10, verbose_name="نوع چک",
            ),
        ),
        migrations.AddField(
            model_name="cheque",
            name="status",
            field=models.CharField(
                choices=[("in_hand", "در صندوق"), ("endorsed", "واگذار شده"), ("issued", "صادر شده")],
                default="in_hand", max_length=10, verbose_name="وضعیت",
            ),
        ),
        migrations.AddField(
            model_name="cheque",
            name="spent_payment",
            field=models.ForeignKey(
                blank=True, null=True,
                help_text="اگر چک به تأمین‌کننده واگذار شده، سند پرداختی که با آن انجام شد",
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="spent_cheques",
                to="accounting.payment",
                verbose_name="پرداخت مصرف‌کننده",
            ),
        ),
        migrations.AddField(
            model_name="cheque",
            name="drawn_account",
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="issued_cheques",
                to="accounting.account",
                verbose_name="حساب جاری صادرکننده (چک صادره)",
            ),
        ),
    ]
