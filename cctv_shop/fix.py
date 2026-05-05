"""
FIX.py - رفع همه مشکلات یکجا
در پوشه cctv_shop اجرا کنید: python FIX.py
"""
import os, sys, ast

print("\n" + "="*55)
print("  رفع کامل همه مشکلات")
print("="*55 + "\n")

def write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"  OK: {path}")

# ════════════════════════════════════════════════════════
# 1. همه admin.py ها را بازنویسی کن
# ════════════════════════════════════════════════════════
print("[1/5] بازنویسی فایل‌های admin...")

write('apps/catalog/admin.py', """
from django.contrib import admin
from django.utils.html import format_html
from import_export.admin import ImportExportModelAdmin
from import_export import resources
from .models import Category, ExchangeRateSetting, Product, ProductImage, ProductVariant, SeoSettings


@admin.register(ExchangeRateSetting)
class ExchangeRateSettingAdmin(admin.ModelAdmin):
    list_display = ["rate_usd_to_irt", "updated_at"]
    readonly_fields = ["updated_at", "created_at"]
    def has_add_permission(self, request):
        return not ExchangeRateSetting.objects.exists()
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "parent", "is_active", "sort_order"]
    list_filter = ["is_active"]
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
    fields = ["sku", "purchase_price_usd", "shipping_cost", "profit_margin",
              "stock_quantity", "reserved_qty", "is_active"]


class ProductVariantResource(resources.ModelResource):
    class Meta:
        model = ProductVariant
        fields = ["id", "sku", "purchase_price_usd", "shipping_cost", "profit_margin", "stock_quantity"]


@admin.register(Product)
class ProductAdmin(ImportExportModelAdmin):
    resource_class = ProductVariantResource
    list_display = ["name", "category", "part_type", "chipset", "is_active", "seo_status"]
    list_filter = ["is_active", "part_type", "category"]
    search_fields = ["name", "chipset", "brand"]
    prepopulated_fields = {"slug": ("name",)}
    filter_horizontal = ["compatible_with"]
    list_editable = ["is_active"]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [ProductImageInline, ProductVariantInline]
    actions = ["regenerate_seo_action"]
    fieldsets = (
        ("اطلاعات اصلی", {"fields": ("name", "slug", "category", "brand", "model_number", "short_description", "description")}),
        ("مشخصات فنی", {"fields": ("part_type", "chipset", "voltage", "lens_mount", "resolution", "extra_specs")}),
        ("فایل‌ها", {"fields": ("datasheet_pdf", "whatsapp_link", "bale_link")}),
        ("سازگاری", {"fields": ("compatible_with",)}),
        ("SEO", {"fields": ("meta_title", "meta_description", "keywords", "geo_tags")}),
        ("نمایش", {"fields": ("is_active", "is_featured")}),
        ("تاریخ‌ها", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )
    def seo_status(self, obj):
        n = sum([bool(obj.meta_title), bool(obj.meta_description), bool(obj.keywords), bool(obj.geo_tags)])
        color = "#00C896" if n == 4 else "#FF9500" if n >= 2 else "#FF3B3B"
        return format_html('<span style="color:{}">{}/4 SEO</span>', color, n)
    seo_status.short_description = "SEO"

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
    list_display = ["sku", "product", "is_active"]
    search_fields = ["sku", "product__name"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(SeoSettings)
class SeoSettingsAdmin(admin.ModelAdmin):
    fields = ["target_cities", "site_name"]
    def has_add_permission(self, request):
        return not SeoSettings.objects.exists()
    def has_delete_permission(self, request, obj=None):
        return False
""")

write('apps/orders/admin.py', """
from django.contrib import admin
from django.utils.html import format_html
from .models import Order, OrderItem, StockReservation


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    fields = ["variant", "quantity", "unit_price", "confirmed_unit_price"]
    readonly_fields = ["unit_price"]


class StockReservationInline(admin.TabularInline):
    model = StockReservation
    extra = 0
    readonly_fields = ["variant", "quantity", "reserved_until", "is_released"]
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ["order_number", "user", "status", "order_type", "total_amount", "created_at"]
    list_filter = ["status", "order_type"]
    search_fields = ["order_number", "user__email"]
    readonly_fields = ["order_number", "created_at", "updated_at", "payment_ref_id", "paid_at"]
    inlines = [OrderItemInline, StockReservationInline]
    ordering = ["-created_at"]


@admin.register(StockReservation)
class StockReservationAdmin(admin.ModelAdmin):
    list_display = ["variant", "order", "quantity", "reserved_until", "is_released"]
    list_filter = ["is_released"]
    readonly_fields = ["released_at", "created_at", "updated_at"]
""")

write('apps/users/admin.py', """
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, UserProfile


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    fields = ["user_type", "company_name", "national_id", "is_approved", "credit_limit", "address", "notes"]


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    inlines = [UserProfileInline]
    list_display = ["email", "get_full_name", "is_active", "date_joined"]
    list_filter = ["is_active", "is_staff"]
    search_fields = ["email", "first_name", "last_name"]
    ordering = ["-date_joined"]
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("اطلاعات شخصی", {"fields": ("first_name", "last_name", "phone")}),
        ("دسترسی‌ها", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("تاریخ‌ها", {"fields": ("date_joined", "last_login"), "classes": ("collapse",)}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("email", "password1", "password2")}),
    )
""")

write('apps/inventory/admin.py', """
from django.contrib import admin
from django.utils.html import format_html
from .models import StockAlert, StockMovement


@admin.register(StockAlert)
class StockAlertAdmin(admin.ModelAdmin):
    list_display = ["variant", "stock_at_alert", "is_resolved", "created_at"]
    list_filter = ["is_resolved"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ["variant", "movement_type", "quantity_change", "created_at"]
    list_filter = ["movement_type"]
    readonly_fields = ["created_at"]
    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
""")

write('apps/notifications/admin.py', """
from django.contrib import admin
from .models import NotificationLog


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ["recipient_address", "channel", "status", "created_at"]
    list_filter = ["status", "channel"]
    readonly_fields = ["created_at", "updated_at"]
    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
""")

write('apps/payment/admin.py', """
from django.contrib import admin
from django.utils.html import format_html
from .models import PaymentTransaction


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ["id", "order", "amount", "status", "created_at"]
    list_filter = ["status"]
    search_fields = ["order__order_number"]
    readonly_fields = ["created_at", "updated_at"]
    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
""")

# payments (duplicate app) - خالی کن
if os.path.exists('apps/payments/admin.py'):
    write('apps/payments/admin.py', "# unused\n")

# ════════════════════════════════════════════════════════
# 2. بررسی syntax همه فایل‌ها
# ════════════════════════════════════════════════════════
print("\n[2/5] بررسی syntax...")
errors = []
for root, dirs, files in os.walk('apps'):
    dirs[:] = [d for d in dirs if d != '__pycache__']
    for f in files:
        if f.endswith('.py') and 'venv' not in root:
            path = os.path.join(root, f)
            try:
                ast.parse(open(path, encoding='utf-8').read())
            except SyntaxError as e:
                errors.append(f"  ERROR: {path}: {e}")

if errors:
    for e in errors:
        print(e)
else:
    print("  OK - همه فایل‌ها سالم هستند")

# ════════════════════════════════════════════════════════
# 3. migrate
# ════════════════════════════════════════════════════════
print("\n[3/5] اجرای migrate...")
import subprocess
r = subprocess.run([sys.executable, 'manage.py', 'migrate', '--verbosity=0'],
                   capture_output=True, text=True)
if r.returncode == 0:
    print("  OK - migrate موفق بود")
else:
    # نشان دادن آخرین خطا
    lines = (r.stdout + r.stderr).strip().split('\n')
    for line in lines[-5:]:
        if line.strip():
            print(" ", line)

# ════════════════════════════════════════════════════════
# 4. SEO برای محصولات قدیمی
# ════════════════════════════════════════════════════════
print("\n[4/5] تولید SEO برای محصولات...")
r2 = subprocess.run([sys.executable, 'manage.py', 'generate_missing_seo'],
                    capture_output=True, text=True)
if r2.returncode == 0:
    print("  OK")
    if r2.stdout:
        print(" ", r2.stdout.strip()[:100])
else:
    print("  (SEO بعداً اجرا می‌شود)")

# ════════════════════════════════════════════════════════
# 5. نتیجه
# ════════════════════════════════════════════════════════
print("\n[5/5] بررسی نهایی...")
r3 = subprocess.run([sys.executable, 'manage.py', 'check', '--verbosity=0'],
                    capture_output=True, text=True)
if r3.returncode == 0:
    print("  OK - Django check موفق بود")
else:
    lines = (r3.stdout + r3.stderr).strip().split('\n')
    for line in lines[-5:]:
        if line.strip():
            print(" ", line)

print("\n" + "="*55)
print("  تمام! حالا بزنید:")
print()
print("  python manage.py runserver")
print("="*55 + "\n")
