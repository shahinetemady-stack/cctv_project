from django.contrib import admin
from .models import (
    Contact, Account, PurchaseInvoice, PurchaseItem,
    ExtraCost, Payment, SaleInvoice, SaleItem, SalePayment,
)


# ─── Inlines ─────────────────────────────────────────────────

class PurchaseItemInline(admin.TabularInline):
    model = PurchaseItem
    extra = 1
    fields = ["variant", "quantity", "carton_count", "carton_weight",
              "unit_price_cny", "unit_cost_irr"]
    readonly_fields = ["unit_cost_irr"]


class ExtraCostInline(admin.TabularInline):
    model = ExtraCost
    extra = 0
    fields = ["cost_type", "contact", "amount_irr", "description", "date"]


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    fields = ["contact", "from_account", "to_account", "direction",
              "payment_type", "currency", "amount", "rate_irr", "date", "reference"]


class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 1
    fields = ["variant", "quantity", "unit_price", "discount_percent", "subtotal"]
    readonly_fields = ["subtotal"]

    def subtotal(self, obj):
        return obj.subtotal if obj.pk else 0
    subtotal.short_description = "جمع"


class SalePaymentInline(admin.TabularInline):
    model = SalePayment
    extra = 0
    fields = ["method", "amount", "to_account", "date", "reference", "created_by"]
    readonly_fields = ["created_by"]


# ─── Contact ─────────────────────────────────────────────────

@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display  = ["name", "contact_type", "currency", "phone", "wechat", "is_active"]
    list_filter   = ["contact_type", "currency", "is_active"]
    search_fields = ["name", "phone", "wechat"]
    list_editable = ["is_active"]


# ─── Account ─────────────────────────────────────────────────

@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display  = ["name", "account_type", "currency", "bank_name",
                     "account_number", "balance", "is_active"]
    list_filter   = ["account_type", "currency", "is_active"]
    search_fields = ["name", "bank_name", "account_number"]
    readonly_fields = ["balance"]


# ─── Purchase Invoice ────────────────────────────────────────

@admin.register(PurchaseInvoice)
class PurchaseInvoiceAdmin(admin.ModelAdmin):
    list_display  = ["invoice_number", "supplier", "date", "status",
                     "total_weight", "total_cny", "total_irr", "created_by"]
    list_filter   = ["status", "date", "supplier"]
    search_fields = ["invoice_number", "supplier__name"]
    inlines       = [PurchaseItemInline, ExtraCostInline, PaymentInline]
    readonly_fields = ["total_weight", "total_cny", "total_irr", "created_by"]
    date_hierarchy = "date"
    actions = ["calculate_costs"]

    def save_model(self, request, obj, form, change):
        if not obj.created_by:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    def calculate_costs(self, request, queryset):
        for inv in queryset:
            inv.calculate_items_cost()
        self.message_user(request, "بهای تمام شده محاسبه شد.")
    calculate_costs.short_description = "محاسبه بهای تمام شده"


# ─── Payment ─────────────────────────────────────────────────

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display  = ["contact", "direction", "payment_type", "amount",
                     "currency", "date", "reference", "created_by"]
    list_filter   = ["direction", "currency", "payment_type", "date"]
    search_fields = ["contact__name", "reference"]
    date_hierarchy = "date"
    readonly_fields = ["created_by"]

    def save_model(self, request, obj, form, change):
        if not obj.created_by:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


# ─── Sale Invoice ────────────────────────────────────────────

@admin.register(SaleInvoice)
class SaleInvoiceAdmin(admin.ModelAdmin):
    list_display  = ["invoice_number", "customer_name", "customer_phone",
                     "source", "status", "total_amount", "paid_amount",
                     "remaining_amount", "created_by", "created_at"]
    list_filter   = ["status", "source", "created_at"]
    search_fields = ["invoice_number", "customer_name", "customer_phone"]
    readonly_fields = ["invoice_number", "subtotal", "total_amount",
                       "paid_amount", "remaining_amount", "total_cost",
                       "gross_profit", "created_by", "created_at"]
    inlines = [SaleItemInline, SalePaymentInline]
    date_hierarchy = "created_at"

    def save_model(self, request, obj, form, change):
        if not obj.created_by:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


# ─── Sale Payment ────────────────────────────────────────────

@admin.register(SalePayment)
class SalePaymentAdmin(admin.ModelAdmin):
    list_display  = ["invoice", "method", "amount", "to_account", "date",
                     "reference", "created_by"]
    list_filter   = ["method", "date"]
    search_fields = ["invoice__invoice_number", "reference"]
    readonly_fields = ["created_by"]

    def save_model(self, request, obj, form, change):
        if not obj.created_by:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


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
