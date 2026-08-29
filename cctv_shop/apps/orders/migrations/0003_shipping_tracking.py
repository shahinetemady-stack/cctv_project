from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ("orders", "0002_payment_log"),
    ]
    operations = [
        migrations.AddField(
            model_name="order",
            name="shipping_method",
            field=models.CharField(
                max_length=20, blank=True, default="",
                verbose_name="روش ارسال",
                choices=[
                    ("post", "پست"),
                    ("courier", "پیک"),
                    ("freight", "باربری"),
                ],
            ),
        ),
        migrations.AddField(
            model_name="order",
            name="freight_company",
            field=models.CharField(
                max_length=200, blank=True,
                verbose_name="نام باربری",
            ),
        ),
        migrations.AddField(
            model_name="order",
            name="tracking_code",
            field=models.CharField(
                max_length=100, blank=True,
                verbose_name="کد رهگیری",
            ),
        ),
        migrations.AddField(
            model_name="order",
            name="paid_amount",
            field=models.PositiveBigIntegerField(
                null=True, blank=True,
                verbose_name="مبلغ پرداخت شده (تومان)",
            ),
        ),
        migrations.AddField(
            model_name="order",
            name="payment_method",
            field=models.CharField(
                max_length=50, blank=True,
                verbose_name="روش پرداخت",
                choices=[
                    ("cash", "نقد"),
                    ("transfer", "کارت به کارت"),
                    ("online", "آنلاین"),
                    ("check", "چک"),
                ],
            ),
        ),
    ]
