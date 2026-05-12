from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0004_restructure_product"),
    ]
    operations = [
        migrations.RemoveField("product", "extra_specs"),
    ]
