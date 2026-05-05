"""
apps/catalog/models.py
───────────────────────
Core product catalog models.

Hierarchy:
  Category (self-referential tree, max 2 levels)
    └── Product  (e.g. "سنسور Sony IMX307")
          └── ProductVariant  (e.g. colour / voltage variant)
                └── ProductImage

Pricing formula (on ProductVariant):
  final_price = (purchase_price_usd × exchange_rate) + shipping_cost + profit_margin

Exchange rate is fetched live from ExchangeRateSetting (singleton).
"""

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.utils.text import slugify

from apps.core.models import SingletonModel, TimeStampedModel


# ─── Exchange Rate (Singleton) ─────────────────────────────────────────────────

class ExchangeRateSetting(SingletonModel):
    """
    One row only.  Admin changes rate_usd_to_irt from the panel.
    All variant prices are recalculated on the fly using this value.
    """

    rate_usd_to_irt = models.PositiveBigIntegerField(
        default=60_000,
        verbose_name="نرخ دلار (تومان)",
        help_text="هر دلار چند تومان؟  مثال: 60000",
    )
    updated_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name="بروزرسانی توسط",
    )

    class Meta:
        db_table = "catalog_exchange_rate"
        verbose_name = "نرخ ارز"
        verbose_name_plural = "نرخ ارز"

    def __str__(self):
        return f"نرخ دلار: {self.rate_usd_to_irt:,} تومان"


# ─── SeoSettings (Singleton) ──────────────────────────────────────────────────

class SeoSettings(SingletonModel):
    """
    تنظیمات SEO سراسری — فقط یک رکورد.
    شهرهای هدف برای geo_tags همه محصولات از اینجا خوانده می‌شود.
    """
    target_cities = models.CharField(
        max_length=500,
        default="تهران، مشهد، اصفهان، شیراز، تبریز، کرج",
        verbose_name="شهرهای هدف",
        help_text="با کاما جدا کنید — برای geo_tags محصولات استفاده می‌شود",
    )
    site_name = models.CharField(
        max_length=100,
        default="فروشگاه قطعات دوربین مداربسته",
        verbose_name="نام سایت",
    )

    class Meta:
        db_table = "catalog_seo_settings"
        verbose_name = "تنظیمات سئو"
        verbose_name_plural = "تنظیمات سئو"

    def __str__(self):
        return "تنظیمات سئو"


# ─── Category ─────────────────────────────────────────────────────────────────

class Category(TimeStampedModel):
    """
    Self-referential category tree (max 2 levels recommended).
    e.g.  دوربین ← دوربین بولت
          قطعات  ← سنسور
    """

    name = models.CharField(max_length=150, verbose_name="نام دسته‌بندی")
    slug = models.SlugField(
        max_length=160,
        unique=True,
        allow_unicode=True,
        verbose_name="اسلاگ",
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
        verbose_name="دسته‌بندی والد",
    )
    icon = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="آیکون",
        help_text="نام آیکون (مثلاً نام کلاس FontAwesome یا SVG)",
    )
    image = models.ImageField(
        upload_to="categories/",
        null=True,
        blank=True,
        verbose_name="تصویر دسته",
    )
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    sort_order = models.PositiveSmallIntegerField(default=0, verbose_name="ترتیب نمایش")

    class Meta:
        db_table = "catalog_category"
        verbose_name = "دسته‌بندی"
        verbose_name_plural = "دسته‌بندی‌ها"
        ordering = ["sort_order", "name"]

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} / {self.name}"
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name, allow_unicode=True)
        super().save(*args, **kwargs)


# ─── Product ──────────────────────────────────────────────────────────────────

class Product(TimeStampedModel):
    """
    A product in the CCTV parts catalog.

    Technical fields (chipset, voltage, lens_mount, part_type) are the
    primary axes for the Advanced Filter on the frontend.

    compatible_with: ManyToMany self — برای "محصولات سازگار" در صفحه محصول.
    """

    class PartType(models.TextChoices):
        SENSOR = "sensor", "سنسور"
        LENS = "lens", "لنز"
        BOARD = "board", "برد"
        ISP = "isp", "پردازنده تصویر (ISP)"
        HOUSING = "housing", "پوشش و کیس"
        IR_CUT = "ir_cut", "فیلتر IR-Cut"
        MOTOR = "motor", "موتور"
        FPC = "fpc", "کابل FPC"
        POWER = "power", "منبع تغذیه"
        OTHER = "other", "سایر"

    class LensMount(models.TextChoices):
        M12 = "m12", "M12 (S-Mount)"
        CS = "cs", "CS-Mount"
        C = "c", "C-Mount"
        M16 = "m16", "M16"
        NONE = "none", "بدون مانت"
        OTHER = "other", "سایر"

    # ── Identity ────────────────────────────────────────────────────
    name = models.CharField(max_length=255, verbose_name="نام محصول")
    slug = models.SlugField(
        max_length=270,
        unique=True,
        allow_unicode=True,
        verbose_name="اسلاگ",
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="products",
        verbose_name="دسته‌بندی",
    )
    brand = models.CharField(max_length=100, blank=True, verbose_name="برند / سازنده")
    model_number = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="شماره مدل",
        help_text="مثلاً: IMX307-AAQ",
    )
    description = models.TextField(blank=True, verbose_name="توضیحات")
    short_description = models.CharField(
        max_length=500,
        blank=True,
        verbose_name="توضیح کوتاه",
    )

    # ── Technical Specs (Filter Axes) ────────────────────────────────
    part_type = models.CharField(
        max_length=20,
        choices=PartType.choices,
        default=PartType.OTHER,
        verbose_name="نوع قطعه",
        db_index=True,
    )
    chipset = models.CharField(
        max_length=150,
        blank=True,
        db_index=True,
        verbose_name="چیپست",
        help_text="مثلاً: Sony IMX307 / HiSilicon Hi3516",
    )
    voltage = models.CharField(
        max_length=50,
        blank=True,
        db_index=True,
        verbose_name="ولتاژ",
        help_text="مثلاً: 12V DC / 5V / PoE",
    )
    lens_mount = models.CharField(
        max_length=10,
        choices=LensMount.choices,
        default=LensMount.NONE,
        db_index=True,
        verbose_name="مانت لنز",
    )
    resolution = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="رزولوشن",
        help_text="مثلاً: 2MP / 4K",
    )
    extra_specs = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="مشخصات اضافی",
        help_text="JSON آزاد برای هر مشخصه‌ای که در فیلدهای بالا نگنجد",
    )

    # ── Files & Links ─────────────────────────────────────────────────
    datasheet_pdf = models.FileField(
        upload_to="datasheets/%Y/%m/",
        null=True,
        blank=True,
        verbose_name="دیتاشیت PDF",
    )
    whatsapp_link = models.URLField(
        blank=True,
        verbose_name="لینک واتساپ",
        help_text="مثلاً: https://wa.me/989121234567",
    )
    bale_link = models.URLField(
        blank=True,
        verbose_name="لینک بله",
    )

    # ── Relations ─────────────────────────────────────────────────────
    compatible_with = models.ManyToManyField(
        "self",
        symmetrical=True,
        blank=True,
        verbose_name="محصولات سازگار",
        help_text="محصولاتی که با این قطعه کار می‌کنند",
    )

    # ── Status ────────────────────────────────────────────────────────
    is_active = models.BooleanField(default=True, verbose_name="فعال", db_index=True)
    is_featured = models.BooleanField(default=False, verbose_name="ویژه / پیشنهادی")

    # ── SEO Fields (خودکار پر می‌شوند) ───────────────────────────────
    meta_title = models.CharField(
        max_length=60, blank=True,
        verbose_name="Meta Title",
        help_text="اگر خالی باشد خودکار ساخته می‌شود",
    )
    meta_description = models.CharField(
        max_length=160, blank=True,
        verbose_name="Meta Description",
        help_text="اگر خالی باشد خودکار ساخته می‌شود",
    )
    keywords = models.CharField(
        max_length=500, blank=True,
        verbose_name="کلمات کلیدی",
        help_text="جدا شده با کاما — اگر خالی باشد خودکار ساخته می‌شود",
    )
    geo_tags = models.CharField(
        max_length=300, blank=True,
        verbose_name="شهرهای هدف (Geo Tags)",
        help_text="اگر خالی باشد از تنظیمات سئو گرفته می‌شود",
    )

    class Meta:
        db_table = "catalog_product"
        verbose_name = "محصول"
        verbose_name_plural = "محصولات"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["part_type", "chipset"], name="idx_product_type_chip"),
            models.Index(fields=["is_active", "is_featured"], name="idx_product_active_feat"),
        ]

    def __str__(self):
        return self.name

    def generate_seo_fields(self, force: bool = False) -> None:
        """تولید خودکار همه فیلدهای SEO."""
        from .seo import generate_all_seo_fields
        updates = generate_all_seo_fields(self, force=force)
        for field, value in updates.items():
            setattr(self, field, value)

    def save(self, *args, **kwargs):
        from .seo import generate_slug, generate_all_seo_fields
        # ── Slug ──────────────────────────────────────────────────────
        if not self.slug:
            self.slug = generate_slug(self.name, self.__class__, self.pk)
        # ── Auto-SEO ──────────────────────────────────────────────────
        seo_updates = generate_all_seo_fields(self, force=False)
        for field, value in seo_updates.items():
            setattr(self, field, value)
        super().save(*args, **kwargs)

    @property
    def main_image(self):
        return self.images.filter(is_primary=True).first()

    @property
    def available_stock(self):
        """جمع موجودی واقعی تمام variant‌ها (بعد از کسر رزروها)."""
        return sum(v.available_stock for v in self.variants.all())


# ─── ProductImage ─────────────────────────────────────────────────────────────

class ProductImage(TimeStampedModel):
    """Multiple images per product. One is marked as primary."""

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="images",
        verbose_name="محصول",
    )
    image = models.ImageField(upload_to="products/%Y/%m/", verbose_name="تصویر")
    alt_text = models.CharField(max_length=255, blank=True, verbose_name="متن جایگزین")
    is_primary = models.BooleanField(default=False, verbose_name="تصویر اصلی")
    sort_order = models.PositiveSmallIntegerField(default=0, verbose_name="ترتیب")

    class Meta:
        db_table = "catalog_product_image"
        verbose_name = "تصویر محصول"
        verbose_name_plural = "تصاویر محصول"
        ordering = ["-is_primary", "sort_order"]

    def __str__(self):
        return f"تصویر {self.product.name} ({'اصلی' if self.is_primary else 'فرعی'})"

    def save(self, *args, **kwargs):
        # Ensure only one primary image per product.
        if self.is_primary:
            ProductImage.objects.filter(
                product=self.product, is_primary=True
            ).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)


# ─── ProductVariant ───────────────────────────────────────────────────────────

class ProductVariant(TimeStampedModel):
    """
    A purchasable SKU under a Product.
    Most products will have exactly one variant.
    Multiple variants exist when e.g. voltage or colour differs.

    ┌──────────────────────────────────────────────────────────────────┐
    │  PRICING FORMULA                                                  │
    │  final_price = (purchase_price_usd × rate_usd_to_irt)            │
    │                 + shipping_cost + profit_margin                   │
    │                                                                   │
    │  rate_usd_to_irt  →  ExchangeRateSetting.get_instance()          │
    │  All three cost fields are stored in IRR (تومان).                │
    └──────────────────────────────────────────────────────────────────┘

    Stock fields:
      stock_quantity  : تعداد فیزیکی در انبار
      reserved_qty    : رزرو شده (در انتظار پرداخت)
      available_stock : stock_quantity - reserved_qty  (property)

    When available_stock < settings.LOW_STOCK_THRESHOLD → هشدار ادمین.
    """

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="variants",
        verbose_name="محصول",
    )
    sku = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="کد SKU",
        help_text="کد انحصاری این variant",
    )
    name_suffix = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="پسوند نام",
        help_text="مثلاً: رنگ مشکی / ۱۲ولت — برای تمایز variant‌ها",
    )

    # ── Stock ─────────────────────────────────────────────────────────
    stock_quantity = models.PositiveIntegerField(
        default=0,
        verbose_name="موجودی کل",
    )
    reserved_qty = models.PositiveIntegerField(
        default=0,
        verbose_name="رزرو شده",
        help_text="تعداد رزرو شده توسط سفارش‌های در انتظار پرداخت",
    )

    # ── Pricing inputs ────────────────────────────────────────────────
    purchase_price_usd = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
        verbose_name="قیمت خرید (دلار)",
        help_text="قیمت خرید این قطعه به دلار آمریکا",
    )
    shipping_cost = models.PositiveBigIntegerField(
        default=0,
        verbose_name="هزینه حمل (تومان)",
    )
    profit_margin = models.PositiveBigIntegerField(
        default=0,
        verbose_name="سود (تومان)",
        help_text="مبلغ سود ثابت که به قیمت اضافه می‌شود",
    )

    # ── Flags ─────────────────────────────────────────────────────────
    is_active = models.BooleanField(default=True, verbose_name="فعال")

    class Meta:
        db_table = "catalog_product_variant"
        verbose_name = "نسخه محصول (Variant)"
        verbose_name_plural = "نسخه‌های محصول"
        ordering = ["product", "sku"]

    def __str__(self):
        suffix = f" — {self.name_suffix}" if self.name_suffix else ""
        return f"{self.product.name}{suffix} [{self.sku}]"

    # ── Computed price (live) ──────────────────────────────────────────

    @property
    def final_price(self) -> int:
        """
        قیمت نهایی به تومان (محاسبه لحظه‌ای).

        فرمول:
            final_price = (purchase_price_usd × rate_usd_to_irt)
                           + shipping_cost + profit_margin

        نرخ ارز از ExchangeRateSetting خوانده می‌شود.
        نتیجه به عدد صحیح گرد می‌شود.
        """
        rate = ExchangeRateSetting.get_instance().rate_usd_to_irt
        usd_part = int(self.purchase_price_usd * rate)
        return usd_part + self.shipping_cost + self.profit_margin

    @property
    def available_stock(self) -> int:
        """موجودی واقعی: موجودی کل منهای رزرو شده."""
        return max(0, self.stock_quantity - self.reserved_qty)

    @property
    def is_in_stock(self) -> bool:
        return self.available_stock > 0

    @property
    def is_low_stock(self) -> bool:
        from django.conf import settings
        threshold = getattr(settings, "LOW_STOCK_THRESHOLD", 5)
        return 0 < self.available_stock <= threshold

    def reserve(self, quantity: int) -> bool:
        """
        رزرو موجودی برای یک سفارش.
        اگر موجودی کافی باشد True برمی‌گرداند و ذخیره می‌کند.
        """
        if self.available_stock >= quantity:
            self.reserved_qty += quantity
            self.save(update_fields=["reserved_qty", "updated_at"])
            return True
        return False

    def release_reservation(self, quantity: int) -> None:
        """
        آزاد کردن رزرو (وقتی سفارش منقضی یا کنسل شود).
        فقط reserved_qty کم می‌شود — stock_quantity دست نمی‌خورد.
        """
        self.reserved_qty = max(0, self.reserved_qty - quantity)
        self.save(update_fields=["reserved_qty", "updated_at"])

    def deduct_stock(self, quantity: int) -> None:
        """
        کسر موجودی پس از پرداخت موفق.
        reserved_qty و stock_quantity هر دو کم می‌شوند.
        """
        self.reserved_qty = max(0, self.reserved_qty - quantity)
        self.stock_quantity = max(0, self.stock_quantity - quantity)
        self.save(update_fields=["reserved_qty", "stock_quantity", "updated_at"])
