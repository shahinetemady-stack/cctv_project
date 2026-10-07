"""
apps/publisher/video/builder.py
────────────────────────────────
رندر ویدیوی ریل/استوری/پست از تصاویر محصول با subprocess فراخوانی ffmpeg
(بدون shell، argv امن). متن‌های فارسی قبل از drawtext با arabic-reshaper و
python-bidi شکل‌دهی می‌شوند چون drawtext خودش shaping انجام نمی‌دهد.
"""

import os
import shutil
import subprocess
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
}


class VideoBuildError(Exception):
    """خطای ساخت ویدیو — پیام فارسی و قابل نمایش به کاربر."""


def _escape_drawtext(text: str) -> str:
    """متن را برای قرارگرفتن در مقدار text فیلتر drawtext (داخل کوتیشن تکی) ایمن می‌کند."""
    return (
        text.replace("\\", "\\\\")
        .replace(":", "\\:")
        .replace("'", "\\'")
        .replace("%", "%%")
        .replace(",", "\\,")
        .replace("\n", " ")
    )


def _overlay_text(text: str) -> str:
    return _escape_drawtext(_shape(text.strip()))


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


def _existing(paths: list) -> list:
    return [p for p in paths if os.path.exists(p)]


def _overlay_chain(template: dict, font: str, hook: str, product_name: str, total: float) -> str:
    """سه لایه متن drawtext: قلاب ابتدای ویدیو، نام محصول وسط، CTA در انتها."""
    w, h = template["width"], template["height"]
    filters = []
    layers = [
        (hook, int(w / 14), int(h * 0.12), 0.0, min(3.0, total / 3)),
        (product_name, int(w / 16), int(h * 0.50), total * 0.45, total * 0.75),
        (CTA_TEXT, int(w / 18), int(h * 0.85), max(total - 3.0, 0.0), total),
    ]
    for text, size, y, start, end in layers:
        if not text:
            continue
        # تخمین پهنای متن و کوچک‌کردن فونت تا متن از کادر بیرون نزند
        est_width = len(text) * size * 0.55
        if est_width > w * 0.92:
            size = max(int(size * w * 0.92 / est_width), int(w / 28))
        filters.append(
            f"drawtext=fontfile='{font}':text='{_overlay_text(text)}'"
            f":fontsize={size}:fontcolor=white:borderw=4:bordercolor=black@0.6"
            f":box=1:boxcolor=black@0.35:boxborderw=20"
            f":x=(w-text_w)/2:y={y}:enable='between(t,{start:.2f},{end:.2f})'"
        )
    return ",".join(filters)


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


def _build_filter(images: list, template: dict, hook: str, product_name: str, font: str,
                  music_index: int | None = None, clip_index: int | None = None,
                  clip_duration: float = 0.0, clip_has_audio: bool = False) -> tuple[str, float]:
    """filter_complex کامل را می‌سازد و (رشته فیلتر، طول کل ویدیو) را برمی‌گرداند.
    با clip_index، کلیپ هوک AI ابتدای ویدیو چسبانده می‌شود: صدای خود هوک با ولوم کامل +
    موزیک با ۱۵٪ ولوم زیر هوک (ducking) و بعد از هوک موزیک با سطح عادی."""
    n = len(images)
    w, h = template["width"], template["height"]
    td = template["transition_seconds"]
    target = template["target_seconds"]
    seg = (target + (n - 1) * td) / n if n > 1 else target
    slide_total = n * seg - (n - 1) * td
    total = slide_total + (clip_duration if clip_index is not None else 0.0)

    parts = []
    for i in range(n):
        if i % 2 == 0:
            zexpr = "min(zoom+0.0008\\,1.20)"
        else:
            zexpr = "if(eq(on\\,0)\\,1.20\\,max(zoom-0.0008\\,1.0))"
        parts.append(
            f"[{i}:v]scale={w * 2}:{h * 2}:force_original_aspect_ratio=increase,"
            f"crop={w * 2}:{h * 2},"
            f"zoompan=z='{zexpr}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            f":d=1:s={w}x{h}:fps={FPS},setsar=1,format=yuv420p[v{i}]"
        )

    if n == 1:
        parts.append("[v0]copy[vcat]")
    else:
        prev = "v0"
        for i in range(1, n):
            offset = i * (seg - td)
            out = f"x{i}"
            parts.append(
                f"[{prev}][v{i}]xfade=transition={template['transition']}"
                f":duration={td:.2f}:offset={offset:.2f}[{out}]"
            )
            prev = out

    overlays = _overlay_chain(template, font, hook, product_name, slide_total)
    # متن‌ها روی اسلایدشو می‌نشینند تا تایمینگشان با چسبیدن هوک به‌هم نریزد
    slide_label = "vslide" if clip_index is not None else "vout"
    parts.append(f"[{prev}]{overlays if overlays else 'copy'}[{slide_label}]")

    if clip_index is not None:
        parts.append(
            f"[{clip_index}:v]scale={w}:{h}:force_original_aspect_ratio=increase,"
            f"crop={w}:{h},fps={FPS},setsar=1,format=yuv420p[vclip]"
        )
        parts.append(f"[vclip][vslide]concat=n=2:v=1:a=0[vout]")

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

    template = TEMPLATES.get(post.content_type)
    if template is None:
        raise VideoBuildError(f"نوع محتوای «{post.content_type}» برای ساخت ویدیو پشتیبانی نمی‌شود")

    images, product = _gather_images(post)
    if not images:
        raise VideoBuildError(
            "هیچ تصویری برای ساخت ویدیو یافت نشد — برای محصول مرتبط تصویر ثبت کنید"
        )
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
    clip_index = n if clip_path else None
    music_index = (n + (1 if clip_path else 0)) if music_path else None

    filter_complex, _total = _build_filter(
        picked, template, hook, product_name, font,
        music_index=music_index, clip_index=clip_index,
        clip_duration=clip_duration, clip_has_audio=clip_has_audio,
    )
    has_audio = music_index is not None or (clip_path is not None and clip_has_audio)

    argv = [ffmpeg, "-y"]
    for path in picked:
        argv += ["-framerate", str(FPS), "-loop", "1", "-t", f"{_seg_for(picked, template):.3f}", "-i", path]
    if clip_path:
        argv += ["-i", clip_path]
    if music_path:
        argv += ["-stream_loop", "-1", "-i", music_path]
    argv += ["-filter_complex", filter_complex, "-map", "[vout]"]
    if has_audio:
        argv += ["-map", "[aout]", "-c:a", "aac", "-b:a", "128k", "-shortest"]
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


def _seg_for(images: list, template: dict) -> float:
    n = len(images)
    td = template["transition_seconds"]
    return (template["target_seconds"] + (n - 1) * td) / n if n > 1 else template["target_seconds"]
