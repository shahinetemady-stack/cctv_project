#!/usr/bin/env python
"""
scripts/scrape_missing_products.py
──────────────────────────────────
استخراج محصولاتی که در لیست دسته‌های سایت قدیمی نبودند
(مثلاً محصولات بایگانی‌شده یا بدون دسته فعال) ولی با id مستقیم
در دسترس‌اند — مثل /products/100/...

دسته هر محصول از breadcrumb صفحه (div.breadcrumbs، آخرین لینک /cat/)
و slug واقعی از لینک canonical خوانده می‌شود.

ورودی: لیست idها از خروجی probe (آرگومان --ids یا فایل)
خروجی: scripts/output/doorbinkar_missing.json + دانلود تصاویر

اجرا:
    venv/bin/python scripts/scrape_missing_products.py --ids 100,101,102
"""

import argparse
import json
import re
import sys
import time
import urllib.parse
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from django.utils.text import slugify  # فقط برای تمیزکردن slug؛ بدون نصب جنگو هم قابل حذف است

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scrape_doorbinkar import (  # noqa: E402
    BASE, HEADERS, OUT_DIR, download_images, fetch_product,
)

DELAY = 0.5


def extract_breadcrumb_category(soup):
    """آخرین لینک /cat/ در breadcrumb = زیردسته محصول."""
    bc = soup.select_one("div.breadcrumbs")
    if not bc:
        return None
    ids = re.findall(r"/cat/(\d+)/", str(bc))
    return int(ids[-1]) if ids else None


def extract_canonical_slug(soup):
    tag = soup.find("link", rel="canonical")
    if not tag or not tag.get("href"):
        return ""
    path = urllib.parse.urlparse(tag["href"]).path
    raw = urllib.parse.unquote(path.rstrip("/").split("/")[-1])
    # تمیزکردن برای SlugField (حذف : و + و ...)
    slug = slugify(raw.replace("+", " ").replace(":", " "), allow_unicode=True)
    return slug


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ids", required=True, help="لیست idها با کاما")
    parser.add_argument("--delay", type=float, default=DELAY)
    args = parser.parse_args()

    ids = [int(x) for x in args.ids.split(",") if x.strip()]
    already = {p["legacy_id"] for p in json.load(open(OUT_DIR / "doorbinkar_products.json", encoding="utf-8"))}
    todo = [i for i in ids if i not in already]
    print(f"{len(todo)} محصول جدید برای استخراج (از {len(ids)} id معتبر)")

    session = requests.Session()
    products = []
    for n, pid in enumerate(todo, 1):
        try:
            resp = session.get(f"{BASE}/products/{pid}/x", headers=HEADERS, timeout=30)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            slug = extract_canonical_slug(soup)
            cat_id = extract_breadcrumb_category(soup)

            p = fetch_product(session, pid, "x")  # slug در URL مهم نیست
            p["legacy_slug"] = slug or p["legacy_slug"]
            p["legacy_url"] = f"{BASE}/products/{pid}/{slug}"
            p["category_legacy_id"] = cat_id
            p["images"] = download_images(session, p)
            products.append(p)
            print(f"[{n}/{len(todo)}] {pid} {p['name'][:50]} | {p['price_toman']} | cat={cat_id} | img={len(p['images'])}")
        except Exception as e:
            print(f"[{n}] ! خطا در محصول {pid}: {e}")
        time.sleep(args.delay)

    out = OUT_DIR / "doorbinkar_missing.json"
    out.write_text(json.dumps(products, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n✓ ذخیره شد: {out} ({len(products)} محصول)")


if __name__ == "__main__":
    main()
