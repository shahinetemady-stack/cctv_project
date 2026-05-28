import os

admin_path = os.path.join('apps', 'catalog', 'admin.py')
with open(admin_path, encoding='utf-8') as f:
    content = f.read()

# نمایش ExchangeRateSettingAdmin
idx = content.find('ExchangeRateSettingAdmin')
if idx >= 0:
    start = content.rfind('\n@', 0, idx)
    end = content.find('\n@', idx+1)
    if end < 0:
        end = content.find('\nclass ', idx+1)
    if end < 0:
        end = idx + 500
    print("Found:")
    print(content[start:end])
    print("---")

    # جایگزینی کل کلاس
    old_class = content[start:end]
    new_class = '''

@admin.register(ExchangeRateSetting)
class ExchangeRateSettingAdmin(admin.ModelAdmin):
    list_display = ['currency', 'rate_per_unit']
    readonly_fields = []
'''
    content = content[:start] + new_class + content[end:]
    with open(admin_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("✓ Fixed")
else:
    print("ExchangeRateSettingAdmin not found")

import subprocess, sys
r = subprocess.run([sys.executable, 'manage.py', 'check', '--verbosity=0'],
                   capture_output=True, text=True)
print("✓ check ok" if r.returncode == 0 else r.stderr[-400:])
