import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

models_path = os.path.join('apps', 'accounting', 'models.py')
with open(models_path, encoding='utf-8') as f:
    content = f.read()

old_balance = '''    @property
    def balance_irr(self):
        """مانده حساب به ریال — مثبت یعنی بدهکار به ما"""
        from django.db.models import Sum
        paid = self.payments.filter(currency='IRR').aggregate(s=Sum('amount'))['s'] or 0
        invoiced = self.purchase_invoices.aggregate(s=Sum('total_irr'))['s'] or 0
        return invoiced - paid

    @property
    def balance_cny(self):
        """مانده حساب به یوان"""
        from django.db.models import Sum
        paid = self.payments.filter(currency='CNY').aggregate(s=Sum('amount'))['s'] or 0
        invoiced = self.purchase_invoices.aggregate(s=Sum('total_cny'))['s'] or 0
        return invoiced - paid'''

new_balance = '''    @property
    def balance_irr(self):
        """مانده حساب به ریال — مثبت یعنی بدهکار به ما"""
        from django.db.models import Sum
        # پرداخت‌های ریالی
        paid_irr = self.payments.filter(currency='IRR').aggregate(s=Sum('amount'))['s'] or 0
        # پرداخت‌های یوانی تبدیل شده به ریال
        paid_cny_list = self.payments.filter(currency='CNY').values_list('amount', 'rate_irr')
        paid_cny_irr = sum(float(a) * float(r) for a, r in paid_cny_list)
        total_paid = float(paid_irr) + paid_cny_irr

        # جمع فاکتورها — چون total_irr property است باید loop بزنیم
        total_invoiced = sum(inv.total_irr for inv in self.purchase_invoices.all())
        return total_invoiced - total_paid

    @property
    def balance_cny(self):
        """مانده حساب به یوان"""
        from django.db.models import Sum
        paid = self.payments.filter(currency='CNY').aggregate(s=Sum('amount'))['s'] or 0
        # جمع یوان فاکتورها
        total_cny = sum(float(inv.total_cny) for inv in self.purchase_invoices.all())
        return total_cny - float(paid)'''

if old_balance in content:
    content = content.replace(old_balance, new_balance)
    with open(models_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("✓ models.py اصلاح شد")
else:
    print("متن قدیمی پیدا نشد — دستی اصلاح می‌کنیم")
    # جایگزینی مستقیم با regex
    import re
    pattern = r'(@property\s+def balance_irr.*?return invoiced - paid\s+@property\s+def balance_cny.*?return invoiced - paid)'
    content2 = re.sub(pattern, new_balance, content, flags=re.DOTALL)
    if content2 != content:
        with open(models_path, 'w', encoding='utf-8') as f:
            f.write(content2)
        print("✓ models.py با regex اصلاح شد")
    else:
        # دستی پیدا و جایگزین کن
        lines = content.split('\n')
        start = None
        for i, line in enumerate(lines):
            if 'def balance_irr' in line:
                start = i - 1  # @property
                break
        if start is not None:
            # پیدا کردن انتهای balance_cny
            end = None
            in_cny = False
            for i, line in enumerate(lines[start:], start):
                if 'def balance_cny' in line:
                    in_cny = True
                if in_cny and line.strip().startswith('return') and 'invoiced' in line:
                    end = i + 1
                    break
            if end:
                new_lines = lines[:start] + new_balance.split('\n') + lines[end:]
                with open(models_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(new_lines))
                print("✓ models.py با line replacement اصلاح شد")

# تست
print("\nتست balance:")
from importlib import reload
import apps.accounting.models as m
reload(m)
Contact = m.Contact
for c in Contact.objects.filter(is_active=True):
    try:
        print(f"✓ {c.name}: IRR={c.balance_irr:,.0f} | CNY={c.balance_cny:.2f}")
    except Exception as e:
        print(f"✗ {c.name}: {e}")
