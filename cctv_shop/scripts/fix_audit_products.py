#!/usr/bin/env python
"""اصلاحات ممیزی محصولات — نگارش فارسی + داده‌های ناقص + متن‌های خالی.

اجرا: venv/bin/python scripts/fix_audit_products.py [--apply]
"""
import json
import re
import sqlite3
import sys

DB = "db.sqlite3"
ZWNJ = "\u200c"

TEXT_FIELDS = ["name", "short_description", "description", "board_tech_notes",
               "meta_title", "meta_description", "keywords", "geo_tags"]


def normalize_fa(t):
    """اصلاحات نگارشی استاندارد فارسی — فقط تغییرهای بدون ریسک."""
    if not t:
        return t
    t = t.replace("ي", "ی").replace("ك", "ک")
    # می/نمی + فاصله → نیم‌فاصله (مثل «می شود» → «می‌شود»)
    t = re.sub(r"\b(می|نمی) +", r"\1" + ZWNJ, t)
    # Latin/عدد + ها/های → نیم‌فاصله (مثل NVRهای → NVR‌ها)
    t = re.sub(r"([A-Za-z0-9\)\]])(ها|های|هایی)\b", r"\1" + ZWNJ + r"\2", t)
    # عدد چسبیده به مگاپیکسل/میلی‌متر → فاصله (5مگاپیکسلی → 5 مگاپیکسلی)
    t = re.sub(r"(\d)(مگاپیکسل|میلی‌?متر)", r"\1 \2", t)
    # غلط املایی پرتکرار
    t = t.replace("میلیمتر", "میلی‌متر")
    t = re.sub(r" *\n *", "\n", t)          # فاصله اضافی لبه خطوط
    t = re.sub(r"[^\S\n]{2,}", " ", t)      # فاصله/تب دوبل داخل خط (نه \n\n)
    return t.strip()


# ── تولید متن برای محصولات غیربرد با توضیح خالی ─────────────
def gen_text(p):
    """متن صادقانه بر اساس اجزای نام — بدون ادعای مشخصه‌ای که در نام نیست."""
    name = p["name"]
    model = re.search(r"مدل[:\s]*([\w\-\.\+ ]+)$", name)
    model = model.group(1).strip() if model else ""
    kind = None
    if "کیس" in name:
        kind = "housing"
    elif "کابل" in name:
        kind = "cable"
    elif "هولدر" in name:
        kind = "holder"
    elif "میکروفون" in name:
        kind = "mic"
    elif "فوم" in name or "پیچ" in name:
        kind = "accessory"
    elif name.startswith("دوربین مداربسته"):
        kind = "camera"
    elif "لنز" in name:
        kind = "lens"
    if not kind:
        return None

    m = {"housing": "کیس", "cable": "کابل", "holder": "هولدر لنز", "mic": "میکروفون",
         "accessory": "قلم همراه", "camera": "دوربین آماده", "lens": "لنز"}[kind]
    attrs = []
    if "فلزی" in name:
        attrs.append("بدنه فلزی مقاوم")
    if "پلاستیکی" in name:
        attrs.append("بدنه پلاستیکی سبک")
    if "وارم‌لایت" in name or "وارم لایت" in name:
        attrs.append("سازگار با بردهای وارم‌لایت (دید در شب رنگی)")
    if "پلیسی" in name:
        attrs.append("طراحی پلیسی")
    if "فیش‌آی" in name:
        attrs.append("مناسب لنز فیش‌آی")
    if "رم‌ساپورت" in name:
        attrs.append("پشتیبانی از کارت حافظه")
    if "POE" in name or "poe" in name:
        attrs.append("پشتیبانی از PoE")
    if "صدادار" in name or "صدا" in name:
        attrs.append("دارای مسیر صدا")
    if "آلارم" in name:
        attrs.append("سوکت آلارم")
    attr_txt = "، ".join(attrs)
    model_txt = f" مدل {model}" if model else ""

    short = f"{m}{model_txt} دوربین مداربسته" + (f" با {attr_txt}" if attr_txt else "") + \
            "؛ مناسب مونتاژ، تعمیر و بازسازی دوربین."
    desc = (
        f"{m}{model_txt} برای مونتاژ و تعمیر دوربین‌های مداربسته عرضه می‌شود"
        + (f"؛ {attr_txt}." if attr_txt else ".")
        + "\n\nاین قلم با بردها و قطعات استاندارد بازار سازگار است و برای مونتاژکاران و تعمیرکاران "
          "دوربین مداربسته تامین می‌شود. ارسال به تهران، کرج، مشهد، اصفهان، شیراز، تبریز و سراسر کشور "
          "از فروشگاه دوربینکار."
    )
    return short, desc


def main():
    apply = "--apply" in sys.argv
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    products = c.execute("SELECT * FROM catalog_product WHERE is_active=1").fetchall()

    n_text = n_data = n_gen = 0
    for p in products:
        pid = p["id"]
        # ۱) نرمال‌سازی نگارشی همه فیلدهای متنی
        updates = {}
        for f in TEXT_FIELDS:
            new = normalize_fa(p[f] or "")
            if new != (p[f] or ""):
                updates[f] = new
        # ۲) اصلاحات داده‌ای نقطه‌ای
        if pid == 67 and not p["board_resolution"]:
            updates["board_resolution"] = "3MP"
        if pid in (91, 109) and not p["board_resolution"]:
            updates["board_resolution"] = "5MP"
        if pid == 37 and not p["lens_degree"]:
            updates["lens_degree"] = "3.7mm"
        if pid == 35 and not p["lens_degree"]:
            updates["lens_degree"] = "6-22mm"
        if pid == 137 and not p["lens_degree"]:
            updates["lens_degree"] = "2.8mm"
        if pid in (118, 125) and len(p["meta_title"] or "") > 65:
            updates["meta_title"] = (p["meta_title"] or "")[:62].rstrip() + "…"
        if not p["brand"]:
            updates["brand"] = "NOBRAND"
        if pid == 116:
            updates["brand"] = "RUISION"
        if pid == 122:
            updates["brand"] = "YTOT"
        if pid == 105 and p["brand"] == "IR":
            updates["brand"] = "NOBRAND"
        if pid == 27 and p["brand"] == "onelink":
            updates["brand"] = "Onelink"
        # ۳) تولید توضیح برای خالی‌ها (غیر برد — بردها با اسکریپت SEO پر شدند)
        if not p["short_description"] and not p["description"]:
            gen = gen_text(dict(p))
            if gen:
                updates["short_description"], updates["description"] = gen
                n_gen += 1

        if not updates:
            continue
        label = ", ".join(f"{k}" for k in updates)
        print(f"[{pid}] {p['name'][:50]} ← {label}")
        if "name" in updates or len(updates) > 2:
            n_text += 1
        else:
            n_data += 1
        if apply:
            sets = ", ".join(f"{k}=?" for k in updates)
            c.execute(f"UPDATE catalog_product SET {sets}, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                      (*updates.values(), pid))
    if apply:
        c.commit()
        print(f"\n✅ {n_text + n_data} محصول اصلاح شد ({n_gen} متن تولیدی)")
    else:
        print(f"\n(dry-run) {n_text + n_data} محصول تغییر می‌کند ({n_gen} متن تولیدی) — با --apply اعمال کن")


if __name__ == "__main__":
    main()
