"""
python fix_db.py
"""
import os, django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection

print("rebuild جدول orders_order ...")

with connection.cursor() as c:
    # خواندن ساختار فعلی
    c.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='orders_order'")
    original_sql = c.fetchone()[0]
    
    # تغییر shipping_method از NOT NULL به nullable
    new_sql = original_sql.replace(
        '"shipping_method" varchar(20) NOT NULL',
        '"shipping_method" varchar(20) NOT NULL DEFAULT \'\''
    )
    
    if new_sql == original_sql:
        # روش دیگر
        new_sql = original_sql.replace(
            'shipping_method" varchar(20) NOT NULL',
            'shipping_method" varchar(20) NOT NULL DEFAULT \'\''
        )
    
    print("  تغییر DEFAULT اعمال می‌شود...")
    
    # SQLite نمی‌تواند مستقیم ALTER کند - باید جدول جدید بسازیم
    c.execute("PRAGMA foreign_keys=OFF")
    
    # ساخت جدول موقت با default
    temp_sql = new_sql.replace('CREATE TABLE "orders_order"', 'CREATE TABLE "orders_order_new"')
    
    try:
        c.execute(temp_sql)
        # کپی داده‌ها
        c.execute("INSERT INTO orders_order_new SELECT * FROM orders_order")
        # حذف قدیمی
        c.execute("DROP TABLE orders_order")
        # rename
        c.execute("ALTER TABLE orders_order_new RENAME TO orders_order")
        c.execute("PRAGMA foreign_keys=ON")
        connection.commit()
        print("  OK - جدول rebuild شد")
    except Exception as e:
        print(f"  روش ۱ ناموفق: {e}")
        # روش ساده‌تر: فقط default بگذار
        try:
            c.execute("ALTER TABLE orders_order ADD COLUMN shipping_method_new varchar(20) NOT NULL DEFAULT ''")
            c.execute("UPDATE orders_order SET shipping_method_new = COALESCE(shipping_method, '')")
            print("  OK - ستون جدید اضافه شد")
        except Exception as e2:
            print(f"  روش ۲ هم ناموفق: {e2}")

# تست
with connection.cursor() as c:
    c.execute("INSERT INTO orders_order (user_id, order_number, order_type, status, total_amount, shipping_address, customer_notes, admin_notes, payment_link, confirmed_amount) VALUES (1, 'TEST-999', 'inquiry', 'pending', 0, '', '', '', '', NULL)")
    c.execute("DELETE FROM orders_order WHERE order_number='TEST-999'")
    connection.commit()
    print("  OK - تست insert موفق!")

print("\nتمام! حالا بزنید: python manage.py runserver")
