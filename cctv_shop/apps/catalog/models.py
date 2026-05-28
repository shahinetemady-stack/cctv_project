"""
apps/catalog/models.py
"""
from decimal import Decimal
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.text import slugify
from apps.core.models import SingletonModel, TimeStampedModel


class ExchangeRateSetting(SingletonModel):
    rate_cny_to_irt = models.PositiveBigIntegerField(
        default=8500, verbose_name="نرخ یوان (تومان)",
        help_text="هر یوان چینی چند تومان؟",
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


class Category(TimeStampedModel):
    class CategoryType(models.TextChoices):
        BOARD   = "board",   "برد دوربین مداربسته"
        LENS    = "lens",    "لنز دوربین مداربسته"
        MODEM   = "modem",   "متعلقات"
        HOUSING = "housing", "بدنه دوربین مداربسته"
        OTHER   = "other",   "سایر"

    name = models.CharField(max_length=150, verbose_name="نام دسته‌بندی")
    slug = models.SlugField(max_length=160, unique=True, allow_unicode=True)
    category_type = models.CharField(
        max_length=20, choices=CategoryType.choices,
        default=CategoryType.OTHER, verbose_name="نوع دسته", db_index=True,
    )
    parent = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="children", verbose_name="دسته والد",
    )
    icon = models.CharField(max_length=100, blank=True, verbose_name="آیکون")
    image = models.ImageField(upload_to="categories/", null=True, blank=True)
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


class Product(TimeStampedModel):
    # ── اطلاعات پایه ──────────────────────────────────────
    name     = models.CharField(max_length=255, verbose_name="نام محصول")
    slug     = models.SlugField(max_length=270, unique=True, allow_unicode=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products", verbose_name="دسته‌بندی")
    brand    = models.CharField(max_length=100, blank=True, verbose_name="شرکت سازنده")
    model_number = models.CharField(max_length=100, blank=True, verbose_name="شماره مدل")
    description       = models.TextField(blank=True, verbose_name="توضیحات")
    short_description = models.CharField(max_length=500, blank=True, verbose_name="توضیح کوتاه")

    # ── ویژگی‌های برد دوربین ──────────────────────────────
    board_name = models.CharField(max_length=150, blank=True, verbose_name="نام برد")
    board_system = models.CharField(max_length=20, blank=True, verbose_name="سیستم",
        choices=[("AHD","AHD"),("IP","IP")])
    board_resolution = models.CharField(max_length=20, blank=True, verbose_name="رزولوشن (برد)",
        choices=[("2MP","2MP"),("4MP","4MP"),("5MP","5MP"),("8MP","8MP"),("12MP","12MP")])
    sensor_name  = models.CharField(max_length=150, blank=True, verbose_name="نام سنسور")
    sensor_size  = models.CharField(max_length=30, blank=True, verbose_name="اندازه سنسور",
        choices=[('1/4"','1/4"'),('1/3"','1/3"'),('1/2.8"','1/2.8"'),
                 ('1/2.7"','1/2.7"'),('1/2"','1/2"'),('1/1.8"','1/1.8"')])
    ai_processor    = models.CharField(max_length=150, blank=True, verbose_name="AI پردازنده")
    board_dimensions= models.CharField(max_length=100, blank=True, verbose_name="ابعاد (برد)")

    # ── ویژگی‌های لنز دوربین ──────────────────────────────
    lens_name = models.CharField(max_length=150, blank=True, verbose_name="نام لنز")
    lens_resolution = models.CharField(max_length=20, blank=True, verbose_name="رزولوشن لنز",
        choices=[("3MP","3MP"),("5MP","5MP"),("8MP","8MP")])
    lens_degree = models.CharField(max_length=20, blank=True, verbose_name="فاصله کانونی",
        choices=[("1.7mm","1.7mm"),("1.8mm","1.8mm"),("2.8mm","2.8mm"),
                 ("3.6mm","3.6mm"),("4mm","4mm"),("6mm","6mm"),
                 ("8mm","8mm"),("12mm","12mm"),("16mm","16mm")])
    lens_type = models.CharField(max_length=50, blank=True, verbose_name="نوع لنز",
        choices=[("فیکس","فیکس"),("وریفکال","وریفکال"),
                 ("فیش آی","فیش آی"),("پین هولد","پین هولد"),("موتورایز","موتورایز")])
    focal_ratio = models.CharField(max_length=30, blank=True, verbose_name="نوع کاربرد",
        choices=[("معمولی","معمولی"),("استارلایت","استارلایت"),("دارک لایت","دارک لایت")])

    # ── ویژگی‌های متعلقات ─────────────────────────────────
    modem_model  = models.CharField(max_length=150, blank=True, verbose_name="مدل")
    modem_type   = models.CharField(max_length=100, blank=True, verbose_name="نوع")
    pin_count    = models.CharField(max_length=50,  blank=True, verbose_name="تعداد پین")
    voltage      = models.CharField(max_length=50,  blank=True, verbose_name="ولتاژ کاری")
    ampere_output= models.CharField(max_length=50,  blank=True, verbose_name="آمپر خروجی")
    sim_card     = models.BooleanField(default=False, verbose_name="قابلیت سیم کارت")
    output_ports = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name="تعداد پورت خروجی")
    modem_size   = models.CharField(max_length=100, blank=True, verbose_name="سایز")

    # ── ویژگی‌های بدنه دوربین ─────────────────────────────
    housing_material = models.CharField(max_length=50, blank=True, verbose_name="جنس بدنه",
        choices=[("فلز","فلز"),("پلاستیک","پلاستیک"),("فلز و پلاستیک","فلز و پلاستیک")])
    housing_type = models.CharField(max_length=50, blank=True, verbose_name="نوع بدنه",
        choices=[("Bullet","Bullet"),("Dome","Dome"),("Box","Box"),("PTZ","PTZ"),("Fisheye","Fisheye")])
    housing_size = models.CharField(max_length=100, blank=True, verbose_name="سایز دوربین")
    has_microphone = models.BooleanField(default=False, verbose_name="قابلیت میکروفون")

    # ── فایل‌ها ────────────────────────────────────────────
    datasheet_pdf = models.FileField(upload_to="datasheets/%Y/%m/", null=True, blank=True, verbose_name="دیتاشیت PDF")
    whatsapp_link = models.URLField(blank=True, verbose_name="لینک واتساپ")
    bale_link     = models.URLField(blank=True, verbose_name="لینک بله")
    compatible_with = models.ManyToManyField("self", symmetrical=True, blank=True, verbose_name="محصولات سازگار")

    # ── وضعیت ─────────────────────────────────────────────
    is_active   = models.BooleanField(default=True, verbose_name="فعال", db_index=True)
    is_featured = models.BooleanField(default=False, verbose_name="ویژه")

    # ── SEO ───────────────────────────────────────────────
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
        for k, v in generate_all_seo_fields(self, force=False).items():
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


class ProductImage(TimeStampedModel):
    product    = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
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


class ProductVariant(TimeStampedModel):
    product    = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants", verbose_name="محصول")
    sku        = models.CharField(max_length=100, unique=True, verbose_name="کد SKU")
    name_suffix= models.CharField(max_length=100, blank=True, verbose_name="پسوند نام")
    stock_quantity = models.PositiveIntegerField(default=0, verbose_name="موجودی کل")
    reserved_qty   = models.PositiveIntegerField(default=0, verbose_name="رزرو شده")
    purchase_price_cny = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
        verbose_name="قیمت خرید (یوان)",
        help_text="قیمت خرید به یوان چینی",
    )
    shipping_cost_cny = models.DecimalField(
        max_digits=8, decimal_places=2, default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
        verbose_name="هزینه حمل (یوان)",
        help_text="هزینه حمل به یوان چینی",
    )
    profit_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
        verbose_name="سود (%)",
        help_text="درصد سود روی قیمت خرید + حمل. مثال: 20 یعنی ۲۰٪",
    )
    is_active     = models.BooleanField(default=True, verbose_name="فعال")

    class Meta:
        db_table = "catalog_product_variant"
        verbose_name = "نسخه محصول"
        verbose_name_plural = "نسخه‌های محصول"
        ordering = ["product", "sku"]

    def __str__(self):
        return f"{self.product.name} [{self.sku}]"

    @property
    def final_price(self):
        import math
        rate = ExchangeRateSetting.get_instance().rate_cny_to_irt
        # قیمت خرید به تومان
        purchase_toman  = self.purchase_price_cny * rate
        # هزینه حمل به تومان
        shipping_toman  = self.shipping_cost_cny * rate
        # مجموع قبل از سود
        subtotal        = purchase_toman + shipping_toman
        # سود
        profit_toman    = subtotal * (self.profit_percent / 100)
        # قیمت نهایی - رند به سمت بالا
        return math.ceil(float(subtotal + profit_toman))

    @property
    def available_stock(self):
        return max(0, self.stock_quantity - self.reserved_qty)

    @property
    def is_in_stock(self):
        return self.available_stock > 0

    @property
    def is_low_stock(self):
        from django.conf import settings
        return 0 < self.available_stock <= getattr(settings, "LOW_STOCK_THRESHOLD", 5)

    def reserve(self, quantity):
        if self.available_stock >= quantity:
            self.reserved_qty += quantity
            self.save(update_fields=["reserved_qty","updated_at"])
            return True
        return False

    def release_reservation(self, quantity):
        self.reserved_qty = max(0, self.reserved_qty - quantity)
        self.save(update_fields=["reserved_qty","updated_at"])

    def deduct_stock(self, quantity):
        self.reserved_qty   = max(0, self.reserved_qty - quantity)
        self.stock_quantity = max(0, self.stock_quantity - quantity)
        self.save(update_fields=["reserved_qty","stock_quantity","updated_at"])


class Package(models.Model):
    """پکیج پیشنهادی — ترکیب چند محصول با تخفیف"""

    name        = models.CharField(max_length=200, verbose_name="نام پکیج")
    slug        = models.SlugField(max_length=250, unique=True, allow_unicode=True, verbose_name="نامک")
    description = models.TextField(blank=True, verbose_name="توضیحات")
    image       = models.ImageField(upload_to='packages/', null=True, blank=True, verbose_name="تصویر")
    products    = models.ManyToManyField('Product', through='PackageItem', related_name='packages', verbose_name="محصولات")
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="تخفیف (%)")
    is_active   = models.BooleanField(default=True, verbose_name="فعال")
    is_featured = models.BooleanField(default=False, verbose_name="ویژه")
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "catalog_package"
        verbose_name = "پکیج"
        verbose_name_plural = "پکیج‌ها"
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    @property
    def original_price(self):
        """قیمت اصلی بدون تخفیف"""
        total = 0
        for item in self.package_items.select_related('variant').all():
            total += item.variant.final_price * item.quantity
        return total

    @property
    def final_price(self):
        """قیمت نهایی با تخفیف"""
        import math
        disc = float(self.discount_percent) / 100
        return math.ceil(self.original_price * (1 - disc))

    @property
    def savings(self):
        return self.original_price - self.final_price


class PackageItem(models.Model):
    """آیتم داخل پکیج"""
    package  = models.ForeignKey(Package, on_delete=models.CASCADE, related_name='package_items')
    product  = models.ForeignKey('Product', on_delete=models.CASCADE, verbose_name="محصول")
    variant  = models.ForeignKey('ProductVariant', on_delete=models.CASCADE, verbose_name="نوع محصول")
    quantity = models.PositiveSmallIntegerField(default=1, verbose_name="تعداد")

    class Meta:
        db_table = "catalog_package_item"
        verbose_name = "آیتم پکیج"
        verbose_name_plural = "آیتم‌های پکیج"

    def __str__(self):
        return f"{self.package.name} — {self.product.name} × {self.quantity}"


class ProductPriceHistory(models.Model):
    """تاریخچه قیمت محصول — روزانه ذخیره می‌شود"""
    variant    = models.ForeignKey('ProductVariant', on_delete=models.CASCADE,
                   related_name='price_history', verbose_name="variant")
    date       = models.DateField(verbose_name="تاریخ")
    price_irr  = models.PositiveIntegerField(verbose_name="قیمت (تومان)")
    price_cny  = models.DecimalField(max_digits=10, decimal_places=2,
                   default=0, verbose_name="قیمت (یوان)")

    class Meta:
        db_table = "catalog_price_history"
        verbose_name = "تاریخچه قیمت"
        unique_together = [("variant", "date")]
        ordering = ["-date"]

    def __str__(self):
        return f"{self.variant} | {self.date} | {self.price_irr:,}"
