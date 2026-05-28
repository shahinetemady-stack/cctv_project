"""
python add_stock_movement_api.py
اجرا در پوشه cctv_shop
اضافه کردن endpoint ثبت حرکت موجودی
"""
import os, sys

# ─── 1. آپدیت views.py ───────────────────────────────────────
views_path = os.path.join('apps', 'inventory', 'views.py')
with open(views_path, encoding='utf-8') as f:
    content = f.read()

if 'StockMovementCreateView' in content:
    print("StockMovementCreateView قبلاً اضافه شده.")
else:
    new_view = '''

class StockMovementCreateView(APIView):
    """
    POST /api/inventory/movements/
    ثبت ورود / خروج / تعدیل موجودی
    """
    permission_classes = [IsAdminUser]

    def post(self, request):
        from django.db import transaction
        data = request.data

        # اعتبارسنجی
        required = ['variant_id', 'warehouse_id', 'movement_type', 'quantity']
        for field in required:
            if not data.get(field):
                return Response({'error': f'فیلد {field} الزامی است'}, status=400)

        try:
            variant_id   = int(data['variant_id'])
            warehouse_id = int(data['warehouse_id'])
            quantity     = int(data['quantity'])
            movement_type = data['movement_type']
            unit_price   = int(data.get('unit_price') or 0)
            reference    = data.get('reference', '')
            note         = data.get('note', '')
        except (ValueError, TypeError) as e:
            return Response({'error': f'مقدار نامعتبر: {e}'}, status=400)

        # نوع حرکت معتبر
        valid_types = ['purchase', 'sale', 'transfer_in', 'transfer_out', 'adjustment', 'return']
        if movement_type not in valid_types:
            return Response({'error': f'نوع حرکت نامعتبر. مقادیر مجاز: {valid_types}'}, status=400)

        # برای خروج، quantity باید منفی باشد
        if movement_type in ['sale', 'transfer_out'] and quantity > 0:
            quantity = -quantity

        try:
            from .models import Warehouse, WarehouseStock
            from apps.catalog.models import ProductVariant

            warehouse = Warehouse.objects.get(id=warehouse_id, is_active=True)
            variant   = ProductVariant.objects.get(id=variant_id, is_active=True)

            movement = StockMovement.record(
                warehouse=warehouse,
                variant=variant,
                movement_type=movement_type,
                quantity=quantity,
                unit_price=unit_price,
                reference=reference,
                note=note,
                user=request.user,
            )
            return Response({
                'success': True,
                'id': movement.id,
                'balance_after': movement.balance_after,
                'message': f'موجودی با موفقیت ثبت شد. موجودی فعلی: {movement.balance_after}',
            }, status=201)

        except Warehouse.DoesNotExist:
            return Response({'error': 'انبار یافت نشد'}, status=404)
        except ProductVariant.DoesNotExist:
            return Response({'error': 'محصول یافت نشد'}, status=404)
        except ValueError as e:
            return Response({'error': str(e)}, status=400)
        except Exception as e:
            return Response({'error': f'خطای سرور: {e}'}, status=500)


class AdminStockView(APIView):
    """
    GET /api/inventory/admin-stock/<variant_id>/
    موجودی همه انبارها برای ادمین (شامل انبارهای غیرعمومی)
    """
    permission_classes = [IsAdminUser]

    def get(self, request, variant_id):
        stocks = WarehouseStock.objects.filter(
            variant_id=variant_id,
            warehouse__is_active=True,
        ).select_related('warehouse')
        data = [{'warehouse': s.warehouse.name, 'warehouse_id': s.warehouse.id, 'quantity': s.quantity} for s in stocks]
        return Response({'total': sum(s.quantity for s in stocks), 'stocks': data})
'''
    content += new_view
    with open(views_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("✓ StockMovementCreateView و AdminStockView اضافه شد.")

# ─── 2. آپدیت urls.py ────────────────────────────────────────
urls_path = os.path.join('apps', 'inventory', 'urls.py')
with open(urls_path, encoding='utf-8') as f:
    urls_content = f.read()

new_urls = []
if 'movements/' not in urls_content:
    new_urls.append("    path('movements/', views.StockMovementCreateView.as_view(), name='stock-movement-create'),")
if 'admin-stock/' not in urls_content:
    new_urls.append("    path('admin-stock/<int:variant_id>/', views.AdminStockView.as_view(), name='admin-stock'),")

if new_urls:
    # پیدا کردن آخر urlpatterns
    urls_content = urls_content.rstrip()
    if urls_content.endswith(']'):
        insert = '\n'.join(new_urls)
        urls_content = urls_content[:-1] + ',\n' + insert + '\n]'
    else:
        urls_content += '\n' + '\n'.join(new_urls)
    with open(urls_path, 'w', encoding='utf-8') as f:
        f.write(urls_content)
    print("✓ URL های جدید اضافه شد.")
else:
    print("URL ها قبلاً اضافه شده.")

# ─── 3. چک ───────────────────────────────────────────────────
import subprocess
r = subprocess.run([sys.executable, 'manage.py', 'check', '--verbosity=0'],
                   capture_output=True, text=True)
if r.returncode == 0:
    print("✓ check موفق — سرور را restart کنید")
else:
    print("خطا:")
    print((r.stdout + r.stderr)[-800:])
