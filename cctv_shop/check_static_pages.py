import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

# بررسی وضعیت
from django.contrib import admin
from apps.core.models import SiteSettings
print("SiteSettings registered:", SiteSettings in admin.site._registry)

try:
    from apps.core.models import StaticPage
    print("StaticPage model exists:", True)
    print("StaticPage registered:", StaticPage in admin.site._registry)
except Exception as e:
    print("StaticPage error:", e)

# بررسی migration
import subprocess, sys
r = subprocess.run([sys.executable, 'manage.py', 'showmigrations', 'core'],
                   capture_output=True, text=True)
print(r.stdout)
