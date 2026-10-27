from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0007_alter_stockmovement_movement_type"),
        ("production", "0002_assemblyorder_assembler_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="assemblyorder",
            name="warehouse",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="assembly_orders",
                to="inventory.warehouse",
                verbose_name="انبار مقصد (محصول نهایی)",
            ),
        ),
        migrations.AddField(
            model_name="assemblyorder",
            name="source_warehouse",
            field=models.ForeignKey(
                blank=True,
                help_text="خالی = همان انبار مقصد (دستورهای قدیمی)",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="assembly_orders_sourced",
                to="inventory.warehouse",
                verbose_name="انبار مبدأ (قطعات)",
            ),
        ),
    ]
