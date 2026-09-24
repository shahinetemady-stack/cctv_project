"""
apps/leads/models.py
─────────────────────
دفترچه مخاطبان تبلیغاتی (Lead) + کمپین پیامکی.

Lead: شماره موبایل یکتا (نرمال‌شده 09xxxxxxxxx) + منبع + شهر + تگ + وضعیت قیف.
Campaign: متن + فیلتر مخاطبان + گزارش ارسال (هر رکورد CampaignSend نتیجه هر نفر).
"""
import logging
import re

from django.db import models

from apps.core.models import AuditMixin, TimeStampedModel

logger = logging.getLogger(__name__)

_FA_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


def normalize_phone(raw: str) -> str:
    """
    نرمال‌سازی موبایل ایران به فرمت 09xxxxxxxxx.
    ارقام فارسی/عربی، +98 و 98 ابتدایی، فاصله و خط‌تیره را هندل می‌کند.
    نامعتبر → رشته خالی.
    """
    if not raw:
        return ""
    digits = re.sub(r"\D", "", str(raw).translate(_FA_DIGITS))
    if digits.startswith("0098"):
        digits = digits[4:]
    elif digits.startswith("98"):
        digits = digits[2:]
    if len(digits) == 10 and digits.startswith("9"):
        digits = "0" + digits
    if re.fullmatch(r"09\d{9}", digits):
        return digits
    return ""


class Lead(TimeStampedModel, AuditMixin):
    """یک مخاطب تبلیغاتی — مبنای dedup شماره موبایل است."""

    class Source(models.TextChoices):
        DIVAR    = "divar",    "دیوار"
        SHEYPOOR = "sheypoor", "شیپور"
        GOOGLE   = "google",   "گوگل"
        TELEGRAM = "telegram", "تلگرام"
        MANUAL   = "manual",   "دستی/ایمپورت"

    class Category(models.TextChoices):
        INSTALLER = "installer", "نصاب و مجری"
        SELLER    = "seller",    "فروشگاه و فروشنده"
        COMPANY   = "company",   "شرکت نظارتی/حفاظتی"
        OTHER     = "other",     "سایر"

    class Status(models.TextChoices):
        NEW       = "new",       "جدید"
        CONTACTED = "contacted", "پیامک شد"
        REPLIED   = "replied",   "پاسخ داد"
        CUSTOMER  = "customer",  "مشتری شد"
        REJECTED  = "rejected",  "رد شده"

    phone = models.CharField(max_length=11, unique=True, verbose_name="موبایل")
    name = models.CharField(max_length=200, blank=True, verbose_name="نام/فروشگاه")
    city = models.CharField(max_length=60, blank=True, db_index=True, verbose_name="شهر")
    source = models.CharField(max_length=20, choices=Source.choices, default=Source.MANUAL,
                              db_index=True, verbose_name="منبع")
    source_url = models.URLField(blank=True, verbose_name="لینک آگهی/منبع")
    source_title = models.CharField(max_length=300, blank=True, verbose_name="عنوان آگهی")
    keyword = models.CharField(max_length=100, blank=True, verbose_name="کلیدواژه برخورد")
    category = models.CharField(max_length=12, choices=Category.choices, default=Category.OTHER,
                                db_index=True, verbose_name="دسته‌بندی")
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.NEW,
                              db_index=True, verbose_name="وضعیت")
    notes = models.TextField(blank=True, verbose_name="یادداشت")
    sms_count = models.PositiveIntegerField(default=0, verbose_name="تعداد پیامک ارسالی")
    last_sms_at = models.DateTimeField(null=True, blank=True, verbose_name="آخرین پیامک")

    class Meta:
        db_table = "leads_lead"
        verbose_name = "مخاطب"
        verbose_name_plural = "مخاطبان تبلیغاتی"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "city"], name="idx_lead_status_city"),
            models.Index(fields=["source", "created_at"], name="idx_lead_source_date"),
        ]

    def __str__(self):
        return f"{self.phone} — {self.name or 'بدون‌نام'} ({self.get_source_display()})"


class LeadCampaign(TimeStampedModel, AuditMixin):
    """کمپین پیامکی روی زیرمجموعه‌ای از مخاطبان."""

    class Status(models.TextChoices):
        DRAFT   = "draft",   "پیش‌نویس"
        SENDING = "sending", "در حال ارسال"
        DONE    = "done",    "تمام شده"
        FAILED  = "failed",  "ناموفق"

    name = models.CharField(max_length=200, verbose_name="نام کمپین")
    message = models.TextField(verbose_name="متن پیامک")
    # فیلتر مخاطبان — خالی یعنی همه
    filter_city = models.CharField(max_length=60, blank=True, verbose_name="فیلتر شهر")
    filter_source = models.CharField(max_length=20, blank=True, verbose_name="فیلتر منبع")
    filter_category = models.CharField(max_length=12, blank=True, verbose_name="فیلتر دسته‌بندی")
    filter_status = models.CharField(max_length=12, default=Lead.Status.NEW,
                                     verbose_name="فیلتر وضعیت")
    filter_keyword = models.CharField(max_length=100, blank=True, verbose_name="فیلتر کلیدواژه")

    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT,
                              verbose_name="وضعیت")
    total_targets = models.PositiveIntegerField(default=0, verbose_name="تعداد مخاطب هدف")
    sent_count = models.PositiveIntegerField(default=0, verbose_name="ارسال موفق")
    failed_count = models.PositiveIntegerField(default=0, verbose_name="ناموفق")
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "leads_campaign"
        verbose_name = "کمپین پیامکی"
        verbose_name_plural = "کمپین‌های پیامکی"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.sent_count}/{self.total_targets})"


class CampaignSend(models.Model):
    """نتیجه ارسال برای هر مخاطب در هر کمپین."""

    campaign = models.ForeignKey(LeadCampaign, on_delete=models.CASCADE,
                                 related_name="sends", verbose_name="کمپین")
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE,
                             related_name="campaign_sends", verbose_name="مخاطب")
    ok = models.BooleanField(default=False)
    error = models.CharField(max_length=300, blank=True)
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "leads_campaign_send"
        unique_together = [["campaign", "lead"]]
        ordering = ["-sent_at"]


class ScraperRun(models.Model):
    """گزارش هر اجرای اسکرپر — برای نمایش وضعیت/خطا در پنل."""

    class Status(models.TextChoices):
        RUNNING = "running", "در حال اجرا"
        SUCCESS = "success", "موفق"
        ERROR   = "error",   "خطا"

    source = models.CharField(max_length=20, db_index=True, verbose_name="منبع")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.RUNNING)
    new_count = models.PositiveIntegerField(default=0, verbose_name="لید جدید")
    seen_count = models.PositiveIntegerField(default=0, verbose_name="تکراری/رد شده")
    message = models.CharField(max_length=500, blank=True, verbose_name="پیام/خطا")
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "leads_scraper_run"
        verbose_name = "اجرای اسکرپر"
        verbose_name_plural = "اجراهای اسکرپر"
        ordering = ["-started_at"]

    @classmethod
    def latest_for(cls, source: str):
        return cls.objects.filter(source=source).first()

    def finish(self, status: str, new_count: int = 0, seen_count: int = 0, message: str = ""):
        from django.utils import timezone
        self.status = status
        self.new_count = new_count
        self.seen_count = seen_count
        self.message = message[:500]
        self.finished_at = timezone.now()
        self.save()


class LeadSettings(models.Model):
    """تنظیمات اسکرپر لید — سینگلتون (قابل ویرایش در ادمین جنگو)."""

    divar_token = models.TextField(
        blank=True,
        verbose_name="کوکی لاگین دیوار",
        help_text="بدون کوکی، دیوار شماره تماس آگهی‌ها را نمی‌دهد. روش گرفتن: در مرورگر divar.ir ← لاگین ← F12 ← تب Console ← تایپ کن copy(document.cookie) و Enter ← محتوای کلیپ‌بورد را همین‌جا بچسبان. عمر کوکی چند ساعت است؛ وقتی اسکرپر خطای «توکن منقضی» داد، همین کار را دوباره انجام بده.",
    )
    sheypoor_token = models.TextField(
        blank=True,
        verbose_name="کوکی لاگین شیپور",
        help_text="روش گرفتن مثل دیوار: در مرورگر sheypoor.com ← لاگین ← F12 ← تب Console ← تایپ کن copy(document.cookie) و Enter ← اینجا بچسبان. عمر کوکی شیپور معمولاً چند هفته است.",
    )
    serpapi_key = models.CharField(
        max_length=100, blank=True,
        verbose_name="کلید SerpAPI (گوگل مپ)",
        help_text="از serpapi.com رایگان بساز (پلن رایگان ماهی ۱۰۰ جستجو). اسکرپر گوگل با این کلید کسب‌وکارهای گوگل مپ را با شماره تماس جمع می‌کند.",
    )

    class Meta:
        db_table = "leads_settings"
        verbose_name = "تنظیمات لید"
        verbose_name_plural = "تنظیمات لید"

    @classmethod
    def get_instance(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
