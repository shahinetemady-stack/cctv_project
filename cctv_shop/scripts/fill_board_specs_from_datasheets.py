#!/usr/bin/env python
"""تکمیل خودکار مشخصات بردها از روی متن دیتاشیت PDF لینک‌شده.

اجرا:  venv/bin/python scripts/fill_board_specs_from_datasheets.py [--apply]
بدون --apply فقط گزارش می‌دهد (dry-run). مقادیر موجود بازنویسی نمی‌شوند —
فقط کلیدهای خالی/ناموجود پر می‌شوند. «ندارد» هرگز خودکار ثبت نمی‌شود
(ذکرنشدن در دیتاشیت به معنای نبود قابلیت نیست).
"""
import json
import re
import sqlite3
import subprocess
import sys

DB = "db.sqlite3"
MEDIA = "media/"

# الگوها: (کلید spec، نوع، regexها، مقدار/استخراج)
def lux_or_none(m):
    return m if m else None

RULES = [
    # ── مشترک (دسته ریشه برد) ──
    ("پشتیبانی-از-کارت-حافظه", "checkbox", [r"tf\s*card", r"sd\s*card", r"micro\s*sd", r"کارت حافظه"], True),
    ("پشتیبانی-led-دوال-لایت", "checkbox", [r"dual[\s-]?light", r"دوال لایت", r"دو منبع نور", r"دو نور"], True),
    ("خروجی-آلارم", "select", [r"alarm[\s_-]?out", r"خروجی آلارم", r"خروجی هشدار"], "دارد"),
    ("dwdr3dnr", "select", [r"dwdr", r"3d[\s-]?nr", r"3dnr"], "دارد"),
    ("مکالمه-دوطرفه", "select", [r"two[\s-]?way", r"دوطرفه", r"intercom", r"مکالمه"], "دارد"),
    # آمپلی‌فایر داخلی = آمپ قدرت سرجمع برای اتصال مستقیم اسپیکر — نه پین IO یا پری‌امپ میکروفون
    ("امپلی-فایر-داخلی", "checkbox",
     [r"built-in (power )?amplifier", r"on-?board amplifier", r"amplifier output",
      r"آمپلی‌? ?فایر (داخلی|سرجمع)", r"اتصال مستقیم اسپیکر", r"speaker directly"], True),
    ("wdr", "checkbox", [r"\bwdr\b", r"true wdr"], True),
    # ── IP ──
    ("onvif", "checkbox", [r"onvif"], True),
    ("پشتیبانی-poe", "checkbox", [r"\bpoe\b", r"power over ethernet", r"پاور اترنت|پوئه"], True),
    ("لنز-زوم-موتوردار", "checkbox", [r"motorized", r"موتوردار", r"موتورایز"], True),
    ("حصار-الکترونیکی", "checkbox", [r"electronic fence", r"electric fence", r"حصار الکترونیکی"], True),
    ("تشخیص-عبور-از-مرز", "checkbox", [r"cross[\s-]?border", r"cross[\s-]?line", r"عبور از مرز"], True),
    ("ردیابی-خودکار", "checkbox", [r"auto[\s-]?track", r"human tracking", r"ردیابی"], True),
    ("تشخیص-چهره", "select", [r"face (detection|capture|recognition)", r"humanoid", r"human (shape )?detection", r"تشخیص چهره", r"تشخیص انسان"], "دارد"),
    ("تشخیص-خودرو", "select", [r"vehicle detection", r"humanoid/?vehicle", r"تشخیص خودرو"], "دارد"),
]

def extract_text(pdf_path):
    try:
        return subprocess.run(
            ["pdftotext", "-layout", pdf_path, "-"],
            capture_output=True, text=True, timeout=30,
        ).stdout.lower()
    except Exception:
        return ""

def extra_rules(text):
    """فیلدهای مبتنی بر استخراج مقدار (نه صرفاً حضور کلیدواژه)."""
    out = {}
    # فشرده‌سازی ویدئو — بالاترین سطح ذکرشده
    if re.search(r"h\.?\s?265\+|h265\+", text):
        out["فشرده-سازی-ویدئو"] = "H.265+"
    elif re.search(r"h\.?\s?265", text):
        out["فشرده-سازی-ویدئو"] = "H.265"
    elif re.search(r"h\.?\s?264", text):
        out["فشرده-سازی-ویدئو"] = "H.264"
    # توان NPU — 1T / 0.5T / 2.5TOPS
    m = re.search(r"(\d+(?:\.\d+)?)\s*t(?:ops)?[\s@]", text)
    if m and ("npu" in text or "computing power" in text or "algorithm" in text or "tops" in text):
        v = m.group(1)
        out["npu-tops"] = f"{v}TOPS" if "tops" in text else f"{v}T"
    # ظرفیت کارت حافظه
    m = re.search(r"(?:max|up to|تا|support)\D{0,12}(\d{3})\s*g", text)
    if m and ("tf" in text or "card" in text or "کارت" in text):
        cap = m.group(1)
        if cap in ("128", "256", "512"):
            out["ظرفیت-کارت-حافظه"] = f"تا {cap}GB"
    # جستجو/رکورد چهره/پلاک — سیگنال: مقایسه/دیتابیس چهره یا شناسایی پلاک،
    # نه صرفاً تشخیص (عباراتی مثل face recognition without exposure سیگنال نیستند)
    face = bool(re.search(r"face (comparison|database|library|search)|مقایسه چهره|کتابخانه چهره|تطبیق چهره", text))
    # پلاک = شناسایی/دیتابیس/لیست — صرف «تصویربرداری پلاک» (capture) کافی نیست
    plate = bool(re.search(r"license[\s-]?plate.{0,40}(recognition|database|black|white|search)|(capture|recognition) & recognition|شناسایی پلاک|پلاک‌خوان|خوانش پلاک", text))
    if face and plate:
        out["جستجو-چهره-پلاک"] = "چهره و پلاک"
    elif face:
        out["جستجو-چهره-پلاک"] = "چهره"
    elif plate:
        out["جستجو-چهره-پلاک"] = "پلاک"
    # AHD — 4in1 / UTC / صدای کواکسیال / ولتاژ / صاعقه
    if re.search(r"4\s*in\s*1|4in1|ahd/tvi/cvi", text):
        out["خروجی-4in1"] = "دارد"
    if re.search(r"\butc\b", text):
        out["پشتیبانی-utc"] = True
    if re.search(r"audio over coax|coaxial audio|صدای کواکسیال|\baoc\b", text):
        out["صدای-کواکسیال"] = True
    m = re.search(r"dc\s*(\d+)\s*[-–]\s*(\d+)\s*v", text)
    if not m:
        # الگوی بدون DC — مثل Support 6-15V Wide voltage (با زمینه voltage/wide/power)
        m = re.search(r"(?:wide voltage|voltage|power|supply|تغذیه|ولتاژ)[^\n]{0,25}?(\d{1,2})\s*[-–]\s*(\d{1,2})\s*v", text)
    if not m:
        m = re.search(r"(\d{1,2})\s*[-–]\s*(\d{1,2})\s*v\s*wide", text)
    if m:
        out["محدوده-ولتاژ-کاری"] = f"DC {m.group(1)}-{m.group(2)}V"
    m = re.search(r"(\d+)\s*kv\s*(?:lightning|surge)|(?:lightning|surge)\D{0,15}(\d+)\s*kv", text)
    if m:
        out["حفاظت-صاعقه"] = f"{m.group(1) or m.group(2)}KV"
    elif "صاعقه" in text or "lightning" in text:
        out["حفاظت-صاعقه"] = "دارد"
    return out


def extract_fps(text):
    """نرخ فریم استریم اصلی — فقط جایی که صریح است (خط main/اصلی یا الگوی XMP@NNfps)."""
    for line in text.splitlines():
        l = line.lower()
        if ("main" in l or "اصلی" in l) and "fps" in l:
            nums = [int(x) for x in re.findall(r"(\d{2})\s*fps", l) if 10 <= int(x) <= 60]
            if nums:
                return f"{max(nums)}fps"
    m = re.findall(r"(\d)\s*mp\D{0,20}?(\d{2})\s*fps", text.lower())
    if m:
        return f"{max(m, key=lambda x: int(x[0]))[1]}fps"
    return ""

def main():
    apply = "--apply" in sys.argv
    c = sqlite3.connect(DB)
    rows = c.execute("""
        SELECT p.id, p.model_number, p.datasheet_pdf, p.board_system, p.dynamic_specs, p.board_fps
        FROM catalog_product p JOIN catalog_category cc ON cc.id = p.category_id
        WHERE cc.id IN (1,10,11) AND p.is_active=1 AND p.datasheet_pdf != ''
        ORDER BY p.board_system, p.id
    """).fetchall()
    changed = 0
    for pid, model, pdf, system, specs_json, fps in rows:
        specs = json.loads(specs_json or "{}")
        text = extract_text(MEDIA + pdf)
        if not text:
            print(f"{pid:>4} {model:<28} ⚠️ متن استخراج نشد")
            continue
        found = {}
        for key, ftype, patterns, value in RULES:
            if key in specs and specs[key] not in ("", None, False):
                continue
            if any(re.search(p, text) for p in patterns):
                found[key] = value
        for key, value in extra_rules(text).items():
            if key not in specs or specs[key] in ("", None, False):
                found[key] = value
        # نرخ فریم — فیلد مدل است نه dynamic_specs
        new_fps = "" if fps else extract_fps(text)
        if not found and not new_fps:
            print(f"{pid:>4} {model:<28} — چیز جدیدی پیدا نشد")
            continue
        changed += 1
        pretty = ", ".join([f"{k}={v}" for k, v in found.items()] + ([f"board_fps={new_fps}"] if new_fps else []))
        print(f"{pid:>4} {model:<28} ← {pretty}")
        if apply:
            specs.update(found)
            if new_fps:
                c.execute("UPDATE catalog_product SET dynamic_specs=?, board_fps=? WHERE id=?",
                          (json.dumps(specs, ensure_ascii=False), new_fps, pid))
            else:
                c.execute("UPDATE catalog_product SET dynamic_specs=? WHERE id=?",
                          (json.dumps(specs, ensure_ascii=False), pid))
    if apply:
        c.commit()
        print(f"\n✅ {changed} محصول به‌روز شد")
    else:
        print(f"\n(dry-run) {changed} محصول تغییر می‌کند — با --apply اعمال کن")

if __name__ == "__main__":
    main()
