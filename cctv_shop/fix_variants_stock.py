import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

views_path = os.path.join('apps', 'catalog', 'views.py')
with open(views_path, encoding='utf-8') as f:
    content = f.read()

old = '''        data = []
        for v in qs:
            data.append({
                'id': v.id,
                'sku': v.sku,
                'name': v.product.name + (' - ' + v.name_suffix if v.name_suffix else ''),
                'product_name': v.product.name,
                'product_id': v.product.id,
                'category': v.product.category.name if v.product.category else '',
                'stock_quantity': v.stock_quantity,
            })
        return Response(data)'''

new = '''        from apps.inventory.models import WarehouseStock
        from django.db.models import Sum

        # موجودی واقعی از WarehouseStock
        stock_map = {}
        for ws in WarehouseStock.objects.filter(warehouse__is_active=True).values('variant_id').annotate(total=Sum('quantity')):
            stock_map[ws['variant_id']] = ws['total']

        data = []
        for v in qs:
            # موجودی واقعی: اول از WarehouseStock، اگر نبود از stock_quantity
            real_stock = stock_map.get(v.id, v.stock_quantity)
            data.append({
                'id': v.id,
                'sku': v.sku,
                'name': v.product.name + (' - ' + v.name_suffix if v.name_suffix else ''),
                'product_name': v.product.name,
                'product_id': v.product.id,
                'category': v.product.category.name if v.product.category else '',
                'stock_quantity': real_stock,
            })
        return Response(data)'''

if old in content:
    content = content.replace(old, new)
    with open(views_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("✓ variants endpoint اصلاح شد")
else:
    print("✗ متن پیدا نشد")
    idx = content.find("'stock_quantity': v.stock_quantity")
    print(repr(content[idx-200:idx+100]))

import subprocess, sys
r = subprocess.run([sys.executable, 'manage.py', 'check', '--verbosity=0'], capture_output=True, text=True)
print("✓ check موفق" if r.returncode == 0 else r.stderr[-200:])
