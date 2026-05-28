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

new_balance = '''    @property
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

if old_balance in content:
    content = content.replace(old_balance, new_balance)
    with open(models_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("✓ models.py اصلاح شد")
else:
    print("✗ متن قدیمی پیدا نشد!")
    # نمایش بخشی از فایل برای debug
    idx = content.find('def balance_irr')
    if idx >= 0:
        print("محتوای فعلی balance_irr:")
        print(content[idx-20:idx+500])

# تست
print("\nتست balance جدید:")
from apps.accounting.models import Contact, PurchaseInvoice
for c in Contact.objects.filter(is_active=True):
    try:
        print(f"✓ {c.name} [{c.contact_type}]: IRR={c.balance_irr:,.0f} | CNY={c.balance_cny:.2f}")
    except Exception as e:
        print(f"✗ {c.name}: {e}")

print("\nبررسی فاکتورها:")
for inv in PurchaseInvoice.objects.all():
    print(f"  فاکتور #{inv.id}: تامین={inv.supplier.name} | حمل={inv.shipping_contact.name if inv.shipping_contact else 'ندارد'}")
    print(f"    کالا IRR: {sum(float(i.unit_price_cny)*inv.rate_purchase_cny*i.quantity for i in inv.items.all()):,.0f}")
    print(f"    حمل IRR: {float(inv.shipping_cost_cny)*inv.rate_shipping_cny:,.0f}")
    print(f"    ترخیص IRR: {inv.clearance_cost_irr:,.0f}")
