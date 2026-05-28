from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAdminUser
from django.db.models import Sum
from .models import Warehouse, WarehouseStock, StockMovement


class PublicStockView(APIView):
    permission_classes = [AllowAny]
    def get(self, request, variant_id):
        stocks = WarehouseStock.objects.filter(
            variant_id=variant_id, warehouse__is_public=True, warehouse__is_active=True,
        ).select_related("warehouse")
        data = [{"warehouse": s.warehouse.name, "quantity": s.quantity} for s in stocks]
        return Response({"total": sum(s.quantity for s in stocks), "stocks": data})


class KardexView(APIView):
    permission_classes = [IsAdminUser]
    def get(self, request, variant_id):
        warehouse_id = request.query_params.get("warehouse")
        qs = StockMovement.objects.filter(variant_id=variant_id).select_related("warehouse")
        if warehouse_id:
            qs = qs.filter(warehouse_id=warehouse_id)
        data = [{
            "date": m.created_at.strftime("%Y-%m-%d %H:%M"),
            "warehouse": m.warehouse.name,
            "type": m.get_movement_type_display(),
            "quantity": m.quantity,
            "balance_after": m.balance_after,
            "unit_price": m.unit_price,
            "reference": m.reference,
        } for m in qs[:200]]
        return Response(data)


class WarehouseSummaryView(APIView):
    permission_classes = [IsAdminUser]
    def get(self, request):
        warehouses = Warehouse.objects.filter(is_active=True)
        result = []
        for w in warehouses:
            total = w.stocks.aggregate(t=Sum("quantity"))["t"] or 0
            result.append({
                "id": w.id, "name": w.name, "code": w.code,
                "type": w.get_warehouse_type_display(),
                "is_public": w.is_public, "total_quantity": total,
            })
        return Response(result)


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
