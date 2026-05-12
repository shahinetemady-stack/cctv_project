from django.contrib import admin
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
