import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

models_path = os.path.join('apps', 'accounting', 'models.py')
with open(models_path, encoding='utf-8') as f:
    content = f.read()

# پیدا کردن و جایگزینی balance_irr و balance_cny
old = '''    @property
    def balance_irr(self):
        """
        مانده حساب به ریال — مثبت یعنی بدهکار به ما
        تامین‌کننده: فقط ارزش کالا (قیمت خرید × نرخ)
        شرکت حمل/ترخیص‌کار: هزینه حمل + ترخیص
        """
        from django.db.models import Sum

        # پرداخت‌های انجام شده به این طرف حساب
        paid_irr = self.payments.filter(currency='IRR').aggregate(s=Sum('amount'))['s'] or 0
        paid_cny_list = self.payments.filter(currency='CNY').values_list('amount', 'rate_irr')
        paid_cny_irr = sum(float(a) * float(r) for a, r in paid_cny_list)
        total_paid = float(paid_irr) + paid_cny_irr

        total_invoiced = 0

        # اگر تامین‌کننده است: فقط ارزش کالا
        for inv in self.purchase_invoices.all():
            items_irr = sum(
                float(item.unit_price_cny) * inv.rate_purchase_cny * item.quantity
                for item in inv.items.all()
            )
            total_invoiced += items_irr

        # اگر شرکت حمل/ترخیص‌کار است: هزینه حمل + ترخیص
        for inv in self.shipping_invoices.all():
            shipping_irr = float(inv.shipping_cost_cny) * inv.rate_shipping_cny
            clearance_irr = inv.clearance_cost_irr
            total_invoiced += shipping_irr + clearance_irr

        # هزینه‌های جانبی مرتبط با این طرف حساب
        extra_irr = self.extra_costs.aggregate(s=Sum('amount_irr'))['s'] or 0
        total_invoiced += extra_irr

        return total_invoiced - total_paid

    @property
    def balance_cny(self):
        """مانده حساب به یوان — فقط برای تامین‌کنندگان"""
        from django.db.models import Sum
        paid = self.payments.filter(currency='CNY').aggregate(s=Sum('amount'))['s'] or 0
        # جمع یوان کالا (بدون حمل)
        total_cny = 0
        for inv in self.purchase_invoices.all():
            items_cny = sum(float(item.unit_price_cny) * item.quantity for item in inv.items.all())
            total_cny += items_cny
        # حمل یوانی برای شرکت حمل
        for inv in self.shipping_invoices.all():
            total_cny += float(inv.shipping_cost_cny)
        return total_cny - float(paid)'''

new = '''    @property
    def balance_irr(self):
        """
        مانده ریالی طرف حساب:
        - تامین‌کننده: ارزش کالا به ریال (قیمت یوان × نرخ خرید × تعداد)
        - شرکت حمل/ترخیص‌کار: فقط هزینه ترخیص ریالی (حمل یوانی جداست)
        - سایر: هزینه‌های جانبی ریالی
        منهای: پرداخت‌های ریالی
        """
        from django.db.models import Sum

        # فقط پرداخت‌های ریالی کسر می‌شود
        paid_irr = self.payments.filter(currency='IRR').aggregate(s=Sum('amount'))['s'] or 0
        total_paid_irr = float(paid_irr)

        total_invoiced_irr = 0

        # تامین‌کننده: ارزش کالا به ریال
        for inv in self.purchase_invoices.all():
            items_irr = sum(
                float(item.unit_price_cny) * inv.rate_purchase_cny * item.quantity
                for item in inv.items.all()
            )
            total_invoiced_irr += items_irr

        # شرکت حمل/ترخیص‌کار: فقط هزینه ترخیص ریالی
        for inv in self.shipping_invoices.all():
            total_invoiced_irr += inv.clearance_cost_irr

        # هزینه‌های جانبی ریالی
        extra_irr = self.extra_costs.aggregate(s=Sum('amount_irr'))['s'] or 0
        total_invoiced_irr += extra_irr

        return total_invoiced_irr - total_paid_irr

    @property
    def balance_cny(self):
        """
        مانده یوانی طرف حساب:
        - تامین‌کننده: ارزش کالا به یوان
        - شرکت حمل: هزینه حمل به یوان
        منهای: پرداخت‌های یوانی
        """
        from django.db.models import Sum
        paid_cny = self.payments.filter(currency='CNY').aggregate(s=Sum('amount'))['s'] or 0
        total_paid_cny = float(paid_cny)

        total_cny = 0

        # تامین‌کننده: ارزش کالا به یوان
        for inv in self.purchase_invoices.all():
            items_cny = sum(
                float(item.unit_price_cny) * item.quantity
                for item in inv.items.all()
            )
            total_cny += items_cny

        # شرکت حمل: هزینه حمل به یوان
        for inv in self.shipping_invoices.all():
            total_cny += float(inv.shipping_cost_cny)

        return total_cny - total_paid_cny'''

if old in content:
    content = content.replace(old, new)
    with open(models_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("✓ models.py اصلاح شد")
else:
    print("✗ متن پیدا نشد — فایل را دستی چک کنید")
    import sys; sys.exit(1)

# تست
print("\nتست balance اصلاح شده:")
from apps.accounting.models import Contact
for c in Contact.objects.filter(is_active=True):
    try:
        print(f"  {c.name} [{c.contact_type}]:")
        print(f"    IRR = {c.balance_irr:,.0f} ریال")
        print(f"    CNY = {c.balance_cny:.2f} یوان")
    except Exception as e:
        print(f"  ✗ {c.name}: {e}")

print("\nانتظار داریم:")
print("  zizi (supplier): IRR=1,080,000,000 | CNY=540")
print("  mad amvaj (shipping): IRR=4,500,000 | CNY=540")
