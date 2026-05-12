from django.db import migrations, models
import django.core.validators
from decimal import Decimal

class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0006_add_field_choices"),
    ]
    operations = [
        # هزینه حمل: از تومان به یوان
        migrations.RenameField("productvariant", "shipping_cost", "shipping_cost_cny"),
        migrations.AlterField(
            model_name="productvariant",
            name="shipping_cost_cny",
            field=models.DecimalField(
                max_digits=8, decimal_places=2, default=0,
                verbose_name="هزینه حمل (یوان)",
                validators=[django.core.validators.MinValueValidator(Decimal("0"))],
            ),
        ),
        # سود: از تومان به درصد
        migrations.RenameField("productvariant", "profit_margin", "profit_percent"),
        migrations.AlterField(
            model_name="productvariant",
            name="profit_percent",
            field=models.DecimalField(
                max_digits=5, decimal_places=2, default=0,
                verbose_name="سود (%)",
                help_text="درصد سود روی قیمت خرید + حمل. مثال: 20 یعنی ۲۰٪",
                validators=[django.core.validators.MinValueValidator(Decimal("0"))],
            ),
        ),
    ]
