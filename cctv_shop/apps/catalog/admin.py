from django.contrib import admin
from django.utils.html import format_html
from django import forms
from django.urls import path
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Category, ExchangeRateSetting, Product, ProductImage, ProductVariant, SeoSettings



@admin.register(ExchangeRateSetting)
class ExchangeRateSettingAdmin(admin.ModelAdmin):
    pass

class ExchangeRateSettingAdmin(admin.ModelAdmin):
    list_display = ['rate_cny_to_irt', 'updated_by']

class ExchangeRateSettingAdmin(admin.ModelAdmin):
    list_display = ['currency', 'rate_per_unit']
    readonly_fields = []

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "category_type", "parent", "is_active", "sort_order"]
    list_filter  = ["is_active", "category_type"]
    search_fields = ["name"]
    prepopulated_fields = {"slug": ("name",)}
    list_editable = ["is_active"]


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ["image", "alt_text", "is_primary", "sort_order"]


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    fields = ["sku", "purchase_price_cny", "shipping_cost_cny", "profit_percent", "stock_quantity", "is_active"]


class ExcelUploadForm(forms.Form):
    excel_file = forms.FileField(label="فایل Excel")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display    = ["name", "category", "brand", "is_active"]
    list_filter     = ["is_active", "category__category_type", "category"]
    search_fields   = ["name", "brand", "model_number"]
    prepopulated_fields = {"slug": ("name",)}
    filter_horizontal   = ["compatible_with"]
    list_editable       = ["is_active"]
    readonly_fields     = ["created_at", "updated_at"]
    inlines             = [ProductImageInline, ProductVariantInline]
    actions             = ["delete_selected", "regenerate_seo_action"]
    change_list_template = "admin/catalog/product/change_list.html"

    fieldsets = (
        ("اطلاعات اصلی", {
            "fields": ("name", "slug", "category", "brand", "model_number",
                       "short_description", "description"),
        }),
        ("ویژگی‌های برد دوربین", {
            "fields": ("board_name", "board_system", "board_resolution",
                       "sensor_name", "sensor_size", "ai_processor", "board_dimensions", "board_fps"),
            "classes": ("collapse",),
        }),
        ("ویژگی‌های لنز دوربین", {
            "fields": ("lens_degree", "lens_resolution", "focal_ratio", "lens_aperture",
                       "lens_image_size", "lens_mount", "lens_kit", "lens_holder_pitch", "lens_fov"),
            "classes": ("collapse",),
        }),
        ("ویژگی‌های متعلقات", {
            "fields": ("modem_model", "modem_type", "pin_count", "voltage",
                       "ampere_output", "sim_card", "output_ports", "modem_size"),
            "classes": ("collapse",),
        }),
        ("ویژگی‌های بدنه دوربین", {
            "fields": ("housing_material", "housing_size", "has_microphone"),
            "classes": ("collapse",),
        }),
        ("دیتاشیت", {"fields": ("datasheet_pdf",)}),
        ("محصولات سازگار", {"fields": ("compatible_with",)}),
        ("SEO", {
            "fields": ("meta_title", "meta_description", "keywords", "geo_tags"),
            "classes": ("collapse",),
        }),
        ("نمایش", {"fields": ("is_active", "is_featured")}),
        ("تاریخ‌ها", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    def get_urls(self):
        urls = super().get_urls()
        extra = [
            path("import-excel/",
                 self.admin_site.admin_view(self.import_excel_view),
                 name="catalog_product_import_excel"),
        ]
        return extra + urls

    def import_excel_view(self, request):
        from apps.catalog.excel_importer import import_products_from_excel
        import tempfile, os
        if request.method == "POST":
            form = ExcelUploadForm(request.POST, request.FILES)
            if form.is_valid():
                f = request.FILES["excel_file"]
                with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
                    for chunk in f.chunks(): tmp.write(chunk)
                    tmp_path = tmp.name
                try:
                    dry_run = "dry_run" in request.POST
                    results = import_products_from_excel(tmp_path, dry_run=dry_run)
                    if dry_run:
                        messages.info(request, f"[پیش‌نمایش] {results['created']} محصول اضافه می‌شد")
                    else:
                        messages.success(request, f"✓ {results['created']} اضافه | {results['updated']} بروزرسانی")
                    for e in results.get("errors",[])[:5]:
                        messages.warning(request, e)
                except Exception as e:
                    messages.error(request, f"خطا: {e}")
                finally:
                    os.unlink(tmp_path)
                return redirect("..")
        else:
            form = ExcelUploadForm()
        return render(request, "admin/catalog/product/import_excel.html", {
            "form": form, "title": "آپلود Excel", "opts": self.model._meta,
        })

    @admin.action(description="بازنویسی خودکار SEO")
    def regenerate_seo_action(self, request, queryset):
        try:
            from apps.catalog.seo import generate_all_seo_fields
            count = 0
            for p in queryset:
                changes = generate_all_seo_fields(p, force=True)
                if changes:
                    Product.objects.filter(pk=p.pk).update(**changes)
                    count += 1
            self.message_user(request, f"SEO {count} محصول بازنویسی شد.")
        except Exception as e:
            self.message_user(request, f"خطا: {e}", level="error")


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display  = ["sku", "product", "purchase_price_cny", "stock_quantity", "is_active"]
    search_fields = ["sku", "product__name"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(SeoSettings)
class SeoSettingsAdmin(admin.ModelAdmin):
    fields = ["target_cities", "site_name"]
    def has_add_permission(self, request): return not SeoSettings.objects.exists()
    def has_delete_permission(self, request, obj=None): return False


# ─── Package Admin ────────────────────────────────────────────
from apps.catalog.models import Package, PackageItem

class PackageItemInline(admin.TabularInline):
    model = PackageItem
    extra = 1
    fields = ['product', 'variant', 'quantity']
    autocomplete_fields = ['product']

@admin.register(Package)
class PackageAdmin(admin.ModelAdmin):
    list_display  = ['name', 'discount_percent', 'original_price_display',
                     'final_price_display', 'savings_display', 'is_active', 'is_featured']
    list_filter   = ['is_active', 'is_featured']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}
    inlines = [PackageItemInline]

    def original_price_display(self, obj):
        return f"{obj.original_price:,} ت"
    original_price_display.short_description = "قیمت اصلی"

    def final_price_display(self, obj):
        return f"{obj.final_price:,} ت"
    final_price_display.short_description = "قیمت با تخفیف"

    def savings_display(self, obj):
        return f"{obj.savings:,} ت"
    savings_display.short_description = "صرفه‌جویی"


from apps.catalog.models import ProductPriceHistory, ProductReview

@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    list_display  = ["product", "author_name", "rating", "is_approved", "created_at"]
    list_filter   = ["is_approved", "rating", "created_at"]
    list_editable = ["is_approved"]
    search_fields = ["product__name", "author_name", "body"]
    autocomplete_fields = ["product"]


@admin.register(ProductPriceHistory)
class ProductPriceHistoryAdmin(admin.ModelAdmin):
    list_display = ["variant", "date", "price_irr", "price_cny"]
    list_filter  = ["date"]
    date_hierarchy = "date"
