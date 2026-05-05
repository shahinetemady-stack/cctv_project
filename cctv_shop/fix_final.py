"""
در پوشه cctv_shop اجرا کنید:
python fix_final.py
"""
import os, sqlite3, sys

print("\n" + "="*55)
print("  رفع مشکل نهایی")
print("="*55 + "\n")

# ─── 1. حذف PaymentLogInline از orders/admin.py ─────────
print("[1/3] اصلاح orders/admin.py ...")
path = os.path.join('apps', 'orders', 'admin.py')
with open(path, encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
skip_block = False
skip_names = ['PaymentLogInline', 'PaymentLogAdmin', '@admin.register(PaymentLog)']

i = 0
while i < len(lines):
    line = lines[i]
    # شروع بلاک‌هایی که باید حذف شوند
    if any(name in line for name in ['class PaymentLogInline', 'class PaymentLogAdmin']):
        skip_block = True
    elif '@admin.register(PaymentLog)' in line:
        skip_block = True
    
    if skip_block:
        # پایان بلاک: خط بعدی که با class یا @ شروع می‌شود
        if i > 0 and line.strip() and not line.startswith(' ') and not line.startswith('@') and 'PaymentLog' not in line:
            skip_block = False
            new_lines.append(line)
    else:
        # حذف PaymentLogInline از inlines لیست
        if 'PaymentLogInline' in line:
            line = line.replace(', PaymentLogInline', '').replace('PaymentLogInline, ', '').replace('PaymentLogInline', '')
        # حذف PaymentLog از import
        if 'from .models import' in line and 'PaymentLog' in line:
            line = line.replace(', PaymentLog', '').replace('PaymentLog, ', '')
        new_lines.append(line)
    i += 1

with open(path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
print("      OK")

# ─── 2. اصلاح migration dependency ─────────────────────
print("[2/3] اصلاح migration 0003 ...")
mig_path = os.path.join('apps', 'orders', 'migrations', '0003_remove_cartitem_unique_cart_variant_and_more.py')
if os.path.exists(mig_path):
    with open(mig_path, encoding='utf-8') as f:
        content = f.read()
    # اگر dependency روی 0002 دارد که در سیستم نیست، حذف کن
    if '("orders", "0002_payment_log")' in content:
        content = content.replace('("orders", "0002_payment_log"),', '')
        content = content.replace('("orders", "0002_payment_log")', '')
        with open(mig_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print("      OK - dependency اصلاح شد")
    else:
        print("      OK - نیازی به تغییر نبود")
else:
    # پیدا کردن فایل 0003
    mig_dir = os.path.join('apps', 'orders', 'migrations')
    files = sorted(os.listdir(mig_dir))
    for fn in files:
        if fn.startswith('0003') and fn.endswith('.py'):
            mig_path = os.path.join(mig_dir, fn)
            with open(mig_path, encoding='utf-8') as f:
                content = f.read()
            if '0002_payment_log' in content:
                content = content.replace('("orders", "0002_payment_log"),', '')
                with open(mig_path, 'w', encoding='utf-8') as f:
                    f.write(content)
            print(f"      OK - {fn} اصلاح شد")
            break

# ─── 3. بررسی نهایی syntax ─────────────────────────────
print("[3/3] بررسی syntax ...")
import ast
files_to_check = [
    os.path.join('apps', 'orders', 'admin.py'),
    os.path.join('apps', 'catalog', 'admin.py'),
]
all_ok = True
for f in files_to_check:
    if os.path.exists(f):
        try:
            ast.parse(open(f, encoding='utf-8').read())
            print(f"      OK: {os.path.basename(f)}")
        except SyntaxError as e:
            print(f"      ERROR: {os.path.basename(f)}: {e}")
            all_ok = False

print("\n" + "="*55)
if all_ok:
    print("  تمام! حالا بزنید:")
    print()
    print("  python manage.py migrate")
    print("  python manage.py runserver")
else:
    print("  هنوز خطا دارد - لطفاً نتیجه را بفرستید")
print("="*55 + "\n")
