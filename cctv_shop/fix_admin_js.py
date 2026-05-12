import os, subprocess, sys

admin_content = '''from django.contrib import admin
from django.utils.html import format_html
from .models import Category, ExchangeRateSetting, Product, ProductImage, ProductVariant, SeoSettings


@admin.register(ExchangeRateSetting)
class ExchangeRateSettingAdmin(admin.ModelAdmin):
    list_display = ["rate_cny_to_irt", "updated_at"]
    readonly_fields = ["updated_at", "created_at"]
    def has_add_permission(self, request): return not ExchangeRateSetting.objects.exists()
    def has_delete_permission(self, request, obj=None): return False


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display  = ["name", "category_type", "parent", "is_active", "sort_order"]
    list_filter   = ["is_active", "category_type"]
    search_fields = ["name"]
    prepopulated_fields = {"slug": ("name",)}
    list_editable = ["is_active"]


class ProductImageInline(admin.TabularInline):
    model  = ProductImage
    extra  = 1
    fields = ["image", "alt_text", "is_primary", "sort_order"]


class ProductVariantInline(admin.TabularInline):
    model  = ProductVariant
    extra  = 1
    fields = ["sku", "purchase_price_cny", "shipping_cost", "profit_margin", "stock_quantity", "is_active"]


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display    = ["name", "category", "is_active", "is_featured"]
    list_filter     = ["is_active", "is_featured", "category__category_type", "category"]
    search_fields   = ["name", "brand", "model_number"]
    prepopulated_fields = {"slug": ("name",)}
    filter_horizontal   = ["compatible_with"]
    list_editable       = ["is_active"]
    readonly_fields     = ["created_at", "updated_at"]
    inlines             = [ProductImageInline, ProductVariantInline]

    class Media:
        js = ("admin/js/category_filter.js",)

    def get_fieldsets(self, request, obj=None):
        # تشخیص نوع دسته از query string (برای صفحه add)
        cat_type = None
        if obj and obj.category_id:
            cat_type = obj.category.category_type
        elif request.GET.get("cat_type"):
            cat_type = request.GET.get("cat_type")

        base = [
            ("اطلاعات اصلی", {
                "fields": ("name", "slug", "category", "brand", "model_number",
                           "short_description", "description"),
            }),
        ]

        if cat_type == "board":
            base.append(("ویژگی‌های برد دوربین", {
                "fields": ("board_name", "board_system", "board_resolution",
                           "sensor_name", "sensor_size", "ai_processor", "board_dimensions"),
            }))
        elif cat_type == "lens":
            base.append(("ویژگی‌های لنز دوربین", {
                "fields": ("lens_name", "lens_degree", "lens_type",
                           "focal_ratio", "lens_resolution"),
            }))
        elif cat_type == "modem":
            base.append(("ویژگی‌های متعلقات", {
                "fields": ("modem_model", "modem_type", "pin_count", "voltage",
                           "ampere_output", "sim_card", "output_ports", "modem_size"),
            }))
        elif cat_type == "housing":
            base.append(("ویژگی‌های بدنه دوربین", {
                "fields": ("housing_material", "housing_type", "housing_size", "has_microphone"),
            }))
        else:
            # هیچ دسته‌ای انتخاب نشده - راهنما نشان بده
            base.append(("⚠️ راهنما", {
                "fields": (),
                "description": "ابتدا دسته‌بندی را انتخاب کنید و ذخیره کنید — سپس ویژگی‌های اختصاصی نمایش داده می‌شوند.",
            }))

        base += [
            ("دیتاشیت", {"fields": ("datasheet_pdf",)}),
            ("محصولات سازگار", {"fields": ("compatible_with",)}),
            ("SEO", {
                "fields": ("meta_title", "meta_description", "keywords", "geo_tags"),
                "classes": ("collapse",),
            }),
            ("نمایش", {"fields": ("is_active", "is_featured")}),
            ("تاریخ‌ها", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
        ]
        return base

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

    def response_add(self, request, obj, post_url_continue=None):
        """بعد از ذخیره اول، به صفحه ویرایش هدایت کن تا ویژگی‌ها نمایش داده شود"""
        return super().response_add(request, obj, post_url_continue)


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display    = ["sku", "product", "purchase_price_cny", "stock_quantity", "is_active"]
    search_fields   = ["sku", "product__name"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(SeoSettings)
class SeoSettingsAdmin(admin.ModelAdmin):
    fields = ["target_cities", "site_name"]
    def has_add_permission(self, request): return not SeoSettings.objects.exists()
    def has_delete_permission(self, request, obj=None): return False
'''

with open(os.path.join('apps','catalog','admin.py'), 'w', encoding='utf-8') as f:
    f.write(admin_content)
print("OK - admin.py")

# ساخت فایل JavaScript
js_dir = os.path.join('static','admin','js')
os.makedirs(js_dir, exist_ok=True)
js_content = '''
// وقتی دسته‌بندی انتخاب می‌شود، صفحه را با نوع دسته reload کن
(function() {
    document.addEventListener("DOMContentLoaded", function() {
        var catField = document.getElementById("id_category");
        if (!catField) return;

        catField.addEventListener("change", function() {
            var catId = this.value;
            if (!catId) return;

            // دریافت نوع دسته از API
            fetch("/api/catalog/categories/")
                .then(function(r) { return r.json(); })
                .then(function(data) {
                    var cats = Array.isArray(data) ? data : (data.results || []);
                    var selected = cats.find(function(c) { return String(c.id) === String(catId); });
                    if (selected && selected.category_type) {
                        var url = new URL(window.location.href);
                        url.searchParams.set("cat_type", selected.category_type);
                        window.location.href = url.toString();
                    }
                })
                .catch(function(e) { console.error(e); });
        });
    });
})();
'''
with open(os.path.join(js_dir, 'category_filter.js'), 'w', encoding='utf-8') as f:
    f.write(js_content)
print("OK - category_filter.js")

r = subprocess.run([sys.executable,'manage.py','check','--verbosity=0'],
                   capture_output=True, text=True)
if r.returncode == 0:
    print("OK - همه چیز درست است!")
    print("\nحالا بزنید: python manage.py runserver")
else:
    for line in (r.stdout+r.stderr).strip().split('\n')[-5:]:
        if line.strip(): print(" ", line)
