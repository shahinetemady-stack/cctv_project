from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

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
    whatsapp_number   = models.CharField(max_length=20, blank=True)
    bale_username     = models.CharField(max_length=50, blank=True)
    eitaa_username    = models.CharField(max_length=50, blank=True)
    telegram_username = models.CharField(max_length=50, blank=True)
    instagram_username = models.CharField(max_length=50, blank=True)
    about_us_text = models.TextField(blank=True)
    bank_accounts = models.JSONField(default=list, blank=True)

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
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "core_static_page"
        verbose_name = "صفحه استاتیک"
        verbose_name_plural = "صفحات استاتیک"

    def __str__(self):
        return self.get_key_display()
