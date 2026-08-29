"""
scripts/fix_nonstandard_slugs.py
────────────────────────────────
تبدیل اسلاگ‌های غیراستاندارد (فارسی/خراب/طولانی) محصولات و مقالات به لاتین.
ریدایرکت ۳۰۱ از اسلاگ قدیمی به‌صورت خودکار توسط هوک save مدل‌ها
در جدول SlugRedirect ثبت می‌شود. یک‌بار اجرا شود (idempotent).

اجرا:  venv/bin/python scripts/fix_nonstandard_slugs.py
"""

import os
import sys

import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from apps.catalog.models import Product, SlugRedirect  # noqa: E402
from apps.education.models import Article  # noqa: E402

PRODUCT_SLUGS = {
    77: "h43-ip-4mp-board",
    38: "cw-1065-5mp-ir0717-lens-ircut",
    36: "cw-811-3mp-ir0722-lens",
    35: "cw-d14-0622ir-5mp-motorized-lens",
    33: "cw-fisheye-1-8mm-5mp-lens",
    32: "n664mwarm-metal-dome-housing",
    31: "n937mb-large-metal-bullet-housing",
    30: "n821m-large-metal-bullet-housing",
    29: "n746pr-plastic-dome-housing",
    28: "n745pr-plastic-dome-housing-led",
    21: "huhuk-taiwan-poe-board-1-5a",
    9:  "ahd-cctv-cable-large-socket-1-5",
    6:  "cw-811-3mp-holder-lens",
    5:  "yt-10169-5mp-lens-ircut",
    4:  "h53-ip-5mp-board",
    3:  "yt-10169-5mp-lens-holder",
    1:  "h55-ip-5mp-board",
}

ARTICLE_SLUGS = {
    3: "chin-omadi",
    2: "original-cctv-verification",
    1: "how-to-assemble-bullet-camera",
}


def unique_slug(model, base, pk):
    slug, i = base, 1
    while model.objects.filter(slug=slug).exclude(pk=pk).exists():
        i += 1
        slug = f"{base}-{i}"
    return slug


def apply(model, mapping, label):
    for pk, base in mapping.items():
        obj = model.objects.filter(pk=pk).first()
        if obj is None:
            print(f"  ⚠️  {label} {pk} پیدا نشد")
            continue
        new = unique_slug(model, base, pk)
        if obj.slug == new:
            print(f"  = {label} {pk}: بدون تغییر ({new})")
            continue
        old = obj.slug
        obj.slug = new
        obj.save()
        print(f"  ✓ {label} {pk}: {old[:60]} → {new}")


print("محصولات:")
apply(Product, PRODUCT_SLUGS, "محصول")
print("مقالات:")
apply(Article, ARTICLE_SLUGS, "مقاله")
print(f"\nریدایرکتهای ثبت‌شده در SlugRedirect: {SlugRedirect.objects.count()}")
