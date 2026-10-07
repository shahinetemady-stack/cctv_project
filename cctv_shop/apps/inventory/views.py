from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAdminUser
from django.db.models import Sum, Q
from .models import Warehouse, WarehouseStock, StockMovement, StockTransfer
from apps.core.utils import user_label


# ─── RBAC helpers ────────────────────────────────────────────

def _has_perm(user, code):
    """چک دسترسی RBAC پرسنل — سوپریوزر همیشه True"""
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    sp = getattr(user, 'staff_profile', None)
    return bool(sp and sp.is_active and sp.has_perm(code))


def _has_any_perm(user, *codes):
    return any(_has_perm(user, c) for c in codes)


def _forbidden(msg='شما دسترسی لازم برای این عملیات را ندارید'):
    return Response({'error': msg}, status=403)


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
        if not _has_perm(request.user, 'kardex_view'):
            return _forbidden()
        from apps.accounting.models import SaleInvoice, PurchaseInvoice
        warehouse_id = request.query_params.get("warehouse")
        qs = StockMovement.objects.filter(variant_id=variant_id).select_related("warehouse", "created_by")
        if warehouse_id:
            qs = qs.filter(warehouse_id=warehouse_id)
        movements = list(qs[:200])

        # نام طرف حساب از روی شماره فاکتور: فروش → مشتری، خرید → تأمین‌کننده (کوئری دسته‌ای)
        # مرجع خرید گاهی invoice_number خالی است و id فاکتور ذخیره شده — هر دو چک می‌شود
        refs = {m.reference for m in movements if m.reference}
        numeric_ids = [int(r) for r in refs if str(r).isdigit()]
        sale_names = {
            s.invoice_number: (s.customer_name or str(s.customer))
            for s in SaleInvoice.objects.filter(invoice_number__in=refs).select_related("customer")
        }
        purchase_names = {}
        for p in PurchaseInvoice.objects.filter(
            Q(invoice_number__in=refs) | Q(id__in=numeric_ids)
        ).select_related("supplier"):
            if p.invoice_number:
                purchase_names[p.invoice_number] = p.supplier.name
            purchase_names[str(p.id)] = p.supplier.name

        data = [{
            "date": m.created_at.strftime("%Y-%m-%d %H:%M"),
            "warehouse": m.warehouse.name,
            "type": m.get_movement_type_display(),
            "quantity": m.quantity,
            "balance_after": m.balance_after,
            "unit_price": m.unit_price,
            "reference": m.reference,
            "counterparty": sale_names.get(m.reference) or purchase_names.get(m.reference) or "—",
            "created_by": user_label(m.created_by),
        } for m in movements]
        return Response(data)


class WarehouseSummaryView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        if not _has_any_perm(request.user, 'warehouses_view', 'kardex_view', 'purchase_view', 'products_edit', 'categories_view'):
            return _forbidden()
        warehouses = Warehouse.objects.filter(is_active=True)
        result = []
        for w in warehouses:
            total = w.stocks.aggregate(t=Sum("quantity"))["t"] or 0
            result.append({
                "id": w.id, "name": w.name, "code": w.code,
                "type": w.get_warehouse_type_display(),
                "warehouse_type": w.warehouse_type,
                "is_public": w.is_public, "total_quantity": total,
                "address": w.address,
            })
        return Response(result)

    def post(self, request):
        """ساخت انبار جدید"""
        if not _has_any_perm(request.user, 'warehouses_view', 'kardex_view', 'purchase_view', 'products_edit', 'categories_view'):
            return _forbidden()
        data = request.data
        name = (data.get("name") or "").strip()
        code = (data.get("code") or "").strip()
        warehouse_type = data.get("warehouse_type") or ""
        if not name or not code:
            return Response({"error": "نام و کد انبار الزامی است"}, status=400)
        if warehouse_type not in Warehouse.Type.values:
            return Response({"error": "نوع انبار نامعتبر است"}, status=400)
        if Warehouse.objects.filter(code=code).exists():
            return Response({"error": "این کد انبار قبلاً ثبت شده است"}, status=400)
        w = Warehouse.objects.create(
            name=name, code=code, warehouse_type=warehouse_type,
            is_public=bool(data.get("is_public")),
            address=data.get("address", ""),
        )
        return Response({
            "id": w.id, "name": w.name, "code": w.code,
            "type": w.get_warehouse_type_display(),
            "warehouse_type": w.warehouse_type,
            "is_public": w.is_public, "total_quantity": 0,
        }, status=201)


class WarehouseDetailView(APIView):
    """حذف/ویرایش انبار — حذف فقط اگر موجودی و سابقه حرکت نداشته باشد"""
    permission_classes = [IsAdminUser]

    def patch(self, request, pk):
        """ویرایش مشخصات انبار — نام، کد، نوع، نمایش به مشتری، فعال/غیرفعال، آدرس"""
        if not _has_any_perm(request.user, 'warehouses_view', 'kardex_view', 'purchase_view', 'products_edit', 'categories_view'):
            return _forbidden()
        try:
            w = Warehouse.objects.get(pk=pk)
        except Warehouse.DoesNotExist:
            return Response({"error": "انبار یافت نشد"}, status=404)

        data = request.data
        if "name" in data:
            name = (data.get("name") or "").strip()
            if not name:
                return Response({"error": "نام انبار الزامی است"}, status=400)
            w.name = name
        if "code" in data:
            code = (data.get("code") or "").strip()
            if not code:
                return Response({"error": "کد انبار الزامی است"}, status=400)
            if Warehouse.objects.filter(code=code).exclude(pk=w.pk).exists():
                return Response({"error": "این کد انبار قبلاً ثبت شده است"}, status=400)
            w.code = code
        if "warehouse_type" in data:
            if data["warehouse_type"] not in Warehouse.Type.values:
                return Response({"error": "نوع انبار نامعتبر است"}, status=400)
            w.warehouse_type = data["warehouse_type"]
        if "is_public" in data:
            w.is_public = bool(data.get("is_public"))
        if "is_active" in data:
            w.is_active = bool(data.get("is_active"))
        if "address" in data:
            w.address = data.get("address") or ""

        w.save()
        return Response({
            "id": w.id, "name": w.name, "code": w.code,
            "type": w.get_warehouse_type_display(),
            "warehouse_type": w.warehouse_type,
            "is_public": w.is_public, "is_active": w.is_active,
            "address": w.address,
            "total_quantity": w.stocks.aggregate(t=Sum("quantity"))["t"] or 0,
        })

    def delete(self, request, pk):
        if not _has_any_perm(request.user, 'warehouses_view', 'kardex_view', 'purchase_view', 'products_edit', 'categories_view'):
            return _forbidden()
        try:
            w = Warehouse.objects.get(pk=pk)
        except Warehouse.DoesNotExist:
            return Response({"error": "انبار یافت نشد"}, status=404)
        remaining = w.stocks.aggregate(t=Sum("quantity"))["t"] or 0
        if remaining > 0:
            return Response({"error": f"این انبار {remaining} قلم موجودی دارد — ابتدا موجودی را به انبار دیگر منتقل کنید"}, status=400)
        if w.movements.exists() or w.transfers_out.exists() or w.transfers_in.exists():
            return Response({"error": "این انبار سابقه حرکت/انتقال دارد و قابل حذف نیست"}, status=400)
        w.delete()
        return Response({"success": True})


class WarehouseStockListView(APIView):
    """GET /api/inventory/warehouses/<pk>/stocks/ — موجودی اقلام یک انبار"""
    permission_classes = [IsAdminUser]

    def get(self, request, pk):
        if not _has_any_perm(request.user, 'warehouses_view', 'kardex_view', 'purchase_view', 'products_edit', 'categories_view'):
            return _forbidden()
        stocks = (
            WarehouseStock.objects.filter(warehouse_id=pk, quantity__gt=0)
            .select_related("variant__product")
            .order_by("variant__product__name")
        )
        data = [{
            "variant_id": s.variant_id,
            "product_name": s.variant.product.name,
            "variant_name": str(s.variant),
            "sku": s.variant.sku,
            "quantity": s.quantity,
        } for s in stocks]
        return Response(data)


class TransferListCreateView(APIView):
    """
    GET  /api/inventory/transfers/ — آخرین انتقال‌ها
    POST /api/inventory/transfers/ — انتقال کالا بین دو انبار (تکی یا جمعی با items=[{variant_id, quantity}])
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        if not _has_perm(request.user, 'warehouses_view'):
            return _forbidden()
        transfers = StockTransfer.objects.select_related(
            "from_warehouse", "to_warehouse", "variant__product", "transferred_by", "updated_by"
        )[:100]
        data = [{
            "id": t.id,
            "date": t.created_at.strftime("%Y-%m-%d %H:%M"),
            "from_warehouse": t.from_warehouse.name,
            "to_warehouse": t.to_warehouse.name,
            "product_name": t.variant.product.name,
            "sku": t.variant.sku,
            "quantity": t.quantity,
            "status": t.get_status_display(),
            "note": t.note,
            "transferred_by": user_label(t.transferred_by) or "—",
            "updated_by": user_label(t.updated_by),
        } for t in transfers]
        return Response(data)

    def post(self, request):
        if not _has_perm(request.user, 'warehouses_view'):
            return _forbidden()
        from django.db import transaction
        from apps.catalog.models import ProductVariant

        data = request.data
        try:
            from_id  = int(data.get("from_warehouse_id"))
            to_id    = int(data.get("to_warehouse_id"))
        except (TypeError, ValueError):
            return Response({"error": "مقادیر ورودی نامعتبر است"}, status=400)
        note = data.get("note", "")

        if from_id == to_id:
            return Response({"error": "انبار مبدأ و مقصد نمی‌تواند یکی باشد"}, status=400)

        # حالت جمعی: items=[{variant_id, quantity}] — حالت تکی (سازگاری قدیمی): variant_id+quantity
        raw_items = data.get("items")
        if raw_items is None:
            raw_items = [{"variant_id": data.get("variant_id"), "quantity": data.get("quantity")}]
        items = []
        seen = set()
        for it in raw_items:
            try:
                vid = int(it.get("variant_id"))
                qty = int(it.get("quantity"))
            except (TypeError, ValueError, AttributeError):
                return Response({"error": "مقادیر ورودی نامعتبر است"}, status=400)
            if qty <= 0:
                return Response({"error": "تعداد باید بزرگ‌تر از صفر باشد"}, status=400)
            if vid in seen:
                return Response({"error": "یک محصول دوبار در لیست آمده — تعدادش را در همان ردیف اصلاح کنید"}, status=400)
            seen.add(vid)
            items.append((vid, qty))
        if not items:
            return Response({"error": "حداقل یک قلم کالا لازم است"}, status=400)

        try:
            from_w = Warehouse.objects.get(pk=from_id, is_active=True)
            to_w   = Warehouse.objects.get(pk=to_id, is_active=True)
        except Warehouse.DoesNotExist:
            return Response({"error": "انبار یافت نشد"}, status=404)
        variants = {v.id: v for v in ProductVariant.objects.filter(pk__in=seen, is_active=True)}
        missing = seen - set(variants)
        if missing:
            return Response({"error": "محصول یافت نشد"}, status=404)

        try:
            with transaction.atomic():
                # همه یا هیچ‌کدام — اگر موجودی یک قلم کافی نباشد هیچ انتقالی ثبت نمی‌شود
                transfer_ids = []
                for vid, qty in items:
                    variant = variants[vid]
                    transfer = StockTransfer.objects.create(
                        from_warehouse=from_w, to_warehouse=to_w,
                        variant=variant, quantity=qty, note=note,
                        transferred_by=request.user, status=StockTransfer.Status.DONE,
                    )
                    transfer_ids.append(transfer.id)
                    ref = f"TR-{transfer.id}"
                    StockMovement.record(
                        warehouse=from_w, variant=variant,
                        movement_type="transfer_out", quantity=-qty,
                        reference=ref, note=note, user=request.user,
                    )
                    StockMovement.record(
                        warehouse=to_w, variant=variant,
                        movement_type="transfer_in", quantity=qty,
                        reference=ref, note=note, user=request.user,
                    )
        except ValueError as e:
            return Response({"error": str(e)}, status=400)

        total_qty = sum(q for _, q in items)
        if len(items) == 1:
            msg = f"{total_qty} عدد از «{from_w.name}» به «{to_w.name}» منتقل شد"
        else:
            msg = f"{len(items)} قلم کالا (مجموع {total_qty} عدد) از «{from_w.name}» به «{to_w.name}» منتقل شد"
        return Response({"success": True, "ids": transfer_ids, "count": len(items),
                         "message": msg}, status=201)


class StockMovementCreateView(APIView):
    """
    POST /api/inventory/movements/
    ثبت ورود / خروج / تعدیل موجودی
    """
    permission_classes = [IsAdminUser]

    def post(self, request):
        if not _has_perm(request.user, 'kardex_edit'):
            return _forbidden()
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

        # نوع حرکت معتبر — ثبت دستی فقط برای اول دوره و تعدیل است.
        # خرید/فروش/مرجوعی باید از فاکتورهایشان ثبت شوند تا انبار و حسابداری هماهنگ بمانند؛
        # انتقال هم فقط دوطرفه از مسیر /api/inventory/transfers/
        valid_types = ['opening', 'adjustment']
        if movement_type not in valid_types:
            if movement_type == 'purchase':
                return Response({'error': 'خرید را از «فاکتور خرید» ثبت کنید تا کاردکس و حسابداری با هم به‌روز شوند'}, status=400)
            if movement_type == 'sale':
                return Response({'error': 'فروش را از «فاکتور فروش» ثبت کنید تا کاردکس و حسابداری با هم به‌روز شوند'}, status=400)
            if movement_type == 'return':
                return Response({'error': 'مرجوعی را از «فاکتور مرجوعی» ثبت کنید تا کاردکس و حسابداری با هم به‌روز شوند'}, status=400)
            if movement_type in ('transfer_in', 'transfer_out'):
                return Response({'error': 'انتقال بین انبارها را از بخش «انتقال کالا» (صفحه انبارها) ثبت کنید تا هم از مبدأ کم و هم به مقصد اضافه شود'}, status=400)
            return Response({'error': f'نوع حرکت نامعتبر. مقادیر مجاز: {valid_types}'}, status=400)

        # تعدیل موجودی علامت‌دار است: مثبت = افزایش (اضافه شمارش)، منفی = کاهش (کسری شمارش)

        # برای خروج، quantity باید منفی باشد
        if movement_type in ['sale', 'transfer_out'] and quantity > 0:
            quantity = -quantity

        # موجودی اول دوره همیشه ورودی (مثبت) است
        if movement_type == 'opening' and quantity < 0:
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
            # سینک موجودی کل واریانت — record فقط WarehouseStock را تغییر می‌دهد و
            # صفحه‌های مدیریت محصولات/لیست قیمت از stock_quantity واریانت می‌خوانند
            variant.stock_quantity = max(0, variant.stock_quantity + quantity)
            variant.save(update_fields=['stock_quantity', 'updated_at'])
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
        if not _has_perm(request.user, 'kardex_view'):
            return _forbidden()
        stocks = WarehouseStock.objects.filter(
            variant_id=variant_id,
            warehouse__is_active=True,
        ).select_related('warehouse')
        data = [{'warehouse': s.warehouse.name, 'warehouse_id': s.warehouse.id, 'quantity': s.quantity} for s in stocks]
        return Response({'total': sum(s.quantity for s in stocks), 'stocks': data})
