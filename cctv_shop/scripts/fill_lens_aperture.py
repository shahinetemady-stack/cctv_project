"""
پر کردن ضریب دیافراگم (lens_aperture) لنزهایی که خالی مانده بود — از روی سند:
- CW-811 3.6mm (3/4/5MP) → F2.0 — کاتالوگ رسمی سازنده (seculens.cn/list_10/93.html)
- YT-10100 2.8mm → F2.0 — کاتالوگ Seculens (مونتاژکننده YTOT) + سری عمومی YTOT
- YT-10169 4mm استارلایت → F1.4 — کاتالوگ Seculens «Starlight lens 10169»

فقط فیلدهای خالی پر می‌شوند؛ مقادیر موجود دست نمی‌خورند.
YT-10190، CW-10083 و CW-1065 سند معتبری پیدا نشد — خالی می‌مانند.

اجرا: ./venv/bin/python scripts/fill_lens_aperture.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django
django.setup()

from apps.catalog.models import Product

APERTURE = {
    6: "F2.0",    # CW-811-3MP+HOLDER
    36: "F2.0",   # CW-811-3MP+IR0722
    99: "F2.0",   # CW-811-4mp+HOLDER
    100: "F2.0",  # CW-811-5mp+HOLDER
    98: "F2.0",   # YT-10100 2.8mm
    61: "F1.4",   # YT-10169 4mm استارلایت
}

updated, skipped = [], []
for pid, ap in APERTURE.items():
    p = Product.objects.filter(pk=pid).first()
    if not p:
        skipped.append((pid, "محصول نیست"))
        continue
    if p.lens_aperture:
        skipped.append((pid, f"قبلاً پر بود ({p.lens_aperture})"))
        continue
    p.lens_aperture = ap
    p.save(update_fields=["lens_aperture"])
    updated.append((pid, p.model_number, ap))

print("پر شد:", updated)
print("رد شد:", skipped)
