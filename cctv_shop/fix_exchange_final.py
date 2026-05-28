import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.catalog.models import ExchangeRateSetting
fields = [f.name for f in ExchangeRateSetting._meta.get_fields()]
print("Fields:", fields)

# بازنویسی کامل ExchangeRateSettingAdmin
admin_path = os.path.join('apps', 'catalog', 'admin.py')
with open(admin_path, encoding='utf-8') as f:
    content = f.read()

# پیدا کردن و حذف کلاس قدیمی
import re
pattern = r'\n@admin\.register\(ExchangeRateSetting\).*?(?=\n@admin|\nclass |\Z)'
match = re.search(pattern, content, re.DOTALL)
if match:
    print("Found old class, replacing...")
    new_class = f'''
@admin.register(ExchangeRateSetting)
class ExchangeRateSettingAdmin(admin.ModelAdmin):
    list_display = {[f for f in fields if not f.startswith('_') and f not in ['id']]}
'''
    content = content[:match.start()] + new_class + content[match.end():]
    # ساده‌تر — فقط id را نشان بده
    content = content[:match.start()] + '''
@admin.register(ExchangeRateSetting)
class ExchangeRateSettingAdmin(admin.ModelAdmin):
    pass
''' + content[match.end():]
    with open(admin_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("✓ Fixed")

import subprocess, sys
r = subprocess.run([sys.executable, 'manage.py', 'check', '--verbosity=0'],
                   capture_output=True, text=True)
print("✓ check ok" if r.returncode == 0 else r.stderr[-400:])
