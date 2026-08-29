from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ("orders", "0004_merge_20260509_1629"),
    ]
    operations = [
        migrations.AlterField(
            model_name="order",
            name="shipping_method",
            field=models.CharField(
                max_length=20, blank=True, default="",
                verbose_name="روش ارسال",
                choices=[("post","پست"),("courier","پیک"),("freight","باربری")],
            ),
        ),
    ]
