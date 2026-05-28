"""
python setup_logo.py
اضافه کردن آپلود لوگو به backend و نمایش در header
"""
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

# ─── 1. views.py ──────────────────────────────────────────────
views_path = os.path.join('apps', 'core', 'views.py')
with open(views_path, encoding='utf-8') as f:
    content = f.read()

if 'IsAuthenticated' not in content:
    content = content.replace(
        'from rest_framework.permissions import AllowAny',
        'from rest_framework.permissions import AllowAny, IsAuthenticated'
    )

if 'LogoUploadView' not in content:
    content += '''

class LogoUploadView(APIView):
    """POST /api/core/settings/logo/ — آپلود لوگو"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not request.user.is_staff:
            return Response({'error': 'دسترسی ندارید'}, status=403)
        logo = request.FILES.get('logo')
        if not logo:
            return Response({'error': 'فایل ارسال نشده'}, status=400)
        s = SiteSettings.get_instance()
        s.site_logo = logo
        s.save()
        logo_url = request.build_absolute_uri(s.site_logo.url) if s.site_logo else None
        return Response({'logo_url': logo_url})
'''
    with open(views_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("✓ LogoUploadView اضافه شد")

# ─── 2. urls.py ───────────────────────────────────────────────
with open(os.path.join('apps', 'core', 'urls.py'), 'w', encoding='utf-8') as f:
    f.write("""from django.urls import path
from . import views

urlpatterns = [
    path('settings/', views.SiteSettingsView.as_view()),
    path('settings/logo/', views.LogoUploadView.as_view()),
    path('pages/<str:key>/', views.StaticPageView.as_view()),
]
""")
print("✓ URLs آپدیت شد")

# ─── 3. SiteSettingsView — اضافه کردن full URL لوگو ──────────
with open(views_path, encoding='utf-8') as f:
    content = f.read()

# آپدیت site_logo در response
old = "            'site_logo': s.site_logo.url if s.site_logo else None,"
new = "            'site_logo': request.build_absolute_uri(s.site_logo.url) if s.site_logo else None,"
if old in content and 'build_absolute_uri' not in content:
    content = content.replace(old, new)
    with open(views_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("✓ site_logo URL کامل شد")

import subprocess, sys
r = subprocess.run([sys.executable, 'manage.py', 'check', '--verbosity=0'],
                   capture_output=True, text=True)
print("✓ check ok" if r.returncode == 0 else r.stderr[-300:])
print("restart server")
