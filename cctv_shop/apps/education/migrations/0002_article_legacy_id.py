# Generated manually — legacy_id on Article for doorbinkar.com redirects

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("education", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="article",
            name="legacy_id",
            field=models.PositiveIntegerField(
                blank=True, db_index=True, null=True, unique=True,
                verbose_name="شناسه در سایت قدیمی",
                help_text="برای ریدایرکت ۳۰۱ از doorbinkar.com",
            ),
        ),
    ]
