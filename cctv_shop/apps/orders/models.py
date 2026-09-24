"""
apps/orders/models.py
──────────────────────
Order lifecycle:

  PUBLIC user:
    Cart → Order(type=DIRECT_PURCHASE, status=PENDING)
    → درگاه پرداخت → status=PAID → deduct_stock()

  PARTNER user:
    InquiryCart → Order(type=INQUIRY, status=PENDING)
    → SMS به ادمین → ادمین تأیید → status=AWAITING_PAYMENT
    → StockReservation (۲ ساعت) → لینک پرداخت → status=PAID
    → deduct_stock()

  Cancellation (manual or cron):
    status=CANCELLED → release_reservation() on each item
"""

import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone
from datetime import timedelta

from apps.core.models import TimeStampedModel, AuditMixin


def generate_order_number():
    """OR-1000، OR-1001، ... — شماره ساده و ترتیبی."""
    last = (
        Order.objects.filter(order_number__regex=r"^OR-\d+$")
        .order_by("-id")
        .values_list("order_number", flat=True)
        .first()
    )
    try:
        n = int(last.split("-")[1]) + 1 if last else 1000
    except (ValueError, IndexError, AttributeError):
        n = 1000
    return f"OR-{n}"


class Settlement(models.TextChoices):
    """نحوه تسویه — مشترک بین سفارش و تک‌تک اقلام آن."""
    CASH   = "cash",   "نقدی"
    CREDIT = "credit", "تو حسابی"
    MONTH1 = "month1", "یکماهه"
    MONTH2 = "month2", "دوماهه"


# فاصله موعد تسویه (روز) از تاریخ ثبت برای هر نوع
SETTLEMENT_DUE_DAYS = {
    Settlement.CASH: 0,
    Settlement.CREDIT: 14,
    Settlement.MONTH1: 30,
    Settlement.MONTH2: 60,
}


def settlement_due_for(settlement_type, from_date=None):
    """موعد تسویه پیش‌فرض برای یک نوع تسویه از تاریخ مشخص (پیش‌فرض: امروز)."""
    base = from_date or timezone.now().date()
    return base + timedelta(days=SETTLEMENT_DUE_DAYS.get(settlement_type, 0))


# ─── Cart (سبد خرید عمومی) ────────────────────────────────────────────────────

class Cart(TimeStampedModel):
    """
    Temporary cart before checkout.
    Can belong to a logged-in user OR an anonymous session.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="carts",
        verbose_name="کاربر",
    )
    session_key = models.CharField(
        max_length=40,
        null=True,
        blank=True,
        verbose_name="کلید سشن (برای کاربر مهمان)",
    )

    class Meta:
        db_table = "orders_cart"
        verbose_name = "سبد خرید"
        verbose_name_plural = "سبدهای خرید"

    def __str__(self):
        owner = str(self.user) if self.user else f"session:{self.session_key}"
        return f"سبد {owner}"

    @property
    def total_price(self) -> int:
        return sum(item.subtotal for item in self.items.all())


class CartItem(TimeStampedModel):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey(
        "catalog.ProductVariant",
        on_delete=models.CASCADE,
        related_name="cart_items",
        verbose_name="نسخه محصول",
        null=True, blank=True,
    )
    package = models.ForeignKey(
        "catalog.Package",
        on_delete=models.CASCADE,
        related_name="cart_items",
        null=True, blank=True,
        verbose_name="پکیج",
        help_text="اگر پر باشد این آیتم یک پکیج است و variant خالی می‌ماند",
    )
    quantity = models.PositiveSmallIntegerField(default=1, verbose_name="تعداد")
    settlement_type = models.CharField(
        max_length=10, choices=Settlement.choices,
        default=Settlement.CASH, verbose_name="نحوه تسویه",
    )

    class Meta:
        db_table = "orders_cart_item"
        verbose_name = "آیتم سبد خرید"
        verbose_name_plural = "آیتم‌های سبد خرید"
        unique_together = [["cart", "variant", "settlement_type"]]

    def __str__(self):
        return f"{self.quantity}× {self.variant}"

    @property
    def unit_price(self) -> int:
        # آیتم پکیج: قیمت بسته برای همین کاربر (ریال، تخفیف‌دار) — یکسان با قیمت نمایشی صفحه پکیج
        if self.package_id:
            _, final = self.package.prices_for(self.cart.user)
            return final
        from apps.catalog.pricing import price_for_settlement
        return price_for_settlement(self.variant, self.cart.user, self.settlement_type)

    @property
    def subtotal(self) -> int:
        return self.unit_price * self.quantity


# ─── InquiryCart (سبد استعلام همکار) ─────────────────────────────────────────

class InquiryCart(TimeStampedModel):
    """Inquiry basket for PARTNER users — no direct price shown."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="inquiry_carts",
        verbose_name="کاربر همکار",
    )
    notes = models.TextField(blank=True, verbose_name="یادداشت مشتری")

    class Meta:
        db_table = "orders_inquiry_cart"
        verbose_name = "سبد استعلام"
        verbose_name_plural = "سبدهای استعلام"

    def __str__(self):
        return f"سبد استعلام {self.user}"


class InquiryCartItem(TimeStampedModel):
    cart = models.ForeignKey(InquiryCart, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey(
        "catalog.ProductVariant",
        on_delete=models.CASCADE,
        related_name="inquiry_items",
        verbose_name="نسخه محصول",
    )
    quantity = models.PositiveSmallIntegerField(default=1, verbose_name="تعداد")
    settlement_type = models.CharField(
        max_length=10, choices=Settlement.choices,
        default=Settlement.CASH, verbose_name="نحوه تسویه",
    )

    class Meta:
        db_table = "orders_inquiry_cart_item"
        verbose_name = "آیتم سبد استعلام"
        verbose_name_plural = "آیتم‌های سبد استعلام"
        unique_together = [["cart", "variant", "settlement_type"]]

    def __str__(self):
        return f"{self.quantity}× {self.variant}"


# ─── Order ────────────────────────────────────────────────────────────────────

class Order(TimeStampedModel, AuditMixin):
    """
    One order per checkout.

    order_type:
      DIRECT_PURCHASE  → مشتری عمومی، قیمت شفاف، پرداخت فوری
      INQUIRY          → مشتری همکار، قیمت استعلامی، نیاز به تأیید ادمین

    status flow:
      PENDING → CONFIRMED → AWAITING_PAYMENT → PAID
                          ↘ CANCELLED
    """

    class OrderType(models.TextChoices):
        DIRECT_PURCHASE = "direct_purchase", "خرید مستقیم"
        INQUIRY = "inquiry", "استعلام"

    class Status(models.TextChoices):
        PENDING = "pending", "در انتظار بررسی"
        CONFIRMED = "confirmed", "تأیید شده توسط ادمین"
        AWAITING_PAYMENT = "awaiting_payment", "در انتظار پرداخت"
        READY_TO_SHIP = "ready_to_ship", "منتظر ارسال"
        PAID = "paid", "پرداخت شده"
        CANCELLED = "cancelled", "لغو شده"
        REFUNDED = "refunded", "مسترد شده"
        REJECTED = "rejected", "رد شده"

    # ── Identity ─────────────────────────────────────────────────────
    order_number = models.CharField(
        max_length=30,
        unique=True,
        default=generate_order_number,
        verbose_name="شماره سفارش",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="orders",
        verbose_name="کاربر",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="created_orders",
        verbose_name="ثبت‌کننده",
    )

    # ── Type & Status ─────────────────────────────────────────────────
    order_type = models.CharField(
        max_length=20,
        choices=OrderType.choices,
        default=OrderType.DIRECT_PURCHASE,
        verbose_name="نوع سفارش",
        db_index=True,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name="وضعیت",
        db_index=True,
    )

    # ── Financials ────────────────────────────────────────────────────
    total_amount = models.PositiveBigIntegerField(
        default=0,
        verbose_name="مبلغ کل (تومان)",
    )
    confirmed_amount = models.PositiveBigIntegerField(
        default=0,
        verbose_name="مبلغ تأیید شده توسط ادمین (تومان)",
        help_text="فقط برای سفارش‌های استعلامی — ادمین مقدار نهایی را وارد می‌کند",
    )

    # ── Payment ───────────────────────────────────────────────────────
    Settlement = Settlement  # دسترسی سازگار: Order.Settlement

    settlement_type = models.CharField(
        max_length=10, choices=Settlement.choices,
        default=Settlement.CASH, verbose_name="نحوه تسویه",
    )
    settlement_due_date = models.DateField(
        null=True, blank=True, verbose_name="موعد تسویه",
        help_text="سررسید تسویه — در این تاریخ به مشتری و کاربران هشدار داده می‌شود",
    )
    payment_link = models.URLField(
        blank=True,
        verbose_name="لینک پرداخت",
    )
    payment_deadline = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="مهلت پرداخت",
        help_text="۲ ساعت بعد از تأیید ادمین برای سفارش استعلامی",
    )
    payment_ref_id = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="کد پیگیری پرداخت",
    )
    paid_at = models.DateTimeField(null=True, blank=True, verbose_name="زمان پرداخت")

    # ── Shipping ──────────────────────────────────────────────────────
    shipping_address = models.TextField(blank=True, verbose_name="آدرس ارسال")
    shipping_method = models.CharField(
        max_length=20, blank=True, default="",
        verbose_name="روش ارسال",
        choices=[("post","پست"),("courier","پیک"),("freight","باربری")],
    )
    freight_company = models.CharField(max_length=200, blank=True, default="", verbose_name="نام باربری")
    tracking_code = models.CharField(max_length=100, blank=True, default="", verbose_name="کد رهگیری")
    paid_amount = models.PositiveBigIntegerField(null=True, blank=True, verbose_name="مبلغ پرداخت شده")
    payment_method = models.CharField(
        max_length=50, blank=True, default="",
        verbose_name="روش پرداخت",
        choices=[("cash","نقد"),("transfer","کارت به کارت"),("online","آنلاین"),("check","چک")],
    )
    sarraf_account_number = models.CharField(
        max_length=50, blank=True, default="", verbose_name="شماره حساب/کارت صراف"
    )
    sarraf_account_holder = models.CharField(
        max_length=200, blank=True, default="", verbose_name="نام صراف / صاحب حساب"
    )
    customer_notes = models.TextField(blank=True, verbose_name="یادداشت مشتری")
    admin_notes = models.TextField(blank=True, verbose_name="یادداشت ادمین")

    # ── Deadlines ─────────────────────────────────────────────────────
    admin_confirm_deadline = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="مهلت تأیید ادمین",
        help_text="ادمین باید تا این زمان سفارش استعلامی را تأیید کند",
    )


    # ─── فیلدهای رهگیری ──────────────────────────────────────
    courier_company = models.CharField(
        max_length=20, blank=True, default='',
        choices=[
            ('post', 'پست'), ('tipax', 'تیپاکس'),
            ('chapar', 'چاپار'), ('snap', 'اسنپ‌باکس'), ('other', 'سایر'),
        ],
        verbose_name='شرکت حمل'
    )
    delivery_status = models.CharField(
        max_length=20, blank=True, default='pending',
        choices=[
            ('pending', 'در انتظار ارسال'), ('shipped', 'ارسال شده'),
            ('in_transit', 'در مسیر'), ('delivered', 'تحویل داده شده'),
            ('returned', 'مرجوع شده'),
        ],
        verbose_name='وضعیت ارسال'
    )
    shipped_at = models.DateTimeField(null=True, blank=True, verbose_name='تاریخ ارسال')
    delivered_at = models.DateTimeField(null=True, blank=True, verbose_name='تاریخ تحویل')
    updated_by = models.ForeignKey(
        'users.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='updated_orders', verbose_name='آپدیت شده توسط'
    )
    status_updated_at = models.DateTimeField(null=True, blank=True, verbose_name='تاریخ آخرین تغییر وضعیت')

    # ── رد پیش‌فاکتور ─────────────────────────────────────────────
    reject_reason = models.TextField(blank=True, verbose_name="دلیل رد")
    rejected_at = models.DateTimeField(null=True, blank=True, verbose_name="تاریخ رد")

    class Meta:
        db_table = "orders_order"
        verbose_name = "سفارش"
        verbose_name_plural = "سفارش‌ها"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "order_type"], name="idx_order_status_type"),
            models.Index(fields=["user", "status"], name="idx_order_user_status"),
        ]

    def __str__(self):
        return f"سفارش {self.order_number} — {self.user} [{self.get_status_display()}]"

    # ── Lifecycle helpers ─────────────────────────────────────────────

    def set_payment_deadline(self):
        """تنظیم مهلت پرداخت ۲ ساعته از لحظه تأیید ادمین."""
        minutes = getattr(settings, "RESERVATION_DURATION_MINUTES", 120)
        self.payment_deadline = timezone.now() + timedelta(minutes=minutes)
        self.save(update_fields=["payment_deadline", "updated_at"])

    def set_admin_confirm_deadline(self):
        """تنظیم مهلت ۱۵ دقیقه‌ای برای تأیید ادمین."""
        minutes = getattr(settings, "ADMIN_CONFIRM_DEADLINE_MINUTES", 15)
        self.admin_confirm_deadline = timezone.now() + timedelta(minutes=minutes)
        self.save(update_fields=["admin_confirm_deadline", "updated_at"])

    @property
    def is_payment_expired(self) -> bool:
        if self.payment_deadline is None:
            return False
        return timezone.now() > self.payment_deadline and self.status == self.Status.AWAITING_PAYMENT

    @property
    def is_settlement_due(self) -> bool:
        """موعد تسویه رسیده (سطح سفارش یا هر یک از اقلام) و سفارش هنوز تسویه/لغو نشده."""
        if self.status in (self.Status.PAID, self.Status.CANCELLED, self.Status.REFUNDED, self.Status.REJECTED):
            return False
        today = timezone.now().date()
        if self.settlement_due_date and self.settlement_due_date <= today:
            return True
        return self.items.filter(settlement_due_date__lte=today).exists()

    @property
    def effective_amount(self) -> int:
        """مبلغ مؤثر: اگر ادمین قیمت تأیید کرده، آن را برگردان؛ وگرنه total_amount."""
        return self.confirmed_amount or self.total_amount


# ─── OrderItem ────────────────────────────────────────────────────────────────

class OrderItem(TimeStampedModel):
    """One line in an order. Price is snapshot at order creation time."""

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="سفارش",
    )
    variant = models.ForeignKey(
        "catalog.ProductVariant",
        on_delete=models.PROTECT,
        related_name="order_items",
        verbose_name="نسخه محصول",
    )
    quantity = models.PositiveSmallIntegerField(default=1, verbose_name="تعداد")

    # Snapshot قیمت در زمان سفارش (تغییر نرخ ارز اثر نگذارد)
    unit_price = models.PositiveBigIntegerField(verbose_name="قیمت واحد (تومان) — snapshot")

    # برای سفارش‌های استعلامی: قیمت نهایی تأیید شده
    confirmed_unit_price = models.PositiveBigIntegerField(
        default=0,
        verbose_name="قیمت تأیید شده ادمین",
    )

    # زمان رزرو (اگر این آیتم موجودی رزرو دارد)
    reserved_until = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="رزرو تا",
    )

    # تسویه per-item — هر قلم می‌تواند نحوه تسویه و موعد خودش را داشته باشد
    settlement_type = models.CharField(
        max_length=10, choices=Settlement.choices,
        default=Settlement.CASH, verbose_name="نحوه تسویه",
    )
    settlement_due_date = models.DateField(
        null=True, blank=True, verbose_name="موعد تسویه",
    )

    class Meta:
        db_table = "orders_order_item"
        verbose_name = "آیتم سفارش"
        verbose_name_plural = "آیتم‌های سفارش"

    def __str__(self):
        return f"{self.quantity}× {self.variant} — سفارش {self.order.order_number}"

    @property
    def subtotal(self) -> int:
        price = self.confirmed_unit_price or self.unit_price
        return price * self.quantity

    @property
    def is_settlement_due(self) -> bool:
        if not self.settlement_due_date:
            return False
        if self.order.status in (Order.Status.PAID, Order.Status.CANCELLED, Order.Status.REFUNDED, Order.Status.REJECTED):
            return False
        return self.settlement_due_date <= timezone.now().date()


# ─── StockReservation ─────────────────────────────────────────────────────────

class StockReservation(TimeStampedModel):
    """
    Explicit reservation record per variant per order.

    The cron job (release_expired_reservations) queries this table to find
    expired reservations and calls variant.release_reservation(quantity).

    is_released=True means the reservation has been freed (either by payment
    success or by expiry).
    """

    variant = models.ForeignKey(
        "catalog.ProductVariant",
        on_delete=models.CASCADE,
        related_name="reservations",
        verbose_name="نسخه محصول",
    )
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="reservations",
        verbose_name="سفارش",
    )
    quantity = models.PositiveSmallIntegerField(verbose_name="تعداد رزرو شده")
    reserved_until = models.DateTimeField(verbose_name="رزرو تا")
    is_released = models.BooleanField(
        default=False,
        verbose_name="آزاد شده",
        db_index=True,
    )
    released_at = models.DateTimeField(null=True, blank=True, verbose_name="زمان آزادسازی")
    release_reason = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="دلیل آزادسازی",
        help_text="مثلاً: payment_success / expired / admin_cancel",
    )

    class Meta:
        db_table = "orders_stock_reservation"
        verbose_name = "رزرو موجودی"
        verbose_name_plural = "رزروهای موجودی"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["is_released", "reserved_until"],
                name="idx_reservation_active",
            )
        ]

    def __str__(self):
        status = "آزاد شده" if self.is_released else "فعال"
        return f"رزرو {self.quantity}× {self.variant} — {status}"

    def release(self, reason: str = "expired") -> None:
        """
        آزاد کردن این رزرو:
        1. reserved_qty روی variant کم می‌شود.
        2. رکورد رزرو به عنوان آزاد شده علامت می‌خورد.
        """
        if self.is_released:
            return  # Already released — idempotent
        self.variant.release_reservation(self.quantity)
        self.is_released = True
        self.released_at = timezone.now()
        self.release_reason = reason
        self.save(update_fields=["is_released", "released_at", "release_reason", "updated_at"])


# ─── PaymentLog ───────────────────────────────────────────────────────────────

class PaymentLog(TimeStampedModel):
    """
    لاگ تمام تراکنش‌های درگاه — audit trail کامل.
    هر مرحله (request / verify / settle) یک رکورد جداگانه دارد.
    """

    class Step(models.TextChoices):
        REQUEST = "request", "درخواست پرداخت"
        VERIFY  = "verify",  "تأیید پرداخت"
        SETTLE  = "settle",  "تسویه"

    class TxStatus(models.TextChoices):
        SUCCESS = "success", "موفق"
        FAILED  = "failed",  "ناموفق"
        PENDING = "pending", "در انتظار"

    order = models.ForeignKey(
        Order, on_delete=models.CASCADE,
        related_name="payment_logs", verbose_name="سفارش",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="payment_logs", verbose_name="کاربر",
    )
    step   = models.CharField(max_length=20, choices=Step.choices,     verbose_name="مرحله")
    status = models.CharField(max_length=10, choices=TxStatus.choices,
                              default=TxStatus.PENDING,               verbose_name="وضعیت")
    bank_ref_id   = models.CharField(max_length=100, blank=True, verbose_name="شناسه مرجع بانک")
    res_code      = models.CharField(max_length=10,  blank=True, verbose_name="کد پاسخ")
    amount        = models.PositiveBigIntegerField(default=0,    verbose_name="مبلغ (تومان)")
    raw_request   = models.TextField(blank=True, verbose_name="درخواست خام")
    raw_response  = models.TextField(blank=True, verbose_name="پاسخ خام")
    error_message = models.TextField(blank=True, verbose_name="پیام خطا")
    ip_address    = models.GenericIPAddressField(null=True, blank=True, verbose_name="IP")

    class Meta:
        db_table = "orders_payment_log"
        verbose_name = "لاگ پرداخت"
        verbose_name_plural = "لاگ‌های پرداخت"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["order", "step"], name="idx_paylog_order_step"),
        ]

    def __str__(self):
        return (
            f"[{self.get_step_display()}] {self.order.order_number} "
            f"— {self.get_status_display()}"
        )


class ChinaOrderRequest(models.Model):
    """درخواست سفارش مستقیم از چین"""

    class Status(models.TextChoices):
        PENDING   = "pending",   "در انتظار بررسی"
        REVIEWING = "reviewing", "در حال بررسی"
        APPROVED  = "approved",  "تأیید شده"
        REJECTED  = "rejected",  "رد شده"

    # اطلاعات درخواست‌دهنده
    name        = models.CharField(max_length=100, verbose_name="نام و نام خانوادگی")
    phone       = models.CharField(max_length=20, verbose_name="شماره تماس")
    email       = models.EmailField(blank=True, verbose_name="ایمیل")
    user        = models.ForeignKey(
        'users.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='china_requests', verbose_name="کاربر"
    )

    # اطلاعات کالا
    product_name = models.CharField(max_length=300, verbose_name="نام کالا")
    quantity     = models.PositiveIntegerField(verbose_name="تعداد")
    description  = models.TextField(blank=True, verbose_name="توضیحات")
    product_link = models.URLField(blank=True, verbose_name="لینک کالا (اختیاری)")

    # وضعیت
    status      = models.CharField(max_length=20, choices=Status.choices,
                    default=Status.PENDING, verbose_name="وضعیت")
    admin_note  = models.TextField(blank=True, verbose_name="یادداشت ادمین")
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "orders_china_request"
        verbose_name = "درخواست از چین"
        verbose_name_plural = "درخواست‌های از چین"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} | {self.product_name} × {self.quantity}"


# ─── StockShortage ────────────────────────────────────────────────────────────

class StockShortage(TimeStampedModel, AuditMixin):
    """
    مازاد تقاضا — وقتی مشتری تعدادی می‌خواهد اما موجودی کافی تأیید نمی‌شود.
    shortage_qty = requested_qty - approved_qty
    """

    class Reason(models.TextChoices):
        STOCK = "stock", "عدم موجودی"
        OTHER = "other", "سایر"

    order = models.ForeignKey(
        Order,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="stock_shortages",
        verbose_name="سفارش",
    )
    variant = models.ForeignKey(
        "catalog.ProductVariant",
        on_delete=models.PROTECT,
        related_name="stock_shortages",
        verbose_name="نسخه محصول",
    )
    requested_qty = models.PositiveIntegerField(verbose_name="تعداد درخواستی")
    approved_qty = models.PositiveIntegerField(verbose_name="تعداد تأییدشده")
    shortage_qty = models.PositiveIntegerField(verbose_name="مازاد تقاضا")
    reason = models.CharField(
        max_length=20,
        choices=Reason.choices,
        default=Reason.STOCK,
        verbose_name="دلیل",
    )
    created_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recorded_stock_shortages",
        verbose_name="ثبت‌کننده",
    )
    updated_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="edited_stock_shortages",
        verbose_name="آخرین ویرایش‌کننده",
    )

    class Meta:
        db_table = "orders_stock_shortage"
        verbose_name = "مازاد تقاضا"
        verbose_name_plural = "مازادهای تقاضا"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["variant", "created_at"], name="idx_shortage_variant_created"),
        ]

    def __str__(self):
        order_no = self.order.order_number if self.order else "بدون سفارش"
        return f"مازاد تقاضا {self.shortage_qty}× {self.variant} — {order_no}"
