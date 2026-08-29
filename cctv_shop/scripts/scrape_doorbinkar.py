#!/usr/bin/env python
"""
scripts/scrape_doorbinkar.py
─────────────────────────────
استخراج محصولات سایت قدیمی doorbinkar.com برای انتقال به فروشگاه جدید.

خروجی:
    scripts/output/doorbinkar_products.json   ← رکورد همه محصولات
    media/products/migrated/<legacy_id>/...    ← تصاویر دانلودشده

اجرا (از دایرکتوری cctv_shop):
    venv/bin/python scripts/scrape_doorbinkar.py
    venv/bin/python scripts/scrape_doorbinkar.py --no-images   # فقط متادیتا

نکته: درخواست‌ها با وقفه فرستاده می‌شوند تا به سایت فشار نیاید.
"""

import argparse
import json
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE = "https://doorbinkar.com"
SEARCH_URL = f"{BASE}/ajax/CategoryController/categorySearch"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
    "X-Requested-With": "XMLHttpRequest",
}
DELAY = 1.0  # ثانیه وقفه بین درخواست‌ها

# دسته‌های قدیمی — leafها اول (محصول به اولین/خاص‌ترین دسته‌ای نسبت داده می‌شود)
LEAF_CATEGORY_IDS = [8, 9, 19, 10, 18, 11, 12, 15, 16, 13, 14, 17, 20, 22]
ROOT_CATEGORY_IDS = [1, 2, 3, 4, 21]

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BASE_DIR / "scripts" / "output"
IMG_DIR = BASE_DIR / "media" / "products" / "migrated"

FA_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")


def fetch_category_product_links(session, category_id):
    """برگرداندن لیست (id, slug) محصولات یک دسته — با صفحه‌بندی."""
    found = {}  # id -> slug
    page = 1
    while True:
        resp = session.post(
            SEARCH_URL,
            headers={**HEADERS, "Referer": f"{BASE}/cat/{category_id}/"},
            data={
                "category_id": category_id,
                "is_buyable": "false",
                "brand_ids": "",
                "spec_ids": "[]",
                "pageNumber": page,
                "itemCount": 48,
                "paginationListCount": 7,
                "__ajax": 1,
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        html = data.get("html", {}).get("content-items", "")
        links = re.findall(r"/products/(\d+)/([^\"?/]+)", html)
        new = 0
        for pid, slug in links:
            if pid not in found:
                found[pid] = slug
                new += 1
        # صفحه‌بندی: اگر «بعدی» نبود یا محصول جدیدی نیامد، تمام
        pages = [int(n) for n in re.findall(r"[?&]page=(\d+)", json.dumps(data.get("paginationList", [])))]
        max_page = max(pages, default=1)
        if page >= max_page or (new == 0 and page > 1):
            break
        page += 1
        time.sleep(DELAY)
    return found


def parse_price(text):
    digits = re.sub(r"[^\d]", "", (text or "").translate(FA_DIGITS))
    return int(digits) if digits else None


def fetch_product(session, legacy_id, slug):
    """استخراج داده‌های یک صفحه محصول."""
    url = f"{BASE}/products/{legacy_id}/{slug}"
    resp = session.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    # نام
    h1 = soup.find("h1")
    name = h1.get_text(strip=True) if h1 else (soup.title.get_text(strip=True) if soup.title else "")

    # قیمت (تومان) — قیمت با تخفیف، fallback به متا
    price = None
    pd = soup.select_one(".price-with-discount")
    if pd:
        price = parse_price(pd.get_text())
    if price is None:
        meta_price = soup.find("meta", attrs={"content": re.compile(r"^\d{5,}$")})
        if meta_price:
            price = int(meta_price["content"])

    # متاها
    def meta(name=None, prop=None):
        tag = soup.find("meta", attrs={"name": name} if name else {"property": prop})
        return (tag.get("content") or "").strip() if tag else ""

    meta_description = meta(name="description")
    keywords = meta(name="keywords")
    meta_title = soup.title.get_text(strip=True) if soup.title else ""

    # توضیحات — متن ساده (با حفظ خطوط لیست‌ها)
    description = ""
    body = soup.select_one("#collapseOne .panel-body") or soup.select_one(".panel-body")
    if body:
        for br in body.find_all(["p", "li", "br"]):
            br.append("\n")
        description = re.sub(r"\n{3,}", "\n\n", body.get_text()).strip()

    # تصاویر — نسخه ۵۰۰×۵۰۰
    images = []
    for src in re.findall(r"/product-image/" + re.escape(str(legacy_id)) + r"/[^\"'\s]+\.webp", resp.text):
        if "-500x500" in src:
            full = src if src.startswith("http") else BASE + src
            if full not in images:
                images.append(full)
    og_image = meta(prop="og:image")

    # موجودی — دکمه افزودن به سبد فعال است؟
    available = bool(soup.select_one(".add_to_cart")) and "ناموجود" not in resp.text[:resp.text.find("add_to_cart") + 200]

    return {
        "legacy_id": int(legacy_id),
        "legacy_slug": slug,
        "legacy_url": url,
        "name": name,
        "price_toman": price,
        "meta_title": meta_title,
        "meta_description": meta_description,
        "keywords": keywords,
        "description": description,
        "image_urls": images or ([og_image] if og_image else []),
        "in_stock": available,
    }


def download_images(session, product):
    """دانلود تصاویر محصول و برگرداندن مسیرهای لوکال نسبت به MEDIA_ROOT."""
    local = []
    pid = str(product["legacy_id"])
    dest_dir = IMG_DIR / pid
    for i, url in enumerate(product["image_urls"]):
        ext = ".webp"
        fname = f"{pid}-{i}{ext}"
        dest = dest_dir / fname
        if not dest.exists():
            dest_dir.mkdir(parents=True, exist_ok=True)
            try:
                r = session.get(url, headers=HEADERS, timeout=60)
                r.raise_for_status()
                dest.write_bytes(r.content)
                time.sleep(0.3)
            except Exception as e:
                print(f"    ! خطا در دانلود {url}: {e}")
                continue
        local.append(str(Path("products") / "migrated" / pid / fname))
    return local


def main():
    global DELAY
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-images", action="store_true", help="تصاویر دانلود نشوند")
    parser.add_argument("--delay", type=float, default=DELAY)
    args = parser.parse_args()
    DELAY = args.delay

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    session = requests.Session()

    # ── ۱) جمع‌آوری لینک محصولات از همه دسته‌ها ──
    product_category = {}  # legacy_id -> (slug, category_legacy_id)
    for cat_id in LEAF_CATEGORY_IDS + ROOT_CATEGORY_IDS:
        links = fetch_category_product_links(session, cat_id)
        print(f"دسته {cat_id}: {len(links)} محصول")
        for pid, slug in links.items():
            product_category.setdefault(pid, (slug, cat_id))
        time.sleep(DELAY)

    print(f"\nجمع محصولات یکتا: {len(product_category)}")

    # ── ۲) استخراج هر محصول ──
    products = []
    for n, (pid, (slug, cat_id)) in enumerate(sorted(product_category.items(), key=lambda x: int(x[0])), 1):
        try:
            p = fetch_product(session, pid, slug)
            p["category_legacy_id"] = cat_id
            if not args.no_images:
                p["images"] = download_images(session, p)
            else:
                p["images"] = []
            products.append(p)
            print(f"[{n}/{len(product_category)}] {pid} {p['name'][:50]} | {p['price_toman']} | cat={cat_id} | img={len(p['images'])}")
        except Exception as e:
            print(f"[{n}] ! خطا در محصول {pid}: {e}")
        time.sleep(DELAY)

    out = OUT_DIR / "doorbinkar_products.json"
    out.write_text(json.dumps(products, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n✓ ذخیره شد: {out} ({len(products)} محصول)")


if __name__ == "__main__":
    main()
