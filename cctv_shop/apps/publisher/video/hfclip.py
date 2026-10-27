"""
apps/publisher/video/hfclip.py
──────────────────────────────
تولید کلیپ قلاب با اسپیس رایگان Hugging Face (Gradio/ZeroGPU) از طریق رلهٔ
Node روی مینی‌پی‌سی (tg-bot/hf-video-relay.js — پورت 3296). huggingface.co از
سرور ایران در دسترس نیست، پس خود تولید روی مینی‌پی‌سی انجام می‌شود و این ماژول
فقط با رله حرف می‌زند: POST /generate → polling /jobs/<id> → دانلود /jobs/<id>/file.

پرامپت و تصویر مرجع دقیقاً همان‌های aiclip هستند (همان _build_prompt).
"""

import logging
import time

import requests
from decouple import config as env

from .aiclip import _build_prompt, _http_detail, _product_for, _reference_image, _validate_download
from .builder import VideoBuildError

logger = logging.getLogger(__name__)

HTTP_TIMEOUT = 60
POLL_SECONDS = 10
POLL_TIMEOUT = 480         # صف + تولید روی ZeroGPU گاهی چند دقیقه طول می‌کشد
TOTAL_TIMEOUT = 600


class QuotaExceeded(VideoBuildError):
    """سهمیهٔ ZeroGPU تمام شده — زنجیرهٔ موتورها سراغ موتور بعدی می‌رود."""


def _is_quota(message: str) -> bool:
    m = message.lower()
    return "quota" in m or "zerogpu" in m or "429" in m or "rate limit" in m


def _relay_config() -> tuple[str, dict | None]:
    base = env("HF_VIDEO_RELAY_URL", default="http://127.0.0.1:3296").rstrip("/")
    token = env("HF_VIDEO_RELAY_TOKEN", default="")
    return base, ({"X-Relay-Token": token} if token else None)


def generate_hook_clip_hf(post, out_path) -> None:
    """هوک را با اسپیس HF می‌سازد و در out_path می‌نویسد؛ در خطا VideoBuildError
    (خطاهای سهمیه QuotaExceeded)."""
    from ..models import PublisherSettings

    st = PublisherSettings.get_instance()
    hf_token = st.hf_token.strip()
    if not hf_token:
        raise VideoBuildError("توکن Hugging Face در تنظیمات استودیو وارد نشده")
    base, headers = _relay_config()

    prompt = _build_prompt(post)
    body = {"prompt": prompt, "hf_token": hf_token}
    image = _reference_image(_product_for(post))
    if image:
        body["image_b64"] = image["bytesBase64Encoded"]
        body["image_mime"] = image["mimeType"]
    if st.hf_space.strip():
        body["space"] = st.hf_space.strip()

    try:
        resp = requests.post(f"{base}/generate", json=body, headers=headers, timeout=HTTP_TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise VideoBuildError(f"شروع تولید هوک با HF ناموفق بود: {_http_detail(exc)}") from exc
    job_id = resp.json().get("job_id")
    if not job_id:
        raise VideoBuildError("رله HF شناسهٔ جاب برنگرداند")
    logger.info(f"[hfclip] جاب {job_id} برای پست #{post.pk} در رله HF ثبت شد")

    total_deadline = time.monotonic() + TOTAL_TIMEOUT
    deadline = min(total_deadline, time.monotonic() + POLL_TIMEOUT)
    while time.monotonic() < deadline:
        time.sleep(POLL_SECONDS)
        try:
            resp = requests.get(f"{base}/jobs/{job_id}", headers=headers, timeout=HTTP_TIMEOUT)
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise VideoBuildError(f"خواندن وضعیت جاب HF ناموفق بود: {_http_detail(exc)}") from exc
        data = resp.json()
        status = data.get("status")
        if status in ("queued", "building"):
            continue
        if status == "failed":
            message = data.get("error") or "خطای نامشخص اسپیس"
            if _is_quota(message):
                raise QuotaExceeded(message)
            raise VideoBuildError(f"تولید هوک با HF ناموفق بود: {message}")
        if status == "ready":
            break
        raise VideoBuildError(f"وضعیت ناشناختهٔ جاب HF: {status}")
    else:
        raise VideoBuildError("زمان تولید ویدیو بیش از حد طول کشید")

    remaining = max(int(total_deadline - time.monotonic()), 10)
    try:
        with requests.get(f"{base}/jobs/{job_id}/file", headers=headers,
                          timeout=min(HTTP_TIMEOUT, remaining), stream=True) as resp:
            resp.raise_for_status()
            with open(out_path, "wb") as fh:
                for chunk in resp.iter_content(chunk_size=1 << 20):
                    fh.write(chunk)
    except requests.RequestException as exc:
        raise VideoBuildError(f"دانلود ویدیوی هوک از رله HF ناموفق بود: {_http_detail(exc)}") from exc

    _validate_download(out_path)
    logger.info(f"[hfclip] هوک پست #{post.pk} با HF ساخته شد: {out_path}")
