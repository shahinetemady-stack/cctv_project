from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ("users", "0003_merge_20260505_1907"),
    ]
    operations = [
        migrations.AlterField(
            model_name="user",
            name="email",
            field=models.EmailField(blank=True, null=True, unique=True, verbose_name="ایمیل"),
        ),
        migrations.AlterField(
            model_name="user",
            name="phone",
            field=models.CharField(max_length=15, unique=True, verbose_name="شماره موبایل"),
        ),
    ]
