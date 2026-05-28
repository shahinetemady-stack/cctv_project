import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

# مستقیم با SQL درست می‌کنیم
from django.db import connection

with connection.cursor() as cursor:
    try:
        # بررسی ستون‌های موجود
        cursor.execute("PRAGMA table_info(orders_order)")
        cols = cursor.fetchall()
        col_names = [c[1] for c in cols]
        print("Columns:", col_names)

        # اگر courier_company وجود دارد، مقدار default بگذار
        if 'courier_company' in col_names:
            cursor.execute("UPDATE orders_order SET courier_company='' WHERE courier_company IS NULL")
            print(f"Updated rows: {cursor.rowcount}")
        else:
            print("courier_company not in table - need to add")
    except Exception as e:
        print("Error:", e)

# آپدیت migration file
migration_path = os.path.join('apps', 'orders', 'migrations', '0007_order_tracking_fields.py')
if os.path.exists(migration_path):
    with open(migration_path, encoding='utf-8') as f:
        content = f.read()

    # اطمینان از اینکه default='' در migration هست
    if "default=''" not in content and "blank=True" not in content:
        content = content.replace(
            "name='courier_company',",
            "name='courier_company',\n            field=models.CharField(max_length=20, blank=True, default='', choices=[('post', 'پست'), ('tipax', 'تیپاکس'), ('chapar', 'چاپار'), ('snap', 'اسنپ‌باکس'), ('other', 'سایر')], verbose_name='شرکت پیک/پست'),"
        )

    with open(migration_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("migration updated")

# آپدیت مدل Order برای اضافه کردن blank=True
orders_models = os.path.join('apps', 'orders', 'models.py')
with open(orders_models, encoding='utf-8') as f:
    models_content = f.read()

# اگر فیلدها از طریق migration اضافه شده‌اند، از طریق SQL آپدیت می‌کنیم
import subprocess, sys
r = subprocess.run([sys.executable, 'manage.py', 'check', '--verbosity=0'],
                   capture_output=True, text=True)
print("check:", "ok" if r.returncode == 0 else r.stderr[-200:])
print("✓ done - restart server")
