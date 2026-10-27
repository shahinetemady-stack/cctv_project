"""
scripts/rename_others_torob_pattern.py
──────────────────────────────────────
استانداردسازی نام کیس‌ها (housing)، لوازم جانبی و مودم‌ها به الگوی بازار:
    «کیس {بولت|دام} {جنس} {وارم‌لایت/…} دوربین مداربسته مدل {کد}»
- کد مدل همیشه با کلمه «مدل» و در انتها
- «وارملایت» → «وارم‌لایت» (نیم‌فاصله استاندارد)، پرانتز حذف می‌شود
- محصولاتی که از قبل استانداردند (29/30/31/32/43/45/46/47/48/55/57/58/105/115) دست نمی‌خورند

اجرا:  venv/bin/python scripts/rename_others_torob_pattern.py          # پیش‌نمایش
       venv/bin/python scripts/rename_others_torob_pattern.py --apply  # اعمال
"""

import os
import sys

import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.db.models.signals import post_save  # noqa: E402

from apps.catalog import signals as catalog_signals  # noqa: E402
from apps.catalog.models import Product  # noqa: E402

post_save.disconnect(catalog_signals.product_indexnow, sender=Product)

RENAMES = {
    # ── کیس‌ها (housing) ──
    28:  "کیس دام پلاستیکی دوربین مداربسته با ال‌ای‌دی مدل N745PR",
    112: "کیس بولت فلزی وارم‌لایت دوربین مداربسته مدل K6",
    123: "کیس بولت فلزی وارم‌لایت دوربین مداربسته مدل K7",
    124: "کیس بولت فلزی وارم‌لایت دوربین مداربسته مدل 90D",
    125: "کیس مینیاتوری فلزی دوربین مداربسته IP مدل MINIATOR IPC",
    126: "کیس دام فلزی وارم‌لایت تک‌پیچ دوربین مداربسته مدل H504",
    127: "کیس دام فلزی وارم‌لایت لنز بزرگ دوربین مداربسته مدل HK",
    128: "کیس دام فلزی وارم‌لایت فیش‌آی دوربین مداربسته مدل BQ3-6",
    129: "کیس دام فلزی وارم‌لایت پلیسی دوربین مداربسته مدل HK",
    130: "کیس بولت فلزی وارم‌لایت دوربین مداربسته مدل 70FJQ",
    131: "کیس بولت فلزی وارم‌لایت رم‌ساپورت دوربین مداربسته مدل 70FJQ-K",
    132: "کیس بولت فلزی وارم‌لایت دوربین مداربسته مدل KING FU4",
    133: "کیس بولت فلزی وارم‌لایت پلیسی دوربین مداربسته مدل K6",
    134: "کیس بولت فلزی وارم‌لایت دوربین مداربسته مدل CY-04",
    135: "کیس بولت فلزی وارم‌لایت دوربین مداربسته مدل 8318",
    136: "کیس بولت فلزی وارم‌لایت دوربین مداربسته مدل 8335",
    # ── لوازم جانبی (accessory) ──
    9:   "کابل AHD دوربین مداربسته سوکت درشت 1.5 میلی‌متر",
    13:  "میکروفون داخلی دوربین مداربسته IP مدل MIC GREY",
    23:  "میکروفون داخلی دوربین مداربسته IP مدل RED-MIC",
    44:  "کابل AHD دوربین مداربسته سوکت ریز 1.25 میلی‌متر",
    66:  "ال‌ای‌دی وارم‌لایت دوربین مداربسته مدل 5006",
    114: "کابل CDS دوربین مداربسته",
    116: "کابل ال‌ای‌دی برد رویژن RUISION",
    # ── مودم و دوربین‌های مونتاژشده ──
    27:  "مودم سیم‌کارتی 4G مدل CPE906 برند Onelink با سرعت 300 مگابیت بر ثانیه",
    117: "دوربین مداربسته 2 مگاپیکسل دام فلزی مدل N665M1084",
    118: "برد ماژول مودم سیم‌کارتی 4G مدل BF21",
    119: "دوربین مداربسته 2 مگاپیکسل بولت فلزی مدل N8234M1084",
}


def main():
    apply = "--apply" in sys.argv
    changed = skipped = 0
    for pk, new_name in sorted(RENAMES.items()):
        p = Product.objects.filter(pk=pk).first()
        if not p:
            print(f"[{pk}] ⚠️ محصول پیدا نشد")
            skipped += 1
            continue
        if p.name == new_name:
            skipped += 1
            continue
        changed += 1
        print(f"[{pk}] {p.name}\n  → {new_name}")
        if apply:
            old_name, p.name = p.name, new_name
            for field in ("meta_title", "meta_description", "keywords"):
                val = getattr(p, field) or ""
                if old_name in val:
                    setattr(p, field, val.replace(old_name, new_name))
            p.save(update_fields=["name", "meta_title", "meta_description", "keywords", "updated_at"])
    print(f"\n{'اعمال شد' if apply else 'پیش‌نمایش'}: {changed} تغییر، {skipped} بدون تغییر/ناموجود.")
    if not apply and changed:
        print("برای اعمال: --apply")


if __name__ == "__main__":
    main()
