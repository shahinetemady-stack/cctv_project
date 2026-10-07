from django.db import models
from django.conf import settings

from .middleware import get_current_user


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class AuditMixin(models.Model):
    """پر کردن خودکار created_by/updated_by از کاربر جاری (میدل‌ور CurrentUserMiddleware).
    مدل‌هایی که فیلدها را خودشان تعریف کرده‌اند از همین میکسین استفاده می‌کنند."""

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        user = get_current_user()
        if user:
            if self._state.adding and hasattr(self, "created_by") and not self.created_by_id:
                self.created_by = user
            if hasattr(self, "updated_by"):
                self.updated_by = user
        super().save(*args, **kwargs)


class AuditableModel(AuditMixin):
    """مدل پایه با ردیابی ثبت‌کننده و آخرین ویرایش‌کننده"""
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, editable=False,
        related_name="created_%(class)ss", verbose_name="ثبت کننده",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, editable=False,
        related_name="edited_%(class)ss", verbose_name="آخرین ویرایش کننده",
    )

    class Meta:
        abstract = True




class SingletonModel(models.Model):
    """مدل Singleton — فقط یک نمونه"""
    class Meta:
        abstract = True

    @classmethod
    def get_instance(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass
class SiteSettings(models.Model):
    site_name     = models.CharField(max_length=100, default="فروشگاه قطعات دوربین", verbose_name="نام سایت")
    site_logo     = models.ImageField(upload_to='site/', null=True, blank=True)
    contact_phone = models.CharField(max_length=20, blank=True, verbose_name="تلفن")
    contact_email = models.EmailField(blank=True, verbose_name="ایمیل")
    contact_address = models.TextField(blank=True, verbose_name="آدرس")
    working_hours = models.CharField(max_length=200, blank=True, default="شنبه تا پنج‌شنبه ۹-۱۸")
    china_phone   = models.CharField(max_length=20, blank=True, verbose_name="تلفن چین")
    china_address = models.TextField(blank=True, verbose_name="آدرس دفتر چین")
    wechat_qr     = models.ImageField(upload_to='site/', null=True, blank=True, verbose_name="کیوآرکد ویچت")
    whatsapp_number   = models.CharField(max_length=20, blank=True)
    bale_username     = models.CharField(max_length=50, blank=True)
    eitaa_username    = models.CharField(max_length=50, blank=True)
    telegram_username = models.CharField(max_length=50, blank=True)
    instagram_username = models.CharField(max_length=50, blank=True)
    about_us_text = models.TextField(blank=True)
    bank_accounts = models.JSONField(default=list, blank=True)
    enamad_id = models.CharField(max_length=20, blank=True, verbose_name="کد اینماد")
    enamad_code = models.CharField(max_length=50, blank=True, verbose_name="کد امنیتی اینماد")

    class Meta:
        db_table = "core_site_settings"
        verbose_name = "تنظیمات سایت"
        verbose_name_plural = "تنظیمات سایت"

    def __str__(self):
        return self.site_name

    @classmethod
    def get_instance(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class StaticPage(models.Model):
    PAGES = [
        ('terms',   'قوانین و مقررات'),
        ('privacy', 'حریم خصوصی'),
        ('about',   'درباره ما'),
        ('faq',     'سؤالات متداول'),
    ]
    key     = models.CharField(max_length=50, choices=PAGES, unique=True, verbose_name="صفحه")
    title   = models.CharField(max_length=200, verbose_name="عنوان")
    content = models.TextField(verbose_name="محتوا (HTML)")
    image1  = models.ImageField(upload_to='pages/', blank=True, verbose_name="تصویر ۱")
    image2  = models.ImageField(upload_to='pages/', blank=True, verbose_name="تصویر ۲")
    image3  = models.ImageField(upload_to='pages/', blank=True, verbose_name="تصویر ۳")
    image4  = models.ImageField(upload_to='pages/', blank=True, verbose_name="تصویر ۴")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "core_static_page"
        verbose_name = "صفحه استاتیک"
        verbose_name_plural = "صفحات استاتیک"

    def __str__(self):
        return self.get_key_display()


class ServiceSubscription(models.Model):
    """سرویس‌ها و اشتراک‌های سایت (دامنه، سرور، CDN و…) — هشدار انقضا روی داشبورد."""

    CATEGORIES = [
        ('domain', 'دامنه'),
        ('server', 'سرور'),
        ('cdn',    'CDN و امنیت'),
        ('sms',    'پیامک'),
        ('email',  'ایمیل'),
        ('ai',     'هوش مصنوعی / API'),
        ('other',  'سایر'),
    ]

    name        = models.CharField(max_length=100, verbose_name="نام سرویس")
    category    = models.CharField(max_length=20, choices=CATEGORIES, default='other', verbose_name="دسته")
    provider    = models.CharField(max_length=100, blank=True, verbose_name="ارائه‌دهنده")
    account     = models.CharField(max_length=150, blank=True, verbose_name="حساب / شناسه")
    expire_date = models.DateField(verbose_name="تاریخ انقضا")
    renew_cost  = models.CharField(max_length=60, blank=True, verbose_name="هزینه تمدید")
    warn_days   = models.PositiveSmallIntegerField(default=30, verbose_name="هشدار از چند روز قبل")
    auto_renew  = models.BooleanField(default=False, verbose_name="تمدید خودکار")
    note        = models.TextField(blank=True, verbose_name="یادداشت")
    is_active   = models.BooleanField(default=True, verbose_name="فعال")
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "core_service_subscription"
        verbose_name = "سرویس و اشتراک"
        verbose_name_plural = "سرویس‌ها و اشتراک‌ها"
        ordering = ["expire_date"]

    def __str__(self):
        return f"{self.name} ({self.expire_date})"

    @property
    def days_left(self):
        from django.utils import timezone
        return (self.expire_date - timezone.localtime().date()).days
