#!/usr/bin/env python
"""تولید/بهینه‌سازی محتوای SEO و GEO بردهای دوربین بر اساس مشخصات ساختاریافته.

اجرا:  venv/bin/python scripts/generate_board_seo.py [--apply] [--sample ID ...]
- meta_title / meta_description / keywords / geo_tags: همیشه بازتولید می‌شوند.
- short_description / description / board_tech_notes: فقط اگر خالی‌اند پر می‌شوند
  (متن‌های دستی موجود حفظ می‌شود).
هیچ مشخصه‌ای به متن اضافه نمی‌شود مگر اینکه در فیلدهای محصول موجود باشد.
"""
import json
import re
import sqlite3
import sys

DB = "db.sqlite3"

GEO_CITIES = "تهران، کرج، مشهد، اصفهان، شیراز، تبریز، قم، اهواز، رشت، کرمان"

RES_FA = {"2MP": "دو", "3MP": "سه", "4MP": "چهار", "5MP": "پنج", "8MP": "هشت", "12MP": "دوازده"}


def fa_res(res):
    return f"{RES_FA.get(res, res)}‌مگاپیکسل" if res in RES_FA else res


def bare_number(s):
    """GC5083 → 5083 — همان‌طور که نصاب‌ها در گوگل سرچ می‌کنند."""
    if not s:
        return ""
    m = re.search(r"(\d{4,})", s)
    return m.group(1) if m else ""


def feature_labels(specs):
    """ویژگی‌های شاخص از dynamic_specs — فقط موارد مثبت."""
    feats = []
    if specs.get("تشخیص-چهره") == "دارد":
        feats.append("تشخیص انسان و چهره")
    if specs.get("تشخیص-خودرو") == "دارد":
        feats.append("تشخیص خودرو")
    jp = specs.get("جستجو-چهره-پلاک", "")
    if "پلاک" in jp:
        feats.append("پلاک‌خوان با لیست سفید/سیاه")
    if "چهره" in jp:
        feats.append("جستجو و رکورد چهره")
    if specs.get("ردیابی-خودکار"):
        feats.append("ردیابی خودکار")
    if specs.get("حصار-الکترونیکی"):
        feats.append("حصار الکترونیکی")
    if specs.get("پشتیبانی-led-دوال-لایت"):
        feats.append("دید در شب رنگی دوال‌لایت")
    if specs.get("onvif"):
        feats.append("ONVIF")
    if specs.get("پشتیبانی-poe"):
        feats.append("PoE")
    if specs.get("مکالمه-دوطرفه") == "دارد":
        feats.append("مکالمه دوطرفه")
    if specs.get("امپلی-فایر-داخلی"):
        feats.append("آمپلی‌فایر داخلی")
    if specs.get("خروجی-4in1") == "دارد":
        feats.append("خروجی 4in1 (AHD/TVI/CVI/CVBS)")
    if specs.get("پشتیبانی-utc"):
        feats.append("تنظیم OSD از روی دستگاه با UTC")
    cap = specs.get("ظرفیت-کارت-حافظه", "")
    if cap and cap != "ندارد":
        feats.append(f"کارت حافظه {cap.replace('تا ', 'تا ')}")
    return feats


def clean_model(model, name):
    """مدل خوانا برای متن — مدل‌های طولانی انگلیسی به فرم فشرده درمی‌آیند."""
    if model and len(model) <= 20:
        return model
    m = re.search(r"(\d+(?:\.\d+)?)\s*[~\-]\s*(\d+(?:\.\d+)?)", model or "")
    if m:
        return f"{m.group(1)}-{m.group(2)}mm"
    return ""


def build(p):
    """p = dict ردیف محصول. خروجی: dict فیلدهای تولیدشده."""
    name, model = p["name"], p["model_number"] or p["board_name"] or ""
    system = p["board_system"]
    res = p["board_resolution"] or ""
    res_fa = fa_res(res)
    sensor, isp = p["sensor_name"] or "", p["ai_processor"] or ""
    # سنسورهای نامشخص را وارد متن نکن
    sensor = "" if sensor in ("نا مشخص", "نامشخص", "سازنده عنوان نکرده", "CMOS") else sensor
    isp = "" if "عنوان نکرده" in isp else isp
    specs = p["specs"]
    feats = feature_labels(specs)
    model_txt = clean_model(model, name)  # مدل خوانا برای استفاده در متن
    board_num = bare_number(model) or bare_number(sensor)
    sys_fa = "تحت شبکه (IP)" if system == "IP" else "AHD"
    is_lens_ctrl = "کنترل برد" in name or "MOTORIZE CONTROL" in (model or "").upper()

    # ── کلمات کلیدی ──
    kw = [
        f"برد دوربین {model_txt}" if model_txt else None,
        f"برد {board_num}" if board_num else None,
        f"برد دوربین مداربسته {res_fa}" if res else None,
        f"برد دوربین {system}" if system else None,
        f"سنسور {sensor}" if sensor else None,
        f"سنسور {bare_number(sensor)}" if bare_number(sensor) else None,
        f"پردازنده {isp}" if isp else None,
        f"برد {system} {res}" if system and res else None,
        "خرید برد دوربین مداربسته",
        "قیمت برد دوربین مداربسته",
        "برد مونتاژ دوربین",
        "تعمیر دوربین مداربسته",
    ]
    if is_lens_ctrl:
        kw = [f"کنترل برد لنز موتورایز {model_txt}", "برد لنز موتورایز", "لنز موتورایز دوربین مداربسته",
              f"لنز {model_txt}", "برد زوم موتوردار", "کنترل زوم و فوکوس دوربین",
              "خرید کنترل برد لنز", "قیمت لنز موتورایز"] + [k for k in kw if k and "برد دوربین مداربسته" not in k]
    if "پلاک‌خوان با لیست سفید/سیاه" in feats:
        kw += ["برد پلاک‌خوان", "دوربین پلاک‌خوان", "LPR"]
    if specs.get("npu-tops"):
        kw += ["برد هوش مصنوعی دوربین", "دوربین هوشمند تشخیص انسان"]
    if "دید در شب رنگی دوال‌لایت" in feats:
        kw += ["برد فول کالر", "دوربین رنگی شب"]
    if p["brand"]:
        kw.append(f"برد {p['brand']}")
    keywords = "، ".join(dict.fromkeys(k for k in kw if k))

    # ── متا ── (نام محصول از قبل سئوشکل است)
    meta_title = f"{name} | قیمت و خرید"
    if len(meta_title) > 60:
        meta_title = name[:57].rstrip() + "…"

    bits = []
    if sensor:
        bits.append(f"سنسور {sensor}")
    if isp:
        bits.append(f"پردازنده {isp}")
    if p["board_fps"]:
        bits.append(p["board_fps"])
    headline = "، ".join(bits)
    feat_txt = "، ".join(feats[:3])
    base = f"برد {model_txt} {res_fa} {sys_fa}".replace("  ", " ").strip() if model_txt else name
    meta_description = (
        base
        + (f" با {headline}" if headline else "")
        + (f"؛ {feat_txt}" if feat_txt else "")
        + "؛ مناسب مونتاژ و تعمیر دوربین مداربسته. خرید آنلاین از دوربینکار با ارسال سریع."
    )
    if len(meta_description) > 160:
        meta_description = meta_description[:157].rstrip("؛ ،") + "…"

    # ── توضیح کوتاه ──
    if is_lens_ctrl:
        short_description = (
            f"کنترل برد لنز موتورایز {model_txt} برند YTOT برای کنترل زوم و فوکوس خودکار لنزهای موتوردار دوربین‌های IP؛ "
            "مناسب مونتاژ و تعمیر دوربین‌های زوم‌دار."
        )
    else:
        short_description = (
            base
            + (f" با {headline}" if headline else "")
            + (f"؛ {feat_txt}" if feat_txt else "")
            + "؛ آماده مونتاژ و تعمیر دوربین."
        )

    # ── توضیح کامل ──
    if is_lens_ctrl:
        description = (
            f"کنترل برد لنز موتورایز {model_txt} ساخت YTOT، برد کنترل زوم و فوکوس خودکار برای لنزهای موتوردار {model_txt} "
            "دوربین‌های مداربسته تحت شبکه است و زوم اپتیکال چندبرابر را بدون بازکردن کیس دوربین ممکن می‌کند.\n\n"
            "این برد بین برد اصلی دوربین و لنز موتورایز قرار می‌گیرد و فرمان‌های زوم/فوکوس را از نرم‌افزار یا NVR به موتورهای لنز منتقل می‌کند؛ "
            "برای ساخت دوربین‌های وریفوکال موتوردار یا تعویض برد معیوب همین خانواده کاربرد دارد.\n\n"
            "ارسال به تهران، کرج، مشهد، اصفهان، شیراز، تبریز و سراسر کشور از فروشگاه دوربینکار."
        )
    else:
        paras = [
            f"برد {model_txt or name} یک برد دوربین مداربسته {sys_fa}"
            + (f" با رزولوشن {res_fa}" if res else "")
            + " برای مونتاژ، تعمیر و ارتقای دوربین‌هاست"
            + (f"؛ قلب تصویر آن سنسور {sensor}" if sensor else "")
            + (f" و پردازنده {isp} است." if isp else "."),
        ]
        if feats:
            paras.append("قابلیت‌های اصلی: " + "، ".join(feats) + ".")
        tech = []
        if p["board_fps"]:
            tech.append(f"نرخ فریم {p['board_fps']}")
        if specs.get("فشرده-سازی-ویدئو"):
            tech.append(f"فشرده‌سازی {specs['فشرده-سازی-ویدئو']}")
        if p["board_dimensions"]:
            tech.append(f"ابعاد برد {p['board_dimensions']} میلی‌متر")
        if specs.get("محدوده-ولتاژ-کاری"):
            tech.append(f"تغذیه {specs['محدوده-ولتاژ-کاری']}")
        if specs.get("حفاظت-صاعقه"):
            tech.append(f"حفاظت صاعقه {specs['حفاظت-صاعقه']}")
        if tech:
            paras.append("مشخصات فنی: " + "، ".join(tech) + ".")
        paras.append(
            "این برد برای مونتاژکاران، تولیدکنندگان و تعمیرکاران دوربین مداربسته عرضه می‌شود؛ "
            "ارسال به تهران، کرج، مشهد، اصفهان، شیراز، تبریز و سراسر کشور از فروشگاه دوربینکار."
        )
        description = "\n\n".join(paras)

    # ── اطلاعات فنی بیشتر ──
    notes = []
    if specs.get("محدوده-ولتاژ-کاری"):
        notes.append(f"تغذیه: {specs['محدوده-ولتاژ-کاری']}")
    if specs.get("حفاظت-صاعقه"):
        notes.append(f"حفاظت در برابر صاعقه: {specs['حفاظت-صاعقه']}")
    if p["board_dimensions"]:
        notes.append(f"ابعاد: {p['board_dimensions']}mm")
    if p["board_fps"]:
        notes.append(f"نرخ فریم استریم اصلی: {p['board_fps']}")
    if specs.get("ظرفیت-کارت-حافظه") and specs["ظرفیت-کارت-حافظه"] != "ندارد":
        notes.append(f"کارت حافظه: {specs['ظرفیت-کارت-حافظه']}")
    if specs.get("فشرده-سازی-ویدئو"):
        notes.append(f"کدک ویدیو: {specs['فشرده-سازی-ویدئو']}")
    if specs.get("حساسیت-نوری"):
        notes.append(f"حساسیت نوری: {specs['حساسیت-نوری']}")
    board_tech_notes = "؛ ".join(notes)

    return {
        "keywords": keywords, "geo_tags": GEO_CITIES,
        "meta_title": meta_title, "meta_description": meta_description,
        "short_description": short_description, "description": description,
        "board_tech_notes": board_tech_notes,
    }


def main():
    apply = "--apply" in sys.argv
    samples = [int(a) for a in sys.argv[sys.argv.index("--sample") + 1:]] if "--sample" in sys.argv else []
    c = sqlite3.connect(DB)
    rows = c.execute("""
        SELECT id, name, model_number, board_name, board_system, board_resolution,
               sensor_name, ai_processor, board_dimensions, board_fps, brand,
               dynamic_specs, short_description, description, board_tech_notes
        FROM catalog_product WHERE category_id IN (10,11) AND is_active=1 ORDER BY id
    """).fetchall()
    cols = ["id", "name", "model_number", "board_name", "board_system", "board_resolution",
            "sensor_name", "ai_processor", "board_dimensions", "board_fps", "brand",
            "dynamic_specs", "short_description", "description", "board_tech_notes"]
    n = 0
    for row in rows:
        p = dict(zip(cols, row))
        p["specs"] = json.loads(p["dynamic_specs"] or "{}")
        gen = build(p)
        # متن‌های دستی موجود حفظ می‌شوند — فقط فیلدهای خالی پر می‌شوند
        for f in ("short_description", "description", "board_tech_notes"):
            if p[f]:
                gen[f] = p[f]
        if p["id"] in samples or not apply:
            if p["id"] in samples or not samples and not apply:
                pass
        if p["id"] in samples:
            print(f"{'='*70}\n[{p['id']}] {p['name']}")
            for f in ("meta_title", "meta_description", "keywords", "geo_tags",
                      "short_description", "description", "board_tech_notes"):
                print(f"\n▸ {f}:\n{gen[f]}")
        if apply:
            c.execute("""
                UPDATE catalog_product SET meta_title=?, meta_description=?, keywords=?, geo_tags=?,
                       short_description=?, description=?, board_tech_notes=?
                WHERE id=?""",
                (gen["meta_title"], gen["meta_description"], gen["keywords"], gen["geo_tags"],
                 gen["short_description"], gen["description"], gen["board_tech_notes"], p["id"]))
            n += 1
    if apply:
        c.commit()
        print(f"\n✅ {n} محصول به‌روز شد")
    else:
        print(f"\n(dry-run) {len(rows)} محصول — نمونه: --sample 24 8 110")

if __name__ == "__main__":
    main()
