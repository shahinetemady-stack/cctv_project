import os

admin_path = os.path.join('apps', 'catalog', 'admin.py')
with open(admin_path, encoding='utf-8') as f:
    content = f.read()

# حذف created_at و updated_at از ExchangeRateSettingAdmin
content = content.replace(
    "readonly_fields = ['updated_at', 'created_at']",
    "readonly_fields = []"
)
content = content.replace(
    "list_display = ['currency', 'rate_per_unit', 'updated_at']",
    "list_display = ['currency', 'rate_per_unit']"
)

with open(admin_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("✓ ExchangeRateSettingAdmin درست شد")

import subprocess, sys
r = subprocess.run([sys.executable, 'manage.py', 'check', '--verbosity=0'],
                   capture_output=True, text=True)
print("✓ check موفق" if r.returncode == 0 else r.stderr[-400:])
print("سرور را restart کنید")
