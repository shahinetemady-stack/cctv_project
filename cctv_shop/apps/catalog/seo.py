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

# ─── تولید اسلاگ لاتین ──────────────────────────────────────────────────────
# اسلاگها باید لاتین باشند (سئو و خوانایی URL). واژگان فنی فارسی به معادل
# انگلیسی نگاشت می‌شوند؛ واژگان ناشناخته به‌صورت فینگلیش برمی‌گردند تا
# هیچ اسلاگی فارسی تولید نشود.

_SLUG_WORD_MAP = {
    'کیس': 'housing', 'بدنه': 'housing', 'پوشش': 'cover',
    'بولت': 'bullet', 'دام': 'dome', 'باکس': 'box',
    'فلزی': 'metal', 'فلز': 'metal', 'پلاستیکی': 'plastic', 'پلاستیک': 'plastic',
    'وارملایت': 'warmlight', 'ورملایت': 'warmlight', 'استارلایت': 'starlight',
    'لنز': 'lens', 'هولدر': 'holder', 'برد': 'board', 'چیپست': 'chipset',
    'سنسور': 'sensor', 'پردازنده': 'processor', 'مودم': 'modem',
    'کابل': 'cable', 'تیل': 'pigtail', 'آداپتور': 'adapter', 'شارژر': 'charger',
    'فیکس': 'fixed', 'وریفکال': 'varifocal', 'موتورایز': 'motorized',
    'فیش': 'fisheye', 'پینهول': 'pinhole', 'مخفی': 'covert',
    'ضدآب': 'waterproof', 'رنگی': 'color', 'شب': 'night',
    'تغذیه': 'power', 'سیم': 'sim', 'کارت': 'card',
    'مونتاژ': 'assembly', 'نصب': 'installation', 'آموزش': 'tutorial',
    'راهنما': 'guide', 'راهنمای': 'guide', 'مقایسه': 'comparison', 'خرید': 'buy',
    'مگاپیکسل': 'mp', 'ولت': 'v', 'آمپر': 'a',  # به عددِ قبلی می‌چسبند: «۵ مگاپیکسل» → 5mp
}

# واژگانی که در اسلاگ نمی‌آیند (عمومی/اضافه) — قرارداد فعلی اسلاگهای سایت
_SLUG_SKIP_WORDS = {
    'دوربین', 'مداربسته', 'مدل', 'خرید', 'قیمت', 'اصل', 'جدید', 'نو',
    'و', 'با', 'برای', 'در', 'از', 'به', 'مخصوص', 'سیستم', 'آی', 'آر', 'کات',
    'منبع', 'دار',
}

# اعداد فارسی به رقم — برای ترکیب با مگاپیکسل و…
_FA_NUM_WORDS = {
    'یک': '1', 'دو': '2', 'سه': '3', 'چهار': '4', 'پنج': '5',
    'شش': '6', 'هفت': '7', 'هشت': '8', 'نه': '9', 'ده': '10', 'دوازده': '12',
}

# برگردان فینگلیش برای واژه‌های خارج از نگاشت
_FA_CHAR_MAP = {
    'ا': 'a', 'آ': 'a', 'ب': 'b', 'پ': 'p', 'ت': 't', 'ث': 's', 'ج': 'j',
    'چ': 'ch', 'ح': 'h', 'خ': 'kh', 'د': 'd', 'ذ': 'z', 'ر': 'r', 'ز': 'z',
    'ژ': 'zh', 'س': 's', 'ش': 'sh', 'ص': 's', 'ض': 'z', 'ط': 't', 'ظ': 'z',
    'ع': 'a', 'غ': 'gh', 'ف': 'f', 'ق': 'q', 'ک': 'k', 'گ': 'g', 'ل': 'l',
    'م': 'm', 'ن': 'n', 'و': 'v', 'ه': 'h', 'ی': 'i', 'ئ': 'i', 'ء': '',
    'أ': 'a', 'إ': 'e', 'ؤ': 'v', 'ة': 'h', 'ى': 'a',
}

_TOKEN_RE = re.compile(r'[A-Za-z0-9]+(?:[.\-][A-Za-z0-9]+)*|[؀-ۿ]+')


def latin_slugify(text: str) -> str:
    """
    تبدیل متن (فارسی/لاتین) به اسلاگ لاتین.

    - توکن‌های لاتین (مدل، رزولوشن…) دست‌نخورده و در ابتدای اسلاگ می‌آیند
      — همان قرارداد اسلاگهای فعلی سایت (مدل اول).
    - واژگان فارسی با نگاشت تخصصی، وگرنه فینگلیش برگردانده می‌شوند.
    """
    normalized = (text or '').translate(_FA_TO_EN).replace('‌', ' ').replace('‍', ' ')
    latin, persian = [], []
    last = None  # آخرین لیستی که توکن گرفت — برای چسباندن mp/v/a به عدد قبلی
    for tok in _TOKEN_RE.findall(normalized):
        if tok[0].isascii():
            latin.append(tok.lower())
            last = latin
            continue
        en = _SLUG_WORD_MAP.get(tok) or _FA_NUM_WORDS.get(tok)
        # «۵ مگاپیکسل» → 5mp ، «۱۲ ولت» → 12v ، «۲ آمپر» → 2a (به عدد قبلی می‌چسبند)
        if en in ('mp', 'v', 'a') and last and last[-1][-1].isdigit():
            last[-1] += en
        elif en:
            persian.append(en)
            last = persian
        elif tok in _SLUG_SKIP_WORDS:
            last = None
        else:
            tr = ''.join(_FA_CHAR_MAP.get(ch, '') for ch in tok)
            if tr:
                persian.append(tr)
                last = persian
    return slugify('-'.join(latin + persian)) or 'product'

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
_BASE_KEYWORDS = ['قطعات دوربین مداربسته', 'خرید قطعات CCTV']


# ─── Slug ─────────────────────────────────────────────────────────────────────

def generate_slug(name: str, model_class=None, instance_pk=None) -> str:
    """
    تولید slug یکتا از نام محصول — همیشه لاتین.

    مراحل:
      ۱. latin_slugify: نگاشت واژگان فنی + فینگلیش برای بقیه (اعداد فارسی → انگلیسی)
      ۲. بررسی یکتایی — اگر تکراری بود عدد اضافه می‌شود
    """
    base_slug = latin_slugify(name)

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

def _truncate_word_boundary(text: str, limit: int) -> str:
    """کوتاه‌سازی در مرز کلمه (بدون بریدن کلمه وسط) + سه‌نقطه."""
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(' ', 1)[0].rstrip('،؛:,-')
    return cut + '…'


def generate_meta_title(name: str) -> str:
    """
    فرمول: «{name} | قیمت و خرید قطعات دوربین مداربسته»
    حداکثر ۶۰ کاراکتر. اگر نام بلند باشد به پسوند کوتاه «| قیمت و خرید»
    برمی‌گردد تا مدل محصول حذف نشود؛ در بدترین حالت در مرز کلمه کوتاه می‌شود.
    """
    for suffix in (' | قیمت و خرید قطعات دوربین مداربسته', ' | قیمت و خرید'):
        max_name_len = 60 - len(suffix)
        if len(name) <= max_name_len:
            return f"{name}{suffix}"

    suffix = ' | قیمت و خرید'
    name = _truncate_word_boundary(name, 60 - len(suffix) - 1)
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

    closing = f"قیمت مناسب {part_fa} دوربین مداربسته، موجودی لحظه‌ای و ارسال سریع."

    description = '، '.join(parts[:3]) + '. ' + closing

    # محدودیت ۱۶۰ کاراکتر
    if len(description) > 160:
        description = _truncate_word_boundary(description, 159)

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
    keywords = []

    # اطلاعات اختصاصی محصول اول بیاید — کلمات عمومی آخر
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

    keywords.extend(_BASE_KEYWORDS)

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
        # ویژگی‌های مرتبط بر اساس نوع دسته
        chipset_or_sensor = (
            product.sensor_name or product.board_name or
            product.lens_name or product.modem_model or ''
        )
        voltage = getattr(product, 'voltage', '')
        cat_type = product.category.category_type if product.category_id else ''
        new_desc = generate_meta_description(
            name=product.name,
            chipset=chipset_or_sensor,
            voltage=voltage,
            part_type=cat_type,
            brand=product.brand,
        )
        if new_desc != product.meta_description:
            updated['meta_description'] = new_desc

    # ── Keywords ──────────────────────────────────────────────────────
    if force or not getattr(product, 'keywords', ''):
        chipset_or_sensor2 = (
            product.sensor_name or product.board_name or
            product.lens_name or product.modem_model or ''
        )
        voltage2 = getattr(product, 'voltage', '')
        cat_type2 = product.category.category_type if product.category_id else ''
        new_kw = generate_keywords(
            name=product.name,
            chipset=chipset_or_sensor2,
            voltage=voltage2,
            part_type=cat_type2,
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
