import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

# بررسی migration
migration_path = os.path.join('apps', 'orders', 'migrations', '0007_order_tracking_fields.py')
with open(migration_path, encoding='utf-8') as f:
    content = f.read()

print("=== migration فعلی ===")
print(content)
