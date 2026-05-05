"""
این فایل را در پوشه cctv_shop بگذارید و اجرا کنید:
python fix_admin.py
"""
import subprocess, sys, os

print("\n" + "="*50)
print("  رفع مشکل سازگاری Python 3.14 با Django")
print("="*50 + "\n")

# Django 5.0.14 با Python 3.14 مشکل دارد
# باید به Django 5.1+ ارتقا دهیم
print("[1/2] ارتقای Django به نسخه جدیدتر...")
result = subprocess.run(
    [sys.executable, '-m', 'pip', 'install', 'django>=5.1', '--upgrade', '-q'],
    capture_output=True, text=True
)
if result.returncode == 0:
    print("      OK - Django ارتقا یافت")
else:
    # Django 5.1 هم کار نکرد، نسخه دیگری امتحان کنیم
    print("      امتحان نسخه دیگر...")
    result2 = subprocess.run(
        [sys.executable, '-m', 'pip', 'install', 'django==5.2', '--upgrade', '-q'],
        capture_output=True, text=True
    )
    if result2.returncode == 0:
        print("      OK - Django 5.2 نصب شد")
    else:
        print("      ERROR:", result2.stderr[-500:])

# بررسی نسخه نصب شده
result = subprocess.run(
    [sys.executable, '-c', 'import django; print(django.__version__)'],
    capture_output=True, text=True
)
print(f"      نسخه Django: {result.stdout.strip()}")

print("\n[2/2] ارتقای djangorestframework...")
subprocess.run(
    [sys.executable, '-m', 'pip', 'install', 'djangorestframework', '--upgrade', '-q'],
    capture_output=True, text=True
)
print("      OK")

print("\n" + "="*50)
print("  تمام! حالا:")
print("  1. سرور Django را ببندید (Ctrl+C)")
print("  2. دوباره: python manage.py runserver")
print("="*50 + "\n")
