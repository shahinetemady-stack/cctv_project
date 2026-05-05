"""
apps/catalog/admin.py
──────────────────────
Django Admin configuration for the catalog app.

Features:
  - نمایش فرمول قیمت به صورت read-only
  - هشدار موجودی کم با رنگ قرمز
  - فیلتر پیشرفته بر اساس تمام محورهای تکنیکی
  - inline برای تصاویر و variant‌ها
"""

from django.contrib import admin
from django.urls import path
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from import_export.admin import ImportExportModelAdmin
from import_export import resources, fields

from .models import Category, ExchangeRateSetting, Product, ProductImage, ProductVariant, SeoSettings


# ─── Exchange Rate ─────────────────────────────────────────────────────────────

@admin.register(ExchangeRateSetting)
class ExchangeRateSettingAdmin(admin.ModelAdmin):
    list_display = ["rate_usd_to_irt_formatted", "updated_at", "updated_by"]
    readonly_fields = ["updated_at", "updated_by", "created_at"]

    def rate_usd_to_irt_formatted(self, obj):
        return format_html(
            '<span style="font-size:1.2em;font-weight:bold;color:#0066FF">'
            "{:,} تومان"
            "</span>",
            obj.rate_usd_to_irt,
        )
    rate_usd_to_irt_formatted.short_description = "نرخ دلار"

    def save_model(self, request, obj, form, change):
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)

    def has_add_permission(self, request):
        # Singleton — فقط یک رکورد مجاز است
        return not ExchangeRateSetting.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


# ─── Category ─────────────────────────────────────────────────────────────────

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "parent", "is_active", "sort_order", "product_count"]
    list_filter = ["is_active", "parent"]
    search_fields = ["name"]
    prepopulated_fields = {"slug": ("name",)}
    list_editable = ["sort_order", "is_active"]
    ordering = ["sort_order", "name"]

    def product_count(self, obj):
        return obj.products.filter(is_active=True).count()
    product_count.short_description = "تعداد محصول"


# ─── Product Inlines ───────────────────────────────────────────────────────────

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ["image", "alt_text", "is_primary", "sort_order"]
    ordering = ["-is_primary", "sort_order"]


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    fields = [
        "sku", "name_suffix",
        "purchase_price_usd", "shipping_cost", "profit_margin",
        "stock_quantity", "reserved_qty",
        "computed_price_display",
        "is_active",
    ]
    readonly_fields = ["computed_price_display"]

    def computed_price_display(self, obj):
        if not obj.pk:
            return "—"
        price = obj.final_price
        color = "#FF3B3B" if obj.is_low_stock else ("#00C896" if obj.is_in_stock else "#888")
        return format_html(
            '<span style="color:{};font-weight:bold">{:,} تومان</span>',
            color,
            price,
        )
    computed_price_display.short_description = "قیمت نهایی"


# ─── Product Import/Export Resource ───────────────────────────────────────────

class ProductVariantResource(resources.ModelResource):
    """برای آپلود محصولات با اکسل از طریق پنل ادمین."""

    product_name = fields.Field(attribute="product__name", column_name="نام محصول")
    category_name = fields.Field(attribute="product__category__name", column_name="دسته‌بندی")

    class Meta:
        model = ProductVariant
        fields = [
            "id", "sku", "product_name", "category_name",
            "purchase_price_usd", "shipping_cost", "profit_margin",
            "stock_quantity",
        ]
        export_order = fields


# ─── Product ──────────────────────────────────────────────────────────────────

@admin.register(Product)
class ProductAdmin(ImportExportModelAdmin):
    resource_class = ProductVariantResource

    list_display = [
        "name", "category", "part_type", "chipset", "voltage", "lens_mount",
        "total_stock_display", "seo_status_display", "is_active", "is_featured",
    ]
    list_filter = [
        "is_active", "is_featured", "part_type", "lens_mount",
        "category", ("created_at", admin.DateFieldListFilter),
    ]
    search_fields = ["name", "model_number", "chipset", "brand"]
    prepopulated_fields = {"slug": ("name",)}
    filter_horizontal = ["compatible_with"]
    list_editable = ["is_active", "is_featured"]
    readonly_fields = ["created_at", "updated_at", "seo_preview"]
    actions = ["action_regenerate_seo"]

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
        ("محصولات سازگار", {
            "fields": ("compatible_with",),
        }),
        ("🔍 SEO — خودکار پر می‌شود", {
            "fields": ("meta_title", "meta_description", "keywords", "geo_tags", "seo_preview"),
            "description": "این فیلدها هنگام ذخیره خودکار پر می‌شوند. می‌توانید دستی هم ویرایش کنید.",
        }),
        ("نمایش", {
            "fields": ("is_active", "is_featured"),
        }),
        ("تاریخ‌ها", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    inlines = [ProductImageInline, ProductVariantInline]

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "<int:product_id>/regenerate-seo/",
                self.admin_site.admin_view(self.regenerate_seo_view),
                name="catalog_product_regenerate_seo",
            )
        ]
        return custom + urls

    def regenerate_seo_view(self, request, product_id):
        """بازنویسی خودکار SEO برای یک محصول."""
        from apps.catalog.seo import generate_all_seo_fields
        try:
            product = Product.objects.get(pk=product_id)
            changes = generate_all_seo_fields(product, force=True)
            if changes:
                for field, value in changes.items():
                    setattr(product, field, value)
                Product.objects.filter(pk=product_id).update(**changes)
                messages.success(request, f"✓ SEO محصول '{product.name}' بازنویسی شد ({len(changes)} فیلد)")
            else:
                messages.info(request, "هیچ تغییری لازم نبود.")
        except Product.DoesNotExist:
            messages.error(request, "محصول یافت نشد.")
        return HttpResponseRedirect(f"../")

    def seo_status_display(self, obj):
        """نمایش وضعیت SEO با رنگ."""
        filled = sum([
            bool(obj.meta_title),
            bool(obj.meta_description),
            bool(obj.keywords),
            bool(obj.geo_tags),
        ])
        color = {4: "#00C896", 3: "#FF9500", 2: "#FF9500"}.get(filled, "#FF3B3B")
        regen_url = f"{obj.pk}/regenerate-seo/"
        return format_html(
            "<span style='color:{}'>{}/۴</span> "            "<a href='{}' style='font-size:11px;color:#0066FF' title='بازنویسی خودکار SEO'>🔄</a>",
            color, filled, regen_url
        )
    seo_status_display.short_description = "SEO"
    seo_status_display.allow_tags = True

    def seo_preview(self, obj):
        """پیش‌نمایش SEO در فرم ویرایش."""
        if not obj.pk:
            return "پس از ذخیره نمایش داده می‌شود."
        return format_html(
            "<div style='background:#f8f9fa;padding:12px;border-radius:8px;direction:rtl'>"            "<div style='color:#1a0dab;font-size:18px'>{}</div>"            "<div style='color:#006621;font-size:13px'>{}</div>"            "<div style='color:#545454;font-size:13px;margin-top:4px'>{}</div>"            "</div>",
            obj.meta_title or obj.name,
            f"cctvparts.ir/products/{obj.slug}",
            obj.meta_description or "—",
        )
    seo_preview.short_description = "پیش‌نمایش در گوگل"

    @admin.action(description="🔄 بازنویسی خودکار SEO برای محصولات انتخاب‌شده")
    def action_regenerate_seo(self, request, queryset):
        from apps.catalog.seo import generate_all_seo_fields
        count = 0
        for product in queryset:
            changes = generate_all_seo_fields(product, force=True)
            if changes:
                Product.objects.filter(pk=product.pk).update(**changes)
                count += 1
        self.message_user(request, f"✓ SEO {count} محصول بازنویسی شد.", messages.SUCCESS)

    def total_stock_display(self, obj):
        total = obj.available_stock
        if total == 0:
            color, label = "#FF3B3B", "ناموجود"
        elif total <= 5:
            color, label = "#FF9500", f"کم ({total})"
        else:
            color, label = "#00C896", str(total)
        return format_html(
            '<span style="color:{};font-weight:bold">{}</span>',
            color, label,
        )
    total_stock_display.short_description = "موجودی"


# ─── SeoSettings Admin ───────────────────────────────────────────────────────

@admin.register(SeoSettings)
class SeoSettingsAdmin(admin.ModelAdmin):
    """تنظیمات سئو سراسری — فقط یک رکورد."""
    fields = ['target_cities', 'site_name']

    def has_add_permission(self, request):
        return not SeoSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = [
        "sku", "product", "name_suffix",
        "final_price_display", "available_stock_display",
        "reserved_qty", "is_active",
    ]
    list_filter = ["is_active", ("product__category", admin.RelatedOnlyFieldListFilter)]
    search_fields = ["sku", "product__name"]
    readonly_fields = ["final_price_display", "available_stock_display", "created_at", "updated_at"]

    def final_price_display(self, obj):
        return format_html(
            '<b style="color:#0066FF">{:,}</b> تومان',
            obj.final_price,
        )
    final_price_display.short_description = "قیمت نهایی"

    def available_stock_display(self, obj):
        stock = obj.available_stock
        if stock == 0:
            return format_html('<span style="color:#FF3B3B;font-weight:bold">ناموجود</span>')
        elif stock <= 5:
            return format_html(
                '<span style="color:#FF9500;font-weight:bold">⚠ {} عدد</span>', stock
            )
        return format_html('<span style="color:#00C896">{} عدد</span>', stock)
    available_stock_display.short_description = "موجودی واقعی"
