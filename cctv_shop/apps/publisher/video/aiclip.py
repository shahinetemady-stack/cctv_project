"""
apps/publisher/video/aiclip.py
──────────────────────────────
تولید کلیپ قلاب (hook) سینمایی با Google Veo 3.1 از طریق رله جمینای.

جریان: ساخت پرامپت انگلیسی با LLM (فالبک قالبی) → predictLongRunning →
polling عملیات هر ۱۰ ثانیه تا حدود ۸ دقیقه → دانلود mp4 از طریق رله.

سرور ایران به گوگل دسترسی ندارد؛ همهٔ درخواست‌ها از GEMINI_BASE_URL (رله)
با هدر X-Relay-Token عبور می‌کنند و کلید در پارامتر key فرستاده می‌شود —
همان الگوی apps.assistant.engine._ask_gemini.
"""

import base64
import logging
import mimetypes
import os
import shutil
import subprocess
import time
from urllib.parse import urlparse

import requests
from decouple import config as env

from .builder import VideoBuildError

logger = logging.getLogger(__name__)

VEO_MODEL = "veo-3.1-fast-generate-preview"
HTTP_TIMEOUT = 60          # سقف هر فراخوانی HTTP
POLL_SECONDS = 10          # فاصلهٔ polling عملیات
POLL_TIMEOUT = 480         # حداکثر ~۸ دقیقه انتظار برای عملیات
TOTAL_TIMEOUT = 600        # سقف کلی ~۱۰ دقیقه (شامل دانلود)
MIN_BYTES = 100 * 1024     # فایل خروجی کوچک‌تر از این یعنی دانلود ناقص است

# حال‌وهوای بصری هر دستهٔ محتوا برای پرامپت سینمایی
_CATEGORY_MOOD = {
    "product_showcase": "premium, luxurious product showcase",
    "educational": "clean, precise technical demonstration",
    "offer": "energetic, exciting promotional tone",
    "trend": "dynamic, trendy social media energy",
    "behind_scenes": "authentic workshop behind-the-scenes feel",
}

_PROMPT_SYSTEM = """You write prompts for an AI video generator. Output ONLY the video prompt itself — no quotes, no explanation, no JSON.
The clip is a BACKGROUND PLATE for a product commercial, not a product animation. Rules: English only, at most 100 words, a single paragraph. Style: cinematic atmosphere for a security-technology brand — dark studio environment, warm golden accent lighting, slow subtle camera drift, dust particles or soft light rays, shallow depth of field, medium or wide shot, vertical 9:16. Keep the center of the frame dark and empty (negative space) — a product card will be composited there later. No text, no logos, no watermarks, no people. Never show a specific product in close-up — abstract surfaces, bokeh, smoke and light only, so nothing can deform. If a reference image is provided, use it only for color palette and mood, not as a subject."""


def _relay_config() -> tuple[str, str]:
    """(base_url، توکن رله) — همان الگوی _ask_gemini در موتور دستیار."""
    base = env("GEMINI_BASE_URL", default="https://generativelanguage.googleapis.com").rstrip("/")
    token = env("GEMINI_RELAY_TOKEN", default="")
    return base, token


def _headers(token: str) -> dict | None:
    return {"X-Relay-Token": token} if token else None


def _api_key() -> str:
    """اولویت با کلید Veo تنظیمات publisher است؛ بعد کلید Gemini دستیار و در انتها env."""
    from ..models import PublisherSettings

    key = PublisherSettings.get_instance().veo_api_key.strip()
    if not key:
        from apps.assistant.models import AssistantSettings

        key = AssistantSettings.get_instance().gemini_api_key or os.environ.get("GEMINI_API_KEY", "")
    if not key:
        raise VideoBuildError("کلید API جمینای تنظیم نشده — ساخت هوک AI ممکن نیست")
    return key


def _product_for(post):
    """محصول مبنا برای تصویر مرجع — زنجیرهٔ کامل (ایده ← مقاله ← جدیدترین با تصویر)
    تا هوک هرگز محصول موهومی نسازد؛ هیچ تصویری در هیچ محصولی نبود → None (text-to-video)."""
    from .builder import resolve_reference_product

    return resolve_reference_product(post)


def _fallback_prompt(post, product) -> str:
    """پرامپت قالبی وقتی LLM در دسترس نیست — صحنهٔ اتمسفریک (نه انیمیشن محصول)."""
    hint = ""
    if product is not None and product.brand and product.brand.isascii():
        hint = f" inspired by {product.brand} CCTV technology"
    return (
        f"Cinematic atmosphere plate for a security-technology brand{hint}. "
        "Dark studio environment with warm golden accent lighting, slow subtle camera drift, "
        "floating dust particles and soft light rays, shallow depth of field, abstract dark "
        "surfaces and bokeh, medium-wide shot. The center of the frame stays dark and empty "
        "for a product card overlay. Vertical 9:16. No text, no logos, no people, no product close-up."
    )


def _build_prompt(post) -> str:
    """پرامپت انگلیسی ≤۱۰۰ کلمه با ask_llm؛ در خطا فالبک قالبی."""
    product = _product_for(post)
    if product is not None:
        parts = [product.name]
        if product.brand:
            parts.append(f"brand {product.brand}")
        if product.category_id:
            parts.append(f"category {product.category.name}")
        if product.short_description:
            parts.append(product.short_description[:150])
        product_line = " | ".join(parts)
    else:
        product_line = "a professional CCTV camera part"
    mood = _CATEGORY_MOOD.get(post.idea.category if post.idea else "", _CATEGORY_MOOD["product_showcase"])
    user = (
        f"Product domain: {product_line}\n"
        f"Content idea: {post.title}\n"
        f"Mood: {mood}\n"
        "Write the background-plate prompt now — atmosphere only, no product subject."
    )
    try:
        from apps.assistant.engine import ask_llm

        raw, _engine = ask_llm(
            [{"role": "system", "content": _PROMPT_SYSTEM}, {"role": "user", "content": user}],
            max_tokens=300,
        )
        prompt = " ".join(raw.strip().strip('"`').split())
        if prompt and len(prompt.split()) <= 120:
            return prompt
        logger.warning("[aiclip] خروجی LLM برای پرامپت Veo نامعتبر بود — فالبک قالبی")
    except Exception as exc:
        logger.warning(f"[aiclip] ساخت پرامپت با LLM ناموفق — فالبک قالبی: {exc}")
    return _fallback_prompt(post, product)


def _reference_image(product) -> dict | None:
    """تصویر اصلی محصول به‌صورت bytesBase64Encoded برای image-to-video؛ بدون تصویر → None."""
    if product is None:
        return None
    for img in product.images.all():
        if img.image and os.path.exists(img.image.path):
            path = img.image.path
            mime = mimetypes.guess_type(path)[0] or "image/jpeg"
            with open(path, "rb") as fh:
                return {"bytesBase64Encoded": base64.b64encode(fh.read()).decode("ascii"),
                        "mimeType": mime}
    return None


def _start_operation(base: str, headers, key: str, prompt: str, image: dict | None) -> str:
    """predictLongRunning را صدا می‌زند و نام عملیات را برمی‌گرداند."""
    instance = {"prompt": prompt}
    if image:
        instance["image"] = image
    try:
        resp = requests.post(
            f"{base}/v1beta/models/{VEO_MODEL}:predictLongRunning",
            params={"key": key},
            headers=headers,
            json={"instances": [instance],
                  "parameters": {"aspectRatio": "9:16", "durationSeconds": 8}},
            timeout=HTTP_TIMEOUT,
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise VideoBuildError(f"شروع تولید هوک AI ناموفق بود: {_http_detail(exc)}") from exc
    name = resp.json().get("name", "")
    if not name:
        raise VideoBuildError("پاسخ Veo نام عملیات نداشت — تولید هوک شروع نشد")
    return name


def _poll_operation(base: str, headers, key: str, name: str, deadline: float) -> dict:
    """هر ۱۰ ثانیه وضعیت عملیات را می‌خواند تا done شود؛ دیکشنری پاسخ نهایی را برمی‌گرداند."""
    # نام عملیات گاهی «operations/...» و گاهی «models/.../operations/...» برمی‌گردد
    url = f"{base}/v1beta/{name.lstrip('/')}"
    while time.monotonic() < deadline:
        time.sleep(POLL_SECONDS)
        try:
            resp = requests.get(url, params={"key": key}, headers=headers, timeout=HTTP_TIMEOUT)
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise VideoBuildError(f"خواندن وضعیت تولید هوک ناموفق بود: {_http_detail(exc)}") from exc
        data = resp.json()
        if not data.get("done"):
            continue
        error = data.get("error")
        if error:
            message = error.get("message") if isinstance(error, dict) else str(error)
            raise VideoBuildError(f"تولید هوک AI با خطا متوقف شد: {message}")
        return data.get("response") or {}
    raise VideoBuildError("زمان تولید ویدیو بیش از حد طول کشید")


def _validate_download(out_path) -> None:
    """فایل دانلودشده باید >۱۰۰KB و خوانا برای ffprobe باشد."""
    if not os.path.exists(out_path) or os.path.getsize(out_path) < MIN_BYTES:
        raise VideoBuildError("فایل ویدیوی هوک ناقص دانلود شد")
    ffprobe = shutil.which("ffprobe")
    if ffprobe:
        probe = subprocess.run(
            [ffprobe, "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(out_path)],
            capture_output=True, timeout=30,
        )
        if probe.returncode != 0:
            raise VideoBuildError("فایل ویدیوی هوک خراب است (ffprobe آن را نخواند)")


def _download_video(base: str, headers, key: str, response: dict, out_path, deadline: float) -> None:
    """آدرس ویدیوی تولیدشده را از پاسخ عملیات می‌خواند و از طریق رله دانلود می‌کند."""
    gen = response.get("generateVideoResponse") or {}
    samples = gen.get("generatedSamples") or gen.get("generatedVideos") or []
    uri = (samples[0].get("video") or {}).get("uri", "") if samples else ""
    if not uri:
        raise VideoBuildError("پاسخ Veo ویدیویی برای دانلود نداشت")

    # آدرس روی generativelanguage.googleapis.com است — هاست حذف و مسیر از رله عبور می‌کند
    parsed = urlparse(uri)
    url = f"{base}{parsed.path}"
    if parsed.query:
        url += f"?{parsed.query}"
    url += ("&" if parsed.query else "?") + f"key={key}"

    remaining = max(int(deadline - time.monotonic()), 1)
    try:
        with requests.get(url, headers=headers, timeout=min(HTTP_TIMEOUT, remaining), stream=True) as resp:
            resp.raise_for_status()
            with open(out_path, "wb") as fh:
                for chunk in resp.iter_content(chunk_size=1 << 20):
                    fh.write(chunk)
    except requests.RequestException as exc:
        raise VideoBuildError(f"دانلود ویدیوی هوک ناموفق بود: {_http_detail(exc)}") from exc

    _validate_download(out_path)


def _http_detail(exc: requests.RequestException) -> str:
    """جزئیات پاسخ خطا (کد وضعیت + بخشی از بدنه) برای پیام قابل‌تشخیص."""
    resp = getattr(exc, "response", None)
    if resp is None:
        return str(exc)
    body = (resp.text or "")[:1000].strip()
    return f"HTTP {resp.status_code}: {body}"


def generate_hook_clip(post, out_path) -> None:
    """کلیپ قلاب ۸ ثانیه‌ای 9:16 برای post می‌سازد و در out_path می‌نویسد.
    در خطا VideoBuildError با پیام فارسی پرتاب می‌شود."""
    base, token = _relay_config()
    key = _api_key()
    headers = _headers(token)

    prompt = _build_prompt(post)
    image = _reference_image(_product_for(post))
    logger.info(f"[aiclip] شروع تولید هوک برای پست #{post.pk} — پرامپت: {prompt[:120]}")

    deadline = time.monotonic() + TOTAL_TIMEOUT
    name = _start_operation(base, headers, key, prompt, image)
    response = _poll_operation(base, headers, key, name, min(deadline, time.monotonic() + POLL_TIMEOUT))
    _download_video(base, headers, key, response, out_path, deadline)
    logger.info(f"[aiclip] هوک پست #{post.pk} ساخته شد: {out_path}")
