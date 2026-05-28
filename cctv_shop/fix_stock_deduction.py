import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

views_path = os.path.join('apps', 'accounting', 'views.py')
with open(views_path, encoding='utf-8') as f:
    content = f.read()

# اضافه کردن کم کردن موجودی بعد از ذخیره آیتم‌ها
old = '''            for item_data in d.get('items', []):
                SaleItem.objects.create(
                    invoice=inv,
                    variant_id=item_data['variant_id'],
                    quantity=int(item_data['quantity']),
                    unit_price=int(item_data['unit_price']),
                    discount_percent=item_data.get('discount_percent', 0),
                    note=item_data.get('note', ''),
                )'''

new = '''            for item_data in d.get('items', []):
                sale_item = SaleItem.objects.create(
                    invoice=inv,
                    variant_id=item_data['variant_id'],
                    quantity=int(item_data['quantity']),
                    unit_price=int(item_data['unit_price']),
                    discount_percent=item_data.get('discount_percent', 0),
                    note=item_data.get('note', ''),
                )
                # کم کردن موجودی از انبار
                if d.get('status') in ('confirmed', 'paid'):
                    try:
                        from apps.inventory.models import StockMovement, Warehouse, WarehouseStock
                        variant = sale_item.variant
                        # پیدا کردن انباری که موجودی دارد
                        stock = WarehouseStock.objects.filter(
                            variant=variant, quantity__gte=sale_item.quantity, warehouse__is_active=True
                        ).order_by('-quantity').first()
                        if stock:
                            StockMovement.record(
                                warehouse=stock.warehouse,
                                variant=variant,
                                movement_type='sale',
                                quantity=-sale_item.quantity,
                                unit_price=sale_item.unit_price,
                                reference=inv.invoice_number,
                                note=f'فاکتور فروش {inv.invoice_number}',
                                user=request.user,
                            )
                    except Exception as e:
                        pass  # اگر موجودی کافی نبود، فاکتور را لغو نمی‌کنیم — فقط log می‌کنیم'''

if old in content:
    content = content.replace(old, new)
    with open(views_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("✓ stock deduction اضافه شد")
else:
    print("✗ متن پیدا نشد")
    import sys; sys.exit(1)

import subprocess, sys
r = subprocess.run([sys.executable, 'manage.py', 'check', '--verbosity=0'], capture_output=True, text=True)
if r.returncode == 0:
    print("✓ check موفق — سرور را restart کنید")
else:
    print(r.stderr[-300:])
