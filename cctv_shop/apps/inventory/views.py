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
