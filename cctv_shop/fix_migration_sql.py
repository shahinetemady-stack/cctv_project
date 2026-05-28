import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection

# ─── راه حل: recreate جدول با SQLite ────────────────────────
print("Fixing courier_company NOT NULL issue...")

with connection.cursor() as cursor:
    # بررسی ستون‌های فعلی
    cursor.execute("PRAGMA table_info(orders_order)")
    cols = cursor.fetchall()
    col_names = [c[1] for c in cols]
    print("Current columns:", col_names)

    # اگر courier_company وجود دارد و NOT NULL است
    if 'courier_company' in col_names:
        # SQLite: تنها راه برای تغییر constraint = recreate table
        # اما راه ساده‌تر: DROP و ADD دوباره با default

        try:
            # Drop column (SQLite 3.35+)
            cursor.execute("ALTER TABLE orders_order DROP COLUMN courier_company")
            print("Dropped courier_company")
        except Exception as e:
            print(f"Drop failed: {e}")

        try:
            cursor.execute("ALTER TABLE orders_order DROP COLUMN delivery_status")
            print("Dropped delivery_status")
        except Exception as e:
            print(f"Drop failed: {e}")

        try:
            cursor.execute("ALTER TABLE orders_order DROP COLUMN shipped_at")
            print("Dropped shipped_at")
        except Exception as e:
            print(f"Drop failed: {e}")

        try:
            cursor.execute("ALTER TABLE orders_order DROP COLUMN delivered_at")
            print("Dropped delivered_at")
        except Exception as e:
            print(f"Drop failed: {e}")

    # اضافه کردن با default
    try:
        cursor.execute("ALTER TABLE orders_order ADD COLUMN courier_company VARCHAR(20) NOT NULL DEFAULT ''")
        print("Added courier_company with default")
    except Exception as e:
        print(f"Add courier_company: {e}")

    try:
        cursor.execute("ALTER TABLE orders_order ADD COLUMN delivery_status VARCHAR(20) NOT NULL DEFAULT 'pending'")
        print("Added delivery_status with default")
    except Exception as e:
        print(f"Add delivery_status: {e}")

    try:
        cursor.execute("ALTER TABLE orders_order ADD COLUMN shipped_at DATETIME NULL")
        print("Added shipped_at")
    except Exception as e:
        print(f"Add shipped_at: {e}")

    try:
        cursor.execute("ALTER TABLE orders_order ADD COLUMN delivered_at DATETIME NULL")
        print("Added delivered_at")
    except Exception as e:
        print(f"Add delivered_at: {e}")

# آپدیت migration تا fake شود
import subprocess, sys
r = subprocess.run(
    [sys.executable, 'manage.py', 'migrate', 'orders', '0007_order_tracking_fields', '--fake'],
    capture_output=True, text=True
)
print(r.stdout[-200:] if r.stdout else "")
if r.returncode != 0:
    print("fake migrate error:", r.stderr[-200:])

r2 = subprocess.run([sys.executable, 'manage.py', 'check', '--verbosity=0'],
                    capture_output=True, text=True)
print("✓ check ok" if r2.returncode == 0 else r2.stderr[-200:])
print("\nrestart server")
