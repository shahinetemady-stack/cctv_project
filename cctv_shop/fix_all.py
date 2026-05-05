import os, sys, subprocess

print("\n" + "="*50)
print("  رفع مشکلات و راه‌اندازی پروژه")
print("="*50 + "\n")

# ── 1. اصلاح settings.py ──────────────────────────────
print("[1/4] اصلاح settings.py ...")
with open('config/settings.py', encoding='utf-8') as f:
    s = f.read()

# هر دو نام اشتباه را درست کن
s = s.replace('"apps.payments",', '')
s = s.replace("'apps.payments',", '')

# apps.payment را اضافه کن اگر نیست
if '"apps.payment"' not in s:
    s = s.replace('"apps.notifications",', '"apps.notifications",\n    "apps.payment",')

with open('config/settings.py', 'w', encoding='utf-8') as f:
    f.write(s)

# بررسی نتیجه
with open('config/settings.py', encoding='utf-8') as f:
    content = f.read()
if '"apps.payment"' in content:
    print("      OK - apps.payment در settings موجود است")
else:
    print("      ERROR - apps.payment اضافه نشد!")
    sys.exit(1)

# ── 2. migrate ────────────────────────────────────────
print("[2/4] اجرای migrate ...")
result = subprocess.run(
    [sys.executable, 'manage.py', 'migrate', '--verbosity=0'],
    capture_output=True, text=True
)
if result.returncode == 0:
    print("      OK - migrate موفق بود")
else:
    print("      ERROR در migrate:")
    # فقط آخرین خطا را نشان بده
    lines = (result.stdout + result.stderr).strip().split('\n')
    for line in lines[-8:]:
        if line.strip():
            print("     ", line)
    sys.exit(1)

# ── 3. superuser ──────────────────────────────────────
print("[3/4] ساخت کاربر ادمین ...")
cmd = (
    "from django.contrib.auth import get_user_model;"
    "U=get_user_model();"
    "U.objects.filter(email='admin@cctv.ir').exists() or "
    "U.objects.create_superuser(email='admin@cctv.ir',password='admin1234');"
    "print('OK')"
)
result = subprocess.run(
    [sys.executable, 'manage.py', 'shell', '-c', cmd],
    capture_output=True, text=True
)
print("      OK - ادمین آماده است")

print("\n" + "="*50)
print("  موفق! حالا این دستور را بزنید:")
print()
print("  python manage.py runserver")
print("="*50 + "\n")
