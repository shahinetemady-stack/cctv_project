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


class SmsSettings(models.Model):
    """
    تنظیمات پنل پیامک (sms.ir) — سینگلتون؛ از پنل ادمین قابل ویرایش است.
    شناسه قالب‌ها = Template IDهای Verify که در پنل sms.ir ساخته و تأیید شده‌اند.
    """

    # ── اتصال ─────────────────────────────────────────────────────────
    api_key = models.CharField(max_length=100, blank=True, verbose_name="کلید API پنل sms.ir")
    line_number = models.CharField(
        max_length=20, blank=True, verbose_name="شماره خط ارسال",
        help_text="برای ارسال متن آزاد/گروهی (کمپین) — خط اختصاصی پنل",
    )

    # ── قالب‌های Verify ───────────────────────────────────────────────
    otp_template_id = models.CharField(max_length=20, blank=True, verbose_name="قالب کد تأیید (OTP)")
    order_status_template_id = models.CharField(max_length=20, blank=True, verbose_name="قالب تغییر وضعیت سفارش")
    payment_reminder_template_id = models.CharField(max_length=20, blank=True, verbose_name="قالب یادآوری سررسید بدهی")
    tier_change_template_id = models.CharField(max_length=20, blank=True, verbose_name="قالب تغییر سطح همکار")
    partner_approved_template_id = models.CharField(max_length=20, blank=True, verbose_name="قالب تأیید همکار")
    partner_request_template_id = models.CharField(max_length=20, blank=True, verbose_name="قالب ثبت درخواست همکاری")
    invoice_confirmed_template_id = models.CharField(max_length=20, blank=True, verbose_name="قالب تأیید فاکتور")
    account_info_template_id = models.CharField(max_length=20, blank=True, verbose_name="قالب اطلاعات حساب پرداخت")
    near_tier_template_id = models.CharField(max_length=64, blank=True, verbose_name="قالب نزدیک به آستانه ارتقای سطح")

    # ── کلیدهای روشن/خاموش ────────────────────────────────────────────
    order_status_enabled = models.BooleanField(default=True, verbose_name="پیامک تغییر وضعیت سفارش")
    payment_reminder_enabled = models.BooleanField(default=True, verbose_name="پیامک یادآوری سررسید بدهی")
    tier_change_enabled = models.BooleanField(default=True, verbose_name="پیامک تغییر سطح همکار")
    partner_approved_enabled = models.BooleanField(default=True, verbose_name="پیامک تأیید همکار")
    partner_request_enabled = models.BooleanField(default=True, verbose_name="پیامک ثبت درخواست همکاری")
    invoice_confirmed_enabled = models.BooleanField(default=True, verbose_name="پیامک تأیید فاکتور")
    account_info_enabled = models.BooleanField(default=True, verbose_name="پیامک اطلاعات حساب پرداخت")
    near_tier_enabled = models.BooleanField(default=True, verbose_name="پیامک نزدیک به آستانه ارتقای سطح")

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "notifications_sms_settings"
        verbose_name = "تنظیمات پیامک"
        verbose_name_plural = "تنظیمات پیامک"

    def __str__(self):
        return "تنظیمات پیامک"

    @classmethod
    def get_instance(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)
