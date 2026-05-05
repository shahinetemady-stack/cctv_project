"""
در پوشه cctv_shop اجرا کنید:
python fix_admin2.py
"""
import os

print("\n" + "="*50)
print("  رفع مشکل admin.py")
print("="*50 + "\n")

# اصلاح orders/admin.py
path = os.path.join('apps', 'orders', 'admin.py')
with open(path, encoding='utf-8') as f:
    content = f.read()

# حذف PaymentLog از import
content = content.replace(', PaymentLog', '')
content = content.replace('PaymentLog, ', '')

# حذف PaymentLogInline کلاس
lines = content.split('\n')
new_lines = []
skip = False
for line in lines:
    if 'class PaymentLogInline' in line or '@admin.register(PaymentLog)' in line or 'class PaymentLogAdmin' in line:
        skip = True
    if skip and line.startswith('class ') and 'PaymentLog' not in line and 'PaymentLogAdmin' not in line:
        skip = False
    if not skip:
        new_lines.append(line)

content = '\n'.join(new_lines)

# حذف PaymentLogInline از inlines
content = content.replace(', PaymentLogInline', '')
content = content.replace('PaymentLogInline, ', '')
content = content.replace('[PaymentLogInline]', '[]')

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("[1/1] orders/admin.py اصلاح شد")
print("\n" + "="*50)
print("  حالا بزنید:")
print("  python manage.py migrate")
print("  python manage.py runserver")
print("="*50 + "\n")
