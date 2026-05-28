import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

# ─── اضافه کردن StaticPage به core/models.py ─────────────────
models_path = os.path.join('apps', 'core', 'models.py')
with open(models_path, encoding='utf-8') as f:
    content = f.read()

if 'StaticPage' not in content:
    content += '''

class StaticPage(models.Model):
    """صفحات استاتیک قابل ویرایش از Admin"""
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
'''
    with open(models_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("✓ StaticPage اضافه شد")

# ─── Migration ─────────────────────────────────────────────────
import subprocess, sys
r = subprocess.run([sys.executable, 'manage.py', 'makemigrations', 'core'],
                   capture_output=True, text=True)
print(r.stdout[-200:] if r.stdout else "")
r2 = subprocess.run([sys.executable, 'manage.py', 'migrate'],
                    capture_output=True, text=True)
print(r2.stdout[-100:] if r2.stdout else "")

# ─── Admin ────────────────────────────────────────────────────
admin_path = os.path.join('apps', 'core', 'admin.py')
with open(admin_path, encoding='utf-8') as f:
    admin = f.read()

if 'StaticPage' not in admin:
    admin += '''

from .models import StaticPage

@admin.register(StaticPage)
class StaticPageAdmin(admin.ModelAdmin):
    list_display = ["key", "title", "updated_at"]
    fields = ["key", "title", "content"]
'''
    with open(admin_path, 'w', encoding='utf-8') as f:
        f.write(admin)
    print("✓ StaticPageAdmin اضافه شد")

# ─── View ─────────────────────────────────────────────────────
views_path = os.path.join('apps', 'core', 'views.py')
with open(views_path, encoding='utf-8') as f:
    views = f.read()

if 'StaticPageView' not in views:
    views += '''

class StaticPageView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, key):
        from .models import StaticPage
        try:
            page = StaticPage.objects.get(key=key)
            return Response({'title': page.title, 'content': page.content})
        except StaticPage.DoesNotExist:
            return Response({'title': '', 'content': ''})
'''
    with open(views_path, 'w', encoding='utf-8') as f:
        f.write(views)
    print("✓ StaticPageView اضافه شد")

# ─── URL ──────────────────────────────────────────────────────
urls_path = os.path.join('apps', 'core', 'urls.py')
with open(urls_path, 'w', encoding='utf-8') as f:
    f.write("""from django.urls import path
from . import views

urlpatterns = [
    path('settings/', views.SiteSettingsView.as_view()),
    path('pages/<str:key>/', views.StaticPageView.as_view()),
]
""")
print("✓ URL اضافه شد")

# ─── ساخت محتوای پیش‌فرض ─────────────────────────────────────
from apps.core.models import StaticPage
defaults = [
    ('terms', 'قوانین و مقررات', '''<h2>۱. شرایط استفاده</h2>
<p>با استفاده از این سایت، شما با تمام قوانین و مقررات آن موافقت می‌کنید.</p>
<h2>۲. سفارش و پرداخت</h2>
<p>تمام سفارشات پس از تأیید موجودی کالا و دریافت پرداخت، پردازش می‌شوند.</p>
<h2>۳. ارسال کالا</h2>
<p>ارسال در سراسر ایران انجام می‌شود. زمان تحویل ۲ تا ۷ روز کاری است.</p>
<h2>۴. ضمانت و مرجوعی</h2>
<p>کالاهای معیوب تا ۷ روز پس از دریافت قابل مرجوع هستند.</p>'''),
    ('privacy', 'حریم خصوصی', '''<h2>۱. اطلاعات جمع‌آوری شده</h2>
<p>اطلاعاتی مانند نام، شماره تماس و آدرس برای پردازش سفارشات جمع‌آوری می‌شود.</p>
<h2>۲. استفاده از اطلاعات</h2>
<p>اطلاعات شما برای پردازش سفارش و بهبود خدمات استفاده می‌شود و به اشخاص ثالث فروخته نمی‌شود.</p>
<h2>۳. امنیت</h2>
<p>تمام اطلاعات با استفاده از پروتکل‌های امنیتی استاندارد محافظت می‌شود.</p>'''),
]

for key, title, content_html in defaults:
    obj, created = StaticPage.objects.get_or_create(
        key=key, defaults={'title': title, 'content': content_html}
    )
    print(f"{'✓ ساخته شد' if created else '✓ موجود بود'}: {title}")

r3 = subprocess.run([sys.executable, 'manage.py', 'check', '--verbosity=0'],
                    capture_output=True, text=True)
print("✓ check موفق" if r3.returncode == 0 else r3.stderr[-200:])
print("\nبرای ویرایش متن:")
print("http://127.0.0.1:8000/admin/core/staticpage/")
