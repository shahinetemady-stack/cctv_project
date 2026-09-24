#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
بهینه‌سازی in-place تصاویر media — کاهش حجم دانلود صفحه اول (Lighthouse: enormous network payloads).

کارها:
  - کوچک‌نمایی تصاویر بزرگ‌تر از MAX_DIM (به‌جز دیتاشیت‌ها: --datasheets با سقف ۱۶۰۰px)
  - فشرده‌سازی مجدد webp/jpg با همان نام و مسیر (DB دست نمی‌خورد)
  - PNG بدون آلفا که فشرده‌سازی PNGاش بی‌فایده است → تبدیل به فایل .webp واقعی
    و به‌روزرسانی خودکار همه‌ی ImageField/FileFieldهای دیتابیس که به مسیر قدیمی اشاره می‌کنند

اجرا روی لوکال یا سرور (از ریشه‌ی cctv_shop):
    venv/bin/python scripts/optimize_media.py            # اجرای واقعی
    venv/bin/python scripts/optimize_media.py --dry-run  # فقط گزارش
    venv/bin/python scripts/optimize_media.py --datasheets  # شامل صفحات دیتاشیت

ایدِمپوتنت است — فایل‌هایی که کمتر از MIN_SAVING بهبود بگیرند دست نمی‌خورند.
"""
import os
import sys
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django
django.setup()

from django.conf import settings
from django.apps import apps
from django.db import models as dj_models
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

# زیرشاخه‌هایی که بهینه می‌شوند (آپلودهای کاربران مثل receipts/partner_docs نه)
TARGET_DIRS = ["products", "education", "packages", "site", "pages", "categories"]
MAX_DIM = 1000          # سقف ابعاد تصاویر محصول/مقاله/سایت
DATASHEET_MAX_DIM = 1600
WEBP_Q = 80
JPEG_Q = 82
MIN_SAVING = 0.15       # حداقل ۱۵٪ کاهش وگرنه فایل دست نمی‌خورد
MIN_SIZE = 40 * 1024    # فایل‌های کوچک‌تر از ۴۰KB ارزش دست‌کاری ندارند


def iter_images(root, include_datasheets):
    for dirpath, _dirnames, filenames in os.walk(root):
        rel = os.path.relpath(dirpath, root)
        top = rel.split(os.sep)[0]
        if top == "datasheets" and not include_datasheets:
            continue
        for fn in filenames:
            ext = os.path.splitext(fn)[1].lower()
            if ext in (".jpg", ".jpeg", ".png", ".webp"):
                yield os.path.join(dirpath, fn)


def optimize_file(path, dry_run):
    """خروجی: (old_size, new_size, new_path یا None یعنی همان مسیر)"""
    old_size = os.path.getsize(path)
    if old_size < MIN_SIZE:
        return None
    rel = os.path.relpath(path, settings.MEDIA_ROOT)
    max_dim = DATASHEET_MAX_DIM if rel.startswith("datasheets") else MAX_DIM
    ext = os.path.splitext(path)[1].lower()

    try:
        im = Image.open(path)
        im.load()
    except Exception as e:
        print(f"  !! باز نشد: {rel} ({e})")
        return None

    resized = False
    if max(im.size) > max_dim:
        im = im.copy()
        im.thumbnail((max_dim, max_dim), Image.LANCZOS)
        resized = True

    has_alpha = im.mode in ("RGBA", "LA", "PA") and (im.mode == "LA" or im.getextrema()[-1][0] < 255)

    import io
    buf = io.BytesIO()
    new_path = None
    if ext in (".jpg", ".jpeg"):
        im.convert("RGB").save(buf, "JPEG", quality=JPEG_Q, optimize=True, progressive=True)
    elif ext == ".webp":
        im.save(buf, "WEBP", quality=WEBP_Q, method=6)
    elif ext == ".png":
        if has_alpha:
            im.save(buf, "PNG", optimize=True)
        else:
            # PNG عکسی — وب‌پی واقعی خیلی کوچک‌تر است؛ فایل .webp جدید ساخته و DB به‌روز می‌شود
            im.convert("RGB").save(buf, "WEBP", quality=WEBP_Q, method=6)
            new_path = os.path.splitext(path)[0] + ".webp"
    new_size = buf.tell()

    if new_size >= old_size:
        return None  # بازنویسی فقط وقتی که واقعاً کوچک‌تر شود
    if not resized and new_size >= old_size * (1 - MIN_SAVING):
        return None  # بهبود ناچیز

    if not dry_run:
        target = new_path or path
        with open(target, "wb") as f:
            f.write(buf.getvalue())
        if new_path:
            os.remove(path)
    return old_size, new_size, new_path


def update_db_references(old_rel, new_rel, dry_run):
    """هر ImageField/FileField در همه مدل‌ها که دقیقاً به old_rel اشاره کند → new_rel"""
    changed = 0
    for model in apps.get_models():
        file_fields = [
            f.name for f in model._meta.get_fields()
            if isinstance(f, (dj_models.ImageField, dj_models.FileField))
        ]
        for fname in file_fields:
            qs = model.objects.filter(**{fname: old_rel})
            n = qs.count()
            if n:
                changed += n
                if not dry_run:
                    qs.update(**{fname: new_rel})
                print(f"  DB: {model._meta.label}.{fname} ×{n}")
    return changed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--datasheets", action="store_true", help="صفحات دیتاشیت را هم بهینه کن (۱۶۰۰px)")
    args = ap.parse_args()

    root = settings.MEDIA_ROOT
    total_old = total_new = 0
    n_files = 0
    renames = []
    for top in TARGET_DIRS + (["datasheets"] if args.datasheets else []):
        d = os.path.join(root, top)
        if not os.path.isdir(d):
            continue
        for path in iter_images(d, include_datasheets=True):
            res = optimize_file(path, args.dry_run)
            if not res:
                continue
            old_size, new_size, new_path = res
            rel = os.path.relpath(path, root)
            total_old += old_size
            total_new += new_size
            n_files += 1
            tag = "DRY " if args.dry_run else ""
            if new_path:
                new_rel = os.path.relpath(new_path, root)
                renames.append((rel, new_rel))
                print(f"{tag}{rel}: {old_size//1024}K → {new_size//1024}K (.webp)")
            else:
                print(f"{tag}{rel}: {old_size//1024}K → {new_size//1024}K")

    for old_rel, new_rel in renames:
        update_db_references(old_rel, new_rel, args.dry_run)

    print(f"\n{n_files} فایل: {total_old/1e6:.1f}MB → {total_new/1e6:.1f}MB "
          f"(صرفه‌جویی {(total_old-total_new)/1e6:.1f}MB)")
    if args.dry_run:
        print("حالت dry-run — هیچ فایلی تغییر نکرد.")


if __name__ == "__main__":
    main()
