#!/usr/bin/env python
"""ممیزی جامع محصولات: کامل‌بودن مشخصات + سازگاری نام/فیلدها + غلط‌های نگارشی.

اجرا: venv/bin/python scripts/audit_products.py
خروجی: گزارش گروه‌بندی‌شده؛ فقط گزارش می‌دهد، چیزی را تغییر نمی‌دهد.
"""
import json
import re
import sqlite3

DB = "db.sqlite3"
c = sqlite3.connect(DB)
c.row_factory = sqlite3.Row

products = c.execute("""
    SELECT p.*, cc.name AS cat_name, cc.slug AS cat_slug, cc.category_type AS cat_type,
           pc.slug AS parent_slug
    FROM catalog_product p
    JOIN catalog_category cc ON cc.id = p.category_id
    LEFT JOIN catalog_category pc ON pc.id = cc.parent_id
    WHERE p.is_active = 1 ORDER BY p.id
""").fetchall()

# ── ابزارهای نگارشی ─────────────────────────────────────────────
AR_Y = "ي"
AR_K = "ك"
def text_issues(text):
    """غلط‌های نگارشی رایج متن فارسی."""
    out = []
    if not text:
        return out
    if AR_Y in text or AR_K in text:
        out.append("ي/ك عربی")
    if "  " in text:
        out.append("فاصله دوبل")
    if re.search(r"[آ-ی][ ]+(ی|ها|های|تر|ترین)\b", text):
        out.append("نیم‌فاصله جاافتاده (مثل «می تر»)")
    if re.search(r"\bمی [^ ]", text) or re.search(r"\bنمی [^ ]", text):
        out.append("«می/نمی» بدون نیم‌فاصله")
    if text != text.strip():
        out.append("فاصله ابتدا/انتها")
    fa = r"ء-يگچپژک"  # فقط حروف فارسی — نه اعداد/نقطه‌گذاری عربی
    if re.search(rf"[a-zA-Z][{fa}]|[{fa}][a-zA-Z]", text):
        out.append("چسبیدن فارسی/لاتین بدون فاصله/نیم‌فاصله")
    return out

TEXT_FIELDS = ["name", "short_description", "description", "board_tech_notes",
               "meta_title", "meta_description", "keywords", "geo_tags"]

issues = {}   # pid -> list[str]
def add(pid, msg):
    issues.setdefault(pid, []).append(msg)

for p in products:
    pid = p["id"]
    specs = json.loads(p["dynamic_specs"] or "{}")
    name = p["name"] or ""
    cat_type = p["cat_type"] or ("" )

    # ── ۱) فیلدهای عمومی الزامی ──
    for f, label in [("short_description", "توضیح کوتاه"), ("description", "توضیح کامل"),
                     ("meta_title", "عنوان متا"), ("meta_description", "توضیح متا"),
                     ("keywords", "کلمات کلیدی"), ("geo_tags", "شهرهای هدف")]:
        if not (p[f] or "").strip():
            add(pid, f"{label} خالی است")
    if not p["brand"]:
        add(pid, "برند خالی است")

    # ── ۲) محدوده طول متا ──
    mt = p["meta_title"] or ""
    if mt and not (20 <= len(mt) <= 65):
        add(pid, f"طول عنوان متا نامتعارف ({len(mt)} کاراکتر)")
    md = p["meta_description"] or ""
    if md and not (50 <= len(md) <= 165):
        add(pid, f"طول توضیح متا نامتعارف ({len(md)} کاراکتر)")

    # ── ۳) غلط نگارشی در فیلدهای متنی ──
    for f in TEXT_FIELDS:
        for iss in text_issues(p[f] or ""):
            add(pid, f"{f}: {iss}")

    # ── ۴) سازگاری نام با فیلدها ──
    mres = re.search(r"(\d+)\s*مگاپیکسل", name)
    if cat_type == "board" or p["parent_slug"] in ("ahd-camera-board", "ip-camera-board"):
        if not p["board_system"]:
            add(pid, "سیستم برد خالی")
        # رزولوشن نام ↔ فیلد
        if mres and p["board_resolution"]:
            if mres.group(1) + "MP" != p["board_resolution"]:
                # نام‌های دو رزولوشن مثل «5 و 8 مگاپیکسل»
                if " و " not in name.split("مگاپیکسل")[0][-8:]:
                    add(pid, f"رزولوشن نام ({mres.group(1)}MP) ≠ فیلد ({p['board_resolution']})")
        elif mres and not p["board_resolution"]:
            add(pid, "رزولوشن در نام هست ولی فیلد رزولوشن خالی است")
        # سونی در نام ↔ سنسور
        if "سونی" in name and p["sensor_name"] and "sony" not in (p["sensor_name"] or "").lower() \
           and "imx" not in (p["sensor_name"] or "").lower() and "IMX" not in p["sensor_name"]:
            add(pid, f"نام می‌گوید سونی ولی سنسور «{p['sensor_name']}» است")
        # سیستم ↔ دسته
        if p["cat_slug"] == "ahd-camera-board" and p["board_system"] == "IP":
            add(pid, "دسته AHD ولی سیستم IP")
        if p["cat_slug"] == "ip-camera-board" and p["board_system"] == "AHD":
            add(pid, "دسته IP ولی سیستم AHD")
        # ابعاد دو تکه در نام/دیتاشیت ولی فیلد ساده
        # تضاد فشرده‌سازی با سیستم
        if p["board_system"] == "AHD" and specs.get("فشرده-سازی-ویدئو"):
            add(pid, "برد AHD فیلد فشرده‌سازی ویدئو (مخصوص IP) دارد")
        if p["board_system"] == "IP" and specs.get("خروجی-4in1") == "دارد":
            add(pid, "برد IP فیلد خروجی 4in1 (مخصوص AHD) دارد")
        # کارت حافظه: ظرفیت پر ولی «ندارد»
        if specs.get("ظرفیت-کارت-حافظه") == "ندارد" and specs.get("پشتیبانی-از-کارت-حافظه"):
            add(pid, "تضاد کارت حافظه: چک‌باکس دارد ولی ظرفیت «ندارد»")

    if cat_type == "lens" or p["parent_slug"] == "lens-holder":
        if not p["lens_degree"] and not name.strip().startswith("هولدر"):
            add(pid, "فاصله کانونی لنز خالی")
        # فاصله کانونی در نام (4 میلی‌متر) ↔ فیلد
        mm = re.search(r"(\d+(?:\.\d+)?)\s*میلی‌?متر", name)
        if mm and p["lens_degree"]:
            v = mm.group(1) + "mm"
            if p["lens_degree"] != v and " تا " not in name and "-" not in name:
                add(pid, f"فاصله کانونی نام ({v}) ≠ فیلد ({p['lens_degree']})")

    # ── ۵) اسلاگ ↔ نام (رزولوشن/مدل اشتباه در اسلاگ) ──
    slug = p["slug"] or ""
    if not slug:
        add(pid, "اسلاگ خالی")
    else:
        ms = re.search(r"(\d+)mp", slug)
        if ms and mres and ms.group(1) != mres.group(1) and " و " not in name:
            add(pid, f"رزولوشن اسلاگ ({ms.group(1)}mp) ≠ نام ({mres.group(1)}MP)")

    # ── ۶) تصویر ──
    img = c.execute("SELECT COUNT(*) FROM catalog_product_image WHERE product_id=?", (pid,)).fetchone()[0]
    if img == 0:
        add(pid, "بدون تصویر")

    # ── ۷) قیمت/موجودی ──
    var = c.execute("SELECT COUNT(*) FROM catalog_product_variant WHERE product_id=? AND is_active=1", (pid,)).fetchone()[0]
    if var == 0:
        add(pid, "بدون واریانت فعال (قیمت)")

# ── خروجی ────────────────────────────────────────────────────
by_id = {p["id"]: p for p in products}
print(f"محصولات فعال: {len(products)} | دارای حداقل یک مورد: {len(issues)}\n")
for pid, msgs in sorted(issues.items()):
    p = by_id[pid]
    print(f"[{pid}] {p['name'][:60]}")
    for m in msgs:
        print(f"   • {m}")
