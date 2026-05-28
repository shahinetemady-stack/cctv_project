import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

views_path = os.path.join('apps', 'accounting', 'views.py')
with open(views_path, encoding='utf-8') as f:
    content = f.read()

old = """for item_d in d.get('items', []):
                SaleItem.objects.create(
                    invoice=inv,
                    variant_id=item_d['variant_id'],
                    quantity=int(item_d['quantity']),
                    unit_price=int(item_d['unit_price']),
                    discount_percent=item_d.get('discount_percent', 0),"""

new = """for item_d in d.get('items', []):
                sale_item = SaleItem.objects.create(
                    invoice=inv,
                    variant_id=item_d['variant_id'],
                    quantity=int(item_d['quantity']),
                    unit_price=int(item_d['unit_price']),
                    discount_percent=item_d.get('discount_percent', 0),"""

if old in content:
    content = content.replace(old, new)
    print("✓ SaleItem → sale_item")
else:
    print("✗ not found, trying with note field")
    # شاید note هم داره
    idx = content.find("for item_d in d.get('items', []):")
    print(repr(content[idx:idx+400]))

# اضافه کردن کم کردن موجودی بعد از SaleItem.objects.create
# پیدا کردن انتهای create block
old2 = """                    discount_percent=item_d.get('discount_percent', 0),
                    note=item_d.get('note', ''),
                )"""

new2 = """                    discount_percent=item_d.get('discount_percent', 0),
                    note=item_d.get('note', ''),
                )
                # کم کردن موجودی از انبار
                try:
                    from apps.inventory.models import StockMovement, WarehouseStock
                    qty = int(item_d['quantity'])
                    variant_id = int(item_d['variant_id'])
                    stock = WarehouseStock.objects.filter(
                        variant_id=variant_id,
                        quantity__gte=qty,
                        warehouse__is_active=True
                    ).order_by('-quantity').first()
                    if stock:
                        StockMovement.record(
                            warehouse=stock.warehouse,
                            variant=stock.variant,
                            movement_type='sale',
                            quantity=-qty,
                            unit_price=int(item_d.get('unit_price', 0)),
                            reference=inv.invoice_number,
                            note=f'فاکتور فروش {inv.invoice_number}',
                            user=request.user,
                        )
                except Exception as stock_err:
                    import logging
                    logging.getLogger(__name__).warning(f'stock deduction failed: {stock_err}')"""

if old2 in content:
    content = content.replace(old2, new2)
    print("✓ stock deduction اضافه شد")
else:
    print("✗ create block end not found")
    idx = content.find("discount_percent=item_d.get('discount_percent', 0),")
    print(repr(content[idx:idx+200]))

with open(views_path, 'w', encoding='utf-8') as f:
    f.write(content)

import subprocess, sys
r = subprocess.run([sys.executable, 'manage.py', 'check', '--verbosity=0'], capture_output=True, text=True)
if r.returncode == 0:
    print("✓ check موفق — سرور را restart کنید")
else:
    print(r.stderr[-300:])
