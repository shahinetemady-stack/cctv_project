import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

admin_path = os.path.join('apps', 'orders', 'admin.py')
with open(admin_path, encoding='utf-8') as f:
    content = f.read()

# پیدا کردن OrderAdmin و نمایش fieldsets آن
idx = content.find('class OrderAdmin')
if idx >= 0:
    print(content[idx:idx+1500])
