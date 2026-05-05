"""
در پوشه cctv_shop اجرا کنید:
python fix_db.py
"""
import sqlite3, os, sys

print("\n" + "="*50)
print("  رفع مشکل دیتابیس")
print("="*50 + "\n")

# پیدا کردن فایل دیتابیس
db_path = 'db.sqlite3'
if not os.path.exists(db_path):
    print("ERROR: فایل db.sqlite3 پیدا نشد!")
    sys.exit(1)

print("[1/2] اصلاح دیتابیس...")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    # اگر جدول وجود دارد، extra_specs را درست کن
    cursor.execute("""
        UPDATE catalog_product 
        SET extra_specs='{}' 
        WHERE extra_specs IS NULL OR extra_specs=''
    """)
    conn.commit()
    print("      OK")
except Exception as e:
    print(f"      Note: {e}")

conn.close()

print("[2/2] اصلاح کد models.py...")
# اضافه کردن blank=True به extra_specs در migration
models_path = os.path.join('apps', 'catalog', 'migrations', '0001_initial.py')
if os.path.exists(models_path):
    with open(models_path, encoding='utf-8') as f:
        content = f.read()
    
    # اضافه کردن default به extra_specs اگر نیست
    if 'extra_specs' in content and 'default=dict' not in content:
        content = content.replace(
            '"extra_specs", models.JSONField(',
            '"extra_specs", models.JSONField(default=dict, blank=True, '
        )
        with open(models_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print("      OK - migration اصلاح شد")
    else:
        print("      OK - نیازی به تغییر نبود")

print("\n" + "="*50)
print("  تمام! حالا:")
print("  1. سرور را ببندید (Ctrl+C)")  
print("  2. python manage.py migrate")
print("  3. python manage.py runserver")
print("="*50 + "\n")
