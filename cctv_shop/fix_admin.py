with open('apps/accounting/admin.py', 'w', encoding='utf-8') as f:
    f.write("""from django.contrib import admin
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
""")
print("accounting/admin.py done")

# users admin
with open('apps/users/admin.py', 'r', encoding='utf-8') as f:
    users_admin = f.read()

if 'Role' not in users_admin:
    users_admin += """

from apps.users.models import Role, StaffProfile

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display  = ["name", "description", "perm_count", "is_active"]
    list_filter   = ["is_active"]
    search_fields = ["name"]

    def perm_count(self, obj):
        return len(obj.permissions)
    perm_count.short_description = "تعداد دسترسی"


@admin.register(StaffProfile)
class StaffProfileAdmin(admin.ModelAdmin):
    list_display  = ["user", "role", "employee_id", "department", "is_active"]
    list_filter   = ["role", "is_active"]
    search_fields = ["user__phone", "user__first_name", "employee_id"]
"""
    with open('apps/users/admin.py', 'w', encoding='utf-8') as f:
        f.write(users_admin)
    print("users/admin.py done")

# inventory admin
inv_admin_path = 'apps/inventory/admin.py'
with open(inv_admin_path, 'r', encoding='utf-8') as f:
    inv_admin = f.read()

if 'StockMovement' not in inv_admin:
    inv_admin += """

from django.contrib import admin
from .models import Warehouse, WarehouseStock, StockMovement, StockTransfer

@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "warehouse_type", "is_public", "is_active"]
    list_filter  = ["warehouse_type", "is_active", "is_public"]

@admin.register(WarehouseStock)
class WarehouseStockAdmin(admin.ModelAdmin):
    list_display  = ["warehouse", "variant", "quantity", "min_quantity"]
    list_filter   = ["warehouse"]
    search_fields = ["variant__sku", "variant__product__name"]

@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display  = ["warehouse", "variant", "movement_type", "quantity",
                     "balance_after", "reference", "created_by", "created_at"]
    list_filter   = ["movement_type", "warehouse", "created_at"]
    search_fields = ["variant__sku", "reference"]
    readonly_fields = ["created_at"]
    date_hierarchy = "created_at"

@admin.register(StockTransfer)
class StockTransferAdmin(admin.ModelAdmin):
    list_display = ["variant", "from_warehouse", "to_warehouse",
                    "quantity", "status", "transferred_by"]
    list_filter  = ["status"]
"""
    with open(inv_admin_path, 'w', encoding='utf-8') as f:
        f.write(inv_admin)
    print("inventory/admin.py done")

print("\n✓ همه admin.py ها آپدیت شدند — سرور را restart کنید")
