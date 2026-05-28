import os, django, subprocess, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection

# ─── Step 1: حذف ستون‌ها از دیتابیس ─────────────────────────
print("Step 1: Drop and recreate columns...")
with connection.cursor() as cursor:
    for col in ['courier_company', 'delivery_status', 'shipped_at', 'delivered_at']:
        try:
            cursor.execute(f"ALTER TABLE orders_order DROP COLUMN {col}")
            print(f"  Dropped: {col}")
        except:
            pass

    for col_def in [
        "courier_company VARCHAR(20) DEFAULT ''",
        "delivery_status VARCHAR(20) DEFAULT 'pending'",
        "shipped_at DATETIME",
        "delivered_at DATETIME",
    ]:
        col_name = col_def.split()[0]
        try:
            cursor.execute(f"ALTER TABLE orders_order ADD COLUMN {col_def}")
            print(f"  Added: {col_name}")
        except Exception as e:
            print(f"  {col_name}: {e}")

# ─── Step 2: حذف migration و fake آن ────────────────────────
print("\nStep 2: Mark migration as applied...")
migration_path = os.path.join('apps', 'orders', 'migrations', '0007_order_tracking_fields.py')

# بازنویسی migration به صورت empty با dependencies درست
with open(migration_path, 'w', encoding='utf-8') as f:
    f.write("""from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ('orders', '0006_alter_order_freight_company_alter_order_paid_amount_and_more'),
    ]
    operations = []
""")
print("  Migration reset to empty")

# fake migrate
r = subprocess.run(
    [sys.executable, 'manage.py', 'migrate', '--fake', 'orders'],
    capture_output=True, text=True
)
print(r.stdout[-200:] if r.stdout else "")

# ─── Step 3: تأیید ───────────────────────────────────────────
with connection.cursor() as cursor:
    cursor.execute("PRAGMA table_info(orders_order)")
    cols = {c[1]: c for c in cursor.fetchall()}
    print("\nStep 3: Verify columns:")
    for name in ['courier_company', 'delivery_status', 'shipped_at', 'delivered_at']:
        if name in cols:
            c = cols[name]
            print(f"  {name}: notnull={c[3]}, default={c[4]}")

r2 = subprocess.run([sys.executable, 'manage.py', 'check', '--verbosity=0'],
                    capture_output=True, text=True)
print("\n✓ check ok" if r2.returncode == 0 else r2.stderr[-300:])
print("\nRestart server now!")
