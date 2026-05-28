import os, django, sqlite3
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection

# بررسی ساختار جدول
with connection.cursor() as cursor:
    cursor.execute("PRAGMA table_info(orders_order)")
    cols = cursor.fetchall()
    for col in cols:
        print(col)  # (cid, name, type, notnull, default, pk)

print("\n--- fixing ---")

# SQLite روش مستقیم برای تغییر constraint ندارد
# باید جدول را recreate کنیم یا از روش دیگری استفاده کنیم
# ساده‌ترین راه: حذف migration و ساخت مجدد

# ابتدا بررسی می‌کنیم آیا ستون‌ها وجود دارند
with connection.cursor() as cursor:
    cursor.execute("PRAGMA table_info(orders_order)")
    cols = {c[1]: c for c in cursor.fetchall()}

    has_courier = 'courier_company' in cols
    has_delivery = 'delivery_status' in cols
    has_shipped = 'shipped_at' in cols

    print(f"courier_company exists: {has_courier}, notnull: {cols.get('courier_company', (None,)*4)[3]}")

    if has_courier and cols['courier_company'][3] == 1:  # notnull=1
        print("Need to recreate table or use workaround...")
        # SQLite: تنها راه = ALTER TABLE بدون تغییر constraint
        # راه حل: آپدیت مقادیر NULL قبل از هر insert
        print("Setting default values for existing NULL rows...")
        cursor.execute("UPDATE orders_order SET courier_company='' WHERE courier_company IS NULL OR courier_company=''")
        print(f"Updated: {cursor.rowcount} rows")

# راه حل اصلی: آپدیت view برای اینکه courier_company پاس بدهد
views_path = os.path.join('apps', 'orders', 'views.py')
with open(views_path, encoding='utf-8') as f:
    views = f.read()

# پیدا کردن جایی که Order ساخته می‌شود
idx = views.find('Order.objects.create')
if idx >= 0:
    print(f"\nOrder.objects.create at: {idx}")
    print(repr(views[idx:idx+300]))
