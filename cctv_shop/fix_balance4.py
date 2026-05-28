import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

models_path = os.path.join('apps', 'accounting', 'models.py')
with open(models_path, encoding='utf-8') as f:
    content = f.read()

old = '''        # پرداخت‌های خروجی (از ما به طرف حساب) ریالی
        paid_irr = self.payments.filter(currency='IRR', direction='out').aggregate(s=Sum('amount'))['s'] or 0
        total_paid_irr = float(paid_irr)'''

new = '''        # پرداخت‌های خروجی ریالی
        paid_irr = self.payments.filter(currency='IRR', direction='out').aggregate(s=Sum('amount'))['s'] or 0
        # پرداخت‌های خروجی یوانی — تبدیل به ریال با نرخ ثبت شده
        paid_cny_list = self.payments.filter(currency='CNY', direction='out').values_list('amount', 'rate_irr')
        paid_cny_as_irr = sum(float(a) * float(r) for a, r in paid_cny_list)
        total_paid_irr = float(paid_irr) + paid_cny_as_irr'''

if old in content:
    content = content.replace(old, new)
    with open(models_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("✓ models.py اصلاح شد")
else:
    print("✗ متن پیدا نشد")
    import sys; sys.exit(1)

# تست
print("\n=== تست ===")
from apps.accounting.models import Contact, Payment

# نرخ پرداخت zizi را چک کنیم
p = Payment.objects.get(id=1)
print(f"پرداخت: {p.amount} {p.currency} | rate_irr={p.rate_irr}")
print(f"معادل ریال: {float(p.amount) * p.rate_irr:,.0f}")

for c in Contact.objects.filter(is_active=True):
    print(f"\n{c.name} [{c.contact_type}]:")
    print(f"  ریال: {c.balance_irr:,.0f}")
    print(f"  یوان: {c.balance_cny:.2f}")

print("\n=== انتظار ===")
print("zizi: ریال=0 | یوان=0")
print("mad amvaj: ریال=4,500,000 | یوان=540")
