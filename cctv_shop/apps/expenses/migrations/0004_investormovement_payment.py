import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('accounting', '0040_payment_opening_user_payment_settlement_target_and_more'),
        ('expenses', '0003_alter_expensecharge_date'),
    ]

    operations = [
        migrations.AddField(
            model_name='investormovement',
            name='payment',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='investor_movement', to='accounting.payment', verbose_name='سند نقدی'),
        ),
    ]
