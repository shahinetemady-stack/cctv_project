import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

# ─── بازنویسی کامل core/models.py ────────────────────────────
models_path = os.path.join('apps', 'core', 'models.py')
with open(models_path, 'w', encoding='utf-8') as f:
    f.write("""from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


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
""")
print("✓ core/models.py بازنویسی شد")

# ─── بازنویسی core/admin.py ───────────────────────────────────
admin_path = os.path.join('apps', 'core', 'admin.py')
with open(admin_path, 'w', encoding='utf-8') as f:
    f.write("""from django.contrib import admin
from .models import SiteSettings, StaticPage


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        ("اطلاعات پایه", {"fields": ("site_name", "site_logo")}),
        ("تماس", {"fields": ("contact_phone", "contact_email", "contact_address", "working_hours")}),
        ("شبکه‌های اجتماعی", {"fields": (
            "whatsapp_number", "bale_username", "eitaa_username",
            "telegram_username", "instagram_username",
        )}),
        ("درباره ما", {"fields": ("about_us_text",)}),
        ("حساب‌های بانکی", {"fields": ("bank_accounts",)}),
    )

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(StaticPage)
class StaticPageAdmin(admin.ModelAdmin):
    list_display = ["key", "title", "updated_at"]
    fields = ["key", "title", "content"]
""")
print("✓ core/admin.py بازنویسی شد")

# ─── Migration ────────────────────────────────────────────────
import subprocess, sys

# حذف migration های قبلی و ساخت مجدد
migrations_dir = os.path.join('apps', 'core', 'migrations')
for f in os.listdir(migrations_dir):
    if f != '__init__.py' and f.endswith('.py'):
        os.remove(os.path.join(migrations_dir, f))
        print(f"Removed: {f}")

r = subprocess.run([sys.executable, 'manage.py', 'makemigrations', 'core'],
                   capture_output=True, text=True)
print(r.stdout[-200:] if r.stdout else "")
if r.returncode != 0:
    print("خطا:", r.stderr[-300:])

r2 = subprocess.run([sys.executable, 'manage.py', 'migrate', 'core'],
                    capture_output=True, text=True)
print(r2.stdout[-200:] if r2.stdout else "")

# ─── ساخت محتوای پیش‌فرض ─────────────────────────────────────
from apps.core.models import StaticPage
defaults = [
    ('terms', 'قوانین و مقررات', '''<h2>۱. شرایط استفاده</h2>
<p>با استفاده از این سایت، شما با تمام قوانین و مقررات آن موافقت می‌کنید.</p>
<h2>۲. سفارش و پرداخت</h2>
<p>تمام سفارشات پس از تأیید موجودی کالا و دریافت پرداخت پردازش می‌شوند.</p>
<h2>۳. ارسال کالا</h2>
<p>ارسال در سراسر ایران انجام می‌شود. زمان تحویل ۲ تا ۷ روز کاری است.</p>
<h2>۴. ضمانت و مرجوعی</h2>
<p>کالاهای معیوب تا ۷ روز پس از دریافت قابل مرجوع هستند.</p>'''),
    ('privacy', 'حریم خصوصی', '''<h2>۱. اطلاعات جمع‌آوری شده</h2>
<p>اطلاعاتی مانند نام، شماره تماس و آدرس برای پردازش سفارشات جمع‌آوری می‌شود.</p>
<h2>۲. استفاده از اطلاعات</h2>
<p>اطلاعات شما برای پردازش سفارش و بهبود خدمات استفاده می‌شود.</p>
<h2>۳. امنیت</h2>
<p>تمام اطلاعات با استفاده از پروتکل‌های امنیتی استاندارد محافظت می‌شود.</p>'''),
]

for key, title, html in defaults:
    obj, created = StaticPage.objects.get_or_create(
        key=key, defaults={'title': title, 'content': html}
    )
    print(f"{'✓ ساخته شد' if created else '✓ موجود بود'}: {title}")

r3 = subprocess.run([sys.executable, 'manage.py', 'check', '--verbosity=0'],
                    capture_output=True, text=True)
print("✓ check موفق" if r3.returncode == 0 else r3.stderr[-300:])
print("\nhttp://127.0.0.1:8000/admin/core/staticpage/")
