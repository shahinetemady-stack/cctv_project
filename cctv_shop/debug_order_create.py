import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection

# ─── 1. حذف فیلدهای اضافه شده و recreate با default ───────
print("=== بررسی ستون‌های جدول ===")
with connection.cursor() as cursor:
    cursor.execute("PRAGMA table_info(orders_order)")
    cols = cursor.fetchall()
    for col in cols:
        print(f"  {col[1]} | type:{col[2]} | notnull:{col[3]} | default:{col[4]}")

# ─── 2. SQLite workaround: ALTER COLUMN پشتیبانی نمی‌شود ─────
# راه حل: recreate جدول با SQLite
print("\n=== Fix via Python/Django ===")

# اضافه کردن مقدار پیش‌فرض در سطح Python برای موقع ساخت Order
# بهترین راه: پیدا کردن همه Order.objects.create() و اضافه کردن courier_company=''

views_path = os.path.join('apps', 'orders', 'views.py')
with open(views_path, encoding='utf-8') as f:
    content = f.read()

# پیدا کردن همه Order.objects.create
import re
matches = [(m.start(), m.group()) for m in re.finditer(r'Order\.objects\.create\(', content)]
print(f"Found {len(matches)} Order.objects.create")
for pos, match in matches:
    print(f"  at {pos}: {repr(content[pos:pos+200])}")
