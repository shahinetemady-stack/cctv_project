"""
python setup_accounting.py
اجرا در پوشه cctv_shop
ساخت کامل app accounting
"""
import os, sys

BASE = os.path.dirname(os.path.abspath(__file__))

# ─── 1. apps.py ──────────────────────────────────────────────
apps_py = '''from django.apps import AppConfig

class AccountingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounting"
    verbose_name = "حسابداری"
'''

# ─── 2. models.py ────────────────────────────────────────────
models_py = '''"""
apps/accounting/models.py
سیستم حسابداری تجاری
"""
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from decimal import Decimal


class Contact(models.Model):
    """طرف حساب — تامین‌کننده / ترخیص‌کار / کارمند / سایر"""

    class ContactType(models.TextChoices):
        SUPPLIER_CN  = "supplier_cn",  "تامین‌کننده چینی"
        CLEARANCE    = "clearance",    "ترخیص‌کار"
        SHIPPING_CO  = "shipping_co",  "شرکت حمل"
        STAFF        = "staff",        "کارمند / فروشنده"
        OTHER        = "other",        "سایر"

    class Currency(models.TextChoices):
        CNY = "CNY", "یوان چین"
        IRR = "IRR", "ریال ایران"
        USD = "USD", "دلار"

    name         = models.CharField(max_length=200, verbose_name="نام")
    contact_type = models.CharField(max_length=20, choices=ContactType.choices, verbose_name="نوع")
    currency     = models.CharField(max_length=5, choices=Currency.choices, default=Currency.CNY, verbose_name="ارز پیش‌فرض")
    phone        = models.CharField(max_length=50, blank=True, verbose_name="تلفن")
    wechat       = models.CharField(max_length=100, blank=True, verbose_name="وی‌چت / واتساپ")
    note         = models.TextField(blank=True, verbose_name="توضیحات")
    is_active    = models.BooleanField(default=True, verbose_name="فعال")
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "accounting_contact"
        verbose_name = "طرف حساب"
        verbose_name_plural = "طرف حساب‌ها"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.get_contact_type_display()})"

    @property
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
        return invoiced - paid


class PurchaseInvoice(models.Model):
    """فاکتور خرید — یک محموله از یک تامین‌کننده"""

    class Status(models.TextChoices):
        DRAFT     = "draft",     "پیش‌نویس"
        CONFIRMED = "confirmed", "تأیید شده"
        RECEIVED  = "received",  "دریافت شده"
        PAID      = "paid",      "تسویه شده"

    supplier       = models.ForeignKey(Contact, on_delete=models.PROTECT,
                        related_name="purchase_invoices", verbose_name="تامین‌کننده")
    invoice_number = models.CharField(max_length=50, blank=True, verbose_name="شماره فاکتور")
    date           = models.DateField(verbose_name="تاریخ فاکتور")
    warehouse      = models.ForeignKey("inventory.Warehouse", on_delete=models.PROTECT,
                        null=True, blank=True, verbose_name="انبار مقصد")

    # نرخ‌های ارز
    rate_purchase_cny = models.PositiveBigIntegerField(
        verbose_name="نرخ یوان خرید (تومان)",
        help_text="نرخ حواله پرداختی به تامین‌کننده")
    rate_shipping_cny = models.PositiveBigIntegerField(
        verbose_name="نرخ یوان حمل (تومان)",
        help_text="نرخ حواله پرداختی به شرکت حمل")

    # هزینه‌های حمل و ترخیص
    shipping_contact   = models.ForeignKey(Contact, on_delete=models.SET_NULL,
                            null=True, blank=True, related_name="shipping_invoices",
                            verbose_name="شرکت حمل / ترخیص‌کار")
    shipping_cost_cny  = models.DecimalField(max_digits=12, decimal_places=2, default=0,
                            verbose_name="هزینه حمل کل (یوان)")
    clearance_cost_irr = models.PositiveBigIntegerField(default=0,
                            verbose_name="هزینه ترخیص کل (ریال)")

    status     = models.CharField(max_length=20, choices=Status.choices,
                    default=Status.DRAFT, verbose_name="وضعیت")
    note       = models.TextField(blank=True, verbose_name="توضیحات")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                    null=True, blank=True, verbose_name="ثبت‌کننده")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "accounting_purchase_invoice"
        verbose_name = "فاکتور خرید"
        verbose_name_plural = "فاکتورهای خرید"
        ordering = ["-date", "-created_at"]

    def __str__(self):
        return f"فاکتور {self.invoice_number or self.id} — {self.supplier.name} — {self.date}"

    @property
    def total_weight(self):
        """وزن کل محموله (kg)"""
        return sum(item.total_weight for item in self.items.all())

    @property
    def total_cny(self):
        """ارزش کل به یوان (خرید + حمل)"""
        items_cny = sum(item.subtotal_cny for item in self.items.all())
        return items_cny + self.shipping_cost_cny

    @property
    def total_irr(self):
        """ارزش کل به ریال"""
        items_irr = sum(item.subtotal_cny * self.rate_purchase_cny for item in self.items.all())
        shipping_irr = self.shipping_cost_cny * self.rate_shipping_cny
        extra_irr = sum(e.amount_irr for e in self.extra_costs.all())
        return int(items_irr + shipping_irr + self.clearance_cost_irr + extra_irr)

    def calculate_items_cost(self):
        """محاسبه و ذخیره بهای تمام شده هر آیتم"""
        total_w = self.total_weight
        items = list(self.items.all())
        for item in items:
            if total_w > 0:
                weight_ratio = Decimal(str(item.total_weight)) / Decimal(str(total_w))
            else:
                weight_ratio = Decimal('0')

            # سهم حمل این آیتم (ریال)
            shipping_irr = self.shipping_cost_cny * Decimal(str(self.rate_shipping_cny)) * weight_ratio
            item.shipping_cost_irr = int(shipping_irr / item.quantity) if item.quantity else 0

            # سهم ترخیص این آیتم (ریال)
            clearance_share = Decimal(str(self.clearance_cost_irr)) * weight_ratio
            item.clearance_cost_irr = int(clearance_share / item.quantity) if item.quantity else 0

            # سهم هزینه‌های جانبی
            extra_total = sum(e.amount_irr for e in self.extra_costs.all())
            extra_share = Decimal(str(extra_total)) * weight_ratio
            item.extra_cost_irr = int(extra_share / item.quantity) if item.quantity else 0

            # بهای تمام شده واحد
            purchase_irr = item.unit_price_cny * Decimal(str(self.rate_purchase_cny))
            item.unit_cost_irr = int(
                purchase_irr +
                item.shipping_cost_irr +
                item.clearance_cost_irr +
                item.extra_cost_irr
            )
            item.save()


class PurchaseItem(models.Model):
    """آیتم فاکتور خرید — یک نوع کالا در محموله"""

    invoice  = models.ForeignKey(PurchaseInvoice, on_delete=models.CASCADE,
                  related_name="items", verbose_name="فاکتور")
    variant  = models.ForeignKey("catalog.ProductVariant", on_delete=models.PROTECT,
                  related_name="purchase_items", verbose_name="کالا")

    # اطلاعات پکینگ لیست
    quantity        = models.PositiveIntegerField(verbose_name="تعداد کل")
    carton_count    = models.PositiveIntegerField(default=1, verbose_name="تعداد کارتن")
    carton_weight   = models.DecimalField(max_digits=8, decimal_places=3,
                        verbose_name="وزن هر کارتن (kg)")

    # قیمت خرید
    unit_price_cny  = models.DecimalField(max_digits=10, decimal_places=2,
                        verbose_name="قیمت واحد (یوان)")

    # بهای تمام شده (محاسبه شده)
    shipping_cost_irr  = models.PositiveBigIntegerField(default=0,
                            verbose_name="سهم حمل هر واحد (ریال)")
    clearance_cost_irr = models.PositiveBigIntegerField(default=0,
                            verbose_name="سهم ترخیص هر واحد (ریال)")
    extra_cost_irr     = models.PositiveBigIntegerField(default=0,
                            verbose_name="سهم هزینه جانبی هر واحد (ریال)")
    unit_cost_irr      = models.PositiveBigIntegerField(default=0,
                            verbose_name="بهای تمام شده هر واحد (ریال)")

    note = models.CharField(max_length=200, blank=True, verbose_name="توضیح")

    class Meta:
        db_table = "accounting_purchase_item"
        verbose_name = "آیتم فاکتور خرید"
        verbose_name_plural = "آیتم‌های فاکتور خرید"

    def __str__(self):
        return f"{self.variant} × {self.quantity}"

    @property
    def total_weight(self):
        return float(self.carton_weight) * self.carton_count

    @property
    def subtotal_cny(self):
        return self.unit_price_cny * self.quantity


class ExtraCost(models.Model):
    """هزینه‌های جانبی قابل تخصیص به فاکتور"""

    class CostType(models.TextChoices):
        RENT       = "rent",       "اجاره"
        DELIVERY   = "delivery",   "پیک / ارسال"
        COMMISSION = "commission", "پورسانت فروش"
        ELECTRICITY= "electricity","برق"
        INSURANCE  = "insurance",  "بیمه"
        OTHER      = "other",      "سایر"

    invoice    = models.ForeignKey(PurchaseInvoice, on_delete=models.CASCADE,
                    related_name="extra_costs", verbose_name="فاکتور")
    cost_type  = models.CharField(max_length=20, choices=CostType.choices, verbose_name="نوع هزینه")
    contact    = models.ForeignKey(Contact, on_delete=models.SET_NULL,
                    null=True, blank=True, related_name="extra_costs", verbose_name="طرف حساب")
    amount_irr = models.PositiveBigIntegerField(verbose_name="مبلغ (ریال)")
    description= models.CharField(max_length=200, blank=True, verbose_name="توضیح")
    date       = models.DateField(null=True, blank=True, verbose_name="تاریخ")

    class Meta:
        db_table = "accounting_extra_cost"
        verbose_name = "هزینه جانبی"
        verbose_name_plural = "هزینه‌های جانبی"

    def __str__(self):
        return f"{self.get_cost_type_display()} — {self.amount_irr:,} ریال"


class Payment(models.Model):
    """پرداخت / دریافت"""

    class PaymentType(models.TextChoices):
        CASH     = "cash",     "نقد"
        TRANSFER = "transfer", "حواله بانکی"
        INSTALLMENT = "installment", "قسط"
        OTHER    = "other",    "سایر"

    class Direction(models.TextChoices):
        OUT = "out", "پرداختی (بدهکار)"
        IN  = "in",  "دریافتی (بستانکار)"

    class Currency(models.TextChoices):
        CNY = "CNY", "یوان"
        IRR = "IRR", "ریال"
        USD = "USD", "دلار"

    contact      = models.ForeignKey(Contact, on_delete=models.PROTECT,
                      related_name="payments", verbose_name="طرف حساب")
    invoice      = models.ForeignKey(PurchaseInvoice, on_delete=models.SET_NULL,
                      null=True, blank=True, related_name="payments", verbose_name="فاکتور مرتبط")
    direction    = models.CharField(max_length=5, choices=Direction.choices, verbose_name="جهت")
    payment_type = models.CharField(max_length=20, choices=PaymentType.choices, verbose_name="نوع")
    currency     = models.CharField(max_length=5, choices=Currency.choices, verbose_name="ارز")
    amount       = models.DecimalField(max_digits=18, decimal_places=2, verbose_name="مبلغ")
    rate_irr     = models.PositiveBigIntegerField(default=0,
                      verbose_name="نرخ تبدیل به ریال",
                      help_text="اگر ارز CNY/USD است نرخ تبدیل وارد کنید")
    date         = models.DateField(verbose_name="تاریخ")
    reference    = models.CharField(max_length=100, blank=True, verbose_name="شماره حواله / مرجع")
    note         = models.TextField(blank=True, verbose_name="توضیحات")
    created_by   = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                      null=True, blank=True, verbose_name="ثبت‌کننده")
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "accounting_payment"
        verbose_name = "پرداخت"
        verbose_name_plural = "پرداخت‌ها"
        ordering = ["-date", "-created_at"]

    def __str__(self):
        return f"{self.get_direction_display()} | {self.contact.name} | {self.amount} {self.currency}"

    @property
    def amount_irr(self):
        """معادل ریالی"""
        if self.currency == 'IRR':
            return int(self.amount)
        return int(self.amount * self.rate_irr)
'''

# ─── 3. admin.py ─────────────────────────────────────────────
admin_py = '''from django.contrib import admin
from .models import Contact, PurchaseInvoice, PurchaseItem, ExtraCost, Payment


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
    fields = ["direction", "payment_type", "currency", "amount", "rate_irr", "date", "reference"]


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ["name", "contact_type", "currency", "phone", "is_active"]
    list_filter  = ["contact_type", "currency", "is_active"]
    search_fields = ["name", "phone", "wechat"]


@admin.register(PurchaseInvoice)
class PurchaseInvoiceAdmin(admin.ModelAdmin):
    list_display  = ["invoice_number", "supplier", "date", "status",
                     "total_cny", "total_irr"]
    list_filter   = ["status", "date"]
    search_fields = ["invoice_number", "supplier__name"]
    inlines       = [PurchaseItemInline, ExtraCostInline, PaymentInline]
    readonly_fields = ["total_weight", "total_cny", "total_irr"]

    actions = ["calculate_costs"]

    def calculate_costs(self, request, queryset):
        for inv in queryset:
            inv.calculate_items_cost()
        self.message_user(request, "بهای تمام شده محاسبه شد.")
    calculate_costs.short_description = "محاسبه بهای تمام شده"


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display  = ["contact", "direction", "payment_type", "amount", "currency", "date"]
    list_filter   = ["direction", "currency", "payment_type"]
    search_fields = ["contact__name", "reference"]
'''

# ─── 4. views.py ─────────────────────────────────────────────
views_py = '''"""
apps/accounting/views.py
API endpoints برای سیستم حسابداری
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from django.db.models import Sum, Q
from decimal import Decimal
from .models import Contact, PurchaseInvoice, PurchaseItem, ExtraCost, Payment


# ─── Contacts ────────────────────────────────────────────────

class ContactListView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        qs = Contact.objects.filter(is_active=True)
        contact_type = request.query_params.get("type")
        if contact_type:
            qs = qs.filter(contact_type=contact_type)
        data = [{
            "id": c.id, "name": c.name,
            "contact_type": c.contact_type,
            "contact_type_display": c.get_contact_type_display(),
            "currency": c.currency,
            "phone": c.phone,
            "wechat": c.wechat,
            "balance_irr": c.balance_irr,
            "balance_cny": float(c.balance_cny),
        } for c in qs]
        return Response(data)

    def post(self, request):
        d = request.data
        c = Contact.objects.create(
            name=d["name"],
            contact_type=d["contact_type"],
            currency=d.get("currency", "CNY"),
            phone=d.get("phone", ""),
            wechat=d.get("wechat", ""),
            note=d.get("note", ""),
        )
        return Response({"id": c.id, "name": c.name}, status=201)


class ContactDetailView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, pk):
        try:
            c = Contact.objects.get(pk=pk)
        except Contact.DoesNotExist:
            return Response({"error": "یافت نشد"}, status=404)

        payments = [{
            "id": p.id, "date": str(p.date),
            "direction": p.direction,
            "direction_display": p.get_direction_display(),
            "payment_type_display": p.get_payment_type_display(),
            "amount": float(p.amount), "currency": p.currency,
            "amount_irr": p.amount_irr,
            "reference": p.reference, "note": p.note,
            "invoice_id": p.invoice_id,
        } for p in c.payments.order_by("-date")[:50]]

        invoices = [{
            "id": inv.id,
            "invoice_number": inv.invoice_number,
            "date": str(inv.date),
            "status": inv.status,
            "status_display": inv.get_status_display(),
            "total_cny": float(inv.total_cny),
            "total_irr": inv.total_irr,
        } for inv in c.purchase_invoices.order_by("-date")[:20]]

        return Response({
            "id": c.id, "name": c.name,
            "contact_type": c.contact_type,
            "contact_type_display": c.get_contact_type_display(),
            "currency": c.currency,
            "phone": c.phone, "wechat": c.wechat,
            "balance_irr": c.balance_irr,
            "balance_cny": float(c.balance_cny),
            "payments": payments,
            "invoices": invoices,
        })


# ─── Purchase Invoices ───────────────────────────────────────

class PurchaseInvoiceListView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        qs = PurchaseInvoice.objects.select_related("supplier", "warehouse").order_by("-date")
        status = request.query_params.get("status")
        if status:
            qs = qs.filter(status=status)
        data = [{
            "id": inv.id,
            "invoice_number": inv.invoice_number,
            "supplier_id": inv.supplier_id,
            "supplier_name": inv.supplier.name,
            "date": str(inv.date),
            "status": inv.status,
            "status_display": inv.get_status_display(),
            "rate_purchase_cny": inv.rate_purchase_cny,
            "rate_shipping_cny": inv.rate_shipping_cny,
            "shipping_cost_cny": float(inv.shipping_cost_cny),
            "clearance_cost_irr": inv.clearance_cost_irr,
            "total_weight": inv.total_weight,
            "total_cny": float(inv.total_cny),
            "total_irr": inv.total_irr,
            "items_count": inv.items.count(),
        } for inv in qs[:100]]
        return Response(data)

    def post(self, request):
        d = request.data
        try:
            inv = PurchaseInvoice.objects.create(
                supplier_id=d["supplier_id"],
                invoice_number=d.get("invoice_number", ""),
                date=d["date"],
                warehouse_id=d.get("warehouse_id") or None,
                rate_purchase_cny=int(d["rate_purchase_cny"]),
                rate_shipping_cny=int(d["rate_shipping_cny"]),
                shipping_contact_id=d.get("shipping_contact_id") or None,
                shipping_cost_cny=Decimal(str(d.get("shipping_cost_cny", 0))),
                clearance_cost_irr=int(d.get("clearance_cost_irr", 0)),
                note=d.get("note", ""),
                created_by=request.user,
            )
            # ذخیره آیتم‌ها
            for item_data in d.get("items", []):
                PurchaseItem.objects.create(
                    invoice=inv,
                    variant_id=item_data["variant_id"],
                    quantity=int(item_data["quantity"]),
                    carton_count=int(item_data.get("carton_count", 1)),
                    carton_weight=Decimal(str(item_data["carton_weight"])),
                    unit_price_cny=Decimal(str(item_data["unit_price_cny"])),
                    note=item_data.get("note", ""),
                )
            # ذخیره هزینه‌های جانبی
            for extra in d.get("extra_costs", []):
                ExtraCost.objects.create(
                    invoice=inv,
                    cost_type=extra["cost_type"],
                    contact_id=extra.get("contact_id") or None,
                    amount_irr=int(extra["amount_irr"]),
                    description=extra.get("description", ""),
                    date=extra.get("date") or inv.date,
                )
            # محاسبه بهای تمام شده
            inv.calculate_items_cost()
            return Response({"id": inv.id, "message": "فاکتور با موفقیت ثبت شد"}, status=201)
        except Exception as e:
            return Response({"error": str(e)}, status=400)


class PurchaseInvoiceDetailView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, pk):
        try:
            inv = PurchaseInvoice.objects.select_related(
                "supplier", "warehouse", "shipping_contact"
            ).get(pk=pk)
        except PurchaseInvoice.DoesNotExist:
            return Response({"error": "یافت نشد"}, status=404)

        items = [{
            "id": item.id,
            "variant_id": item.variant_id,
            "variant_sku": item.variant.sku,
            "product_name": item.variant.product.name,
            "quantity": item.quantity,
            "carton_count": item.carton_count,
            "carton_weight": float(item.carton_weight),
            "total_weight": item.total_weight,
            "unit_price_cny": float(item.unit_price_cny),
            "subtotal_cny": float(item.subtotal_cny),
            "shipping_cost_irr": item.shipping_cost_irr,
            "clearance_cost_irr": item.clearance_cost_irr,
            "extra_cost_irr": item.extra_cost_irr,
            "unit_cost_irr": item.unit_cost_irr,
            "note": item.note,
        } for item in inv.items.select_related("variant__product").all()]

        extra_costs = [{
            "id": e.id,
            "cost_type": e.cost_type,
            "cost_type_display": e.get_cost_type_display(),
            "contact_id": e.contact_id,
            "contact_name": e.contact.name if e.contact else "",
            "amount_irr": e.amount_irr,
            "description": e.description,
        } for e in inv.extra_costs.all()]

        payments = [{
            "id": p.id, "date": str(p.date),
            "direction": p.direction,
            "direction_display": p.get_direction_display(),
            "payment_type_display": p.get_payment_type_display(),
            "amount": float(p.amount), "currency": p.currency,
            "amount_irr": p.amount_irr, "reference": p.reference,
        } for p in inv.payments.all()]

        return Response({
            "id": inv.id,
            "invoice_number": inv.invoice_number,
            "supplier": {"id": inv.supplier_id, "name": inv.supplier.name},
            "date": str(inv.date),
            "status": inv.status,
            "status_display": inv.get_status_display(),
            "warehouse": {"id": inv.warehouse_id, "name": inv.warehouse.name} if inv.warehouse else None,
            "rate_purchase_cny": inv.rate_purchase_cny,
            "rate_shipping_cny": inv.rate_shipping_cny,
            "shipping_contact": {"id": inv.shipping_contact_id, "name": inv.shipping_contact.name} if inv.shipping_contact else None,
            "shipping_cost_cny": float(inv.shipping_cost_cny),
            "clearance_cost_irr": inv.clearance_cost_irr,
            "total_weight": inv.total_weight,
            "total_cny": float(inv.total_cny),
            "total_irr": inv.total_irr,
            "note": inv.note,
            "items": items,
            "extra_costs": extra_costs,
            "payments": payments,
        })

    def patch(self, request, pk):
        """آپدیت وضعیت فاکتور"""
        try:
            inv = PurchaseInvoice.objects.get(pk=pk)
        except PurchaseInvoice.DoesNotExist:
            return Response({"error": "یافت نشد"}, status=404)
        if "status" in request.data:
            inv.status = request.data["status"]
            inv.save()
        return Response({"id": inv.id, "status": inv.status})


# ─── Payments ────────────────────────────────────────────────

class PaymentCreateView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        d = request.data
        try:
            p = Payment.objects.create(
                contact_id=d["contact_id"],
                invoice_id=d.get("invoice_id") or None,
                direction=d["direction"],
                payment_type=d.get("payment_type", "transfer"),
                currency=d["currency"],
                amount=Decimal(str(d["amount"])),
                rate_irr=int(d.get("rate_irr", 0)),
                date=d["date"],
                reference=d.get("reference", ""),
                note=d.get("note", ""),
                created_by=request.user,
            )
            return Response({
                "id": p.id,
                "amount_irr": p.amount_irr,
                "message": "پرداخت با موفقیت ثبت شد",
            }, status=201)
        except Exception as e:
            return Response({"error": str(e)}, status=400)


# ─── Reports ─────────────────────────────────────────────────

class BalanceReportView(APIView):
    """گزارش تراز — ریالی و ارزی"""
    permission_classes = [IsAdminUser]

    def get(self, request):
        contacts = Contact.objects.filter(is_active=True)
        data = []
        for c in contacts:
            bal_irr = c.balance_irr
            bal_cny = float(c.balance_cny)
            if bal_irr != 0 or bal_cny != 0:
                data.append({
                    "id": c.id,
                    "name": c.name,
                    "contact_type_display": c.get_contact_type_display(),
                    "balance_irr": bal_irr,
                    "balance_cny": bal_cny,
                    "status_irr": "بدهکار" if bal_irr > 0 else "بستانکار",
                    "status_cny": "بدهکار" if bal_cny > 0 else "بستانکار",
                })
        return Response({"contacts": data})
'''

# ─── 5. urls.py ──────────────────────────────────────────────
urls_py = '''from django.urls import path
from . import views

urlpatterns = [
    path("contacts/", views.ContactListView.as_view()),
    path("contacts/<int:pk>/", views.ContactDetailView.as_view()),
    path("invoices/", views.PurchaseInvoiceListView.as_view()),
    path("invoices/<int:pk>/", views.PurchaseInvoiceDetailView.as_view()),
    path("payments/", views.PaymentCreateView.as_view()),
    path("reports/balance/", views.BalanceReportView.as_view()),
]
'''

# ─── نوشتن فایل‌ها ────────────────────────────────────────────
files = {
    os.path.join("apps", "accounting", "apps.py"):    apps_py,
    os.path.join("apps", "accounting", "models.py"):  models_py,
    os.path.join("apps", "accounting", "admin.py"):   admin_py,
    os.path.join("apps", "accounting", "views.py"):   views_py,
    os.path.join("apps", "accounting", "urls.py"):    urls_py,
}

for path, content in files.items():
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✓ {path}")

# ─── اضافه کردن به settings ───────────────────────────────────
settings_path = os.path.join("config", "settings.py")
with open(settings_path, encoding="utf-8") as f:
    settings = f.read()

if "apps.accounting" not in settings:
    settings = settings.replace(
        '"apps.payment",',
        '"apps.payment",\n    "apps.accounting",'
    )
    with open(settings_path, "w", encoding="utf-8") as f:
        f.write(settings)
    print("✓ settings.py آپدیت شد")
else:
    print("✓ apps.accounting قبلاً در settings بود")

# ─── اضافه کردن به config/urls.py ────────────────────────────
config_urls_path = os.path.join("config", "urls.py")
with open(config_urls_path, encoding="utf-8") as f:
    config_urls = f.read()

if "accounting" not in config_urls:
    config_urls = config_urls.replace(
        'path("api/inventory/", include("apps.inventory.urls")),',
        'path("api/inventory/", include("apps.inventory.urls")),\n    path("api/accounting/", include("apps.accounting.urls")),'
    )
    with open(config_urls_path, "w", encoding="utf-8") as f:
        f.write(config_urls)
    print("✓ config/urls.py آپدیت شد")
else:
    print("✓ URL accounting قبلاً اضافه شده بود")

# ─── migration ───────────────────────────────────────────────
import subprocess
r = subprocess.run([sys.executable, "manage.py", "makemigrations", "accounting"],
                   capture_output=True, text=True)
print(r.stdout[-300:] if r.stdout else "")
if r.returncode != 0:
    print("خطای migration:")
    print(r.stderr[-500:])
else:
    r2 = subprocess.run([sys.executable, "manage.py", "migrate"],
                        capture_output=True, text=True)
    print(r2.stdout[-300:] if r2.stdout else "")
    if r2.returncode != 0:
        print("خطای migrate:")
        print(r2.stderr[-500:])
    else:
        print("✓ migrate موفق")

r3 = subprocess.run([sys.executable, "manage.py", "check", "--verbosity=0"],
                    capture_output=True, text=True)
if r3.returncode == 0:
    print("✓ check موفق — سرور را restart کنید")
else:
    print("خطای check:")
    print((r3.stdout + r3.stderr)[-500:])
