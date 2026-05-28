import os

# ─── ساخت core/urls.py ────────────────────────────────────────
core_urls = os.path.join('apps', 'core', 'urls.py')
with open(core_urls, 'w', encoding='utf-8') as f:
    f.write("""from django.urls import path
from . import views

urlpatterns = [
    path('settings/', views.SiteSettingsView.as_view()),
    path('pages/<str:key>/', views.StaticPageView.as_view()),
]
""")
print("✓ core/urls.py ساخته شد")

# ─── بررسی core/views.py ─────────────────────────────────────
views_path = os.path.join('apps', 'core', 'views.py')
with open(views_path, encoding='utf-8') as f:
    views = f.read()

print("SiteSettingsView:", 'SiteSettingsView' in views)
print("StaticPageView:", 'StaticPageView' in views)

if 'SiteSettingsView' not in views:
    views += '''
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from .models import SiteSettings, StaticPage


class SiteSettingsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        s = SiteSettings.get_instance()
        return Response({
            'site_name': s.site_name,
            'contact_phone': s.contact_phone,
            'contact_email': s.contact_email,
            'contact_address': s.contact_address,
            'working_hours': s.working_hours,
            'whatsapp_number': s.whatsapp_number,
            'bale_username': s.bale_username,
            'eitaa_username': s.eitaa_username,
            'telegram_username': s.telegram_username,
            'instagram_username': s.instagram_username,
            'about_us_text': s.about_us_text,
            'bank_accounts': s.bank_accounts,
            'site_logo': s.site_logo.url if s.site_logo else None,
        })


class StaticPageView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, key):
        try:
            page = StaticPage.objects.get(key=key)
            return Response({'title': page.title, 'content': page.content})
        except StaticPage.DoesNotExist:
            return Response({'title': '', 'content': ''})
'''
    with open(views_path, 'w', encoding='utf-8') as f:
        f.write(views)
    print("✓ views اضافه شدند")

# ─── بررسی config/urls.py ────────────────────────────────────
with open('config/urls.py', encoding='utf-8') as f:
    urls = f.read()

print("api/core/ in urls:", 'api/core/' in urls)

if 'api/core/' not in urls:
    urls = urls.replace(
        'path("api/education/"',
        'path("api/core/", include("apps.core.urls")),\n    path("api/education/"'
    )
    with open('config/urls.py', 'w', encoding='utf-8') as f:
        f.write(urls)
    print("✓ api/core/ به config/urls.py اضافه شد")

import subprocess, sys
r = subprocess.run([sys.executable, 'manage.py', 'check', '--verbosity=0'],
                   capture_output=True, text=True)
print("✓ check ok" if r.returncode == 0 else r.stderr[-300:])
print("restart server")
