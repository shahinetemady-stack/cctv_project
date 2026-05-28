import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

views_path = os.path.join('apps', 'accounting', 'views.py')
with open(views_path, encoding='utf-8') as f:
    content = f.read()

old = """                    discount_percent=item_d.get('discount_percent', 0),
                )

            return Response({"""

new = """                    discount_percent=item_d.get('discount_percent', 0),
                )
                # کم کردن موجودی از انبار
                try:
                    from apps.inventory.models import StockMovement, WarehouseStock
                    qty = int(item_d['quantity'])
                    stock = WarehouseStock.objects.filter(
                        variant_id=int(item_d['variant_id']),
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
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).warning(f'stock deduction failed: {e}')

            return Response({"""

if old in content:
    content = content.replace(old, new)
    with open(views_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("✓ stock deduction اضافه شد")
else:
    print("✗ not found")
    idx = content.find("discount_percent=item_d.get('discount_percent', 0),")
    print(repr(content[idx:idx+100]))

import subprocess, sys
r = subprocess.run([sys.executable, 'manage.py', 'check', '--verbosity=0'], capture_output=True, text=True)
print("✓ check موفق" if r.returncode == 0 else r.stderr[-200:])
