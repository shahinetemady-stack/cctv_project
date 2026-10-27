from django.db import migrations, models


def mark_existing_paid_orders(apps, schema_editor):
    Order = apps.get_model('orders', 'Order')
    Order.objects.filter(status='paid').update(stock_deducted=True)


class Migration(migrations.Migration):
    dependencies = [
        ('orders', '0016_cartitem_package_alter_cartitem_variant'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='stock_deducted',
            field=models.BooleanField(default=False, verbose_name='موجودی سفارش کسر شده'),
        ),
        migrations.AlterField(
            model_name='order',
            name='payment_method',
            field=models.CharField(blank=True, choices=[('cash', 'نقد'), ('transfer', 'کارت به کارت'), ('online', 'آنلاین'), ('check', 'چک'), ('credit', 'بستانکاری')], default='', max_length=50, verbose_name='روش پرداخت'),
        ),
        migrations.RunPython(mark_existing_paid_orders, migrations.RunPython.noop),
    ]
