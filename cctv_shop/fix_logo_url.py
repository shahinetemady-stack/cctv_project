import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

views_path = os.path.join('apps', 'core', 'views.py')
with open(views_path, encoding='utf-8') as f:
    content = f.read()

# درست کردن URL لوگو — از نسبی به کامل
old = "            'site_logo': s.site_logo.url if s.site_logo else None,"
new = "            'site_logo': request.build_absolute_uri(s.site_logo.url) if s.site_logo else None,"

if old in content:
    content = content.replace(old, new)
    with open(views_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("✓ site_logo URL کامل شد")
elif 'build_absolute_uri' in content:
    print("✓ قبلاً درست شده بود")
else:
    # پیدا کردن خط site_logo
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if 'site_logo' in line:
            print(f"خط {i+1}: {line.strip()}")
    print("خط مناسب پیدا نشد — دستی درست کنید")

import subprocess, sys
r = subprocess.run([sys.executable, 'manage.py', 'check', '--verbosity=0'],
                   capture_output=True, text=True)
print("✓ ok" if r.returncode == 0 else r.stderr[-200:])
print("restart server")
