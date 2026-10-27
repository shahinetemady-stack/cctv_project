"""
apps/production/views.py
────────────────────────
API امور تولید:
  GET/POST /api/production/recipes/          لیست/ساخت محصول نهایی + دستوره مونتاژ
  PUT      /api/production/recipes/<id>/     جایگزینی آیتم‌های دستوره (BOM)
  GET/POST /api/production/orders/           تاریخچه / اجرای دستور مونتاژ
  POST     /api/production/orders/<id>/cancel/  برگشت دستور مونتاژ
"""
from decimal import Decimal

from django.db import transaction
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.models import Category, ExchangeRateSetting, Product, ProductVariant
from apps.catalog.views import _has_staff_perm
from apps.inventory.models import StockMovement, Warehouse, WarehouseStock, get_variant_cost_irr

from .models import AssemblyOrder, AssemblyRecipe, AssemblyRecipeItem


def _forbidden():
    return Response({"error": "شما دسترسی لازم برای این عملیات را ندارید"}, status=403)


def _default_warehouse():
    """انبار پیش‌فرض مونتاژ — نوع assembly، وگرنه اولین انبار فعال."""
    return (Warehouse.objects.filter(is_active=True, warehouse_type=Warehouse.Type.ASSEMBLY).first()
            or Warehouse.objects.filter(is_active=True).first())


def _recipe_payload(recipe):
    recipe_items = list(recipe.items.select_related("component", "component__product"))
    stock_rows = (WarehouseStock.objects
                  .filter(variant_id__in=[it.component_id for it in recipe_items],
                          warehouse__is_active=True)
                  .values("variant_id", "warehouse_id", "quantity"))
    stock_map = {}
    for row in stock_rows:
        stock_map.setdefault(row["variant_id"], {})[row["warehouse_id"]] = row["quantity"]
    items = []
    for it in recipe_items:
        c = it.component
        items.append({
            "variant_id": c.id,
            "sku": c.sku,
            "name": f"{c.product.name}{' — ' + c.name_suffix if c.name_suffix else ''}",
            "quantity": it.quantity,
            "unit_cost_irr": get_variant_cost_irr(c),
            "stock_quantity": c.stock_quantity,
            "warehouse_stocks": stock_map.get(c.id, {}),
        })
    variant = recipe.product.variants.filter(is_active=True).first()
    return {
        "id": recipe.id,
        "product_id": recipe.product_id,
        "product_name": recipe.product.name,
        "product_slug": recipe.product.slug,
        "category_name": str(recipe.product.category) if recipe.product.category else "",
        "variant_id": variant.id if variant else None,
        "sku": variant.sku if variant else "",
        "stock_quantity": variant.stock_quantity if variant else 0,
        "purchase_price_cny": float(variant.purchase_price_cny) if variant else 0,
        "is_active": recipe.product.is_active,
        "note": recipe.note,
        "items": items,
        "unit_cost_irr": sum(i["unit_cost_irr"] * i["quantity"] for i in items),
    }


class RecipeListView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        if not _has_staff_perm(request.user, "production_view"):
            return _forbidden()
        recipes = (AssemblyRecipe.objects
                   .select_related("product", "product__category")
                   .prefetch_related("items__component__product", "product__variants")
                   .order_by("-created_at"))
        warehouses = [{"id": w.id, "name": w.name, "warehouse_type": w.warehouse_type}
                      for w in Warehouse.objects.filter(is_active=True)]
        default_wh = _default_warehouse()
        return Response({
            "recipes": [_recipe_payload(r) for r in recipes],
            "warehouses": warehouses,
            "default_warehouse_id": default_wh.id if default_wh else None,
            "rate_cny_to_irt": float(ExchangeRateSetting.get_instance().rate_cny_to_irt or 0),
        })

    def post(self, request):
        """ساخت محصول نهایی جدید + رسیپی خالی — SKU اختیاری (پیش‌فرض P-<id>)."""
        if not _has_staff_perm(request.user, "production_manage"):
            return _forbidden()
        d = request.data
        name = (d.get("name") or "").strip()
        if not name:
            return Response({"error": "نام محصول الزامی است"}, status=400)
        category = Category.objects.filter(pk=d.get("category_id"), is_active=True).first()
        if not category:
            return Response({"error": "دسته معتبر نیست"}, status=400)
        sku = (d.get("sku") or "").strip()
        if sku and ProductVariant.objects.filter(sku=sku).exists():
            return Response({"error": f"SKU «{sku}» تکراری است"}, status=400)
        with transaction.atomic():
            product = Product.objects.create(
                name=name, category=category,
                model_number=(d.get("model_number") or "").strip(),
            )
            variant = ProductVariant.objects.create(
                product=product, sku=sku or f"P-{product.id}", purchase_price_cny=0,
            )
            recipe = AssemblyRecipe.objects.create(product=product, note=d.get("note") or "")
        return Response(_recipe_payload(recipe), status=201)


class RecipeDetailView(APIView):
    permission_classes = [IsAdminUser]

    def put(self, request, pk):
        """جایگزینی کامل آیتم‌های BOM — items: [{variant_id, quantity}]"""
        if not _has_staff_perm(request.user, "production_manage"):
            return _forbidden()
        recipe = AssemblyRecipe.objects.filter(pk=pk).first()
        if recipe is None:
            return Response({"error": "دستوره یافت نشد"}, status=404)
        items = request.data.get("items")
        if not isinstance(items, list):
            return Response({"error": "فرمت آیتم‌ها نامعتبر است"}, status=400)
        cleaned = []
        for it in items:
            try:
                vid, qty = int(it["variant_id"]), int(it["quantity"])
            except (KeyError, TypeError, ValueError):
                return Response({"error": "فرمت آیتم‌ها نامعتبر است"}, status=400)
            if qty < 1:
                return Response({"error": "تعداد هر قطعه باید حداقل ۱ باشد"}, status=400)
            if vid == (recipe.product.variants.values_list("id", flat=True).first()):
                return Response({"error": "محصول نهایی نمی‌تواند قطعه خودش باشد"}, status=400)
            cleaned.append((vid, qty))
        variant_ids = {vid for vid, _ in cleaned}
        found = set(ProductVariant.objects.filter(pk__in=variant_ids, is_active=True)
                    .values_list("id", flat=True))
        missing = variant_ids - found
        if missing:
            return Response({"error": f"قطعه با شناسه {sorted(missing)} یافت نشد"}, status=400)
        with transaction.atomic():
            recipe.items.all().delete()
            AssemblyRecipeItem.objects.bulk_create([
                AssemblyRecipeItem(recipe=recipe, component_id=vid, quantity=qty)
                for vid, qty in cleaned
            ])
            if "note" in request.data:
                recipe.note = request.data["note"] or ""
                recipe.save(update_fields=["note", "updated_at"])
        return Response(_recipe_payload(recipe))


class OrderListView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        if not _has_staff_perm(request.user, "production_view"):
            return _forbidden()
        orders = (AssemblyOrder.objects
                  .select_related("product", "warehouse", "source_warehouse", "created_by")[:100])
        return Response([_order_payload(o) for o in orders])

    def post(self, request):
        """اجرای مونتاژ: مصرف قطعات از انبار مبدأ + تولید محصول نهایی در انبار مقصد (اتمیک)."""
        if not _has_staff_perm(request.user, "production_manage"):
            return _forbidden()
        d = request.data
        recipe = (AssemblyRecipe.objects
                  .prefetch_related("items__component__product", "product__variants")
                  .filter(pk=d.get("recipe_id")).first())
        if recipe is None:
            return Response({"error": "دستوره یافت نشد"}, status=404)
        items = list(recipe.items.all())
        if not items:
            return Response({"error": "دستوره مونتاژ هنوز قطعه‌ای ندارد"}, status=400)
        try:
            qty = int(d.get("quantity"))
            assert qty >= 1
        except (TypeError, ValueError, AssertionError):
            return Response({"error": "تعداد تولید نامعتبر است"}, status=400)
        warehouse = Warehouse.objects.filter(pk=d.get("warehouse_id"), is_active=True).first() \
            if d.get("warehouse_id") else _default_warehouse()
        if warehouse is None:
            return Response({"error": "انبار مقصد (محصول نهایی) معتبر نیست"}, status=400)
        source = Warehouse.objects.filter(pk=d.get("source_warehouse_id"), is_active=True).first() \
            if d.get("source_warehouse_id") else warehouse
        if source is None:
            return Response({"error": "انبار مبدأ (قطعات) معتبر نیست"}, status=400)

        # اجرت مونتاژ و لوازم مصرفی — هزینه‌های برون‌سپاری، جزو بهای تمام‌شده
        try:
            labor = max(0, int(d.get("labor_cost_irr") or 0))
            consumables = max(0, int(d.get("consumables_cost_irr") or 0))
        except (TypeError, ValueError):
            return Response({"error": "مبلغ اجرت/لوازم نامعتبر است"}, status=400)
        from datetime import date as date_cls
        from django.utils import timezone
        production_date = None
        if d.get("production_date"):
            try:
                production_date = date_cls.fromisoformat(str(d["production_date"])[:10])
            except ValueError:
                return Response({"error": "تاریخ تولید نامعتبر است"}, status=400)
        assembler = None
        if d.get("assembler_id"):
            from apps.accounting.models import Contact
            assembler = Contact.objects.filter(pk=d["assembler_id"], is_active=True).first()
            if assembler is None:
                return Response({"error": "طرف حساب مونتاژکار یافت نشد"}, status=400)
        if labor + consumables > 0 and assembler is None:
            return Response({"error": "برای اجرت/لوازم مصرفی باید مونتاژکار (طرف حساب) انتخاب شود"}, status=400)
        variant = recipe.product.variants.filter(is_active=True).first()
        if variant is None:
            return Response({"error": "محصول نهایی واریانت فعال ندارد"}, status=400)

        # چک کفایت موجودی همه قطعات در انبار مبدأ قبل از هر تغییری
        shortages = []
        for it in items:
            stock_qty = (WarehouseStock.objects
                         .filter(warehouse=source, variant=it.component)
                         .values_list("quantity", flat=True).first() or 0)
            need = it.quantity * qty
            if stock_qty < need:
                shortages.append(f"{it.component.product.name} ({it.component.sku}): "
                                 f"موجودی {stock_qty} در «{source.name}»، نیاز {need}")
        if shortages:
            return Response({"error": "موجودی قطعات کافی نیست", "shortages": shortages}, status=400)

        comp_unit = sum(get_variant_cost_irr(it.component) * it.quantity for it in items)
        # اجرت و لوازم «هر واحد» هستند — بهای واحد = قطعات + اجرت واحد + لوازم واحد
        unit_cost = comp_unit + labor + consumables
        total_cost = unit_cost * qty
        ref = f"ASM-{recipe.product_id}"
        note = d.get("note") or ""
        with transaction.atomic():
            for it in items:
                need = it.quantity * qty
                StockMovement.record(
                    warehouse=source, variant=it.component,
                    movement_type="assembly_out", quantity=-need,
                    unit_price=get_variant_cost_irr(it.component),
                    reference=ref, note=f"مصرف مونتاژ {recipe.product.name} × {qty}",
                    user=request.user,
                )
                c = it.component
                c.stock_quantity = max(0, c.stock_quantity - need)
                c.save(update_fields=["stock_quantity"])
            StockMovement.record(
                warehouse=warehouse, variant=variant,
                movement_type="assembly_in", quantity=qty,
                unit_price=unit_cost, reference=ref,
                note=f"تولید {recipe.product.name} × {qty}", user=request.user,
            )
            variant.stock_quantity += qty
            # بهای تمام‌شده به یوان در واریانت نهایی → قیمت‌های سایت از فرمول دسته
            rate = Decimal(str(ExchangeRateSetting.get_instance().rate_cny_to_irt or 0))
            if rate > 0:
                variant.purchase_price_cny = (Decimal(unit_cost) / rate).quantize(Decimal("0.01"))
            variant.save(update_fields=["stock_quantity", "purchase_price_cny"])
            order = AssemblyOrder.objects.create(
                product=recipe.product, quantity=qty, warehouse=warehouse,
                source_warehouse=source,
                unit_cost_irr=unit_cost, total_cost_irr=total_cost,
                labor_cost_irr=labor, consumables_cost_irr=consumables,
                assembler=assembler, production_date=production_date or timezone.localdate(),
                note=note, created_by=request.user,
            )
            # سند هزینه اجرت/لوازم در حساب مونتاژکار — مبلغ = نرخ واحد × تعداد
            if labor + consumables > 0:
                from apps.expenses.models import ExpenseCharge
                from apps.expenses.services import book_charge_accrual
                pd = order.production_date
                parts = []
                if labor: parts.append(f"اجرت {labor:,}/دستگاه")
                if consumables: parts.append(f"لوازم مصرفی {consumables:,}/دستگاه")
                charge = ExpenseCharge.objects.create(
                    source=ExpenseCharge.Source.GENERAL,
                    title=f"مونتاژ {recipe.product.name} × {qty} (دستور #{order.id}) — {' + '.join(parts)}",
                    contact=assembler,
                    year=pd.year, month=pd.month, date=pd,
                    amount=(labor + consumables) * qty,
                    notes=note,
                )
                book_charge_accrual(charge, actor=request.user)
                order.expense_charge = charge
                order.save(update_fields=["expense_charge"])
        return Response(_order_payload(order), status=201)


def _order_payload(o):
    return {
        "id": o.id,
        "product_id": o.product_id,
        "product_name": o.product.name,
        "quantity": o.quantity,
        "warehouse_name": o.warehouse.name,
        "source_warehouse_name": o.source_warehouse.name if o.source_warehouse else o.warehouse.name,
        "unit_cost_irr": o.unit_cost_irr,
        "total_cost_irr": o.total_cost_irr,
        "labor_cost_irr": o.labor_cost_irr,
        "consumables_cost_irr": o.consumables_cost_irr,
        "assembler_name": o.assembler.name if o.assembler else "",
        "expense_charge_id": o.expense_charge_id,
        "status": o.status,
        "status_display": o.get_status_display(),
        "production_date": o.production_date.isoformat() if o.production_date else "",
        "note": o.note,
        "created_by": (o.created_by.get_full_name() or o.created_by.phone) if o.created_by else "-",
        "created_at": o.created_at.isoformat(),
    }


class OrderCancelView(APIView):
    """برگشت دستور مونتاژ — معکوس کامل حرکت‌ها (قطعات به انبار مبدأ برمی‌گردند، محصول نهایی از انبار مقصد خارج می‌شود)."""
    permission_classes = [IsAdminUser]

    def post(self, request, pk):
        if not _has_staff_perm(request.user, "production_manage"):
            return _forbidden()
        order = (AssemblyOrder.objects
                 .select_related("product", "warehouse", "source_warehouse")
                 .filter(pk=pk).first())
        if order is None:
            return Response({"error": "دستور یافت نشد"}, status=404)
        if order.status == AssemblyOrder.Status.CANCELLED:
            return Response({"error": "این دستور قبلاً برگشت داده شده"}, status=400)
        recipe = (AssemblyRecipe.objects
                  .prefetch_related("items__component")
                  .filter(product=order.product).first())
        if recipe is None or not recipe.items.exists():
            return Response({"error": "دستوره مونتاژ این محصول یافت نشد — برگشت دستی لازم است"}, status=400)
        variant = order.product.variants.filter(is_active=True).first()
        need_out = order.quantity
        stock_qty = (WarehouseStock.objects
                     .filter(warehouse=order.warehouse, variant=variant)
                     .values_list("quantity", flat=True).first() or 0)
        if stock_qty < need_out:
            return Response({"error": f"موجودی فعلی محصول نهایی در {order.warehouse.name} "
                                      f"({stock_qty}) برای برگشت کافی نیست"}, status=400)
        ref = f"ASM-{order.product_id}"
        # دستورهای قدیمی انبار مبدأ ندارند — قطعات از/به همان انبار مقصد می‌رفت
        source = order.source_warehouse or order.warehouse
        with transaction.atomic():
            # خروج محصول نهایی از انبار مقصد
            StockMovement.record(
                warehouse=order.warehouse, variant=variant,
                movement_type="assembly_out", quantity=-need_out,
                unit_price=order.unit_cost_irr, reference=ref,
                note=f"برگشت دستور مونتاژ #{order.id}", user=request.user,
            )
            variant.stock_quantity = max(0, variant.stock_quantity - need_out)
            variant.save(update_fields=["stock_quantity"])
            # برگشت قطعات به انبار مبدأ
            for it in recipe.items.all():
                back = it.quantity * order.quantity
                StockMovement.record(
                    warehouse=source, variant=it.component,
                    movement_type="assembly_in", quantity=back,
                    unit_price=get_variant_cost_irr(it.component), reference=ref,
                    note=f"برگشت قطعه از دستور مونتاژ #{order.id}", user=request.user,
                )
                c = it.component
                c.stock_quantity += back
                c.save(update_fields=["stock_quantity"])
            order.status = AssemblyOrder.Status.CANCELLED
            order.save(update_fields=["status"])
            # برگشت سند هزینه اجرت/لوازم از حساب مونتاژکار (الگوی reversal — سابقه می‌ماند)
            if order.expense_charge_id:
                from apps.expenses.services import reverse_charge
                reverse_charge(order.expense_charge, actor=request.user)
        return Response(_order_payload(order))
