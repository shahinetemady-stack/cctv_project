"""
python fix_kardex.py
سیستم کاردکس کالا
"""
import os, subprocess, sys

print("ساخت سیستم کاردکس ...")

# ─── 1. اضافه کردن StockMovement به models.py ─────────────
models_path = os.path.join('apps','inventory','models.py')
with open(models_path, encoding='utf-8') as f:
    content = f.read()

if 'StockMovement' not in content:
    content += '''

class StockMovement(models.Model):
    """کاردکس — هر ورود/خروج کالا یک رکورد"""
    class MovementType(models.TextChoices):
        PURCHASE  = "purchase",  "خرید"
        SALE      = "sale",      "فروش"
        TRANSFER_IN  = "transfer_in",  "انتقال ورودی"
        TRANSFER_OUT = "transfer_out", "انتقال خروجی"
        ADJUSTMENT   = "adjustment",   "تعدیل موجودی"
        RETURN    = "return",    "مرجوعی"

    warehouse   = models.ForeignKey(Warehouse, on_delete=models.PROTECT,
                    related_name="movements", verbose_name="انبار")
    variant     = models.ForeignKey("catalog.ProductVariant", on_delete=models.PROTECT,
                    related_name="movements", verbose_name="محصول")
    movement_type = models.CharField(max_length=20, choices=MovementType.choices, verbose_name="نوع حرکت")
    quantity    = models.IntegerField(verbose_name="تعداد", help_text="مثبت=ورود، منفی=خروج")
    unit_price  = models.PositiveBigIntegerField(default=0, verbose_name="قیمت واحد (تومان)")
    balance_after = models.PositiveIntegerField(default=0, verbose_name="موجودی بعد از حرکت")
    reference   = models.CharField(max_length=100, blank=True, verbose_name="مرجع (شماره سفارش/فاکتور)")
    note        = models.TextField(blank=True, verbose_name="توضیحات")
    created_by  = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                    null=True, blank=True, verbose_name="ثبت کننده")
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "inventory_stock_movement"
        verbose_name = "حرکت موجودی (کاردکس)"
        verbose_name_plural = "کاردکس موجودی"
        ordering = ["-created_at"]

    def __str__(self):
        sign = "+" if self.quantity > 0 else ""
        return f"{self.warehouse.name} | {self.variant} | {sign}{self.quantity}"

    @classmethod
    def record(cls, warehouse, variant, movement_type, quantity, unit_price=0,
               reference="", note="", user=None):
        """ثبت یک حرکت موجودی و بروزرسانی موجودی انبار"""
        from django.db import transaction
        with transaction.atomic():
            stock, _ = WarehouseStock.objects.get_or_create(
                warehouse=warehouse, variant=variant
            )
            stock.quantity += quantity
            if stock.quantity < 0:
                raise ValueError(f"موجودی کافی نیست ({stock.quantity + abs(quantity)} < {abs(quantity)})")
            stock.save()
            return cls.objects.create(
                warehouse=warehouse,
                variant=variant,
                movement_type=movement_type,
                quantity=quantity,
                unit_price=unit_price,
                balance_after=stock.quantity,
                reference=reference,
                note=note,
                created_by=user,
            )
'''
    with open(models_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("  OK - StockMovement اضافه شد")

# ─── 2. migration ──────────────────────────────────────────
migration = '''from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings

class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0001_initial_warehouse"),
        ("catalog", "0008_partner_price"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.CreateModel(
            name="StockMovement",
            fields=[
                ("id", models.BigAutoField(primary_key=True)),
                ("warehouse", models.ForeignKey("inventory.Warehouse", on_delete=django.db.models.deletion.PROTECT, related_name="movements", verbose_name="انبار")),
                ("variant", models.ForeignKey("catalog.ProductVariant", on_delete=django.db.models.deletion.PROTECT, related_name="movements", verbose_name="محصول")),
                ("movement_type", models.CharField(max_length=20, verbose_name="نوع حرکت",
                    choices=[("purchase","خرید"),("sale","فروش"),("transfer_in","انتقال ورودی"),
                             ("transfer_out","انتقال خروجی"),("adjustment","تعدیل"),("return","مرجوعی")])),
                ("quantity", models.IntegerField(verbose_name="تعداد")),
                ("unit_price", models.PositiveBigIntegerField(default=0, verbose_name="قیمت واحد")),
                ("balance_after", models.PositiveIntegerField(default=0, verbose_name="موجودی بعد")),
                ("reference", models.CharField(max_length=100, blank=True, verbose_name="مرجع")),
                ("note", models.TextField(blank=True, verbose_name="توضیحات")),
                ("created_by", models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=django.db.models.deletion.SET_NULL, null=True, blank=True, verbose_name="ثبت کننده")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"db_table": "inventory_stock_movement", "verbose_name": "کاردکس", "ordering": ["-created_at"]},
        ),
    ]
'''

mig_path = os.path.join('apps','inventory','migrations','0002_stock_movement.py')
with open(mig_path, 'w', encoding='utf-8') as f:
    f.write(migration)
print("  OK - migration کاردکس")

# ─── 3. admin.py با کاردکس ────────────────────────────────
admin_content = '''from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Sum
from .models import Warehouse, WarehouseStock, StockTransfer, StockMovement


class WarehouseStockInline(admin.TabularInline):
    model = WarehouseStock
    extra = 1
    fields = ["variant", "quantity", "min_quantity"]


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display  = ["name", "code", "warehouse_type", "is_public", "is_active", "total_stock"]
    list_filter   = ["warehouse_type", "is_public", "is_active"]
    list_editable = ["is_public", "is_active"]
    search_fields = ["name", "code"]
    inlines       = [WarehouseStockInline]
    fields        = ["name", "code", "warehouse_type", "is_public", "is_active", "address"]

    def total_stock(self, obj):
        total = obj.stocks.aggregate(t=Sum("quantity"))["t"] or 0
        return str(total) + " عدد"
    total_stock.short_description = "کل موجودی"


@admin.register(WarehouseStock)
class WarehouseStockAdmin(admin.ModelAdmin):
    list_display  = ["variant_name", "warehouse", "quantity", "min_quantity", "status_badge"]
    list_filter   = ["warehouse", "warehouse__warehouse_type"]
    search_fields = ["variant__sku", "variant__product__name"]
    list_editable = ["quantity", "min_quantity"]

    def variant_name(self, obj):
        return str(obj.variant.product.name) + " [" + str(obj.variant.sku) + "]"
    variant_name.short_description = "محصول"

    def status_badge(self, obj):
        if obj.quantity == 0:
            return format_html('<span style="color:#FF3B3B">ناموجود</span>')
        if obj.min_quantity and obj.quantity <= obj.min_quantity:
            return format_html('<span style="color:#FF9500">کم موجود</span>')
        return format_html('<span style="color:#00C896">موجود</span>')
    status_badge.short_description = "وضعیت"


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display  = ["created_at", "variant_name", "warehouse", "movement_type_badge",
                     "quantity_display", "balance_after", "reference", "created_by"]
    list_filter   = ["movement_type", "warehouse", ("created_at", admin.DateFieldListFilter)]
    search_fields = ["variant__sku", "variant__product__name", "reference"]
    readonly_fields = ["created_at", "created_by", "balance_after"]
    date_hierarchy = "created_at"

    def variant_name(self, obj):
        return str(obj.variant.product.name)
    variant_name.short_description = "محصول"

    def movement_type_badge(self, obj):
        colors = {
            "purchase": "#00C896", "sale": "#FF3B3B",
            "transfer_in": "#0066FF", "transfer_out": "#FF9500",
            "adjustment": "#8B5CF6", "return": "#FF6B6B",
        }
        color = colors.get(obj.movement_type, "#888")
        return format_html(
            '<span style="color:{};font-weight:bold">{}</span>',
            color, obj.get_movement_type_display()
        )
    movement_type_badge.short_description = "نوع"

    def quantity_display(self, obj):
        color = "#00C896" if obj.quantity > 0 else "#FF3B3B"
        sign = "+" if obj.quantity > 0 else ""
        return format_html(
            '<span style="color:{};font-weight:bold">{}{}</span>',
            color, sign, obj.quantity
        )
    quantity_display.short_description = "تعداد"

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(StockTransfer)
class StockTransferAdmin(admin.ModelAdmin):
    list_display  = ["variant", "from_warehouse", "to_warehouse", "quantity", "status", "created_at"]
    list_filter   = ["status", "from_warehouse", "to_warehouse"]
    search_fields = ["variant__sku", "variant__product__name"]
    readonly_fields = ["transferred_by", "created_at", "updated_at"]
    actions = ["execute_transfer"]

    @admin.action(description="انجام انتقال")
    def execute_transfer(self, request, queryset):
        success = 0
        for transfer in queryset.filter(status="pending"):
            try:
                transfer.execute(user=request.user)
                # ثبت در کاردکس
                StockMovement.record(
                    warehouse=transfer.from_warehouse,
                    variant=transfer.variant,
                    movement_type="transfer_out",
                    quantity=-transfer.quantity,
                    reference=f"انتقال به {transfer.to_warehouse.name}",
                    user=request.user,
                )
                StockMovement.record(
                    warehouse=transfer.to_warehouse,
                    variant=transfer.variant,
                    movement_type="transfer_in",
                    quantity=transfer.quantity,
                    reference=f"انتقال از {transfer.from_warehouse.name}",
                    user=request.user,
                )
                success += 1
            except ValueError as e:
                self.message_user(request, str(e), level="error")
        if success:
            self.message_user(request, str(success) + " انتقال انجام شد.")
'''

with open(os.path.join('apps','inventory','admin.py'), 'w', encoding='utf-8') as f:
    f.write(admin_content)
print("  OK - admin.py با کاردکس")

# ─── 4. views.py با API کاردکس ────────────────────────────
views_content = '''from rest_framework.views import APIView
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
        data = [{"warehouse": s.warehouse.name, "quantity": s.quantity, "is_low": s.is_low} for s in stocks]
        return Response({"total": sum(s.quantity for s in stocks), "stocks": data})


class KardexView(APIView):
    permission_classes = [IsAdminUser]
    def get(self, request, variant_id):
        warehouse_id = request.query_params.get("warehouse")
        qs = StockMovement.objects.filter(variant_id=variant_id).select_related("warehouse", "created_by")
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
            "note": m.note,
        } for m in qs[:200]]
        return Response(data)


class WarehouseSummaryView(APIView):
    permission_classes = [IsAdminUser]
    def get(self, request):
        warehouses = Warehouse.objects.filter(is_active=True)
        result = []
        for w in warehouses:
            total = w.stocks.aggregate(t=Sum("quantity"))["t"] or 0
            low = w.stocks.filter(quantity__gt=0, min_quantity__gt=0).filter(quantity__lte=models.F("min_quantity") if False else 0).count()
            result.append({
                "id": w.id, "name": w.name, "code": w.code,
                "type": w.warehouse_type, "is_public": w.is_public,
                "total_quantity": total,
            })
        return Response(result)
'''

# اصلاح ساده‌تر
views_content = '''from rest_framework.views import APIView
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
'''

with open(os.path.join('apps','inventory','views.py'), 'w', encoding='utf-8') as f:
    f.write(views_content)

with open(os.path.join('apps','inventory','urls.py'), 'w', encoding='utf-8') as f:
    f.write('''from django.urls import path
from .views import PublicStockView, KardexView, WarehouseSummaryView
urlpatterns = [
    path("stock/<int:variant_id>/", PublicStockView.as_view()),
    path("kardex/<int:variant_id>/", KardexView.as_view()),
    path("warehouses/", WarehouseSummaryView.as_view()),
]
''')
print("  OK - views.py و urls.py")

# ─── 5. migrate ──────────────────────────────────────────
r = subprocess.run([sys.executable,'manage.py','migrate','--verbosity=0'],
                   capture_output=True, text=True)
if r.returncode == 0:
    print("  OK - migrate موفق")
else:
    for line in (r.stdout+r.stderr).strip().split('\n')[-6:]:
        if line.strip(): print(" ", line)

r2 = subprocess.run([sys.executable,'manage.py','check','--verbosity=0'],
                    capture_output=True, text=True)
print("  OK - check" if r2.returncode == 0 else r2.stderr[-200:])
print("\nتمام! python manage.py runserver")
