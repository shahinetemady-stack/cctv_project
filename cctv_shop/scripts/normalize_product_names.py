"""
scripts/normalize_product_names.py
──────────────────────────────────
استانداردسازی نام محصولات برای SEO:
  ۱. «دو‌مگاپیکسل» → «2 مگاپیکسل» (اعداد فارسی/حروفی → رقم لاتین با فاصله)
  ۲. فاصله حول + : «8536+2053» → «8536 + 2053»
  ۳. همه اعداد فارسی داخل نام → لاتین (کاربران با اعداد لاتین سرچ می‌کنند)

اسلاگ‌ها دست نمی‌خورند (URLها ثابت می‌مانند — بدون ضربه به ایندکس).
فیلدهای SEO که نام قدیمی را در خود دارند با نام جدید بازنویسی می‌شوند
(فقط جایگذاری رشته — متن دستی واردشده حفظ می‌شود).

اجرا:  venv/bin/python scripts/normalize_product_names.py          # پیش‌نمایش
       venv/bin/python scripts/normalize_product_names.py --apply  # اعمال
"""

import os
import re
import sys

import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.db.models.signals import post_save  # noqa: E402

from apps.catalog import signals as catalog_signals  # noqa: E402
from apps.catalog.models import Product  # noqa: E402

# در حین اجرای گروهی، پینگ IndexNow برای هر محصول لازم نیست
post_save.disconnect(catalog_signals.product_indexnow, sender=Product)

_FA_TO_EN = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")

_NUM_WORDS = {
    "یک": "1", "دو": "2", "سه": "3", "چهار": "4", "پنج": "5", "شش": "6",
    "هفت": "7", "هشت": "8", "نه": "9", "ده": "10", "یازده": "11", "دوازده": "12",
}

# نام دقیق درخواستی کاربر برای این محصول — کلید، نام فعلی در دیتابیس است
_EXACT_RENAMES = {
    "برد دوربین مداربسته AHD دو‌مگاپیکسل وارم‌لایت فولهان 8536+2053 HS":
        "برد دوربین مداربسته 2 مگاپیکسل AHD مدل 2053 فولهان (GC2053 + FH8536H) وارم‌لایت HS",
}


def normalize_name(name: str) -> str:
    if name in _EXACT_RENAMES:
        return _EXACT_RENAMES[name]
    n = name.translate(_FA_TO_EN)
    # «دو‌مگاپیکسل» / «پنج مگاپیکسل» → «2 مگاپیکسل» / «5 مگاپیکسل»
    for word, digit in _NUM_WORDS.items():
        n = re.sub(rf"{word}\s*‌?\s*مگاپیکسل", f"{digit} مگاپیکسل", n)
    # «5مگاپیکسل» → «5 مگاپیکسل»
    n = re.sub(r"(\d(?:\.\d+)?)\s*‌?\s*مگاپیکسل", r"\1 مگاپیکسل", n)
    # فاصله حول +
    n = re.sub(r"\s*\+\s*", " + ", n)
    # جمع کردن فاصله‌های پشت‌سرهم
    return re.sub(r" {2,}", " ", n).strip()


def main():
    apply = "--apply" in sys.argv
    changed = 0
    for p in Product.objects.all().order_by("id"):
        new_name = normalize_name(p.name)
        if new_name == p.name:
            continue
        changed += 1
        print(f"[{p.pk}] {p.name}\n  → {new_name}")
        if apply:
            old_name, p.name = p.name, new_name
            # بازنویسی فیلدهای SEO که نام قدیمی را جاسازی کرده‌اند
            for field in ("meta_title", "meta_description", "keywords"):
                val = getattr(p, field) or ""
                if old_name in val:
                    setattr(p, field, val.replace(old_name, new_name))
            p.save(update_fields=["name", "meta_title", "meta_description", "keywords", "updated_at"])
    print(f"\n{'اعمال شد' if apply else 'پیش‌نمایش'}: {changed} محصول تغییر می‌کند.")
    if not apply and changed:
        print("برای اعمال: --apply")


if __name__ == "__main__":
    main()
