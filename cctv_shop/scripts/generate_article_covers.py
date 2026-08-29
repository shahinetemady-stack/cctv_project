# -*- coding: utf-8 -*-
"""ساخت قالب HTML کاور مقالات (تم تیره/طلایی SENTINEL + وزیرمتن)."""
import os

FONT_DIR = "/home/shahin/Desktop/cctv_project/cctv_project/cctv_frontend/public/fonts"
OUT = "/tmp/covers"
os.makedirs(OUT, exist_ok=True)

MOTIFS = {
    "chip": """
      <g stroke="#FBC02D" fill="none" stroke-width="3">
        <rect x="130" y="120" width="180" height="180" rx="18" opacity="0.9"/>
        <rect x="170" y="160" width="100" height="100" rx="10" opacity="0.45"/>
        <g opacity="0.7">
          <line x1="100" y1="150" x2="130" y2="150"/><line x1="100" y1="190" x2="130" y2="190"/>
          <line x1="100" y1="230" x2="130" y2="230"/><line x1="100" y1="270" x2="130" y2="270"/>
          <line x1="310" y1="150" x2="340" y2="150"/><line x1="310" y1="190" x2="340" y2="190"/>
          <line x1="310" y1="230" x2="340" y2="230"/><line x1="310" y1="270" x2="340" y2="270"/>
          <line x1="160" y1="90" x2="160" y2="120"/><line x1="200" y1="90" x2="200" y2="120"/>
          <line x1="240" y1="90" x2="240" y2="120"/><line x1="280" y1="90" x2="280" y2="120"/>
          <line x1="160" y1="300" x2="160" y2="330"/><line x1="200" y1="300" x2="200" y2="330"/>
          <line x1="240" y1="300" x2="240" y2="330"/><line x1="280" y1="300" x2="280" y2="330"/>
        </g>
        <circle cx="152" cy="142" r="6" fill="#FBC02D" stroke="none"/>
      </g>""",
    "lens": """
      <g stroke="#FBC02D" fill="none">
        <circle cx="220" cy="210" r="130" stroke-width="4" opacity="0.9"/>
        <circle cx="220" cy="210" r="95" stroke-width="3" opacity="0.55"/>
        <circle cx="220" cy="210" r="58" stroke-width="3" opacity="0.35"/>
        <circle cx="220" cy="210" r="26" stroke-width="2" opacity="0.8"/>
        <g stroke-width="2" opacity="0.7">
          <line x1="220" y1="80" x2="220" y2="115"/><line x1="220" y1="305" x2="220" y2="340"/>
          <line x1="90" y1="210" x2="125" y2="210"/><line x1="315" y1="210" x2="350" y2="210"/>
        </g>
        <path d="M 170 150 A 70 70 0 0 1 255 145" stroke-width="5" opacity="0.9" stroke-linecap="round"/>
      </g>""",
    "cable": """
      <g stroke="#FBC02D" fill="none" stroke-width="3">
        <circle cx="120" cy="170" r="34" opacity="0.9"/>
        <circle cx="120" cy="170" r="16" opacity="0.5"/>
        <path d="M 154 170 C 220 170, 250 250, 316 250" opacity="0.8" stroke-width="4"/>
        <rect x="316" y="222" width="70" height="56" rx="8" opacity="0.9"/>
        <line x1="330" y1="222" x2="330" y2="278" opacity="0.4"/>
        <line x1="346" y1="222" x2="346" y2="278" opacity="0.4"/>
        <line x1="362" y1="222" x2="362" y2="278" opacity="0.4"/>
        <text x="96" y="330" fill="#FBC02D" stroke="none" font-family="JetBrains Mono" font-size="26" opacity="0.85">AHD</text>
        <text x="322" y="330" fill="#FBC02D" stroke="none" font-family="JetBrains Mono" font-size="26" opacity="0.85">IP</text>
      </g>""",
    "night": """
      <g stroke="#FBC02D" fill="none" stroke-width="3">
        <path d="M 250 90 A 120 120 0 1 0 250 330 A 95 95 0 1 1 250 90 Z" opacity="0.9"/>
        <g opacity="0.8">
          <path d="M 330 150 q 26 60 0 120" />
          <path d="M 362 138 q 34 72 0 144" opacity="0.55"/>
          <path d="M 394 126 q 42 84 0 168" opacity="0.3"/>
        </g>
        <g fill="#FBC02D" stroke="none" opacity="0.9">
          <circle cx="120" cy="120" r="4"/><circle cx="160" cy="86" r="3"/>
          <circle cx="96" cy="180" r="3"/><circle cx="150" cy="150" r="2.5"/>
        </g>
      </g>""",
    "housing": """
      <g stroke="#FBC02D" fill="none" stroke-width="3">
        <path d="M 90 260 A 80 80 0 0 1 250 260 Z" opacity="0.9"/>
        <circle cx="170" cy="245" r="26" opacity="0.55"/>
        <line x1="90" y1="260" x2="250" y2="260" opacity="0.9"/>
        <g opacity="0.9">
          <rect x="292" y="150" width="120" height="58" rx="29"/>
          <circle cx="386" cy="179" r="18" opacity="0.6"/>
          <line x1="330" y1="208" x2="330" y2="252" opacity="0.7"/>
          <line x1="312" y1="252" x2="348" y2="252" opacity="0.7"/>
        </g>
      </g>""",
}

COVERS = [
    ("fullhan-vs-sony-cctv-board", "chip", "فولهان یا سونی؟", "تفاوت واقعی بردهای دوربین و انتخاب درست"),
    ("cctv-lens-focal-length-guide", "lens", "۲.۸، ۳.۶ یا ۴؟", "راهنمای انتخاب فاصله کانونی لنز"),
    ("ahd-vs-ip-existing-cabling", "cable", "AHD یا IP؟", "انتخاب دوربین بر اساس کابل‌کشی موجود"),
    ("night-vision-white-blurry-image", "night", "تصویر شب سفید یا تار است؟", "علت‌ها و راه‌حل‌های عملی"),
    ("bullet-vs-dome-housing-guide", "housing", "بولت یا دام؟", "راهنمای انتخاب بدنه دوربین مداربسته"),
]

TEMPLATE = """<!doctype html>
<html lang="fa" dir="rtl"><head><meta charset="utf-8">
<style>
@font-face {{ font-family: Vazirmatn; src: url('file://{fonts}/vazirmatn-arabic.woff2') format('woff2'); font-weight: 100 900; }}
@font-face {{ font-family: 'JetBrains Mono'; src: url('file://{fonts}/jetbrainsmono-latin.woff2') format('woff2'); }}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
html, body {{ width: 1200px; height: 630px; }}
body {{ overflow: hidden; background: #0A0A0B; font-family: Vazirmatn, sans-serif; }}
.page {{ position: relative; width: 1200px; height: 630px; overflow: hidden; }}
.grid {{ position: absolute; inset: 0;
  background-image: linear-gradient(rgba(251,192,45,0.05) 1px, transparent 1px), linear-gradient(90deg, rgba(251,192,45,0.05) 1px, transparent 1px);
  background-size: 60px 60px; }}
.glow {{ position: absolute; left: -120px; top: -5px; width: 640px; height: 640px; border-radius: 50%;
  background: radial-gradient(circle, rgba(251,192,45,0.14), rgba(251,192,45,0.04) 45%, transparent 70%); }}
.motif {{ position: absolute; left: 40px; top: 105px; width: 440px; height: 420px; }}
.content {{ position: absolute; left: 520px; top: 0; width: 608px; height: 630px;
  display: flex; flex-direction: column; justify-content: center; align-items: flex-end; text-align: right; }}
.badge {{ display: inline-flex; align-items: center; gap: 10px;
  border: 1px solid rgba(251,192,45,0.4); border-radius: 100px; padding: 8px 20px;
  color: #FBC02D; font-family: 'JetBrains Mono', monospace; font-size: 17px; letter-spacing: 3px; direction: ltr; }}
.badge .dot {{ width: 8px; height: 8px; border-radius: 50%; background: #FBC02D; box-shadow: 0 0 12px #FBC02D; }}
h1 {{ color: #F4F4F5; font-size: 62px; font-weight: 900; line-height: 1.3; margin: 34px 0 18px; }}
p.sub {{ color: #A1A1AA; font-size: 28px; font-weight: 500; line-height: 1.6; }}
.rule {{ width: 130px; height: 5px; border-radius: 3px; margin-top: 40px;
  background: linear-gradient(90deg, #FBC02D, rgba(251,192,45,0.1)); }}
.url {{ position: absolute; bottom: 34px; left: 520px; color: #71717A; font-family: 'JetBrains Mono', monospace; font-size: 19px; letter-spacing: 1px; direction: ltr; }}
</style></head>
<body>
  <div class="page">
    <div class="grid"></div>
    <div class="glow"></div>
    <svg class="motif" viewBox="0 0 440 420">{motif}</svg>
    <div class="content">
      <span class="badge"><span class="dot"></span>DOORBINKAR</span>
      <h1>{title}</h1>
      <p class="sub">{sub}</p>
      <div class="rule"></div>
    </div>
    <div class="url">doorbinkar.com/blog</div>
  </div>
</body></html>"""

for slug, motif, title, sub in COVERS:
    html = TEMPLATE.format(fonts=FONT_DIR, motif=MOTIFS[motif], title=title, sub=sub)
    with open(f"{OUT}/{slug}.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("wrote", slug)
