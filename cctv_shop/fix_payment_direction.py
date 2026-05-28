import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.accounting.models import Payment, Contact

# ─── 1. اصلاح direction پرداخت ───────────────────────────────
p = Payment.objects.get(id=1)
print(f"قبل: direction={p.direction} | amount={p.amount} {p.currency}")
p.direction = 'out'  # پرداختی از ما به طرف حساب
p.save()
print(f"بعد: direction={p.direction}")

# ─── 2. اصلاح balance در models.py ───────────────────────────
models_path = os.path.join('apps', 'accounting', 'models.py')
with open(models_path, encoding='utf-8') as f:
    content = f.read()

old_irr = '''        # فقط پرداخت‌های ریالی کسر می‌شود
        paid_irr = self.payments.filter(currency='IRR').aggregate(s=Sum('amount'))['s'] or 0
        total_paid_irr = float(paid_irr)'''

new_irr = '''        # پرداخت‌های خروجی (از ما به طرف حساب) ریالی
        paid_irr = self.payments.filter(currency='IRR', direction='out').aggregate(s=Sum('amount'))['s'] or 0
        total_paid_irr = float(paid_irr)'''

old_cny = '''        paid_cny = self.payments.filter(currency='CNY').aggregate(s=Sum('amount'))['s'] or 0
        total_paid_cny = float(paid_cny)'''

new_cny = '''        # پرداخت‌های خروجی (از ما به طرف حساب) یوانی
        paid_cny = self.payments.filter(currency='CNY', direction='out').aggregate(s=Sum('amount'))['s'] or 0
        total_paid_cny = float(paid_cny)'''

changed = False
if old_irr in content:
    content = content.replace(old_irr, new_irr)
    changed = True
if old_cny in content:
    content = content.replace(old_cny, new_cny)
    changed = True

if changed:
    with open(models_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("✓ models.py اصلاح شد")
else:
    print("⚠ models.py نیاز به اصلاح دستی دارد")

# ─── 3. تست ──────────────────────────────────────────────────
print("\n=== تست balance اصلاح شده ===")
for c in Contact.objects.filter(is_active=True):
    print(f"\n{c.name} [{c.contact_type}]:")
    print(f"  مانده ریال: {c.balance_irr:,.0f}")
    print(f"  مانده یوان: {c.balance_cny:.2f}")

print("\n=== انتظار ===")
print("zizi: ریال=0 | یوان=0 (تسویه کامل)")
print("mad amvaj: ریال=4,500,000 | یوان=540")
