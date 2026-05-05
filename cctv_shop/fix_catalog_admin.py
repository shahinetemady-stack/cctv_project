import os

print("بازنویسی catalog/admin.py ...")

catalog_admin = '''from django.contrib import admin
from django.urls import path
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.utils.html import format_html
from import_export.admin import ImportExportModelAdmin
from import_export import resources, fields
from .models import Category, ExchangeRateSetting, Product, ProductImage, ProductVariant, SeoSettings


@admin.register(ExchangeRateSetting)
class ExchangeRateSettingAdmin(admin.ModelAdmin):
    list_display = ["rate_usd_to_irt", "updated_at", "updated_by"]
    readonly_fields = ["updated_at", "updated_by", "created_at"]
    def save_model(self, request, obj, form, change):
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)
    def has_add_permission(self, request):
        return not ExchangeRateSetting.objects.exists()
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "parent", "is_active", "sort_order"]
    list_filter = ["is_active", "parent"]
    search_fields = ["name"]
    prepopulated_fields = {"slug": ("name",)}
    list_editable = ["sort_order", "is_active"]
    ordering = ["sort_order", "name"]


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ["image", "alt_text", "is_primary", "sort_order"]


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    fields = ["sku", "name_suffix", "purchase_price_usd", "shipping_cost",
              "profit_margin", "stock_quantity", "reserved_qty", "is_active"]


class ProductVariantResource(resources.ModelResource):
    class Meta:
        model = ProductVariant
        fields = ["id", "sku", "purchase_price_usd", "shipping_cost",
                  "profit_margin", "stock_quantity"]


@admin.register(Product)
class ProductAdmin(ImportExportModelAdmin):
    resource_class = ProductVariantResource
    list_display = ["name", "category", "part_type", "chipset",
                    "voltage", "lens_mount", "stock_display", "seo_status", "is_active"]
    list_filter = ["is_active", "is_featured", "part_type", "lens_mount", "category"]
    search_fields = ["name", "model_number", "chipset", "brand"]
    prepopulated_fields = {"slug": ("name",)}
    filter_horizontal = ["compatible_with"]
    list_editable = ["is_active"]
    readonly_fields = ["created_at", "updated_at", "seo_preview"]
    actions = ["action_regenerate_seo"]
    inlines = [ProductImageInline, ProductVariantInline]

    fieldsets = (
        ("اطلاعات اصلی", {
            "fields": ("name", "slug", "category", "brand", "model_number",
                       "short_description", "description"),
        }),
        ("مشخصات فنی", {
            "fields": ("part_type", "chipset", "voltage", "lens_mount",
                       "resolution", "extra_specs"),
        }),
        ("فایل‌ها و لینک‌ها", {
            "fields": ("datasheet_pdf", "whatsapp_link", "bale_link"),
        }),
        ("محصولات سازگار", {"fields": ("compatible_with",)}),
        ("SEO - خودکار پر می‌شود", {
            "fields": ("meta_title", "meta_description", "keywords", "geo_tags", "seo_preview"),
        }),
        ("نمایش", {"fields": ("is_active", "is_featured")}),
        ("تاریخ‌ها", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path("<int:product_id>/regenerate-seo/",
                 self.admin_site.admin_view(self.regenerate_seo_view),
                 name="catalog_product_regenerate_seo")
        ]
        return custom + urls

    def regenerate_seo_view(self, request, product_id):
        from apps.catalog.seo import generate_all_seo_fields
        try:
            product = Product.objects.get(pk=product_id)
            changes = generate_all_seo_fields(product, force=True)
            if changes:
                Product.objects.filter(pk=product_id).update(**changes)
                messages.success(request, f"SEO محصول بازنویسی شد ({len(changes)} فیلد)")
            else:
                messages.info(request, "تغییری لازم نبود.")
        except Product.DoesNotExist:
            messages.error(request, "محصول یافت نشد.")
        return HttpResponseRedirect("../")

    def stock_display(self, obj):
        total = obj.available_stock
        if total == 0:
            return format_html(\'<span style="color:#FF3B3B">ناموجود</span>\')
        elif total <= 5:
            return format_html(\'<span style="color:#FF9500">کم ({})</span>\', total)
        return format_html(\'<span style="color:#00C896">{}</span>\', total)
    stock_display.short_description = "موجودی"

    def seo_status(self, obj):
        filled = sum([bool(obj.meta_title), bool(obj.meta_description),
                      bool(obj.keywords), bool(obj.geo_tags)])
        color = "#00C896" if filled == 4 else "#FF9500" if filled >= 2 else "#FF3B3B"
        url = f"{obj.pk}/regenerate-seo/"
        return format_html(
            \'<span style="color:{}">{}/4</span> <a href="{}" title="بازنویسی SEO">🔄</a>\',
            color, filled, url)
    seo_status.short_description = "SEO"

    def seo_preview(self, obj):
        if not obj.pk:
            return "پس از ذخیره نمایش داده می‌شود."
        return format_html(
            \'<div style="background:#f8f9fa;padding:12px;border-radius:8px;direction:rtl">\'\
            \'<div style="color:#1a0dab;font-size:16px">{}</div>\'\
            \'<div style="color:#006621;font-size:12px">cctvparts.ir/products/{}</div>\'\
            \'<div style="color:#545454;font-size:12px;margin-top:4px">{}</div></div>\',
            obj.meta_title or obj.name,
            obj.slug,
            obj.meta_description or "—")
    seo_preview.short_description = "پیش‌نمایش گوگل"

    @admin.action(description="بازنویسی خودکار SEO")
    def action_regenerate_seo(self, request, queryset):
        from apps.catalog.seo import generate_all_seo_fields
        count = 0
        for product in queryset:
            changes = generate_all_seo_fields(product, force=True)
            if changes:
                Product.objects.filter(pk=product.pk).update(**changes)
                count += 1
        self.message_user(request, f"SEO {count} محصول بازنویسی شد.", messages.SUCCESS)


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ["sku", "product", "final_price_display", "available_stock_display", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["sku", "product__name"]
    readonly_fields = ["created_at", "updated_at"]

    def final_price_display(self, obj):
        return format_html(\'<b style="color:#0066FF">{:,}</b> تومان\', obj.final_price)
    final_price_display.short_description = "قیمت نهایی"

    def available_stock_display(self, obj):
        stock = obj.available_stock
        if stock == 0:
            return format_html(\'<span style="color:#FF3B3B">ناموجود</span>\')
        elif stock <= 5:
            return format_html(\'<span style="color:#FF9500">{} عدد</span>\', stock)
        return format_html(\'<span style="color:#00C896">{} عدد</span>\', stock)
    available_stock_display.short_description = "موجودی"


@admin.register(SeoSettings)
class SeoSettingsAdmin(admin.ModelAdmin):
    fields = ["target_cities", "site_name"]
    def has_add_permission(self, request):
        return not SeoSettings.objects.exists()
    def has_delete_permission(self, request, obj=None):
        return False
'''

path = os.path.join('apps', 'catalog', 'admin.py')
with open(path, 'w', encoding='utf-8') as f:
    f.write(catalog_admin)

import ast
try:
    ast.parse(catalog_admin)
    print("OK - syntax درست است")
except SyntaxError as e:
    print(f"ERROR: {e}")

print("\nحالا بزنید:")
print("python manage.py migrate")
print("python manage.py runserver")
