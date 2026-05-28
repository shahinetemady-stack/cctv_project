"""
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
        """
        مانده ریالی طرف حساب:
        - تامین‌کننده: ارزش کالا به ریال (قیمت یوان × نرخ خرید × تعداد)
        - شرکت حمل/ترخیص‌کار: فقط هزینه ترخیص ریالی (حمل یوانی جداست)
        - سایر: هزینه‌های جانبی ریالی
        منهای: پرداخت‌های ریالی
        """
        from django.db.models import Sum

        # پرداخت‌های خروجی ریالی
        paid_irr = self.payments.filter(currency='IRR', direction='out').aggregate(s=Sum('amount'))['s'] or 0
        # پرداخت‌های خروجی یوانی — تبدیل به ریال با نرخ ثبت شده
        paid_cny_list = self.payments.filter(currency='CNY', direction='out').values_list('amount', 'rate_irr')
        paid_cny_as_irr = sum(float(a) * float(r) for a, r in paid_cny_list)
        total_paid_irr = float(paid_irr) + paid_cny_as_irr

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
        # پرداخت‌های خروجی (از ما به طرف حساب) یوانی
        paid_cny = self.payments.filter(currency='CNY', direction='out').aggregate(s=Sum('amount'))['s'] or 0
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

        return total_cny - total_paid_cny


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




class Account(models.Model):
    """حساب بانکی / صندوق / تنخواه"""

    class AccountType(models.TextChoices):
        CASH      = "cash",      "صندوق نقد"
        BANK      = "bank",      "حساب بانکی"
        PETTY     = "petty",     "تنخواه"
        VIRTUAL   = "virtual",   "کیف پول / ارزی"

    class Currency(models.TextChoices):
        IRR = "IRR", "ریال"
        CNY = "CNY", "یوان"
        USD = "USD", "دلار"

    name         = models.CharField(max_length=100, verbose_name="نام حساب")
    account_type = models.CharField(max_length=20, choices=AccountType.choices, verbose_name="نوع")
    currency     = models.CharField(max_length=5, choices=Currency.choices, default=Currency.IRR, verbose_name="ارز")
    bank_name    = models.CharField(max_length=100, blank=True, verbose_name="نام بانک")
    account_number = models.CharField(max_length=50, blank=True, verbose_name="شماره حساب / کارت")
    initial_balance = models.DecimalField(max_digits=18, decimal_places=2, default=0, verbose_name="موجودی اولیه")
    is_active    = models.BooleanField(default=True, verbose_name="فعال")
    note         = models.TextField(blank=True, verbose_name="توضیحات")
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "accounting_account"
        verbose_name = "حساب بانکی / صندوق"
        verbose_name_plural = "حساب‌های بانکی / صندوق"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.get_account_type_display()}) — {self.currency}"

    @property
    def balance(self):
        """موجودی فعلی = موجودی اولیه + دریافتی‌ها - پرداختی‌ها"""
        from django.db.models import Sum
        paid_out = self.payments_out.aggregate(s=Sum('amount'))['s'] or 0
        paid_in  = self.payments_in.aggregate(s=Sum('amount'))['s'] or 0
        return float(self.initial_balance) + float(paid_in) - float(paid_out)

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
                      null=True, blank=True,
                      related_name="payments", verbose_name="طرف حساب")
    invoice      = models.ForeignKey(PurchaseInvoice, on_delete=models.SET_NULL,
                      null=True, blank=True, related_name="payments", verbose_name="فاکتور مرتبط")
    from_account = models.ForeignKey('Account', on_delete=models.SET_NULL,
                      null=True, blank=True, related_name="payments_out",
                      verbose_name="از حساب (پرداختی)")
    to_account   = models.ForeignKey('Account', on_delete=models.SET_NULL,
                      null=True, blank=True, related_name="payments_in",
                      verbose_name="به حساب (دریافتی)")
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


def generate_invoice_number(prefix='INV'):
    """شماره فاکتور خودکار: INV-YYYYMMDD-XXXX"""
    from django.utils import timezone
    import uuid
    today = timezone.now().strftime("%Y%m%d")
    short = uuid.uuid4().hex[:6].upper()
    return f"{prefix}-{today}-{short}"


class SaleInvoice(models.Model):
    """فاکتور فروش — هم از سفارش سایت، هم دستی"""

    class Status(models.TextChoices):
        DRAFT     = "draft",     "پیش‌نویس"
        CONFIRMED = "confirmed", "تأیید شده"
        PAID      = "paid",      "تسویه شده"
        CANCELLED = "cancelled", "لغو شده"

    class InvoiceSource(models.TextChoices):
        ORDER  = "order",  "سفارش سایت"
        MANUAL = "manual", "دستی (خارج از سایت)"

    # شماره و هویت
    invoice_number = models.CharField(max_length=50, unique=True,
                        default=generate_invoice_number, verbose_name="شماره فاکتور")
    source    = models.CharField(max_length=10, choices=InvoiceSource.choices,
                    default=InvoiceSource.MANUAL, verbose_name="منبع")

    # لینک به سفارش سایت (اختیاری)
    order     = models.OneToOneField('orders.Order', on_delete=models.SET_NULL,
                    null=True, blank=True, related_name='sale_invoice',
                    verbose_name="سفارش سایت")

    # مشتری
    customer  = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                    related_name='sale_invoices', verbose_name="مشتری")
    customer_name = models.CharField(max_length=200, blank=True, verbose_name="نام مشتری")
    customer_phone = models.CharField(max_length=20, blank=True, verbose_name="تلفن")

    # مالی
    discount_amount = models.PositiveBigIntegerField(default=0, verbose_name="تخفیف (ریال)")
    shipping_cost   = models.PositiveBigIntegerField(default=0, verbose_name="هزینه ارسال (ریال)")
    tax_amount      = models.PositiveBigIntegerField(default=0, verbose_name="مالیات (ریال)")
    note      = models.TextField(blank=True, verbose_name="توضیحات")
    status    = models.CharField(max_length=20, choices=Status.choices,
                    default=Status.DRAFT, verbose_name="وضعیت")

    # ثبت‌کننده
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                    null=True, blank=True, related_name='created_invoices',
                    verbose_name="صادرکننده")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "accounting_sale_invoice"
        verbose_name = "فاکتور فروش"
        verbose_name_plural = "فاکتورهای فروش"
        ordering = ["-created_at"]

    def __str__(self):
        return f"فاکتور {self.invoice_number} — {self.customer_name or self.customer}"

    @property
    def subtotal(self):
        return sum(item.subtotal for item in self.items.all())

    @property
    def total_amount(self):
        return self.subtotal - self.discount_amount + self.shipping_cost + self.tax_amount

    @property
    def paid_amount(self):
        from django.db.models import Sum
        return self.sale_payments.aggregate(s=Sum('amount'))['s'] or 0

    @property
    def remaining_amount(self):
        return self.total_amount - self.paid_amount

    @property
    def total_cost(self):
        """بهای تمام شده کل فاکتور"""
        return sum(item.total_cost for item in self.items.all())

    @property
    def gross_profit(self):
        """سود ناخالص ریالی"""
        return self.total_amount - self.total_cost


class SaleItem(models.Model):
    """آیتم فاکتور فروش"""
    invoice   = models.ForeignKey(SaleInvoice, on_delete=models.CASCADE,
                    related_name='items', verbose_name="فاکتور")
    variant   = models.ForeignKey('catalog.ProductVariant', on_delete=models.PROTECT,
                    related_name='sale_items', verbose_name="کالا")
    quantity  = models.PositiveIntegerField(verbose_name="تعداد")
    unit_price = models.PositiveBigIntegerField(verbose_name="قیمت واحد (ریال)")
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0,
                        verbose_name="تخفیف (%)")

    class Meta:
        db_table = "accounting_sale_item"
        verbose_name = "آیتم فاکتور فروش"
        verbose_name_plural = "آیتم‌های فاکتور فروش"

    def __str__(self):
        return f"{self.variant} × {self.quantity}"

    @property
    def subtotal(self):
        disc = self.unit_price * self.quantity * float(self.discount_percent) / 100
        return int(self.unit_price * self.quantity - disc)

    @property
    def unit_cost(self):
        """بهای تمام شده واحد از آخرین فاکتور خرید"""
        item = self.variant.purchase_items.order_by('-invoice__date').first()
        return item.unit_cost_irr if item else 0

    @property
    def total_cost(self):
        return self.unit_cost * self.quantity

    @property
    def profit(self):
        return self.subtotal - self.total_cost


class SalePayment(models.Model):
    """پرداخت مشتری بابت فاکتور فروش"""

    class PaymentMethod(models.TextChoices):
        CASH     = "cash",     "نقد"
        TRANSFER = "transfer", "حواله بانکی"
        CARD     = "card",     "کارت به کارت"
        ONLINE   = "online",   "پرداخت آنلاین"
        CREDIT   = "credit",   "نسیه (حساب باز)"

    invoice    = models.ForeignKey(SaleInvoice, on_delete=models.CASCADE,
                    related_name='sale_payments', verbose_name="فاکتور")
    to_account = models.ForeignKey('Account', on_delete=models.SET_NULL,
                    null=True, blank=True, related_name='sale_receipts',
                    verbose_name="به حساب (بانک/صندوق)")
    method     = models.CharField(max_length=20, choices=PaymentMethod.choices,
                    verbose_name="روش پرداخت")
    amount     = models.PositiveBigIntegerField(verbose_name="مبلغ (ریال)")
    date       = models.DateField(verbose_name="تاریخ")
    reference  = models.CharField(max_length=100, blank=True, verbose_name="شماره پیگیری")
    note       = models.TextField(blank=True, verbose_name="توضیحات")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                    null=True, blank=True, verbose_name="ثبت‌کننده")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "accounting_sale_payment"
        verbose_name = "پرداخت فروش"
        verbose_name_plural = "پرداخت‌های فروش"
        ordering = ["-date"]

    def __str__(self):
        return f"{self.invoice.invoice_number} | {self.amount:,} ریال | {self.get_method_display()}"
