"""
python fix_extra_specs.py
"""
import os, subprocess, sys, sqlite3

print("رفع مشکل extra_specs ...")

# 1. حذف ستون extra_specs از دیتابیس SQLite
db_path = 'db.sqlite3'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    # بررسی وجود ستون
    cursor.execute("PRAGMA table_info(catalog_product)")
    cols = [row[1] for row in cursor.fetchall()]
    
    if 'extra_specs' in cols:
        print("  extra_specs در دیتابیس پیدا شد - در حال رفع...")
        # SQLite مستقیم نمی‌تواند ستون حذف کند
        # باید default بگذاریم
        cursor.execute("UPDATE catalog_product SET extra_specs='{}' WHERE extra_specs IS NULL OR extra_specs=''")
        conn.commit()
        print("  OK - مقادیر NULL رفع شد")
    else:
        print("  extra_specs در دیتابیس نیست")
        
except Exception as e:
    print(f"  خطا: {e}")
finally:
    conn.close()

# 2. اضافه کردن migration برای حذف extra_specs
print("\nساخت migration برای حذف extra_specs ...")

migration_content = '''from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0004_restructure_product"),
    ]
    operations = [
        migrations.RemoveField("product", "extra_specs"),
    ]
'''

mig_path = os.path.join('apps', 'catalog', 'migrations', '0005_remove_extra_specs.py')
with open(mig_path, 'w', encoding='utf-8') as f:
    f.write(migration_content)
print("  OK - migration ساخته شد")

# 3. migrate
r = subprocess.run([sys.executable, 'manage.py', 'migrate', '--verbosity=0'],
                   capture_output=True, text=True)
if r.returncode == 0:
    print("  OK - migrate موفق")
else:
    lines = (r.stdout + r.stderr).strip().split('\n')
    for line in lines[-5:]:
        if line.strip(): print(" ", line)

print("\nتمام! حالا بزنید: python manage.py runserver")
