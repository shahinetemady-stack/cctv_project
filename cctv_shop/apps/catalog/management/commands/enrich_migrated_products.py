"""
python manage.py enrich_migrated_products [--dry-run]

غنی‌سازی محصولات منتقل‌شده از doorbinkar.com:
۱. تصحیح نام‌های مشکل‌دار (فاصله اضافی، مگاپیکسیل، IPچهار، مدل:X)
۲. استخراج مشخصات ساختاری از نام و توضیحات → فیلدهای مدل
   (سیستم، رزولوشن، سنسور، پردازنده، لنز، بدنه، ولتاژ...) تا
   فیلترها، جدول مشخصات و جستجوی هوشمند برای محصولات منتقل‌شده کار کنند
۳. تشخیص برند از روی نام

فقط فیلدهای خالی پر می‌شوند؛ slug و legacy_id دست‌نخورده می‌مانند
(ریدایرکتها تحت تأثیر قرار نمی‌گیرند).
"""

import re

from django.core.management.base import BaseCommand

from apps.catalog.models import Product

FA_NUM = {"دو": "2", "سه": "3", "چهار": "4", "پنج": "5", "هشت": "8", "دوازده": "12"}

BOARD_RES = {"2": "2MP", "4": "4MP", "5": "5MP", "8": "8MP", "12": "12MP"}
LENS_RES = {"3": "3MP", "5": "5MP", "8": "8MP"}
SENSOR_SIZES = ['1/1.8"', '1/2.7"', '1/2.8"', '1/2"', '1/3"', '1/4"']
LENS_DEGREES = ["1.7mm", "1.8mm", "2.8mm", "3.6mm", "4mm", "6mm", "8mm", "12mm", "16mm"]

BRANDS = [
    (r"سونی|sony", "سونی"),
    (r"فولهان|fullhan", "فولهان"),
    (r"ytot", "YTOT"),
    (r"\bcw[-\s]", "CW"),
    (r"onelink", "onelink"),
    (r"\bhs\b", "HS"),
    (r"hikvision|هایک‌ویژن|هایک ویژن", "هایک‌ویژن"),
]


def normalize_name(name):
    """تصحیح تایپوهای رایج نام‌های سایت قدیمی."""
    n = name
    n = n.replace("مگاپیکسیل", "مگاپیکسل")
    n = re.sub(r"\b(IP|AHD)(?=[\u0600-\u06FF])", r"\1 ", n)      # IPچهار → IP چهار
    n = re.sub(r"(?<=[\u0600-\u06FF])(IP|AHD)\b", r" \1", n)     # دوربینAHD → دوربین AHD
    n = re.sub(r"مدل:(?=\S)", "مدل: ", n)                         # مدل:X → مدل: X
    n = re.sub(r"\s{2,}", " ", n)                                # فاصله‌های اضافی
    return n.strip()


def find_mp(text, mapping):
    """یافتن رزولوشن از نام/توضیح — در صورت ابهام (دو رزولوشن) None."""
    found = set()
    for fa, digit in FA_NUM.items():
        if re.search(rf"{fa}\s*مگاپیکسل|{digit}\s*مگاپیکسل|\b{digit}\s*MP\b", text, re.I):
            if digit in mapping:
                found.add(mapping[digit])
    return found.pop() if len(found) == 1 else None


def desc_value(description, label):
    """مقدار روبروی یک لیبل در توضیحات: «لیبل: مقدار»"""
    m = re.search(rf"{re.escape(label)}\s*[:：]\s*(.+)", description or "")
    return m.group(1).strip() if m else ""


def extract_specs(product):
    """برگرداندن dict فیلدهای قابل استخراج بر اساس نوع دسته."""
    out = {}
    text = f"{product.name}\n{product.description or ''}"
    desc = product.description or ""
    cat_type = product.category.category_type if product.category_id else ""

    # برند — برای همه انواع
    for pattern, brand in BRANDS:
        if re.search(pattern, product.name, re.I):
            out["brand"] = brand
            break

    if cat_type == "board":
        if re.search(r"\bIP\b|تحت شبکه", text, re.I) and not re.search(r"\bAHD\b", text, re.I):
            out["board_system"] = "IP"
        elif re.search(r"\bAHD\b", text, re.I):
            out["board_system"] = "AHD"
        res = find_mp(text, BOARD_RES)
        if res:
            out["board_resolution"] = res
        v = desc_value(desc, "مدل برد")
        if v:
            out["board_name"] = v[:150]
        v = desc_value(desc, "پردازنده")
        if v:
            out["ai_processor"] = v[:150]
        m = re.search(r"\b(IMX\d+|GC\d{4}|SC\d{3,4}|OV\d+|NVP\d+[A-Z]*)\b", text, re.I)
        if m:
            out["sensor_name"] = m.group(1)
        for size in SENSOR_SIZES:
            if size in text:
                out["sensor_size"] = size
                break

    elif cat_type == "lens":
        m = re.search(r"مدل:\s*(\S+)", product.name)
        if m:
            out["lens_name"] = m.group(1)[:150]
        res = find_mp(text, LENS_RES)
        if res:
            out["lens_resolution"] = res
        for deg in LENS_DEGREES:
            if deg.replace("mm", "") in re.findall(r"\d+\.?\d*\s*(?:mm|میل)", text, re.I).__str__() or deg in text:
                out["lens_degree"] = deg
                break
        for key, val in [("فیش آی", "فیش آی"), ("پینهول|پین هول", "پین هولد"),
                         ("موتورایز", "موتورایز"), ("وریفکال", "وریفکال")]:
            if re.search(key, text):
                out["lens_type"] = val
                break
        else:
            out["lens_type"] = "فیکس"
        if re.search(r"استارلایت", text):
            out["focal_ratio"] = "استارلایت"
        elif re.search(r"دارک لایت", text):
            out["focal_ratio"] = "دارک لایت"
        else:
            out["focal_ratio"] = "معمولی"

    elif cat_type == "housing":
        slug = product.category.slug if product.category_id else ""
        if "bullet" in slug:
            out["housing_type"] = "Bullet"
        elif "dome" in slug:
            out["housing_type"] = "Dome"
        if re.search(r"فلز و پلاستیک", text):
            out["housing_material"] = "فلز و پلاستیک"
        elif re.search(r"فلزی?", text):
            out["housing_material"] = "فلز"
        elif re.search(r"پلاستیک", text):
            out["housing_material"] = "پلاستیک"
        if re.search(r"میکروفن|میکروفون", text):
            out["has_microphone"] = True

    elif cat_type == "modem":
        v = desc_value(desc, "ولتاژ") or desc_value(desc, "ولتاژ کاری")
        if v:
            out["voltage"] = v[:50]
        m = re.search(r"(\d+)\s*پین", text)
        if m:
            out["pin_count"] = m.group(1)
        if re.search(r"سیم ?کارت", text):
            out["sim_card"] = True
        m = re.search(r"مدل:\s*(\S+)", product.name)
        if m:
            out["modem_model"] = m.group(1)[:150]

    return {k: v for k, v in out.items() if v not in ("", None)}


class Command(BaseCommand):
    help = "غنی‌سازی محصولات منتقل‌شده (تصحیح نام + مشخصات ساختاری + برند)"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        dry = options["dry_run"]
        renamed = 0
        filled = {}

        for p in Product.objects.filter(legacy_id__isnull=False).select_related("category"):
            changes = {}

            # ۱) تصحیح نام
            new_name = normalize_name(p.name)
            if new_name != p.name:
                changes["name"] = new_name
                renamed += 1
                if dry:
                    self.stdout.write(f"نام {p.legacy_id}: {p.name!r} → {new_name!r}")

            # ۲) مشخصات — فقط فیلدهای خالی
            for field, value in extract_specs(p).items():
                current = getattr(p, field, None)
                if current in ("", None, False):
                    changes[field] = value
                    filled[field] = filled.get(field, 0) + 1

            if changes and not dry:
                for k, v in changes.items():
                    setattr(p, k, v)
                p.save()

        self.stdout.write(f"\n✓ نام اصلاح شد: {renamed}")
        self.stdout.write("✓ فیلدهای پر شده:")
        for f, c in sorted(filled.items(), key=lambda x: -x[1]):
            self.stdout.write(f"  {f}: {c}")
