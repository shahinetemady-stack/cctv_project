"""
apps/notifications/models.py
──────────────────────────────
Logs every SMS and email sent by the system.
Provides a full audit trail visible in the admin panel.
"""

from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class NotificationLog(TimeStampedModel):
    """
    Immutable log of every notification (SMS / email) dispatched.
    """

    class Channel(models.TextChoices):
        SMS = "sms", "پیامک"
        EMAIL = "email", "ایمیل"
        PUSH = "push", "اعلان Push"

    class RecipientType(models.TextChoices):
        ADMIN = "admin", "ادمین"
        USER = "user", "کاربر"

    class Status(models.TextChoices):
        SENT = "sent", "ارسال شد"
        FAILED = "failed", "شکست خورد"
        PENDING = "pending", "در صف"

    # ── Relations ─────────────────────────────────────────────────────
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notifications",
        verbose_name="کاربر",
    )
    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notifications",
        verbose_name="سفارش",
    )

    # ── Content ───────────────────────────────────────────────────────
    channel = models.CharField(
        max_length=10,
        choices=Channel.choices,
        verbose_name="کانال",
    )
    recipient_type = models.CharField(
        max_length=10,
        choices=RecipientType.choices,
        verbose_name="نوع گیرنده",
    )
    recipient_address = models.CharField(
        max_length=255,
        verbose_name="آدرس گیرنده",
        help_text="شماره موبایل یا ایمیل",
    )
    subject = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="موضوع (برای ایمیل)",
    )
    message = models.TextField(verbose_name="متن پیام")

    # ── Delivery ──────────────────────────────────────────────────────
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name="وضعیت ارسال",
    )
    sent_at = models.DateTimeField(null=True, blank=True, verbose_name="زمان ارسال")
    provider_response = models.TextField(
        blank=True,
        verbose_name="پاسخ سرویس‌دهنده",
        help_text="پاسخ خام Kavenegar یا SMTP",
    )
    error_message = models.TextField(blank=True, verbose_name="پیام خطا")

    class Meta:
        db_table = "notifications_log"
        verbose_name = "لاگ اعلان"
        verbose_name_plural = "لاگ اعلان‌ها"
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.get_channel_display()}] {self.recipient_address} — {self.get_status_display()}"
