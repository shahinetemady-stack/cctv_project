"""
RESTRUCTURE.py - بازسازی کامل ساختار محصولات
در پوشه cctv_shop اجرا کنید: python RESTRUCTURE.py
"""
import os, sys, subprocess

print("\n" + "="*60)
print("  بازسازی کامل ساختار محصولات")
print("="*60 + "\n")

def write(path, content):
    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else '.', exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"  OK: {path}")

# ════════════════════════════════════════════════════════
# 1. models.py - ساختار جدید
# ════════════════════════════════════════════════════════
print("[1/4] بازنویسی models.py ...")

write('apps/catalog/models.py', '''"""
apps/catalog/models.py - ساختار جدید با ویژگی‌های اختصاصی هر دسته
ارز مرجع: یوان چینی (CNY)
"""
from decimal import Decimal
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.text import slugify
from apps.core.models import SingletonModel, TimeStampedModel


# ─── نرخ ارز (یوان چینی) ──────────────────────────────────────────────────────
class ExchangeRateSetting(SingletonModel):
    """نرخ یوان چینی به تومان - singleton"""
    rate_cny_to_irt = models.PositiveBigIntegerField(
        default=8_500,
        verbose_name="نرخ یوان (تومان)",
        help_text="هر یوان چینی چند تومان؟  مثال: 8500",
    )
    updated_by = models.ForeignKey(
        "users.User", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="+",
        verbose_name="بروزرسانی توسط",
    )
    class Meta:
        db_table = "catalog_exchange_rate"
        verbose_name = "نرخ ارز (یوان)"
        verbose_name_plural = "نرخ ارز (یوان)"
    def __str__(self):
        return f"نرخ یوان: {self.rate_cny_to_irt:,} تومان"


# ─── تنظیمات SEO ──────────────────────────────────────────────────────────────
class SeoSettings(SingletonModel):
    target_cities = models.CharField(
        max_length=500, default="تهران، مشهد، اصفهان، شیراز، تبریز، کرج",
        verbose_name="شهرهای هدف",
    )
    site_name = models.CharField(
        max_length=100, default="فروشگاه قطعات دوربین مداربسته",
        verbose_name="نام سایت",
    )
    class Meta:
        db_table = "catalog_seo_settings"
        verbose_name = "تنظیمات سئو"
        verbose_name_plural = "تنظیمات سئو"
    def __str__(self):
        return "تنظیمات سئو"


# ─── دسته‌بندی ────────────────────────────────────────────────────────────────
class Category(TimeStampedModel):
    class CategoryType(models.TextChoices):
        BOARD   = "board",   "برد دوربین مداربسته"
        LENS    = "lens",    "لنز دوربین مداربسته"
        MODEM   = "modem",   "متعلقات"
        HOUSING = "housing", "بدنه دوربین مداربسته"
        OTHER   = "other",   "سایر"

    name = models.CharField(max_length=150, verbose_name="نام دسته‌بندی")
    slug = models.SlugField(max_length=160, unique=True, allow_unicode=True, verbose_name="اسلاگ")
    category_type = models.CharField(
        max_length=20, choices=CategoryType.choices,
        default=CategoryType.OTHER, verbose_name="نوع دسته",
        db_index=True,
    )
    parent = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="children", verbose_name="دسته والد",
    )
    icon = models.CharField(max_length=100, blank=True, verbose_name="آیکون")
    image = models.ImageField(upload_to="categories/", null=True, blank=True, verbose_name="تصویر")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    sort_order = models.PositiveSmallIntegerField(default=0, verbose_name="ترتیب")

    class Meta:
        db_table = "catalog_category"
        verbose_name = "دسته‌بندی"
        verbose_name_plural = "دسته‌بندی‌ها"
        ordering = ["sort_order", "name"]

    def __str__(self):
        return f"{self.parent.name} / {self.name}" if self.parent else self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name, allow_unicode=True)
        super().save(*args, **kwargs)


# ─── محصول ────────────────────────────────────────────────────────────────────
class Product(TimeStampedModel):
    # ── اطلاعات پایه ──────────────────────────────────────────────
    name     = models.CharField(max_length=255, verbose_name="نام محصول")
    slug     = models.SlugField(max_length=270, unique=True, allow_unicode=True, verbose_name="اسلاگ")
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products", verbose_name="دسته‌بندی")
    brand    = models.CharField(max_length=100, blank=True, verbose_name="شرکت سازنده")
    model_number = models.CharField(max_length=100, blank=True, verbose_name="شماره مدل")
    description       = models.TextField(blank=True, verbose_name="توضیحات")
    short_description = models.CharField(max_length=500, blank=True, verbose_name="توضیح کوتاه")

    # ── ویژگی‌های برد دوربین ──────────────────────────────────────
    board_name      = models.CharField(max_length=150, blank=True, verbose_name="نام برد")
    board_system    = models.CharField(max_length=100, blank=True, verbose_name="سیستم")
    board_resolution= models.CharField(max_length=50,  blank=True, verbose_name="رزولوشن (برد)")
    sensor_name     = models.CharField(max_length=150, blank=True, verbose_name="نام سنسور")
    sensor_size     = models.CharField(max_length=50,  blank=True, verbose_name="اندازه سنسور")
    ai_processor    = models.CharField(max_length=150, blank=True, verbose_name="AI پردازنده")
    board_dimensions= models.CharField(max_length=100, blank=True, verbose_name="ابعاد (برد)")

    # ── ویژگی‌های لنز ─────────────────────────────────────────────
    lens_name       = models.CharField(max_length=150, blank=True, verbose_name="نام لنز")
    lens_resolution = models.CharField(max_length=50,  blank=True, verbose_name="رزولوشن (لنز)")
    lens_degree     = models.CharField(max_length=50,  blank=True, verbose_name="درجه لنز")
    lens_type       = models.CharField(max_length=100, blank=True, verbose_name="نوع لنز")
    focal_ratio     = models.CharField(max_length=50,  blank=True, verbose_name="نسبت کانونی")

    # ── ویژگی‌های متعلقات (مودم) ──────────────────────────────────
    modem_model     = models.CharField(max_length=150, blank=True, verbose_name="مدل")
    modem_type      = models.CharField(max_length=100, blank=True, verbose_name="نوع")
    pin_count       = models.CharField(max_length=50,  blank=True, verbose_name="تعداد پین")
    voltage         = models.CharField(max_length=50,  blank=True, verbose_name="ولتاژ کاری")
    ampere_output   = models.CharField(max_length=50,  blank=True, verbose_name="آمپر خروجی")
    sim_card        = models.BooleanField(default=False, verbose_name="قابلیت سیم کارت")
    output_ports    = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name="تعداد پورت خروجی")
    modem_size      = models.CharField(max_length=100, blank=True, verbose_name="سایز")

    # ── ویژگی‌های بدنه دوربین ─────────────────────────────────────
    housing_material= models.CharField(max_length=100, blank=True, verbose_name="جنس بدنه")
    housing_type    = models.CharField(max_length=100, blank=True, verbose_name="نوع بدنه")
    housing_size    = models.CharField(max_length=100, blank=True, verbose_name="سایز دوربین")
    has_microphone  = models.BooleanField(default=False, verbose_name="قابلیت میکروفون")

    # ── فایل‌ها و لینک‌ها ─────────────────────────────────────────
    datasheet_pdf = models.FileField(upload_to="datasheets/%Y/%m/", null=True, blank=True, verbose_name="دیتاشیت PDF")
    whatsapp_link = models.URLField(blank=True, verbose_name="لینک واتساپ")
    bale_link     = models.URLField(blank=True, verbose_name="لینک بله")

    # ── محصولات سازگار ────────────────────────────────────────────
    compatible_with = models.ManyToManyField("self", symmetrical=True, blank=True, verbose_name="محصولات سازگار")

    # ── وضعیت ─────────────────────────────────────────────────────
    is_active   = models.BooleanField(default=True,  verbose_name="فعال", db_index=True)
    is_featured = models.BooleanField(default=False, verbose_name="ویژه")

    # ── SEO ───────────────────────────────────────────────────────
    meta_title       = models.CharField(max_length=60,  blank=True, verbose_name="Meta Title")
    meta_description = models.CharField(max_length=160, blank=True, verbose_name="Meta Description")
    keywords         = models.CharField(max_length=500, blank=True, verbose_name="کلمات کلیدی")
    geo_tags         = models.CharField(max_length=300, blank=True, verbose_name="شهرهای هدف")

    class Meta:
        db_table = "catalog_product"
        verbose_name = "محصول"
        verbose_name_plural = "محصولات"
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        from apps.catalog.seo import generate_slug, generate_all_seo_fields
        if not self.slug:
            self.slug = generate_slug(self.name, self.__class__, self.pk)
        seo = generate_all_seo_fields(self, force=False)
        for k, v in seo.items():
            setattr(self, k, v)
        super().save(*args, **kwargs)

    def generate_seo_fields(self, force=False):
        from apps.catalog.seo import generate_all_seo_fields
        for k, v in generate_all_seo_fields(self, force=force).items():
            setattr(self, k, v)

    @property
    def main_image(self):
        return self.images.filter(is_primary=True).first()

    @property
    def available_stock(self):
        return sum(v.available_stock for v in self.variants.all())

    @property
    def category_type(self):
        return self.category.category_type if self.category_id else None


# ─── تصویر محصول ──────────────────────────────────────────────────────────────
class ProductImage(TimeStampedModel):
    product    = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images", verbose_name="محصول")
    image      = models.ImageField(upload_to="products/%Y/%m/", verbose_name="تصویر")
    alt_text   = models.CharField(max_length=255, blank=True, verbose_name="متن جایگزین")
    is_primary = models.BooleanField(default=False, verbose_name="تصویر اصلی")
    sort_order = models.PositiveSmallIntegerField(default=0, verbose_name="ترتیب")

    class Meta:
        db_table = "catalog_product_image"
        verbose_name = "تصویر محصول"
        verbose_name_plural = "تصاویر محصول"
        ordering = ["-is_primary", "sort_order"]

    def save(self, *args, **kwargs):
        if self.is_primary:
            ProductImage.objects.filter(product=self.product, is_primary=True).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)


# ─── نسخه محصول (Variant) ─────────────────────────────────────────────────────
class ProductVariant(TimeStampedModel):
    """
    فرمول قیمت:
      final_price = (purchase_price_cny × rate_cny_to_irt) + shipping_cost + profit_margin
    """
    product    = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants", verbose_name="محصول")
    sku        = models.CharField(max_length=100, unique=True, verbose_name="کد SKU")
    name_suffix= models.CharField(max_length=100, blank=True, verbose_name="پسوند نام")

    # موجودی
    stock_quantity = models.PositiveIntegerField(default=0, verbose_name="موجودی کل")
    reserved_qty   = models.PositiveIntegerField(default=0, verbose_name="رزرو شده")

    # قیمت‌گذاری - یوان چینی
    purchase_price_cny = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
        verbose_name="قیمت خرید (یوان)",
        help_text="قیمت خرید به یوان چینی",
    )
    shipping_cost  = models.PositiveBigIntegerField(default=0, verbose_name="هزینه حمل (تومان)")
    profit_margin  = models.PositiveBigIntegerField(default=0, verbose_name="سود (تومان)")
    is_active      = models.BooleanField(default=True, verbose_name="فعال")

    class Meta:
        db_table = "catalog_product_variant"
        verbose_name = "نسخه محصول"
        verbose_name_plural = "نسخه‌های محصول"
        ordering = ["product", "sku"]

    def __str__(self):
        suffix = f" — {self.name_suffix}" if self.name_suffix else ""
        return f"{self.product.name}{suffix} [{self.sku}]"

    @property
    def final_price(self) -> int:
        """قیمت نهایی = (قیمت یوان × نرخ یوان) + حمل + سود"""
        rate = ExchangeRateSetting.get_instance().rate_cny_to_irt
        cny_part = int(self.purchase_price_cny * rate)
        return cny_part + self.shipping_cost + self.profit_margin

    @property
    def available_stock(self) -> int:
        return max(0, self.stock_quantity - self.reserved_qty)

    @property
    def is_in_stock(self) -> bool:
        return self.available_stock > 0

    @property
    def is_low_stock(self) -> bool:
        from django.conf import settings
        return 0 < self.available_stock <= getattr(settings, "LOW_STOCK_THRESHOLD", 5)

    def reserve(self, quantity: int) -> bool:
        if self.available_stock >= quantity:
            self.reserved_qty += quantity
            self.save(update_fields=["reserved_qty", "updated_at"])
            return True
        return False

    def release_reservation(self, quantity: int) -> None:
        self.reserved_qty = max(0, self.reserved_qty - quantity)
        self.save(update_fields=["reserved_qty", "updated_at"])

    def deduct_stock(self, quantity: int) -> None:
        self.reserved_qty   = max(0, self.reserved_qty - quantity)
        self.stock_quantity = max(0, self.stock_quantity - quantity)
        self.save(update_fields=["reserved_qty", "stock_quantity", "updated_at"])
''')

# ════════════════════════════════════════════════════════
# 2. migration جدید
# ════════════════════════════════════════════════════════
print("[2/4] ساخت migration ...")

write('apps/catalog/migrations/0004_restructure_product.py', '''"""
Migration 0004 - بازسازی کامل ساختار محصول
ارز: دلار → یوان چینی
ویژگی‌ها: اختصاصی هر دسته
"""
from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0003_product_seo_fields"),
    ]
    operations = [
        # ── ارز: دلار → یوان ──────────────────────────────────────
        migrations.RenameField("exchangeratesetting", "rate_usd_to_irt", "rate_cny_to_irt"),
        migrations.AlterField(
            model_name="exchangeratesetting",
            name="rate_cny_to_irt",
            field=models.PositiveBigIntegerField(
                default=8500, verbose_name="نرخ یوان (تومان)",
                help_text="هر یوان چینی چند تومان؟",
            ),
        ),

        # ── دسته‌بندی: اضافه کردن category_type ──────────────────
        migrations.AddField(
            model_name="category",
            name="category_type",
            field=models.CharField(
                max_length=20, db_index=True, default="other",
                choices=[("board","برد دوربین مداربسته"),("lens","لنز دوربین مداربسته"),
                         ("modem","متعلقات"),("housing","بدنه دوربین مداربسته"),("other","سایر")],
                verbose_name="نوع دسته",
            ),
        ),

        # ── محصول: حذف فیلدهای قدیمی ─────────────────────────────
        migrations.RemoveField("product", "part_type"),
        migrations.RemoveField("product", "chipset"),
        migrations.RemoveField("product", "voltage"),
        migrations.RemoveField("product", "lens_mount"),
        migrations.RemoveField("product", "resolution"),

        # ── محصول: ویژگی‌های برد ──────────────────────────────────
        migrations.AddField("product", "board_name",       models.CharField(max_length=150, blank=True, verbose_name="نام برد")),
        migrations.AddField("product", "board_system",     models.CharField(max_length=100, blank=True, verbose_name="سیستم")),
        migrations.AddField("product", "board_resolution", models.CharField(max_length=50,  blank=True, verbose_name="رزولوشن (برد)")),
        migrations.AddField("product", "sensor_name",      models.CharField(max_length=150, blank=True, verbose_name="نام سنسور")),
        migrations.AddField("product", "sensor_size",      models.CharField(max_length=50,  blank=True, verbose_name="اندازه سنسور")),
        migrations.AddField("product", "ai_processor",     models.CharField(max_length=150, blank=True, verbose_name="AI پردازنده")),
        migrations.AddField("product", "board_dimensions", models.CharField(max_length=100, blank=True, verbose_name="ابعاد (برد)")),

        # ── محصول: ویژگی‌های لنز ──────────────────────────────────
        migrations.AddField("product", "lens_name",       models.CharField(max_length=150, blank=True, verbose_name="نام لنز")),
        migrations.AddField("product", "lens_resolution", models.CharField(max_length=50,  blank=True, verbose_name="رزولوشن (لنز)")),
        migrations.AddField("product", "lens_degree",     models.CharField(max_length=50,  blank=True, verbose_name="درجه لنز")),
        migrations.AddField("product", "lens_type",       models.CharField(max_length=100, blank=True, verbose_name="نوع لنز")),
        migrations.AddField("product", "focal_ratio",     models.CharField(max_length=50,  blank=True, verbose_name="نسبت کانونی")),

        # ── محصول: ویژگی‌های متعلقات ──────────────────────────────
        migrations.AddField("product", "modem_model",   models.CharField(max_length=150, blank=True, verbose_name="مدل")),
        migrations.AddField("product", "modem_type",    models.CharField(max_length=100, blank=True, verbose_name="نوع")),
        migrations.AddField("product", "pin_count",     models.CharField(max_length=50,  blank=True, verbose_name="تعداد پین")),
        migrations.AddField("product", "voltage",       models.CharField(max_length=50,  blank=True, verbose_name="ولتاژ کاری")),
        migrations.AddField("product", "ampere_output", models.CharField(max_length=50,  blank=True, verbose_name="آمپر خروجی")),
        migrations.AddField("product", "sim_card",      models.BooleanField(default=False, verbose_name="قابلیت سیم کارت")),
        migrations.AddField("product", "output_ports",  models.PositiveSmallIntegerField(null=True, blank=True, verbose_name="تعداد پورت خروجی")),
        migrations.AddField("product", "modem_size",    models.CharField(max_length=100, blank=True, verbose_name="سایز")),

        # ── محصول: ویژگی‌های بدنه ─────────────────────────────────
        migrations.AddField("product", "housing_material", models.CharField(max_length=100, blank=True, verbose_name="جنس بدنه")),
        migrations.AddField("product", "housing_type",     models.CharField(max_length=100, blank=True, verbose_name="نوع بدنه")),
        migrations.AddField("product", "housing_size",     models.CharField(max_length=100, blank=True, verbose_name="سایز دوربین")),
        migrations.AddField("product", "has_microphone",   models.BooleanField(default=False, verbose_name="قابلیت میکروفون")),

        # ── Variant: دلار → یوان ──────────────────────────────────
        migrations.RenameField("productvariant", "purchase_price_usd", "purchase_price_cny"),
        migrations.AlterField(
            model_name="productvariant",
            name="purchase_price_cny",
            field=models.DecimalField(
                max_digits=10, decimal_places=2,
                verbose_name="قیمت خرید (یوان)",
                help_text="قیمت خرید به یوان چینی",
            ),
        ),
    ]
''')

# ════════════════════════════════════════════════════════
# 3. admin.py جدید با fieldsets اختصاصی هر دسته
# ════════════════════════════════════════════════════════
print("[3/4] بازنویسی admin.py ...")

write('apps/catalog/admin.py', '''from django.contrib import admin
from django.utils.html import format_html
from import_export.admin import ImportExportModelAdmin
from import_export import resources
from .models import Category, ExchangeRateSetting, Product, ProductImage, ProductVariant, SeoSettings


@admin.register(ExchangeRateSetting)
class ExchangeRateSettingAdmin(admin.ModelAdmin):
    list_display = ["rate_cny_to_irt", "updated_at"]
    readonly_fields = ["updated_at", "created_at"]
    fieldsets = (
        (None, {"fields": ("rate_cny_to_irt",),
                "description": "نرخ یوان چینی (CNY) به تومان — همه قیمت‌ها بر این اساس محاسبه می‌شوند"}),
    )
    def has_add_permission(self, request):
        return not ExchangeRateSetting.objects.exists()
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "category_type", "parent", "is_active", "sort_order"]
    list_filter  = ["is_active", "category_type"]
    search_fields = ["name"]
    prepopulated_fields = {"slug": ("name",)}
    list_editable = ["is_active", "sort_order"]
    ordering = ["sort_order", "name"]


class ProductImageInline(admin.TabularInline):
    model  = ProductImage
    extra  = 1
    fields = ["image", "alt_text", "is_primary", "sort_order"]


class ProductVariantInline(admin.TabularInline):
    model  = ProductVariant
    extra  = 1
    fields = ["sku", "purchase_price_cny", "shipping_cost", "profit_margin",
              "stock_quantity", "reserved_qty", "price_display", "is_active"]
    readonly_fields = ["price_display"]
    def price_display(self, obj):
        if not obj.pk: return "—"
        return format_html(\'<b style="color:#0066FF">{:,}</b> تومان\', obj.final_price)
    price_display.short_description = "قیمت نهایی"


class ProductVariantResource(resources.ModelResource):
    class Meta:
        model  = ProductVariant
        fields = ["id","sku","purchase_price_cny","shipping_cost","profit_margin","stock_quantity"]


# ── fieldsets اختصاصی هر دسته ─────────────────────────────────────────────────
_BOARD_FIELDS = (
    ("ویژگی‌های برد دوربین", {
        "fields": ("board_name","board_system","board_resolution",
                   "sensor_name","sensor_size","ai_processor","board_dimensions"),
        "description": "فقط فیلدهای پر شده در سایت نمایش داده می‌شوند",
    }),
)
_LENS_FIELDS = (
    ("ویژگی‌های لنز", {
        "fields": ("lens_name","lens_resolution","lens_degree","lens_type","focal_ratio"),
        "description": "فقط فیلدهای پر شده در سایت نمایش داده می‌شوند",
    }),
)
_MODEM_FIELDS = (
    ("ویژگی‌های متعلقات", {
        "fields": ("modem_model","modem_type","pin_count","voltage",
                   "ampere_output","sim_card","output_ports","modem_size"),
        "description": "فقط فیلدهای پر شده در سایت نمایش داده می‌شوند",
    }),
)
_HOUSING_FIELDS = (
    ("ویژگی‌های بدنه دوربین", {
        "fields": ("housing_material","housing_type","housing_size","has_microphone"),
        "description": "فقط فیلدهای پر شده در سایت نمایش داده می‌شوند",
    }),
)

_BASE_FIELDSETS = (
    ("اطلاعات اصلی", {
        "fields": ("name","slug","category","brand","model_number",
                   "short_description","description"),
    }),
    ("فایل‌ها و لینک‌ها", {
        "fields": ("datasheet_pdf","whatsapp_link","bale_link"),
    }),
    ("محصولات سازگار", {"fields": ("compatible_with",)}),
    ("SEO", {
        "fields": ("meta_title","meta_description","keywords","geo_tags"),
        "classes": ("collapse",),
        "description": "اگر خالی بگذارید خودکار پر می‌شود",
    }),
    ("نمایش", {"fields": ("is_active","is_featured")}),
    ("تاریخ‌ها", {"fields": ("created_at","updated_at"), "classes": ("collapse",)}),
)


@admin.register(Product)
class ProductAdmin(ImportExportModelAdmin):
    resource_class = ProductVariantResource
    list_display   = ["name","category","stock_display","price_display","seo_status","is_active"]
    list_filter    = ["is_active","is_featured","category__category_type","category"]
    search_fields  = ["name","brand","model_number"]
    prepopulated_fields  = {"slug": ("name",)}
    filter_horizontal    = ["compatible_with"]
    list_editable        = ["is_active"]
    readonly_fields      = ["created_at","updated_at"]
    inlines              = [ProductImageInline, ProductVariantInline]
    actions              = ["regenerate_seo_action"]

    def get_fieldsets(self, request, obj=None):
        """fieldsets اختصاصی بر اساس دسته انتخاب شده"""
        cat_type = None
        if obj and obj.category_id:
            cat_type = obj.category.category_type
        elif request.GET.get("category"):
            try:
                from .models import Category as Cat
                cat_type = Cat.objects.get(pk=request.GET["category"]).category_type
            except Exception:
                pass

        extra = {
            "board":   _BOARD_FIELDS,
            "lens":    _LENS_FIELDS,
            "modem":   _MODEM_FIELDS,
            "housing": _HOUSING_FIELDS,
        }.get(cat_type, _BOARD_FIELDS + _LENS_FIELDS + _MODEM_FIELDS + _HOUSING_FIELDS)

        return (_BASE_FIELDSETS[:1],) + extra + _BASE_FIELDSETS[1:]

    def stock_display(self, obj):
        t = obj.available_stock
        if t == 0:    return format_html(\'<span style="color:#FF3B3B">ناموجود</span>\')
        if t <= 5:    return format_html(\'<span style="color:#FF9500">کم ({})</span>\', t)
        return format_html(\'<span style="color:#00C896">{}</span>\', t)
    stock_display.short_description = "موجودی"

    def price_display(self, obj):
        v = obj.variants.filter(is_active=True).first()
        if not v: return "—"
        return format_html(\'<b>{:,}</b> ت\', v.final_price)
    price_display.short_description = "قیمت"

    def seo_status(self, obj):
        n = sum([bool(obj.meta_title),bool(obj.meta_description),bool(obj.keywords),bool(obj.geo_tags)])
        color = "#00C896" if n==4 else "#FF9500" if n>=2 else "#FF3B3B"
        return format_html(\'<span style="color:{}">{}/4</span>\', color, n)
    seo_status.short_description = "SEO"

    @admin.action(description="بازنویسی خودکار SEO")
    def regenerate_seo_action(self, request, queryset):
        from apps.catalog.seo import generate_all_seo_fields
        count = 0
        for p in queryset:
            changes = generate_all_seo_fields(p, force=True)
            if changes:
                Product.objects.filter(pk=p.pk).update(**changes)
                count += 1
        self.message_user(request, f"SEO {count} محصول بازنویسی شد.")


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display  = ["sku","product","purchase_price_cny","final_price_display","available_stock_display","is_active"]
    search_fields = ["sku","product__name"]
    readonly_fields = ["created_at","updated_at"]
    def final_price_display(self, obj):
        return format_html(\'<b style="color:#0066FF">{:,}</b> ت\', obj.final_price)
    final_price_display.short_description = "قیمت نهایی"
    def available_stock_display(self, obj):
        s = obj.available_stock
        if s == 0: return format_html(\'<span style="color:#FF3B3B">ناموجود</span>\')
        if s <= 5: return format_html(\'<span style="color:#FF9500">{}</span>\', s)
        return format_html(\'<span style="color:#00C896">{}</span>\', s)
    available_stock_display.short_description = "موجودی"


@admin.register(SeoSettings)
class SeoSettingsAdmin(admin.ModelAdmin):
    fields = ["target_cities","site_name"]
    def has_add_permission(self, request): return not SeoSettings.objects.exists()
    def has_delete_permission(self, request, obj=None): return False
''')

# ════════════════════════════════════════════════════════
# 4. migrate + check
# ════════════════════════════════════════════════════════
print("[4/4] اجرای migrate ...")
r = subprocess.run([sys.executable,"manage.py","migrate","--verbosity=0"],
                   capture_output=True, text=True)
if r.returncode == 0:
    print("  OK - migrate موفق")
else:
    lines = (r.stdout+r.stderr).strip().split("\n")
    for l in lines[-8:]:
        if l.strip(): print(" ", l)

r2 = subprocess.run([sys.executable,"manage.py","check","--verbosity=0"],
                    capture_output=True, text=True)
if r2.returncode == 0:
    print("  OK - Django check موفق")
else:
    lines = (r2.stdout+r2.stderr).strip().split("\n")
    for l in lines[-8:]:
        if l.strip(): print(" ", l)

print("\n" + "="*60)
print("  تمام! حالا بزنید:")
print("  python manage.py runserver")
print("="*60 + "\n")
