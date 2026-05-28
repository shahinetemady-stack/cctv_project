import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

views_path = os.path.join('apps', 'accounting', 'views.py')
with open(views_path, encoding='utf-8') as f:
    content = f.read()

old = '''                # کم کردن موجودی از انبار
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
                    logging.getLogger(__name__).warning(f'stock deduction failed: {e}')'''

new = '''                # کم کردن موجودی از انبار
                try:
                    from apps.inventory.models import StockMovement, WarehouseStock
                    from apps.catalog.models import ProductVariant
                    qty = int(item_d['quantity'])
                    variant_id = int(item_d['variant_id'])
                    stock = WarehouseStock.objects.filter(
                        variant_id=variant_id,
                        warehouse__is_active=True,
                        quantity__gt=0
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
                    else:
                        variant_obj = ProductVariant.objects.get(id=variant_id)
                        if variant_obj.stock_quantity >= qty:
                            variant_obj.stock_quantity -= qty
                            variant_obj.save(update_fields=['stock_quantity'])
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).warning(f'stock deduction failed: {e}')'''

if old in content:
    content = content.replace(old, new)
    with open(views_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("fixed")
else:
    print("not found")
