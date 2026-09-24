"""
apps/payment/models.py
───────────────────────
مدل ثبت تراکنش‌های بانکی.

هر بار که کاربر به درگاه هدایت می‌شود یک PaymentTransaction ساخته می‌شود.
این جدول audit کاملی از وضعیت هر تراکنش نگه می‌دارد — حتی اگر callback
دو بار برسد یا پرداخت ناموفق باشد.

وضعیت‌ها:
  INITIATED   → token از بانک گرفته شد، کاربر هنوز پرداخت نکرده
  SUCCESS     → بانک تأیید کرد، verify هم موفق بود
  FAILED      → پرداخت ناموفق یا تأیید ناموفق
  EXPIRED     → کاربر برنگشت / مهلت تمام شد
"""

from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class PaymentTransaction(TimeStampedModel):

    class Status(models.TextChoices):
        INITIATED = "initiated", "شروع شده"
        SUCCESS   = "success",   "موفق"
        FAILED    = "failed",    "ناموفق"
        EXPIRED   = "expired",   "منقضی"

    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.PROTECT,
        related_name="payment_transactions",
        verbose_name="سفارش",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="payment_transactions",
        verbose_name="کاربر",
    )

    # ── فیلدهای به‌پرداخت ────────────────────────────────────────────
    # درخواست پرداخت
    bank_token = models.CharField(
        max_length=64, blank=True, default="",
        verbose_name="توکن بانکی",
        help_text="RefId دریافتی از bpPayRequest (رشته هگز)",
    )
    amount = models.PositiveBigIntegerField(
        verbose_name="مبلغ (ریال)",
        help_text="به‌پرداخت با ریال کار می‌کند — تومان × ۱۰",
    )

    # callback از بانک
    res_code = models.CharField(
        max_length=10, blank=True,
        verbose_name="کد نتیجه بانک",
        help_text="0 = موفق",
    )
    sale_ref_id = models.CharField(
        max_length=50, blank=True,
        verbose_name="شماره پیگیری فروش",
        help_text="SaleReferenceId از بانک پس از verify",
    )
    sale_order_id = models.CharField(
        max_length=30, blank=True,
        verbose_name="شماره سفارش ارسالی به بانک",
    )

    # نتیجه نهایی
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.INITIATED,
        verbose_name="وضعیت تراکنش",
        db_index=True,
    )
    error_message = models.TextField(blank=True, verbose_name="پیام خطا")
    raw_request  = models.JSONField(default=dict, blank=True, verbose_name="درخواست خام به بانک")
    raw_callback = models.JSONField(default=dict, blank=True, verbose_name="callback خام از بانک")
    raw_verify   = models.JSONField(default=dict, blank=True, verbose_name="پاسخ verify خام")

    class Meta:
        db_table = "payment_transaction"
        verbose_name = "تراکنش پرداخت"
        verbose_name_plural = "تراکنش‌های پرداخت"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["bank_token"], name="idx_pay_token"),
            models.Index(fields=["order", "status"], name="idx_pay_order_status"),
        ]

    def __str__(self):
        return (
            f"تراکنش {self.order.order_number} "
            f"| {self.amount:,} ریال | {self.get_status_display()}"
        )
