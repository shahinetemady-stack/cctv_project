import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

# ─── اضافه کردن صفحه گزارش به accounting/admin.py ───────────
admin_path = os.path.join('apps', 'accounting', 'admin.py')
with open(admin_path, encoding='utf-8') as f:
    content = f.read()

custom_admin = '''

# ─── Custom Admin Views ──────────────────────────────────────

from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator
from django.views import View
from django.shortcuts import render
from django.urls import path as url_path


class BalanceReportAdminView(View):
    """صفحه تراز در Django Admin"""

    @method_decorator(staff_member_required)
    def get(self, request):
        from .models import Contact, SaleInvoice, Account
        from apps.catalog.models import ExchangeRateSetting
        from apps.inventory.models import WarehouseStock
        from django.db.models import Sum

        rate = ExchangeRateSetting.get_instance().rate_cny_to_irt // 10

        # ─── تراز طرف حساب‌ها ──────────────────────────────
        contacts = []
        for c in Contact.objects.filter(is_active=True):
            bal_irr = c.balance_irr
            bal_cny = c.balance_cny
            if bal_irr != 0 or bal_cny != 0:
                contacts.append({
                    'name': c.name,
                    'type': c.get_contact_type_display(),
                    'balance_irr': bal_irr,
                    'balance_cny': float(bal_cny),
                    'status_irr': 'بستانکار' if bal_irr > 0 else 'بدهکار',
                    'status_cny': 'بستانکار' if bal_cny > 0 else 'بدهکار',
                })

        # ─── موجودی انبارها ─────────────────────────────────
        stock_value = 0
        stock_items = []
        for ws in WarehouseStock.objects.select_related('variant__product', 'warehouse').filter(quantity__gt=0):
            pi = ws.variant.purchase_items.order_by('-invoice__date').first()
            cost = pi.unit_cost_irr if pi else 0
            total = cost * ws.quantity
            stock_value += total
            stock_items.append({
                'warehouse': ws.warehouse.name,
                'product': ws.variant.product.name,
                'sku': ws.variant.sku,
                'qty': ws.quantity,
                'cost': cost,
                'total': total,
            })

        # ─── فاکتورهای فروش ─────────────────────────────────
        invoices = SaleInvoice.objects.filter(status__in=['confirmed', 'paid'])
        total_revenue = sum(inv.total_amount for inv in invoices)
        total_cost_sold = sum(inv.total_cost for inv in invoices)
        gross_profit = total_revenue - total_cost_sold

        # ─── حساب‌های بانکی ─────────────────────────────────
        accounts = []
        cash_total = 0
        for a in Account.objects.filter(is_active=True):
            bal = a.balance
            accounts.append({
                'name': a.name,
                'type': a.get_account_type_display(),
                'currency': a.currency,
                'balance': bal,
            })
            if a.currency == 'IRR':
                cash_total += bal

        # ─── جمع‌بندی ────────────────────────────────────────
        payable_irr = sum(c['balance_irr'] for c in contacts if c['balance_irr'] > 0)
        payable_cny = sum(c['balance_cny'] for c in contacts if c['balance_cny'] > 0)
        receivable = sum(
            inv.remaining_amount for inv in SaleInvoice.objects.filter(status__in=['confirmed', 'paid'])
            if inv.remaining_amount > 0
        )
        total_assets = stock_value + receivable + cash_total + int(payable_cny * rate)
        total_liabilities = payable_irr + int(payable_cny * rate)
        equity = total_assets - total_liabilities

        context = {
            'title': 'تراز و گزارشات مالی',
            'contacts': contacts,
            'stock_items': stock_items,
            'stock_value': stock_value,
            'accounts': accounts,
            'cash_total': cash_total,
            'receivable': receivable,
            'total_revenue': total_revenue,
            'total_cost_sold': total_cost_sold,
            'gross_profit': gross_profit,
            'payable_irr': payable_irr,
            'payable_cny': payable_cny,
            'total_assets': total_assets,
            'total_liabilities': total_liabilities,
            'equity': equity,
            'rate': rate,
            'opts': {'app_label': 'accounting'},
            'has_permission': True,
        }
        return render(request, 'admin/accounting/balance_report.html', context)


# ثبت URL در admin
from django.contrib import admin as django_admin

_original_get_urls = django_admin.site.__class__.get_urls

def get_urls_with_balance(self):
    urls = _original_get_urls(self)
    custom = [
        url_path('accounting/balance-report/', BalanceReportAdminView.as_view(), name='balance_report'),
    ]
    return custom + urls

django_admin.site.__class__.get_urls = get_urls_with_balance
'''

if 'BalanceReportAdminView' not in content:
    content += custom_admin
    with open(admin_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("✓ BalanceReportAdminView اضافه شد")
else:
    print("✓ قبلاً موجود بود")

# ─── ساخت template ───────────────────────────────────────────
template_dir = os.path.join('templates', 'admin', 'accounting')
os.makedirs(template_dir, exist_ok=True)

template = '''{% extends "admin/base_site.html" %}
{% load humanize %}

{% block content %}
<style>
  .report-section { background: #fff; border: 1px solid #ddd; border-radius: 8px; padding: 20px; margin-bottom: 20px; }
  .report-section h2 { color: #333; border-bottom: 2px solid #007bff; padding-bottom: 8px; margin-bottom: 15px; }
  .summary-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 20px; }
  .summary-card { background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 6px; padding: 15px; text-align: center; }
  .summary-card .label { font-size: 12px; color: #6c757d; margin-bottom: 5px; }
  .summary-card .value { font-size: 18px; font-weight: bold; }
  .positive { color: #28a745; }
  .negative { color: #dc3545; }
  .neutral { color: #007bff; }
  table { width: 100%; border-collapse: collapse; font-size: 13px; }
  th { background: #f8f9fa; padding: 8px 12px; text-align: right; border-bottom: 2px solid #dee2e6; }
  td { padding: 8px 12px; border-bottom: 1px solid #f0f0f0; }
  tr:hover td { background: #f8f9fa; }
</style>

<h1>📊 تراز و گزارشات مالی</h1>

<!-- خلاصه کلی -->
<div class="summary-grid">
  <div class="summary-card">
    <div class="label">کل دارایی‌ها</div>
    <div class="value positive">{{ total_assets|intcomma }} ت</div>
  </div>
  <div class="summary-card">
    <div class="label">کل بدهی‌ها</div>
    <div class="value negative">{{ total_liabilities|intcomma }} ت</div>
  </div>
  <div class="summary-card">
    <div class="label">خالص دارایی</div>
    <div class="value {% if equity >= 0 %}positive{% else %}negative{% endif %}">{{ equity|intcomma }} ت</div>
  </div>
  <div class="summary-card">
    <div class="label">سود ناخالص</div>
    <div class="value {% if gross_profit >= 0 %}positive{% else %}negative{% endif %}">{{ gross_profit|intcomma }} ت</div>
  </div>
</div>

<!-- سود و زیان -->
<div class="report-section">
  <h2>💰 سود و زیان</h2>
  <div class="summary-grid">
    <div class="summary-card">
      <div class="label">کل فروش</div>
      <div class="value neutral">{{ total_revenue|intcomma }} ت</div>
    </div>
    <div class="summary-card">
      <div class="label">بهای تمام شده فروش</div>
      <div class="value negative">{{ total_cost_sold|intcomma }} ت</div>
    </div>
    <div class="summary-card">
      <div class="label">سود ناخالص</div>
      <div class="value positive">{{ gross_profit|intcomma }} ت</div>
    </div>
    <div class="summary-card">
      <div class="label">طلب از مشتریان</div>
      <div class="value neutral">{{ receivable|intcomma }} ت</div>
    </div>
  </div>
</div>

<!-- تراز طرف حساب‌ها -->
<div class="report-section">
  <h2>👥 تراز طرف حساب‌ها</h2>
  <table>
    <thead>
      <tr>
        <th>نام</th>
        <th>نوع</th>
        <th>مانده ریال</th>
        <th>وضعیت</th>
        <th>مانده یوان</th>
        <th>وضعیت</th>
      </tr>
    </thead>
    <tbody>
      {% for c in contacts %}
      <tr>
        <td><strong>{{ c.name }}</strong></td>
        <td>{{ c.type }}</td>
        <td class="{% if c.balance_irr > 0 %}negative{% else %}positive{% endif %}">
          {{ c.balance_irr|intcomma }} ت
        </td>
        <td>{{ c.status_irr }}</td>
        <td class="{% if c.balance_cny > 0 %}negative{% else %}positive{% endif %}">
          {% if c.balance_cny != 0 %}{{ c.balance_cny|floatformat:0 }} ¥{% else %}—{% endif %}
        </td>
        <td>{% if c.balance_cny != 0 %}{{ c.status_cny }}{% endif %}</td>
      </tr>
      {% empty %}
      <tr><td colspan="6" style="text-align:center;color:#999">تراکنشی ثبت نشده</td></tr>
      {% endfor %}
    </tbody>
  </table>
</div>

<!-- حساب‌های بانکی -->
<div class="report-section">
  <h2>🏦 موجودی حساب‌های بانکی و صندوق</h2>
  <table>
    <thead>
      <tr><th>نام حساب</th><th>نوع</th><th>ارز</th><th>موجودی</th></tr>
    </thead>
    <tbody>
      {% for a in accounts %}
      <tr>
        <td>{{ a.name }}</td>
        <td>{{ a.type }}</td>
        <td>{{ a.currency }}</td>
        <td class="{% if a.balance >= 0 %}positive{% else %}negative{% endif %}">
          {{ a.balance|floatformat:0|intcomma }} {{ a.currency }}
        </td>
      </tr>
      {% empty %}
      <tr><td colspan="4" style="text-align:center;color:#999">حسابی تعریف نشده</td></tr>
      {% endfor %}
    </tbody>
  </table>
</div>

<!-- موجودی کالا -->
<div class="report-section">
  <h2>📦 موجودی کالا (بهای تمام شده)</h2>
  <p><strong>جمع کل: {{ stock_value|intcomma }} ریال</strong></p>
  <table>
    <thead>
      <tr><th>انبار</th><th>کالا</th><th>SKU</th><th>تعداد</th><th>بهای واحد</th><th>جمع</th></tr>
    </thead>
    <tbody>
      {% for s in stock_items %}
      <tr>
        <td>{{ s.warehouse }}</td>
        <td>{{ s.product }}</td>
        <td>{{ s.sku }}</td>
        <td>{{ s.qty|intcomma }}</td>
        <td>{{ s.cost|intcomma }} ت</td>
        <td class="neutral"><strong>{{ s.total|intcomma }} ت</strong></td>
      </tr>
      {% empty %}
      <tr><td colspan="6" style="text-align:center;color:#999">موجودی ثبت نشده</td></tr>
      {% endfor %}
    </tbody>
  </table>
</div>

<p style="color:#999;font-size:12px;text-align:left">
  نرخ یوان: {{ rate|intcomma }} تومان
</p>
{% endblock %}
'''

with open(os.path.join(template_dir, 'balance_report.html'), 'w', encoding='utf-8') as f:
    f.write(template)
print("✓ template ساخته شد")

# ─── اطمینان از وجود templates در settings ───────────────────
settings_path = os.path.join('config', 'settings.py')
with open(settings_path, encoding='utf-8') as f:
    settings = f.read()

if "'DIRS': []" in settings:
    settings = settings.replace(
        "'DIRS': []",
        "'DIRS': [BASE_DIR / 'templates']"
    )
    with open(settings_path, 'w', encoding='utf-8') as f:
        f.write(settings)
    print("✓ TEMPLATES DIRS اضافه شد")

import subprocess, sys
r = subprocess.run([sys.executable, 'manage.py', 'check', '--verbosity=0'], capture_output=True, text=True)
print("✓ check موفق" if r.returncode == 0 else r.stderr[-300:])
print("\nآدرس گزارش تراز در Django Admin:")
print("http://127.0.0.1:8000/admin/accounting/balance-report/")
