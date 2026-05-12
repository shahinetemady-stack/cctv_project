import os, subprocess, sys

print("رفع مشکل shipping_method ...")

# 1. مستقیم دیتابیس را درست کن
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection
cursor = connection.cursor()

# بررسی ستون
try:
    cursor.execute("UPDATE orders_order SET shipping_method='' WHERE shipping_method IS NULL")
    connection.commit()
    print("  OK - مقادیر NULL پاک شد")
except Exception as e:
    print(f"  {e}")

# 2. migration برای nullable کردن
migration = '''from django.db import migrations, models

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
'''

mig_path = os.path.join('apps','orders','migrations','0005_fix_shipping_nullable.py')
with open(mig_path, 'w', encoding='utf-8') as f:
    f.write(migration)
print("  OK - migration ساخته شد")

r = subprocess.run([sys.executable,'manage.py','migrate','--verbosity=0'],
                   capture_output=True, text=True)
if r.returncode == 0:
    print("  OK - migrate موفق")
else:
    for line in (r.stdout+r.stderr).strip().split('\n')[-5:]:
        if line.strip(): print(" ", line)

print("\nتمام! حالا بزنید: python manage.py runserver")
