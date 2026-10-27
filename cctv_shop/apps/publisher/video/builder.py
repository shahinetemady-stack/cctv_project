"""
apps/publisher/video/builder.py
────────────────────────────────
رندر ویدیوی ریل/استوری/پست از تصاویر محصول با subprocess فراخوانی ffmpeg
(بدون shell، argv امن).

متن‌های فارسی با Pillow به PNG شفاف رندر می‌شوند (arabic_reshaper + python-bidi
دقیقاً یک بار) و بعد با overlay + fade روی ویدیو می‌نشینند — drawtext به‌خاطر
تفاوت build اف‌اف‌مپگ (fribidi روی سرور باعث دوبار shaping و متن برعکس می‌شد)
استفاده نمی‌شود.

تصاویر محصول contain-fit هستند: نسخهٔ تیر و تارشدهٔ همان تصویر پس‌زمینه را پر
می‌کند و خود محصول تیز و کامل (بدون کراپ لبه‌ها) وسط قاب می‌نشیند؛ زوم Ken Burns
ظریف (حداکثر ~۸٪) است تا محصول از ناحیهٔ امن خارج نشود.
"""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from django.conf import settings

try:
    import arabic_reshaper
    from bidi.algorithm import get_display

    def _shape(text: str) -> str:
        return get_display(arabic_reshaper.reshape(text))
except ImportError:  # کتابخانه‌های shaping نصب نیستند — متن خام پاس داده می‌شود
    def _shape(text: str) -> str:
        return text


FPS = 30
CRF = "23"
PRESET = "medium"

DEFAULT_FONT = Path(settings.BASE_DIR) / "assets" / "fonts" / "Vazirmatn-Bold.ttf"
_FONT_FALLBACKS = [
    "/usr/share/fonts/truetype/vazirmatn/Vazirmatn-Bold.ttf",
    "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Bold.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansArabic-Bold.ttf",
]

CTA_TEXT = "دربین‌کار | doorbinkar.com"

# قالب‌های ویدیو — افزودن قالب جدید فقط داده است، نه کد
TEMPLATES = {
    "reel": {
        "width": 1080, "height": 1920,
        "min_images": 3, "max_images": 6,
        "target_seconds": 20.0,          # با ۳–۶ تصویر در بازهٔ ۱۵–۳۰ ثانیه می‌افتد
        "transition": "fade", "transition_seconds": 0.7,
    },
    "story": {
        "width": 1080, "height": 1920,
        "min_images": 2, "max_images": 4,
        "target_seconds": 12.0,          # حدود ۱۰–۱۵ ثانیه
        "transition": "fade", "transition_seconds": 0.6,
    },
    "post": {
        "width": 1080, "height": 1080,
        "min_images": 3, "max_images": 5,
        "target_seconds": 15.0,
        "transition": "fade", "transition_seconds": 0.6,
    },
    # قالب موشن‌گرافیک ریل — بدون ویدیوی AI: صحنه‌های متن/کارت متحرک
    "reel_motion": {
        "width": 1080, "height": 1920,
        "scenes": (3.0, 6.5, 4.5, 3.5),   # هوک متنی، کارت محصول + چیپ‌ها، نکته، CTA
        "transition_seconds": 0.4,
    },
}

# رنگ برند (طلایی روی تیره) برای پلت‌های موشن‌گرافیک
_GOLD = (212, 175, 55)


class VideoBuildError(Exception):
    """خطای ساخت ویدیو — پیام فارسی و قابل نمایش به کاربر."""


def _resolve_font() -> str:
    if DEFAULT_FONT.exists():
        return str(DEFAULT_FONT)
    for candidate in _FONT_FALLBACKS:
        if os.path.exists(candidate):
            return candidate
    raise VideoBuildError(
        "فونت فارسی برای ساخت ویدیو یافت نشد — فایل Vazirmatn-Bold.ttf را در assets/fonts قرار دهید"
    )


def _gather_images(post) -> tuple[list, object]:
    """مسیر تصاویر محصول را برمی‌گرداند: محصول ایده، وگرنه محصولات مرتبط مقاله،
    وگرنه جدیدترین محصولاتی که تصویر اصلی دارند. خروجی: (لیست مسیرها، محصولِ مبنا یا None)."""
    from apps.catalog.models import Product

    idea = post.idea
    product = idea.product if idea and idea.product_id else None
    if product is not None:
        paths = [img.image.path for img in product.images.all() if img.image]
        return _existing(paths), product

    if idea is not None and idea.article_id:
        for rel in idea.article.related_products.filter(is_active=True)[:3]:
            paths = [img.image.path for img in rel.images.all() if img.image]
            paths = _existing(paths)
            if paths:
                return paths, rel

    products = Product.objects.filter(is_active=True, images__isnull=False).distinct().order_by("-id")
    for candidate in products[:20]:
        paths = [img.image.path for img in candidate.images.all() if img.image]
        paths = _existing(paths)
        if paths:
            return paths, candidate
    return [], None


def resolve_reference_product(post):
    """محصول مبنا برای تصویر مرجع هوک AI — برخلاف _gather_images فقط محصولی
    برمی‌گردد که دست‌کم یک تصویر موجود روی دیسک دارد: محصول ایده → محصولات
    مرتبط مقاله → جدیدترین محصول با تصویر. هیچ‌کدام نبودند → None (text-to-video)."""
    from apps.catalog.models import Product

    def _has_image(product) -> bool:
        return bool(_existing([img.image.path for img in product.images.all() if img.image]))

    idea = post.idea
    if idea is not None and idea.product_id and _has_image(idea.product):
        return idea.product

    if idea is not None and idea.article_id:
        for rel in idea.article.related_products.filter(is_active=True)[:3]:
            if _has_image(rel):
                return rel

    products = Product.objects.filter(is_active=True, images__isnull=False).distinct().order_by("-id")
    for candidate in products[:20]:
        if _has_image(candidate):
            return candidate
    return None


def _existing(paths: list) -> list:
    return [p for p in paths if os.path.exists(p)]


def _render_text_png(text: str, size: int, font_path: str, frame_w: int, out_path: str) -> None:
    """متن فارسی را به PNG شفاف (متن سفید + باکس گرد تیرهٔ نیمه‌شفاف) رندر می‌کند.
    اگر Pillow با libraqm بیلد شده باشد، shaping/bidi را خودش با direction=rtl انجام
    می‌دهد و متن خام منطقی پاس داده می‌شود؛ در غیر این صورت یک بار با
    arabic_reshaper+python-bidi شکل‌دهی می‌کنیم. در هر دو حالت shaping دقیقاً یک بار
    اتفاق می‌افتد و ffmpeg هیچ دخالتی در متن ندارد."""
    from PIL import Image, ImageDraw, ImageFont, features

    use_raqm = features.check("raqm")
    shown = text.strip() if use_raqm else _shape(text.strip())
    text_kw = {"direction": "rtl"} if use_raqm else {}

    max_w = int(frame_w * 0.92)
    while size > 12:
        font = ImageFont.truetype(font_path, size)
        bbox = font.getbbox(shown, **text_kw)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        if tw <= max_w:
            break
        size = int(size * 0.9)
    pad_x, pad_y = int(size * 0.6), int(size * 0.38)
    img = Image.new("RGBA", (tw + 2 * pad_x, th + 2 * pad_y), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle(
        [0, 0, img.width - 1, img.height - 1],
        radius=int(size * 0.4), fill=(0, 0, 0, 90),
    )
    draw.text((pad_x - bbox[0], pad_y - bbox[1]), shown, font=font,
              fill=(255, 255, 255, 255), **text_kw)
    img.save(out_path)


def _render_card_png(image_path: str, max_w: int, max_h: int, out_path: str) -> None:
    """کارت محصول برای چسبیدن روی صحنهٔ هوک AI: تصویر واقعی محصول (contain-fit)
    داخل یک کارت سفید گوشه‌گرد با پدینگ + سایهٔ نرم. پس‌زمینهٔ سفید عکس حذف
    نمی‌شود — خود کارت سفید، ظاهر «کارت محصول» پرمیوم را می‌دهد و خطر هالهٔ
    colorkey را ندارد."""
    from PIL import Image, ImageDraw, ImageFilter

    product_img = Image.open(image_path).convert("RGBA")
    pad = int(max_w * 0.07)
    inner_w, inner_h = max_w - 2 * pad, max_h - 2 * pad
    product_img.thumbnail((inner_w, inner_h), Image.LANCZOS)

    card_w, card_h = product_img.width + 2 * pad, product_img.height + 2 * pad
    radius = int(max_w * 0.06)
    shadow_margin = int(max_w * 0.08)
    canvas = Image.new("RGBA", (card_w + 2 * shadow_margin, card_h + 2 * shadow_margin), (0, 0, 0, 0))

    # سایه: باکس سیاه گرد + بلر، کمی پایین‌تر از کارت
    shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle(
        [shadow_margin, shadow_margin + int(shadow_margin * 0.35),
         shadow_margin + card_w, shadow_margin + int(shadow_margin * 0.35) + card_h],
        radius=radius, fill=(0, 0, 0, 130),
    )
    canvas.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(shadow_margin * 0.45)))

    card = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
    ImageDraw.Draw(card).rounded_rectangle([0, 0, card_w - 1, card_h - 1], radius=radius,
                                           fill=(255, 255, 255, 255))
    card.alpha_composite(product_img, (pad, pad))
    canvas.alpha_composite(card, (shadow_margin, shadow_margin))
    canvas.save(out_path)


# ─── موشن‌گرافیک (reel_motion) ───────────────────────────────

_FA_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def _fa(value) -> str:
    return str(value).translate(_FA_DIGITS)


def _brand_bg(out_path: str, w: int, h: int, glow_xy: tuple) -> None:
    """پلت پس‌زمینهٔ برند: گرادیان تیرهٔ عمودی + هالهٔ طلایی نرم + چند خط مورب نازک."""
    from PIL import Image, ImageDraw, ImageFilter

    top, bottom = (14, 17, 28), (4, 6, 11)
    img = Image.new("RGB", (w, h))
    px = img.load()
    for y in range(h):
        f = y / h
        color = tuple(int(top[c] + (bottom[c] - top[c]) * f) for c in range(3))
        for x in range(0, w, 4):  # هر ۴ پیکسل یک‌بار — بعد با گاussian بلر نرم می‌شود
            for dx in range(4):
                if x + dx < w:
                    px[x + dx, y] = color
    img = img.filter(ImageFilter.GaussianBlur(2))

    glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    gx, gy = glow_xy
    gr = int(w * 0.75)
    ImageDraw.Draw(glow).ellipse([gx - gr, gy - gr, gx + gr, gy + gr],
                                 fill=(_GOLD[0], _GOLD[1], _GOLD[2], 46))
    img = Image.alpha_composite(img.convert("RGBA"),
                                glow.filter(ImageFilter.GaussianBlur(gr // 2)))

    lines = ImageDraw.Draw(img)
    for i, offset in enumerate((-0.25, 0.0, 0.3)):
        x0 = int(w * (0.55 + offset))
        lines.line([(x0, 0), (x0 - int(h * 0.35), h)],
                   fill=(_GOLD[0], _GOLD[1], _GOLD[2], 22), width=3)
    img.convert("RGB").save(out_path)


def _render_chip_png(text: str, font_path: str, out_path: str) -> None:
    """چیپ مشخصات: قرص گرد تیره با حاشیهٔ طلایی و متن سفید کوچک."""
    from PIL import Image, ImageDraw, ImageFont, features

    size = 34
    use_raqm = features.check("raqm")
    shown = text.strip() if use_raqm else _shape(text.strip())
    text_kw = {"direction": "rtl"} if use_raqm else {}
    font = ImageFont.truetype(font_path, size)
    bbox = font.getbbox(shown, **text_kw)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    pad_x, pad_y = 34, 20
    img = Image.new("RGBA", (tw + 2 * pad_x, th + 2 * pad_y), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    r = (img.height - 1) // 2
    draw.rounded_rectangle([0, 0, img.width - 1, img.height - 1], radius=r,
                           fill=(10, 12, 20, 220), outline=_GOLD + (255,), width=2)
    draw.text((pad_x - bbox[0], pad_y - bbox[1]), shown, font=font,
              fill=(255, 255, 255, 255), **text_kw)
    img.save(out_path)


def _render_bar_png(width: int, height: int, out_path: str) -> None:
    """نوار طلایی زیر متن نکته — با crop زمان‌دار رشد می‌کند."""
    from PIL import Image, ImageDraw

    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    ImageDraw.Draw(img).rounded_rectangle([0, 0, width - 1, height - 1],
                                          radius=height // 2, fill=_GOLD + (255,))
    img.save(out_path)


def _spec_chips(product, limit: int = 3) -> list:
    """حداکثر ۳ چیپ کوتاه از مشخصات محصول: رزولوشن، سنسور، برند، بعد dynamic_specs."""
    chips = []
    if product is None:
        return chips
    if product.board_resolution:
        chips.append("رزولوشن: " + _fa(product.board_resolution.replace("MP", " مگاپیکسل")))
    if product.sensor_name:
        chips.append(f"سنسور: {product.sensor_name}")
    if product.brand:
        chips.append(f"برند: {product.brand}")
    for key, value in (product.dynamic_specs or {}).items():
        label = str(key).replace("-", " ")
        chip = label if value is True else f"{label}: {value}"
        chips.append(chip)
    return [c for c in chips if 4 <= len(c) <= 30][:limit]


def _first_sentence(text: str, max_len: int = 60) -> str:
    import re
    parts = re.split(r"[.!؟?\n]", text or "")
    line = next((p.strip() for p in parts if p.strip()), "")
    return line if len(line) <= max_len else line[:max_len].rstrip() + "…"


def build_motion_reel(post, out_path, product, images: list, template: dict) -> None:
    """ریل موشن‌گرافیک (بدون ویدیوی AI): چهار صحنهٔ متحرک روی پلت‌های برند —
    هوک متنی → کارت محصول + چیپ‌های مشخصات → نکته با زیرخط طلایی → CTA.
    همهٔ عناصر PNG ثابت‌اند (Pillow) و انیمیشن با overlay/scale/crop زمان‌دار
    انجام می‌شود — نه پردازش فریم‌به‌فریم Pillow، نه drawtext."""
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise VideoBuildError("ffmpeg روی سرور نصب نیست — ساخت ویدیو ممکن نیست")

    w, h = template["width"], template["height"]
    td = template["transition_seconds"]
    dur_a, dur_b, dur_c, dur_d = template["scenes"]
    font = _resolve_font()

    # تایم‌لاین بعد از xfadeهای پس‌زمینه
    o1 = dur_a - td                 # شروع گذار A→B
    ab = dur_a + dur_b - td         # پایان B
    o2 = ab - td                    # شروع گذار B→C
    abc = ab + dur_c - td           # پایان C
    o3 = abc - td                   # شروع گذار C→D
    total = abc + dur_d - td

    title = (post.title or "").splitlines()[0].strip()
    punch = _first_sentence(post.body)
    chips = _spec_chips(product)

    tmp_dir = tempfile.mkdtemp(prefix="publisher_mg_")
    try:
        bgs = []
        glows = [(int(w * 0.8), int(h * 0.2)), (int(w * 0.2), int(h * 0.75)),
                 (int(w * 0.75), int(h * 0.3)), (int(w * 0.5), int(h * 0.5))]
        for i, glow in enumerate(glows):
            path = os.path.join(tmp_dir, f"bg{i}.png")
            _brand_bg(path, w, h, glow)
            bgs.append(path)

        pngs = []  # ترتیب = ایندکس ورودی بعد از پس‌زمینه‌ها

        def _add_png(name: str) -> int:
            pngs.append(os.path.join(tmp_dir, name))
            return len(bgs) + len(pngs) - 1

        title_idx = card_idx = bar_idx = cta_idx = None
        chip_indices = []

        if title:
            title_idx = _add_png("title.png")
            _render_text_png(title, int(w / 11), font, w, pngs[title_idx - len(bgs)])
        if images:
            card_idx = _add_png("card.png")
            _render_card_png(images[0], int(w * 0.70), int(h * 0.42),
                             pngs[card_idx - len(bgs)])
        for i, chip in enumerate(chips):
            chip_indices.append(_add_png(f"chip{i}.png"))
            _render_chip_png(chip, font, pngs[chip_indices[-1] - len(bgs)])
        if punch:
            bar_idx = _add_png("bar.png")
            _render_bar_png(int(w * 0.42), 8, pngs[bar_idx - len(bgs)])
            punch_idx = _add_png("punch.png")
            _render_text_png(punch, int(w / 16), font, w, pngs[punch_idx - len(bgs)])
        else:
            punch_idx = None
        cta_idx = _add_png("cta.png")
        _render_text_png(CTA_TEXT, int(w / 17), font, w, pngs[cta_idx - len(bgs)])

        parts = []
        for i in range(4):
            parts.append(f"[{i}:v]fps={FPS},setsar=1,format=yuv420p[b{i}]")
        parts.append(f"[b0][b1]xfade=transition=fade:duration={td:.2f}:offset={o1:.2f}[x1]")
        parts.append(f"[x1][b2]xfade=transition=fade:duration={td:.2f}:offset={o2:.2f}[x2]")
        parts.append(f"[x2][b3]xfade=transition=fade:duration={td:.2f}:offset={o3:.2f}[bgv]")

        prev = "bgv"

        def _overlay(idx: int, x: str, y: int, start: float, end: float,
                     pre: str, label: str) -> None:
            nonlocal prev
            parts.append(f"[{idx}:v]{pre}[{label}]")
            out = f"s{label}"
            parts.append(
                f"[{prev}][{label}]overlay={x}:{y}:shortest=1"
                f":enable='between(t\\,{start:.2f}\\,{end:.2f})'[{out}]"
            )
            prev = out

        # صحنهٔ A — هوک متنی: محو-ورود + اسکیل ۹۰٪→۱۰۰٪
        if title_idx is not None:
            _overlay(
                title_idx, "(W-w)/2", int(h * 0.40), 0.2, o1 + td,
                "format=rgba,"
                "scale=w='trunc(iw*(0.9+0.1*min(max((t-0.2)/0.5\\,0)\\,1))/2)*2':h=-2:eval=frame,"
                "fade=t=in:st=0.2:d=0.4:alpha=1,"
                f"fade=t=out:st={o1:.2f}:d={td}:alpha=1",
                "tA",
            )
        # صحنهٔ B — کارت محصول از راست اسلاید می‌شود
        if card_idx is not None:
            card_t0 = o1 + td + 0.1
            _overlay(
                card_idx,
                f"W-(W+w)/2*min(max((t-{card_t0:.2f})/0.5\\,0)\\,1)", int(h * 0.22),
                card_t0, o2 + td + 0.1,
                f"format=rgba,fade=t=in:st={card_t0:.2f}:d=0.3:alpha=1,"
                f"fade=t=out:st={o2 + td - 0.2:.2f}:d=0.3:alpha=1",
                "card",
            )
        # چیپ‌ها با فاصلهٔ پلکانی از راست
        for i, idx in enumerate(chip_indices):
            t0 = o1 + td + 0.9 + i * 0.7
            _overlay(
                idx,
                f"W-(W+w)/2*min(max((t-{t0:.2f})/0.4\\,0)\\,1)", int(h * (0.64 + i * 0.075)),
                t0, o2 + td + 0.1,
                f"format=rgba,fade=t=in:st={t0:.2f}:d=0.3:alpha=1",
                f"chip{i}",
            )
        # صحنهٔ C — نکته + زیرخط طلایی رشدکننده (از مرکز به طرفین)
        if punch_idx is not None:
            t0 = o2 + td + 0.2
            _overlay(
                punch_idx, "(W-w)/2", int(h * 0.42), t0, o3 + td,
                f"format=rgba,fade=t=in:st={t0:.2f}:d=0.4:alpha=1",
                "punch",
            )
            bar_t0 = t0 + 0.3
            _overlay(
                bar_idx, "(W-w)/2", int(h * 0.42) + int(w / 16) + 40, bar_t0, o3 + td,
                "format=rgba,"
                f"scale=w='max(2\\,trunc(iw*min(max((t-{bar_t0:.2f})/0.6\\,0)\\,1)/2)*2)':h=ih:eval=frame",
                "bar",
            )
        # صحنهٔ D — CTA با پالس ظریف
        cta_t0 = o3 + td + 0.1
        _overlay(
            cta_idx, "(W-w)/2", int(h * 0.44), cta_t0, total,
            "format=rgba,"
            "scale=w='trunc(iw*(1+0.03*sin(6.2832*t))/2)*2':h=-2:eval=frame,"
            f"fade=t=in:st={cta_t0:.2f}:d=0.4:alpha=1",
            "cta",
        )

        parts.append(f"[{prev}]copy[vout]")

        from .music import pick_track
        track = pick_track(post)
        music_path = None
        if track is not None and track.file and os.path.exists(track.file.path):
            music_path = track.file.path
        music_index = len(bgs) + len(pngs) if music_path else None
        if music_index is not None:
            parts.append(
                f"[{music_index}:a]atrim=0:{total:.3f},asetpts=PTS-STARTPTS,"
                f"loudnorm=I=-16:TP=-1.5:LRA=11,aresample=44100[aout]"
            )
        silent_index = None if music_index is not None else len(bgs) + len(pngs)

        argv = [ffmpeg, "-y"]
        for i, path in enumerate(bgs):
            argv += ["-loop", "1", "-t", f"{template['scenes'][i]:.3f}", "-i", path]
        for path in pngs:
            argv += ["-loop", "1", "-framerate", str(FPS), "-i", path]
        if music_path:
            argv += ["-stream_loop", "-1", "-i", music_path]
        else:
            argv += ["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100"]
        argv += ["-filter_complex", ";".join(parts), "-map", "[vout]", "-t", f"{total:.3f}"]
        if music_index is not None:
            argv += ["-map", "[aout]", "-c:a", "aac", "-b:a", "128k", "-shortest"]
        else:
            argv += ["-map", f"{silent_index}:a", "-c:a", "aac", "-b:a", "128k", "-shortest"]
        argv += [
            "-c:v", "libx264", "-preset", PRESET, "-crf", CRF,
            "-pix_fmt", "yuv420p", "-r", str(FPS), "-movflags", "+faststart",
            str(out_path),
        ]

        try:
            result = subprocess.run(argv, capture_output=True, timeout=300)
        except subprocess.TimeoutExpired as exc:
            raise VideoBuildError("ساخت ویدیو بیش از حد طول کشید و متوقف شد") from exc
        if result.returncode != 0:
            tail = result.stderr.decode("utf-8", "replace")[-600:].strip()
            raise VideoBuildError(f"ساخت ویدیو ناموفق بود: {tail}")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def _text_layers(template: dict, hook: str, product_name: str, total: float) -> list:
    """(متن، اندازهٔ فونت، y، شروع، پایان) برای سه لایه: قلاب، نام محصول، CTA."""
    w, h = template["width"], template["height"]
    return [
        (hook, int(w / 14), int(h * 0.12), 0.0, min(3.0, total / 3)),
        (product_name, int(w / 16), int(h * 0.50), total * 0.45, total * 0.75),
        (CTA_TEXT, int(w / 18), int(h * 0.85), max(total - 3.0, 0.0), total),
    ]


def _probe_clip(path: str) -> tuple[float, bool]:
    """(طول به ثانیه، داشتن استریم صدا) برای کلیپ هوک — با ffprobe."""
    ffprobe = shutil.which("ffprobe")
    if ffprobe is None:
        raise VideoBuildError("ffprobe روی سرور نصب نیست — ترکیب هوک با ویدیو ممکن نیست")
    dur = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", path],
        capture_output=True, timeout=30,
    )
    try:
        duration = float(dur.stdout.decode().strip())
    except ValueError:
        duration = 0.0
    if dur.returncode != 0 or duration <= 0:
        raise VideoBuildError("کلیپ هوک خراب است — ffprobe آن را نخواند")
    aud = subprocess.run(
        [ffprobe, "-v", "error", "-select_streams", "a:0",
         "-show_entries", "stream=codec_type", "-of", "csv=p=0", path],
        capture_output=True, timeout=30,
    )
    return duration, bool(aud.stdout.decode().strip())


def _slide_total(n: int, template: dict) -> float:
    td = template["transition_seconds"]
    seg = _seg_for_n(n, template)
    return n * seg - (n - 1) * td


def _build_filter(images: list, template: dict, overlays: list,
                  music_index: int | None = None, clip_index: int | None = None,
                  clip_duration: float = 0.0, clip_has_audio: bool = False,
                  card_index: int | None = None,
                  clip_title: tuple | None = None) -> tuple[str, float]:
    """filter_complex کامل را می‌سازد و (رشته فیلتر، طول کل ویدیو) را برمی‌گرداند.
    overlays: لیست (ایندکس ورودی PNG، y، شروع، پایان) — روی اسلایدشو می‌نشینند.
    با clip_index، کلیپ هوک AI ابتدای ویدیو چسبانده می‌شود: صدای خود هوک با ولوم کامل +
    موزیک با ۱۵٪ ولوم زیر هوک (ducking) و بعد از هوک موزیک با سطح عادی."""
    n = len(images)
    w, h = template["width"], template["height"]
    td = template["transition_seconds"]
    slide_total = _slide_total(n, template)
    total = slide_total + (clip_duration if clip_index is not None else 0.0)

    parts = []
    seg_frames = max(int(round(_seg_for_n(n, template) * FPS)), 1)
    for i in range(n):
        # زوم ظریف (~۸٪) — محصول از ناحیهٔ امن خارج نمی‌شود
        if i % 2 == 0:
            zexpr = "min(zoom+0.0004\\,1.08)"
        else:
            zexpr = "if(eq(on\\,0)\\,1.08\\,max(zoom-0.0004\\,1.0))"
        # contain-fit: پس‌زمینه = همان تصویر تار و تیره (cover)، محصول = تیز و کامل وسط قاب.
        # ورودی تصویر تک‌فریم است و zoompan با d=seg_frames همهٔ فریم‌های قطعه را از همان
        # یک فریم می‌سازد — پس scale/blur/overlay فقط یک بار به ازای هر تصویر اجرا می‌شود.
        # بلر روی نسخهٔ ۱/۴ ابعاد انجام و بعد بزرگ‌نمایی می‌شود (خروجی بصری یکسان، بسیار ارزان‌تر).
        # همهٔ ابعاد زوج‌اند تا yuv420p لبه‌ها را خراب نکند.
        bw, bh = w // 4, h // 4
        parts.append(
            f"[{i}:v]split[ibg{i}][ifg{i}];"
            f"[ibg{i}]scale={bw}:{bh}:force_original_aspect_ratio=increase"
            f":force_divisible_by=2,crop={bw}:{bh},gblur=sigma=20,"
            f"scale={w * 2}:{h * 2},eq=brightness=-0.10:saturation=0.85[bgx{i}];"
            f"[ifg{i}]scale={int(w * 2 * 0.92)}:{int(h * 2 * 0.86)}"
            f":force_original_aspect_ratio=decrease:force_divisible_by=2[fgx{i}];"
            f"[bgx{i}][fgx{i}]overlay=(W-w)/2:(H-h)/2,"
            f"zoompan=z='{zexpr}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            f":d={seg_frames}:s={w}x{h}:fps={FPS},setsar=1,format=yuv420p[v{i}]"
        )

    if n == 1:
        parts.append("[v0]copy[vcat]")
    else:
        prev = "v0"
        for i in range(1, n):
            offset = i * (_seg_for_n(n, template) - td)
            out = f"x{i}"
            parts.append(
                f"[{prev}][v{i}]xfade=transition={template['transition']}"
                f":duration={td:.2f}:offset={offset:.2f}[{out}]"
            )
            prev = out

    # متن‌های PNG (خروجی Pillow) با fade آلفا روی اسلایدشو می‌نشینند
    fade = 0.35
    for j, (png_index, y, start, end) in enumerate(overlays):
        parts.append(
            f"[{png_index}:v]format=rgba,"
            f"fade=t=in:st={start:.2f}:d={fade}:alpha=1,"
            f"fade=t=out:st={max(end - fade, start):.2f}:d={fade}:alpha=1[ov{j}]"
        )
        out = f"vo{j}"
        parts.append(
            f"[{prev}][ov{j}]overlay=(W-w)/2:{y}:shortest=1"
            f":enable='between(t\\,{start:.2f}\\,{end:.2f})'[{out}]"
        )
        prev = out

    slide_label = "vslide" if clip_index is not None else "vout"
    parts.append(f"[{prev}]copy[{slide_label}]")

    if clip_index is not None:
        parts.append(
            f"[{clip_index}:v]scale={w}:{h}:force_original_aspect_ratio=increase,"
            f"crop={w}:{h},fps={FPS},setsar=1,format=yuv420p[vclip0]"
        )
        prev_clip = "vclip0"
        if card_index is not None:
            # کارت واقعی محصول روی صحنهٔ AI: محو-ورود ۰.۵ ثانیه بعد از شروع،
            # اسکیل ظریف ۹۵٪→۱۰۰٪ طی ۰.۸ ثانیه، محو-خروج در انتهای هوک
            parts.append(
                f"[{card_index}:v]format=rgba,"
                f"scale=w='trunc(iw*(0.95+0.05*max(0\\,min((t-0.5)/0.8\\,1)))/2)*2':h=-2:eval=frame,"
                f"fade=t=in:st=0.5:d=0.4:alpha=1,"
                f"fade=t=out:st={max(clip_duration - 0.4, 0.9):.2f}:d=0.4:alpha=1[cardv]"
            )
            parts.append(
                f"[{prev_clip}][cardv]overlay=(W-w)/2:(H-h)/2+{int(h * 0.05)}:shortest=1"
                f":enable='between(t\\,0.5\\,{clip_duration:.2f})'[vclip1]"
            )
            prev_clip = "vclip1"
        if clip_title is not None:
            # متن قلاب بالای کارت (z-order بالاتر) — روی تایم‌لاین هوک
            t_idx, t_y, t_start, t_end = clip_title
            parts.append(
                f"[{t_idx}:v]format=rgba,"
                f"fade=t=in:st={t_start:.2f}:d=0.35:alpha=1,"
                f"fade=t=out:st={max(t_end - 0.35, t_start):.2f}:d=0.35:alpha=1[ovt]"
            )
            parts.append(
                f"[{prev_clip}][ovt]overlay=(W-w)/2:{t_y}:shortest=1"
                f":enable='between(t\\,{t_start:.2f}\\,{t_end:.2f})'[vclip2]"
            )
            prev_clip = "vclip2"
        parts.append(f"[{prev_clip}]copy[vclip]")
        parts.append("[vclip][vslide]concat=n=2:v=1:a=0[vout]")

    if clip_index is not None and clip_has_audio and music_index is not None:
        # صدای هوک تمام‌قد + موزیک با ۱۵٪ ولوم در طول هوک و بعد با سطح عادی
        parts.append(
            f"[{clip_index}:a]atrim=0:{clip_duration:.3f},asetpts=PTS-STARTPTS[aclip]"
        )
        parts.append(
            f"[{music_index}:a]atrim=0:{total:.3f},asetpts=PTS-STARTPTS,"
            f"volume=if(lt(t\\,{clip_duration:.3f})\\,0.15\\,1.0):eval=frame[amusic]"
        )
        parts.append(
            "[aclip][amusic]amix=inputs=2:duration=longest:normalize=0,"
            "loudnorm=I=-16:TP=-1.5:LRA=11,aresample=44100[aout]"
        )
    elif clip_index is not None and clip_has_audio:
        # موزیک نیست — صدای هوک + سکوت تا انتهای ویدیو
        parts.append(
            f"[{clip_index}:a]atrim=0:{clip_duration:.3f},asetpts=PTS-STARTPTS,"
            f"apad=whole_dur={total:.3f},atrim=0:{total:.3f},aresample=44100[aout]"
        )
    elif music_index is not None:
        if clip_index is not None:
            # هوک صدا ندارد — فقط موزیک زیر کل ویدیو
            parts.append(
                f"[{music_index}:a]atrim=0:{total:.3f},asetpts=PTS-STARTPTS,"
                f"loudnorm=I=-16:TP=-1.5:LRA=11,aresample=44100[aout]"
            )
        else:
            parts.append(
                f"[{music_index}:a]loudnorm=I=-16:TP=-1.5:LRA=11,aresample=44100[aout]"
            )
    return ";".join(parts), total


def build_video_for_post(post, out_path) -> None:
    """ویدیوی post را بر اساس content_type رندر و در out_path می‌نویسد.
    در خطا VideoBuildError با پیام فارسی پرتاب می‌شود."""
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise VideoBuildError("ffmpeg روی سرور نصب نیست — ساخت ویدیو ممکن نیست")

    style = getattr(post, "video_style", "auto") or "auto"
    template_key = "reel_motion" if (post.content_type == "reel" and style == "motion") else post.content_type
    template = TEMPLATES.get(template_key)
    if template is None:
        raise VideoBuildError(f"نوع محتوای «{post.content_type}» برای ساخت ویدیو پشتیبانی نمی‌شود")

    images, product = _gather_images(post)
    if not images:
        raise VideoBuildError(
            "هیچ تصویری برای ساخت ویدیو یافت نشد — برای محصول مرتبط تصویر ثبت کنید"
        )

    if template_key == "reel_motion":
        if product is None:
            raise VideoBuildError("برای سبک موشن‌گرافیک، پست باید محصول مرتبط با تصویر داشته باشد")
        build_motion_reel(post, out_path, product, images, template)
        return
    # اگر تصویر کمتر از حداقل قالب است، چرخه‌ای تکرار می‌شود تا تایمینگ قالب حفظ شود
    picked = []
    while len(picked) < template["min_images"]:
        picked.extend(images)
    picked.extend(images)
    picked = picked[: template["max_images"]]

    idea = post.idea
    hook = (post.title or (idea.title if idea else "")).splitlines()[0].strip()
    product_name = product.name if product is not None else ""
    font = _resolve_font()

    from .music import pick_track
    track = pick_track(post)
    music_path = None
    if track is not None and track.file:
        candidate = track.file.path
        if os.path.exists(candidate):
            music_path = candidate

    # کلیپ هوک AI — فقط وقتی آماده است و فایلش روی دیسک هست ابتدای ویدیو می‌چسبد
    clip_path = None
    clip_duration = 0.0
    clip_has_audio = False
    if getattr(post, "hook_status", "") == "ready" and post.hook_clip:
        candidate = post.hook_clip.path
        if os.path.exists(candidate):
            clip_path = candidate
            clip_duration, clip_has_audio = _probe_clip(clip_path)

    n = len(picked)

    # متن‌ها با Pillow به PNG رندر می‌شوند (نه drawtext — مستقل از build اف‌اف‌مپگ)
    slide_total = _slide_total(n, template)
    tmp_dir = tempfile.mkdtemp(prefix="publisher_ov_")
    overlays = []  # (path, y, start, end) — روی اسلایدشو
    title_png = None  # با هوک: روی کلیپ هوک می‌نشیند؛ بدون هوک: لایهٔ اول اسلایدشو
    card_path = None
    try:
        layers = _text_layers(template, hook, product_name, slide_total)
        if clip_path and hook:
            # با هوک، متن قلاب روی خود هوک (بالای کارت محصول) می‌نشیند
            _t, size, y, _s, _e = layers[0]
            title_png = os.path.join(tmp_dir, "title.png")
            _render_text_png(hook, size, font, template["width"], title_png)
            layers = layers[1:]
        for text, size, y, start, end in layers:
            if not text:
                continue
            png_path = os.path.join(tmp_dir, f"ov{len(overlays)}.png")
            _render_text_png(text, size, font, template["width"], png_path)
            overlays.append((png_path, y, start, end))

        # کارت واقعی محصول روی صحنهٔ هوک AI (محصول توسط مدل تغییر شکل نمی‌دهد)
        if clip_path and picked:
            card_path = os.path.join(tmp_dir, "card.png")
            _render_card_png(picked[0], int(template["width"] * 0.70),
                             int(template["height"] * 0.55), card_path)

        # ترتیب ورودی‌ها: تصاویر، PNG متن‌های اسلایدشو، کارت، متن قلاب، هوک، موزیک، سکوت
        extra = 0
        card_index = None
        if card_path:
            card_index = n + len(overlays) + extra
            extra += 1
        title_index = None
        if title_png:
            title_index = n + len(overlays) + extra
            extra += 1
        clip_index = (n + len(overlays) + extra) if clip_path else None
        if clip_path:
            extra += 1
        music_index = (n + len(overlays) + extra) if music_path else None
        if music_path:
            extra += 1
        has_audio = music_index is not None or (clip_path is not None and clip_has_audio)
        # بدون موزیک و بدون صدای هوک هم یک تراک سکوت aac می‌گذاریم تا پخش‌کننده‌ها
        # (اینستاگرام/گالری) با ویدیوی بی‌صدا بد رفتار نکنند
        silent_index = None if has_audio else (n + len(overlays) + extra)

        clip_title = None
        if title_png and clip_path:
            clip_title = (title_index, int(template["height"] * 0.12), 0.0,
                          min(3.0, clip_duration / 3))

        overlay_specs = [
            (n + j, y, start, end) for j, (_p, y, start, end) in enumerate(overlays)
        ]
        filter_complex, _total = _build_filter(
            picked, template, overlay_specs,
            music_index=music_index, clip_index=clip_index,
            clip_duration=clip_duration, clip_has_audio=clip_has_audio,
            card_index=card_index, clip_title=clip_title,
        )

        argv = [ffmpeg, "-y"]
        # تصاویر تک‌فریم — طول هر قطعه را zoompan (d=seg_frames) می‌سازد
        for path in picked:
            argv += ["-i", path]
        for png_path, _y, _s, _e in overlays:
            argv += ["-loop", "1", "-framerate", str(FPS), "-i", png_path]
        if card_path:
            argv += ["-loop", "1", "-framerate", str(FPS), "-i", card_path]
        if title_png:
            argv += ["-loop", "1", "-framerate", str(FPS), "-i", title_png]
        if clip_path:
            argv += ["-i", clip_path]
        if music_path:
            argv += ["-stream_loop", "-1", "-i", music_path]
        if silent_index is not None:
            argv += ["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100"]
        argv += ["-filter_complex", filter_complex, "-map", "[vout]"]
        # طول خروجی صریح محدود می‌شود — ورودی‌های بی‌نهایت (PNG لوپ‌شده، anullsrc،
        # موزیک لوپ‌شده) نباید باعث شوند انکود هرگز تمام نشود
        argv += ["-t", f"{_total:.3f}"]
        if has_audio:
            argv += ["-map", "[aout]", "-c:a", "aac", "-b:a", "128k", "-shortest"]
        elif silent_index is not None:
            argv += ["-map", f"{silent_index}:a", "-c:a", "aac", "-b:a", "128k", "-shortest"]
        argv += [
            "-c:v", "libx264", "-preset", PRESET, "-crf", CRF,
            "-pix_fmt", "yuv420p", "-r", str(FPS), "-movflags", "+faststart",
            str(out_path),
        ]

        try:
            result = subprocess.run(argv, capture_output=True, timeout=300)
        except subprocess.TimeoutExpired as exc:
            raise VideoBuildError("ساخت ویدیو بیش از حد طول کشید و متوقف شد") from exc
        if result.returncode != 0:
            tail = result.stderr.decode("utf-8", "replace")[-600:].strip()
            raise VideoBuildError(f"ساخت ویدیو ناموفق بود: {tail}")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def _seg_for_n(n: int, template: dict) -> float:
    td = template["transition_seconds"]
    return (template["target_seconds"] + (n - 1) * td) / n if n > 1 else template["target_seconds"]
