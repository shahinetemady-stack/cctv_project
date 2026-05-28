import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

# ─── آپدیت catalog/admin.py ──────────────────────────────────
admin_path = os.path.join('apps', 'catalog', 'admin.py')
with open(admin_path, encoding='utf-8') as f:
    content = f.read()

print("=== محتوای فعلی admin.py ===")
print(content[:500])
print("...")

# اضافه کردن filter_horizontal به ProductAdmin
if 'filter_horizontal' not in content:
    # پیدا کردن ProductAdmin
    if 'class ProductAdmin' in content:
        old = 'class ProductAdmin(admin.ModelAdmin):'
        new = '''class ProductAdmin(admin.ModelAdmin):
    filter_horizontal = ['compatible_with']
    search_fields = ['name', 'model_number', 'sensor_name']'''
        
        if old in content and 'filter_horizontal' not in content:
            content = content.replace(old, new)
            with open(admin_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print("✓ filter_horizontal اضافه شد")
        else:
            print("ProductAdmin پیدا نشد یا قبلاً filter_horizontal دارد")
    else:
        # اضافه کردن ProductAdmin جدید
        content += '''

from apps.catalog.models import Product, ProductVariant, Category

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display  = ['name', 'category', 'model_number', 'sensor_name', 'voltage', 'is_active']
    list_filter   = ['category', 'is_active', 'is_featured']
    search_fields = ['name', 'model_number', 'sensor_name', 'board_name']
    filter_horizontal = ['compatible_with']
    prepopulated_fields = {'slug': ('name',)}
    fieldsets = (
        ('اطلاعات اصلی', {'fields': ('name', 'slug', 'category', 'brand', 'model_number', 'is_active', 'is_featured')}),
        ('مشخصات برد', {'fields': ('board_name', 'board_system', 'board_resolution', 'sensor_name', 'sensor_size', 'ai_processor'), 'classes': ('collapse',)}),
        ('مشخصات لنز', {'fields': ('lens_name', 'lens_resolution', 'lens_degree', 'lens_type', 'focal_ratio'), 'classes': ('collapse',)}),
        ('برق', {'fields': ('voltage', 'ampere_output'), 'classes': ('collapse',)}),
        ('سازگاری', {'fields': ('compatible_with',)}),
        ('توضیحات', {'fields': ('description', 'short_description')}),
        ('سئو', {'fields': ('meta_title', 'meta_description', 'keywords'), 'classes': ('collapse',)}),
    )
'''
        with open(admin_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print("✓ ProductAdmin جدید اضافه شد")
else:
    print("✓ filter_horizontal قبلاً موجود بود")

import subprocess, sys
r = subprocess.run([sys.executable, 'manage.py', 'check', '--verbosity=0'], capture_output=True, text=True)
print("✓ check موفق" if r.returncode == 0 else r.stderr[-300:])
print("\nحالا در Django Admin می‌توانید سازگاری بین محصولات را تعریف کنید:")
print("http://127.0.0.1:8000/admin/catalog/product/")
