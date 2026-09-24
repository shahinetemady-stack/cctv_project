from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("accounting", "0031_payment_paired_with"),
    ]

    operations = [
        migrations.AlterField(
            model_name="payment",
            name="payment_type",
            field=models.CharField(
                choices=[
                    ("cash", "نقدی"),
                    ("transfer", "واریز بانک"),
                    ("cheque", "اسناد (چک)"),
                    ("discount", "تخفیف"),
                    ("installment", "قسط"),
                    ("other", "سایر"),
                ],
                max_length=20,
            ),
        ),
        migrations.CreateModel(
            name="Cheque",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("serial_number", models.CharField(max_length=50, verbose_name="شماره چک")),
                ("account_number", models.CharField(blank=True, max_length=50, verbose_name="شماره حساب چک")),
                ("bank_branch", models.CharField(blank=True, max_length=100, verbose_name="شعبه بانک")),
                ("cheque_date", models.DateField(verbose_name="تاریخ چک")),
                ("amount", models.PositiveBigIntegerField(verbose_name="مبلغ چک (ریال)")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("payment", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="cheques",
                    to="accounting.payment",
                    verbose_name="تراکنش",
                )),
            ],
            options={
                "verbose_name": "چک",
                "verbose_name_plural": "چک‌ها",
                "db_table": "accounting_cheque",
                "ordering": ["cheque_date", "id"],
            },
        ),
    ]
