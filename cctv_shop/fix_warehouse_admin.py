import os, subprocess, sys

# اصلاح admin.py انبار
admin_content = '''from django.contrib import admin
from .models import Warehouse, WarehouseStock, StockTransfer


class WarehouseStockInline(admin.TabularInline):
    model = WarehouseStock
    extra = 1
    fields = ["variant", "quantity", "min_quantity"]


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display  = ["name", "code", "warehouse_type", "is_public", "is_active"]
    list_filter   = ["warehouse_type", "is_public", "is_active"]
    list_editable = ["is_public", "is_active"]
    search_fields = ["name", "code"]
    inlines       = [WarehouseStockInline]
    fields        = ["name", "code", "warehouse_type", "is_public", "is_active", "address"]


@admin.register(WarehouseStock)
class WarehouseStockAdmin(admin.ModelAdmin):
    list_display  = ["variant", "warehouse", "quantity", "min_quantity"]
    list_filter   = ["warehouse"]
    search_fields = ["variant__sku", "variant__product__name"]
    list_editable = ["quantity", "min_quantity"]


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
                success += 1
            except ValueError as e:
                self.message_user(request, str(e), level="error")
        if success:
            self.message_user(request, str(success) + " انتقال انجام شد.")
'''

with open(os.path.join('apps','inventory','admin.py'), 'w', encoding='utf-8') as f:
    f.write(admin_content)
print("OK - admin.py")

# ساخت انبارها
init_script = "from apps.inventory.models import Warehouse; warehouses = [{'name':'در راه هوایی','code':'AIR','warehouse_type':'air_transit','is_public':False},{'name':'در راه دریایی','code':'SEA','warehouse_type':'sea_transit','is_public':False},{'name':'فروشگاه یک','code':'SHOP1','warehouse_type':'shop1','is_public':True},{'name':'فروشگاه دو','code':'SHOP2','warehouse_type':'shop2','is_public':True},{'name':'انبار مونتاژ','code':'ASSEMBLY','warehouse_type':'assembly','is_public':False}]; [Warehouse.objects.get_or_create(code=w['code'],defaults=w) for w in warehouses]; print('done')"

r = subprocess.run([sys.executable,'manage.py','shell','-c',init_script], capture_output=True, text=True)
if 'done' in r.stdout:
    print("OK - 5 انبار ساخته شد")
else:
    print(r.stderr[-200:])

r2 = subprocess.run([sys.executable,'manage.py','check','--verbosity=0'], capture_output=True, text=True)
print("OK - check" if r2.returncode == 0 else r2.stderr[-200:])
print("\nتمام!")
