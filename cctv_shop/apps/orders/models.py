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

from apps.core.models import TimeStampedModel


def generate_order_number():
    """ORD-YYYYMMDD-XXXX  (human-readable, near-unique)."""
    today = timezone.now().strftime("%Y%m%d")
    short = uuid.uuid4().hex[:6].upper()
    return f"ORD-{today}-{short}"


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
    )
    quantity = models.PositiveSmallIntegerField(default=1, verbose_name="تعداد")

    class Meta:
        db_table = "orders_cart_item"
        verbose_name = "آیتم سبد خرید"
        verbose_name_plural = "آیتم‌های سبد خرید"
        unique_together = [["cart", "variant"]]

    def __str__(self):
        return f"{self.quantity}× {self.variant}"

    @property
    def subtotal(self) -> int:
        return self.variant.final_price * self.quantity


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

    class Meta:
        db_table = "orders_inquiry_cart_item"
        verbose_name = "آیتم سبد استعلام"
        verbose_name_plural = "آیتم‌های سبد استعلام"
        unique_together = [["cart", "variant"]]

    def __str__(self):
        return f"{self.quantity}× {self.variant}"


# ─── Order ────────────────────────────────────────────────────────────────────

class Order(TimeStampedModel):
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
        PAID = "paid", "پرداخت شده"
        CANCELLED = "cancelled", "لغو شده"
        REFUNDED = "refunded", "مسترد شده"

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
    customer_notes = models.TextField(blank=True, verbose_name="یادداشت مشتری")
    admin_notes = models.TextField(blank=True, verbose_name="یادداشت ادمین")

    # ── Deadlines ─────────────────────────────────────────────────────
    admin_confirm_deadline = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="مهلت تأیید ادمین",
        help_text="ادمین باید تا این زمان سفارش استعلامی را تأیید کند",
    )

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
