"""
python fix_warehouse.py
سیستم چند انبار
"""
import os, subprocess, sys

print("ساخت سیستم انبار ...")

# ─── 1. migration ─────────────────────────────────────────
os.makedirs(os.path.join('apps','inventory','migrations'), exist_ok=True)
open(os.path.join('apps','inventory','migrations','__init__.py'), 'w').close()

migration = '''from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    initial = True
    dependencies = [
        ("catalog", "0008_partner_price"),
    ]
    operations = [
        migrations.CreateModel(
            name="Warehouse",
            fields=[
                ("id", models.BigAutoField(primary_key=True)),
                ("name", models.CharField(max_length=100, verbose_name="نام انبار")),
                ("code", models.CharField(max_length=20, unique=True, verbose_name="کد انبار")),
                ("warehouse_type", models.CharField(
                    max_length=20, verbose_name="نوع انبار",
                    choices=[
                        ("air_transit", "در راه هوایی"),
                        ("sea_transit", "در راه دریایی"),
                        ("shop1", "فروشگاه یک"),
                        ("shop2", "فروشگاه دو"),
                        ("assembly", "انبار مونتاژ"),
                    ]
                )),
                ("is_public", models.BooleanField(default=False, verbose_name="نمایش به مشتری")),
                ("is_active", models.BooleanField(default=True, verbose_name="فعال")),
                ("address", models.TextField(blank=True, verbose_name="آدرس")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "inventory_warehouse", "verbose_name": "انبار", "verbose_name_plural": "انبارها"},
        ),
        migrations.CreateModel(
            name="WarehouseStock",
            fields=[
                ("id", models.BigAutoField(primary_key=True)),
                ("warehouse", models.ForeignKey("inventory.Warehouse", on_delete=django.db.models.deletion.CASCADE, related_name="stocks", verbose_name="انبار")),
                ("variant", models.ForeignKey("catalog.ProductVariant", on_delete=django.db.models.deletion.CASCADE, related_name="warehouse_stocks", verbose_name="محصول")),
                ("quantity", models.PositiveIntegerField(default=0, verbose_name="موجودی")),
                ("min_quantity", models.PositiveIntegerField(default=0, verbose_name="حداقل موجودی")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "inventory_warehouse_stock", "verbose_name": "موجودی انبار", "verbose_name_plural": "موجودی‌های انبار", "unique_together": {("warehouse", "variant")}},
        ),
        migrations.CreateModel(
            name="StockTransfer",
            fields=[
                ("id", models.BigAutoField(primary_key=True)),
                ("from_warehouse", models.ForeignKey("inventory.Warehouse", on_delete=django.db.models.deletion.PROTECT, related_name="transfers_out", verbose_name="از انبار")),
                ("to_warehouse", models.ForeignKey("inventory.Warehouse", on_delete=django.db.models.deletion.PROTECT, related_name="transfers_in", verbose_name="به انبار")),
                ("variant", models.ForeignKey("catalog.ProductVariant", on_delete=django.db.models.deletion.PROTECT, related_name="transfers", verbose_name="محصول")),
                ("quantity", models.PositiveIntegerField(verbose_name="تعداد")),
                ("status", models.CharField(max_length=20, default="pending", choices=[("pending","در انتظار"),("done","انجام شده"),("cancelled","لغو شده")], verbose_name="وضعیت")),
                ("note", models.TextField(blank=True, verbose_name="توضیحات")),
                ("transferred_by", models.ForeignKey("users.User", on_delete=django.db.models.deletion.SET_NULL, null=True, blank=True, verbose_name="انتقال دهنده")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "inventory_stock_transfer", "verbose_name": "انتقال موجودی", "verbose_name_plural": "انتقال‌های موجودی", "ordering": ["-created_at"]},
        ),
    ]
'''

mig_path = os.path.join('apps','inventory','migrations','0001_initial_warehouse.py')
with open(mig_path, 'w', encoding='utf-8') as f:
    f.write(migration)
print("  OK - migration")

# ─── 2. models.py ─────────────────────────────────────────
models_content = '''from django.db import models
from django.conf import settings


class Warehouse(models.Model):
    class Type(models.TextChoices):
        AIR_TRANSIT = "air_transit", "در راه هوایی"
        SEA_TRANSIT = "sea_transit", "در راه دریایی"
        SHOP1       = "shop1",       "فروشگاه یک"
        SHOP2       = "shop2",       "فروشگاه دو"
        ASSEMBLY    = "assembly",    "انبار مونتاژ"

    name           = models.CharField(max_length=100, verbose_name="نام انبار")
    code           = models.CharField(max_length=20, unique=True, verbose_name="کد انبار")
    warehouse_type = models.CharField(max_length=20, choices=Type.choices, verbose_name="نوع انبار")
    is_public      = models.BooleanField(default=False, verbose_name="نمایش به مشتری",
                        help_text="اگر فعال باشد موجودی این انبار به مشتریان نشان داده می‌شود")
    is_active      = models.BooleanField(default=True, verbose_name="فعال")
    address        = models.TextField(blank=True, verbose_name="آدرس")
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "inventory_warehouse"
        verbose_name = "انبار"
        verbose_name_plural = "انبارها"

    def __str__(self):
        return f"{self.name} ({self.get_warehouse_type_display()})"


class WarehouseStock(models.Model):
    warehouse    = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name="stocks", verbose_name="انبار")
    variant      = models.ForeignKey("catalog.ProductVariant", on_delete=models.CASCADE, related_name="warehouse_stocks", verbose_name="محصول")
    quantity     = models.PositiveIntegerField(default=0, verbose_name="موجودی")
    min_quantity = models.PositiveIntegerField(default=0, verbose_name="حداقل موجودی")
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "inventory_warehouse_stock"
        verbose_name = "موجودی انبار"
        verbose_name_plural = "موجودی‌های انبار"
        unique_together = [("warehouse", "variant")]

    def __str__(self):
        return f"{self.warehouse.name} — {self.variant} — {self.quantity}"

    @property
    def is_low(self):
        return self.quantity <= self.min_quantity and self.quantity > 0

    @property
    def is_out(self):
        return self.quantity == 0


class StockTransfer(models.Model):
    class Status(models.TextChoices):
        PENDING   = "pending",   "در انتظار"
        DONE      = "done",      "انجام شده"
        CANCELLED = "cancelled", "لغو شده"

    from_warehouse  = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name="transfers_out", verbose_name="از انبار")
    to_warehouse    = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name="transfers_in", verbose_name="به انبار")
    variant         = models.ForeignKey("catalog.ProductVariant", on_delete=models.PROTECT, related_name="transfers", verbose_name="محصول")
    quantity        = models.PositiveIntegerField(verbose_name="تعداد")
    status          = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, verbose_name="وضعیت")
    note            = models.TextField(blank=True, verbose_name="توضیحات")
    transferred_by  = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                        null=True, blank=True, verbose_name="انتقال دهنده")
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "inventory_stock_transfer"
        verbose_name = "انتقال موجودی"
        verbose_name_plural = "انتقال‌های موجودی"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.variant} | {self.from_warehouse.name} → {self.to_warehouse.name} ({self.quantity})"

    def execute(self, user=None):
        """انجام انتقال — کسر از مبدأ و اضافه به مقصد"""
        from django.db import transaction
        with transaction.atomic():
            src, _ = WarehouseStock.objects.get_or_create(warehouse=self.from_warehouse, variant=self.variant)
            if src.quantity < self.quantity:
                raise ValueError(f"موجودی کافی نیست ({src.quantity} < {self.quantity})")
            src.quantity -= self.quantity
            src.save()
            dst, _ = WarehouseStock.objects.get_or_create(warehouse=self.to_warehouse, variant=self.variant)
            dst.quantity += self.quantity
            dst.save()
            self.status = self.Status.DONE
            if user:
                self.transferred_by = user
            self.save()
'''

with open(os.path.join('apps','inventory','models.py'), 'w', encoding='utf-8') as f:
    f.write(models_content)
print("  OK - models.py")

# ─── 3. admin.py ──────────────────────────────────────────
admin_content = '''from django.contrib import admin
from django.utils.html import format_html
from .models import Warehouse, WarehouseStock, StockTransfer


class WarehouseStockInline(admin.TabularInline):
    model = WarehouseStock
    extra = 0
    fields = ["variant", "quantity", "min_quantity", "stock_status"]
    readonly_fields = ["stock_status"]

    def stock_status(self, obj):
        if obj.quantity == 0:
            return format_html('<span style="color:#FF3B3B">ناموجود</span>')
        if obj.quantity <= obj.min_quantity:
            return format_html('<span style="color:#FF9500">کم</span>')
        return format_html('<span style="color:#00C896">موجود</span>')
    stock_status.short_description = "وضعیت"


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display  = ["name", "code", "warehouse_type", "is_public", "is_active", "total_items"]
    list_filter   = ["warehouse_type", "is_public", "is_active"]
    list_editable = ["is_public", "is_active"]
    search_fields = ["name", "code"]
    inlines       = [WarehouseStockInline]

    def total_items(self, obj):
        from django.db.models import Sum
        total = obj.stocks.aggregate(t=Sum("quantity"))["t"] or 0
        return f"{total:,} عدد"
    total_items.short_description = "کل موجودی"


@admin.register(WarehouseStock)
class WarehouseStockAdmin(admin.ModelAdmin):
    list_display  = ["variant", "warehouse", "quantity", "min_quantity", "status_display"]
    list_filter   = ["warehouse", "warehouse__warehouse_type"]
    search_fields = ["variant__sku", "variant__product__name"]
    list_editable = ["quantity", "min_quantity"]

    def status_display(self, obj):
        if obj.quantity == 0:
            return format_html('<span style="color:#FF3B3B;font-weight:bold">ناموجود</span>')
        if obj.quantity <= obj.min_quantity:
            return format_html('<span style="color:#FF9500;font-weight:bold">کم ({}/{})</span>', obj.quantity, obj.min_quantity)
        return format_html('<span style="color:#00C896">موجود</span>')
    status_display.short_description = "وضعیت"


@admin.register(StockTransfer)
class StockTransferAdmin(admin.ModelAdmin):
    list_display  = ["variant", "from_warehouse", "to_warehouse", "quantity", "status", "transferred_by", "created_at"]
    list_filter   = ["status", "from_warehouse", "to_warehouse"]
    search_fields = ["variant__sku", "variant__product__name"]
    readonly_fields = ["transferred_by", "created_at", "updated_at"]
    actions = ["execute_transfer"]

    @admin.action(description="انجام انتقال انتخاب شده")
    def execute_transfer(self, request, queryset):
        success = 0
        for transfer in queryset.filter(status="pending"):
            try:
                transfer.execute(user=request.user)
                success += 1
            except ValueError as e:
                self.message_user(request, f"خطا در {transfer}: {e}", level="error")
        if success:
            self.message_user(request, f"{success} انتقال با موفقیت انجام شد.")

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
'''

with open(os.path.join('apps','inventory','admin.py'), 'w', encoding='utf-8') as f:
    f.write(admin_content)
print("  OK - admin.py")

# ─── 4. urls.py و views.py ────────────────────────────────
views_content = '''from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAdminUser
from django.db.models import Sum
from .models import Warehouse, WarehouseStock


class PublicStockView(APIView):
    """موجودی انبارهای عمومی برای مشتریان"""
    permission_classes = [AllowAny]

    def get(self, request, variant_id):
        stocks = WarehouseStock.objects.filter(
            variant_id=variant_id,
            warehouse__is_public=True,
            warehouse__is_active=True,
        ).select_related("warehouse")
        data = [
            {
                "warehouse": s.warehouse.name,
                "quantity": s.quantity,
                "is_low": s.is_low,
            }
            for s in stocks
        ]
        total = sum(s.quantity for s in stocks)
        return Response({"total": total, "stocks": data})


class AdminWarehouseView(APIView):
    """موجودی همه انبارها برای ادمین"""
    permission_classes = [IsAdminUser]

    def get(self, request, variant_id):
        stocks = WarehouseStock.objects.filter(
            variant_id=variant_id,
            warehouse__is_active=True,
        ).select_related("warehouse")
        data = [
            {
                "warehouse_id": s.warehouse_id,
                "warehouse": s.warehouse.name,
                "warehouse_type": s.warehouse.warehouse_type,
                "is_public": s.warehouse.is_public,
                "quantity": s.quantity,
                "min_quantity": s.min_quantity,
                "is_low": s.is_low,
                "is_out": s.is_out,
            }
            for s in stocks
        ]
        return Response(data)
'''

with open(os.path.join('apps','inventory','views.py'), 'w', encoding='utf-8') as f:
    f.write(views_content)

with open(os.path.join('apps','inventory','urls.py'), 'w', encoding='utf-8') as f:
    f.write('''from django.urls import path
from .views import PublicStockView, AdminWarehouseView
urlpatterns = [
    path("stock/<int:variant_id>/", PublicStockView.as_view()),
    path("admin/stock/<int:variant_id>/", AdminWarehouseView.as_view()),
]
''')
print("  OK - views.py و urls.py")

# ─── 5. اضافه کردن به INSTALLED_APPS ──────────────────────
settings_path = os.path.join('config','settings.py')
with open(settings_path, encoding='utf-8') as f:
    settings = f.read()

if '"apps.inventory"' not in settings and "'apps.inventory'" not in settings:
    settings = settings.replace(
        '"apps.catalog",',
        '"apps.catalog",\n    "apps.inventory",'
    )
    with open(settings_path, 'w', encoding='utf-8') as f:
        f.write(settings)
    print("  OK - settings.py")

# ─── 6. migrate ──────────────────────────────────────────
r = subprocess.run([sys.executable,'manage.py','migrate','--verbosity=0'],
                   capture_output=True, text=True)
if r.returncode == 0:
    print("  OK - migrate موفق")
else:
    for line in (r.stdout+r.stderr).strip().split('\n')[-6:]:
        if line.strip(): print(" ", line)

# ─── 7. ساخت انبارهای پیش‌فرض ───────────────────────────
init_script = '''
from apps.inventory.models import Warehouse
warehouses = [
    {"name": "در راه هوایی", "code": "AIR", "warehouse_type": "air_transit", "is_public": False},
    {"name": "در راه دریایی", "code": "SEA", "warehouse_type": "sea_transit", "is_public": False},
    {"name": "فروشگاه یک", "code": "SHOP1", "warehouse_type": "shop1", "is_public": True},
    {"name": "فروشگاه دو", "code": "SHOP2", "warehouse_type": "shop2", "is_public": True},
    {"name": "انبار مونتاژ", "code": "ASSEMBLY", "warehouse_type": "assembly", "is_public": False},
]
for w in warehouses:
    Warehouse.objects.get_or_create(code=w["code"], defaults=w)
print("انبارها ساخته شدند")
'''

r2 = subprocess.run([sys.executable,'manage.py','shell','-c', init_script],
                    capture_output=True, text=True)
if 'انبارها ساخته شدند' in r2.stdout:
    print("  OK - ۵ انبار پیش‌فرض ساخته شد")

r3 = subprocess.run([sys.executable,'manage.py','check','--verbosity=0'],
                    capture_output=True, text=True)
print("  OK - check" if r3.returncode == 0 else r3.stderr[-200:])

print("\nتمام! python manage.py runserver")
