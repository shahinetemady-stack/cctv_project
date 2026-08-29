from django.db import migrations, models
from decimal import Decimal
import django.core.validators

class Migration(migrations.Migration):
    dependencies = [
        ("users", "0001_initial"),
    ]
    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="discount_percent",
            field=models.DecimalField(
                max_digits=5, decimal_places=2, default=Decimal("0"),
                verbose_name="درصد تخفیف همکار",
                help_text="مثال: 15 یعنی ۱۵٪ تخفیف روی قیمت نهایی",
                validators=[
                    django.core.validators.MinValueValidator(Decimal("0")),
                    django.core.validators.MaxValueValidator(Decimal("100")),
                ],
            ),
        ),
    ]
