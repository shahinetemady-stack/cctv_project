"""
apps/catalog/seo.py
────────────────────
موتور Auto-SEO برای محصولات.

تمام منطق تولید فیلدهای SEO اینجاست — مجزا از model
تا تست و نگهداری آسان باشد.
"""

import re
from django.utils.text import slugify


# ─── نگاشت اعداد فارسی به انگلیسی ───────────────────────────────────────────
_FA_TO_EN = str.maketrans('۰۱۲۳۴۵۶۷۸۹', '0123456789')

# ─── نام فارسی انواع قطعه ─────────────────────────────────────────────────────
_PART_TYPE_FA = {
    'sensor':  'سنسور',
    'lens':    'لنز',
    'board':   'برد',
    'isp':     'پردازنده تصویر',
    'housing': 'کیس و پوشش',
    'ir_cut':  'فیلتر IR-Cut',
    'motor':   'موتور',
    'fpc':     'کابل FPC',
    'power':   'منبع تغذیه',
    'other':   'قطعه',
}

# ─── کلمات کلیدی پایه ────────────────────────────────────────────────────────
_BASE_KEYWORDS = ['خرید', 'قیمت', 'قطعات دوربین', 'CCTV', 'مداربسته']


# ─── Slug ─────────────────────────────────────────────────────────────────────

def generate_slug(name: str, model_class=None, instance_pk=None) -> str:
    """
    تولید slug یکتا از نام محصول.

    مراحل:
      ۱. اعداد فارسی → انگلیسی
      ۲. slugify (فارسی-دوست)
      ۳. بررسی یکتایی — اگر تکراری بود عدد اضافه می‌شود
    """
    # تبدیل اعداد فارسی
    name_normalized = name.translate(_FA_TO_EN)
    base_slug = slugify(name_normalized, allow_unicode=True)

    if not base_slug:
        base_slug = 'product'

    if model_class is None:
        return base_slug

    # بررسی یکتایی
    slug = base_slug
    counter = 1
    qs = model_class.objects.filter(slug=slug)
    if instance_pk:
        qs = qs.exclude(pk=instance_pk)

    while qs.exists():
        slug = f"{base_slug}-{counter}"
        counter += 1
        qs = model_class.objects.filter(slug=slug)
        if instance_pk:
            qs = qs.exclude(pk=instance_pk)

    return slug


# ─── Meta Title ───────────────────────────────────────────────────────────────

def generate_meta_title(name: str) -> str:
    """
    فرمول: «{name} | قیمت و خرید قطعات دوربین مداربسته»
    حداکثر ۶۰ کاراکتر.
    """
    suffix = ' | قیمت و خرید قطعات دوربین مداربسته'
    max_name_len = 60 - len(suffix)

    if len(name) > max_name_len:
        name = name[:max_name_len - 1] + '…'

    return f"{name}{suffix}"


# ─── Meta Description ─────────────────────────────────────────────────────────

def generate_meta_description(
    name: str,
    chipset: str = '',
    voltage: str = '',
    part_type: str = '',
    brand: str = '',
) -> str:
    """
    توضیح متا از ترکیب مشخصات فنی محصول.
    حداکثر ۱۶۰ کاراکتر (استاندارد SEO).
    """
    part_fa = _PART_TYPE_FA.get(part_type, 'قطعه')

    # ساخت توضیح
    parts = [f"خرید {name}"]

    if brand:
        parts.append(f"برند {brand}")
    if chipset:
        parts.append(f"با چیپست {chipset}")
    if voltage:
        parts.append(f"ولتاژ {voltage}")

    parts.append(f"قیمت مناسب {part_fa} دوربین مداربسته، موجودی لحظه‌ای و ارسال سریع.")

    description = '، '.join(parts[:3]) + '. ' + parts[-1]

    # محدودیت ۱۶۰ کاراکتر
    if len(description) > 160:
        description = description[:158] + '…'

    return description


# ─── Keywords ─────────────────────────────────────────────────────────────────

def generate_keywords(
    name: str,
    chipset: str = '',
    voltage: str = '',
    part_type: str = '',
    brand: str = '',
) -> str:
    """
    ترکیب کلمات کلیدی پایه + اختصاصی محصول.
    حداکثر ۱۰ کلمه، جدا شده با کاما.
    """
    keywords = list(_BASE_KEYWORDS)  # کپی

    # اضافه کردن اطلاعات محصول
    if name:
        keywords.append(name)
    if brand:
        keywords.append(brand)
    if chipset:
        keywords.append(chipset)
    if voltage:
        keywords.append(voltage)
    if part_type and part_type in _PART_TYPE_FA:
        keywords.append(_PART_TYPE_FA[part_type])

    # حذف تکراری‌ها + محدودیت ۱۰ تا
    seen = set()
    unique = []
    for kw in keywords:
        kw = kw.strip()
        if kw and kw not in seen:
            seen.add(kw)
            unique.append(kw)
        if len(unique) >= 10:
            break

    return '، '.join(unique)


# ─── Geo Tags ─────────────────────────────────────────────────────────────────

def generate_geo_tags(target_cities: str = '') -> str:
    """
    تولید geo tags از لیست شهرهای هدف.
    اگر target_cities خالی بود از پیش‌فرض استفاده می‌شود.
    """
    if not target_cities:
        target_cities = 'تهران، مشهد، اصفهان، شیراز، تبریز، کرج'
    return target_cities.strip()


# ─── تابع اصلی: همه فیلدها یکجا ─────────────────────────────────────────────

def generate_all_seo_fields(product, force: bool = False) -> dict:
    """
    تولید همه فیلدهای SEO برای یک product instance.

    اگر force=False باشد، فقط فیلدهای خالی پر می‌شوند.
    اگر force=True باشد، همه فیلدها بازنویسی می‌شوند.

    Returns:
        dict: فیلدهای به‌روزرسانی‌شده (فقط فیلدهایی که تغییر کردند)
    """
    from .models import Product  # import داخلی برای جلوگیری از circular import

    updated = {}

    # ── Slug ──────────────────────────────────────────────────────────
    if force or not product.slug:
        new_slug = generate_slug(product.name, Product, product.pk)
        if new_slug != product.slug:
            updated['slug'] = new_slug

    # ── Meta Title ────────────────────────────────────────────────────
    if force or not product.meta_title:
        new_title = generate_meta_title(product.name)
        if new_title != product.meta_title:
            updated['meta_title'] = new_title

    # ── Meta Description ──────────────────────────────────────────────
    if force or not product.meta_description:
        new_desc = generate_meta_description(
            name=product.name,
            chipset=product.chipset,
            voltage=product.voltage,
            part_type=product.part_type,
            brand=product.brand,
        )
        if new_desc != product.meta_description:
            updated['meta_description'] = new_desc

    # ── Keywords ──────────────────────────────────────────────────────
    if force or not getattr(product, 'keywords', ''):
        new_kw = generate_keywords(
            name=product.name,
            chipset=product.chipset,
            voltage=product.voltage,
            part_type=product.part_type,
            brand=product.brand,
        )
        if new_kw != getattr(product, 'keywords', ''):
            updated['keywords'] = new_kw

    # ── Geo Tags ──────────────────────────────────────────────────────
    if force or not getattr(product, 'geo_tags', ''):
        # دریافت شهرهای هدف از تنظیمات سایت
        try:
            from .models import SeoSettings
            seo_settings = SeoSettings.get_instance()
            cities = seo_settings.target_cities
        except Exception:
            cities = ''

        new_geo = generate_geo_tags(cities)
        if new_geo != getattr(product, 'geo_tags', ''):
            updated['geo_tags'] = new_geo

    return updated
