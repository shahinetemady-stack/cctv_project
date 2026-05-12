"""
python REBUILD.py
همه چیز را از صفر درست می‌کند
"""
import os, subprocess, sys

print("="*60)
print("  بازسازی کامل پروژه")
print("="*60)

# ─── 1. حذف JS مشکل‌ساز ─────────────────────────────────
js_path = os.path.join('static','admin','js','category_filter.js')
if os.path.exists(js_path):
    os.remove(js_path)
    print("OK - category_filter.js حذف شد")

# ─── 2. admin.py بدون JS و با fieldsets ساده ────────────
admin_content = '''from django.contrib import admin
from django.utils.html import format_html
from django import forms
from django.urls import path
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Category, ExchangeRateSetting, Product, ProductImage, ProductVariant, SeoSettings


@admin.register(ExchangeRateSetting)
class ExchangeRateSettingAdmin(admin.ModelAdmin):
    list_display = ["rate_cny_to_irt", "updated_at"]
    readonly_fields = ["updated_at", "created_at"]
    def has_add_permission(self, request): return not ExchangeRateSetting.objects.exists()
    def has_delete_permission(self, request, obj=None): return False


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
                       "sensor_name", "sensor_size", "ai_processor", "board_dimensions"),
            "classes": ("collapse",),
        }),
        ("ویژگی‌های لنز دوربین", {
            "fields": ("lens_name", "lens_degree", "lens_type",
                       "focal_ratio", "lens_resolution"),
            "classes": ("collapse",),
        }),
        ("ویژگی‌های متعلقات", {
            "fields": ("modem_model", "modem_type", "pin_count", "voltage",
                       "ampere_output", "sim_card", "output_ports", "modem_size"),
            "classes": ("collapse",),
        }),
        ("ویژگی‌های بدنه دوربین", {
            "fields": ("housing_material", "housing_type", "housing_size", "has_microphone"),
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
'''

with open(os.path.join('apps','catalog','admin.py'), 'w', encoding='utf-8') as f:
    f.write(admin_content)
print("OK - catalog/admin.py")

# ─── 3. template ها ──────────────────────────────────────
tpl_dir = os.path.join('templates','admin','catalog','product')
os.makedirs(tpl_dir, exist_ok=True)

with open(os.path.join(tpl_dir,'change_list.html'), 'w', encoding='utf-8') as f:
    f.write('''{% extends "admin/change_list.html" %}
{% block object-tools-items %}
<li><a href="import-excel/" class="addlink" style="background:#417690">📊 آپلود Excel</a></li>
{{ block.super }}
{% endblock %}
''')

with open(os.path.join(tpl_dir,'import_excel.html'), 'w', encoding='utf-8') as f:
    f.write('''{% extends "admin/base_site.html" %}
{% block content %}
<div style="direction:rtl;max-width:600px;margin:20px auto">
  <h2>📊 آپلود محصولات از Excel</h2>
  <form method="post" enctype="multipart/form-data" style="background:#fff;padding:20px;border-radius:8px;border:1px solid #ddd">
    {% csrf_token %}
    <table>{{ form.as_table }}</table><br>
    <label><input type="checkbox" name="dry_run"> پیش‌نمایش (بدون ذخیره)</label><br><br>
    <button type="submit" class="default">آپلود</button>
    <a href=".." style="margin-right:10px">انصراف</a>
  </form>
</div>
{% endblock %}
''')
print("OK - templates")

# ─── 4. check ────────────────────────────────────────────
r = subprocess.run([sys.executable,'manage.py','check','--verbosity=0'],
                   capture_output=True, text=True)
if r.returncode == 0:
    print("OK - Django check موفق")
else:
    for line in (r.stdout+r.stderr).strip().split('\n')[-5:]:
        if line.strip(): print(" ", line)

print("\n" + "="*60)
print("  تمام! حالا:")
print("  1. python manage.py runserver")
print("  2. http://127.0.0.1:8000/admin")
print("  3. دسته‌بندی‌ها را بسازید")
print("  4. محصولات را با Excel آپلود کنید")
print("="*60)
