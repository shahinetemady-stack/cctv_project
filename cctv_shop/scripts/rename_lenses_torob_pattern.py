"""
scripts/rename_lenses_torob_pattern.py
──────────────────────────────────────
استانداردسازی نام لنزها به الگوی رتبه‌دار بازار (ترب):
    «لنز دوربین مداربسته {نوع} {رزولوشن} مگاپیکسل {فاصله کانونی} میلی‌متر + {متعلقات} مدل {کد}»
- پسوندهای متعلقات (+ HOLDER / + IRCUT / …) از داخل کد مدل حذف می‌شود —
  متعلقات با کلمه فارسی (هولدر/آی‌آر کات) قبل از «مدل» می‌آید و کد تمیز می‌ماند
- پرانتزهای (A)/(B) حذف می‌شوند (نمایش بد در RTL)
- فاصله کانونی از فیلد lens_degree به نام اضافه می‌شود (سرچ رایج: «لنز 2.8 میلی‌متر»)
- اسلاگ‌ها دست نمی‌خورند؛ فیلدهای SEO با جایگذاری رشته به‌روز می‌شوند
- 89/96/98/101/102/104/113 از قبل استانداردند — دست نمی‌خورند

اجرا:  venv/bin/python scripts/rename_lenses_torob_pattern.py          # پیش‌نمایش
       venv/bin/python scripts/rename_lenses_torob_pattern.py --apply  # اعمال
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
    6:   "لنز دوربین مداربسته 3 مگاپیکسل 3.6 میلی‌متر + هولدر مدل CW-811-3MP",
    12:  "لنز دوربین مداربسته 5 مگاپیکسل 4 میلی‌متر + آی‌آر کات مدل YT-10085-5MP",
    33:  "لنز دوربین مداربسته فیش‌آی 5 مگاپیکسل 1.8 میلی‌متر مدل CW-FISHEYE-1.8MM-5MP",
    34:  "لنز دوربین مداربسته 5 مگاپیکسل 4 میلی‌متر دارک‌لایت + هولدر مدل YT-10116-5MP",
    35:  "لنز دوربین مداربسته موتورایز 5 مگاپیکسل 6 تا 22 میلی‌متر مدل CW-D14",
    36:  "لنز دوربین مداربسته 3 مگاپیکسل 3.6 میلی‌متر + آی‌آر کات مدل CW-811-3MP-IR0722",
    37:  "لنز دوربین مداربسته پین‌هول 1.3 مگاپیکسل 3.7 میلی‌متر مدل CW-PH3.7",
    38:  "لنز دوربین مداربسته 5 مگاپیکسل + آی‌آر کات مدل CW-1065-5MP",
    59:  "لنز دوربین مداربسته 5 مگاپیکسل 3.6 میلی‌متر + هولدر مدل CW-10083-5MP",
    61:  "لنز دوربین مداربسته 5 مگاپیکسل 4 میلی‌متر YTOT + هولدر مدل YT-10169-5MP",
    87:  "لنز دوربین مداربسته 5 مگاپیکسل 4 میلی‌متر استارلایت A + هولدر مدل YT-10081-5MP",
    90:  "لنز دوربین مداربسته 5 مگاپیکسل 4 میلی‌متر استارلایت B + هولدر مدل YT-10081-5MP",
    95:  "لنز دوربین مداربسته 8 مگاپیکسل 4 میلی‌متر دارک‌لایت + هولدر مدل YT-10035",
    97:  "لنز دوربین مداربسته 3 مگاپیکسل 3.6 میلی‌متر + هولدر مدل YT-10190",
    99:  "لنز دوربین مداربسته 4 مگاپیکسل 3.6 میلی‌متر + هولدر مدل CW-811-4MP",
    100: "لنز دوربین مداربسته 5 مگاپیکسل 3.6 میلی‌متر + هولدر مدل CW-811-5MP",
    103: "لنز دوربین مداربسته 8 مگاپیکسل 4 میلی‌متر + هولدر مدل YT-10081-8MP",
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
