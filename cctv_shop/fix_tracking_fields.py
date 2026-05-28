import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection

print("=== Fixing tracking fields ===")

with connection.cursor() as cursor:
    # بررسی ستون‌های فعلی
    cursor.execute("PRAGMA table_info(orders_order)")
    cols = {c[1]: c for c in cursor.fetchall()}
    print("courier_company notnull:", cols.get('courier_company', ['','','',0])[3])
    print("delivery_status notnull:", cols.get('delivery_status', ['','','',0])[3])

    # Drop همه ستون‌های اضافه شده
    for col in ['courier_company', 'delivery_status', 'shipped_at', 'delivered_at']:
        if col in cols:
            try:
                cursor.execute(f"ALTER TABLE orders_order DROP COLUMN {col}")
                print(f"Dropped {col}")
            except Exception as e:
                print(f"Drop {col} error: {e}")

    # اضافه کردن مجدد با DEFAULT مناسب
    adds = [
        ("courier_company", "VARCHAR(20) DEFAULT '' NOT NULL"),
        ("delivery_status", "VARCHAR(20) DEFAULT 'pending' NOT NULL"),
        ("shipped_at", "DATETIME NULL"),
        ("delivered_at", "DATETIME NULL"),
    ]
    for col_name, col_def in adds:
        try:
            cursor.execute(f"ALTER TABLE orders_order ADD COLUMN {col_name} {col_def}")
            print(f"Added {col_name}")
        except Exception as e:
            print(f"Add {col_name} error: {e}")

# تست
with connection.cursor() as cursor:
    cursor.execute("PRAGMA table_info(orders_order)")
    cols = {c[1]: c for c in cursor.fetchall()}
    print("\n=== After fix ===")
    for name in ['courier_company', 'delivery_status', 'shipped_at', 'delivered_at']:
        if name in cols:
            c = cols[name]
            print(f"  {name}: type={c[2]}, notnull={c[3]}, default={c[4]}")

import subprocess, sys
r = subprocess.run([sys.executable, 'manage.py', 'check', '--verbosity=0'],
                   capture_output=True, text=True)
print("✓ check ok" if r.returncode == 0 else r.stderr[-200:])
print("\nrestart server and test again")
