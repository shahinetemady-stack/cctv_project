"""
apps/core/indexnow.py
─────────────────────
اطلاع‌رسانی خودکار ایندکس به موتورهای جستجو با پروتکل IndexNow
(Bing, Yandex, Naver و… — گوگل این پروتکل را ندارد و با سایت‌مپ کار می‌کند).

هر ذخیره/انتشار محصول یا مقاله، URL آن را در یک ترد پس‌زمینه به
api.indexnow.org می‌فرستد تا خزنده‌ها سریع‌تر سراغ صفحه بیایند.
خطاها فقط لاگ می‌شوند و ذخیره اصلی را مختل نمی‌کنند.

کلید: settings.INDEXNOW_KEY — فایل عمومی <KEY>.txt باید روی ریشه دامنه
سرو شود (در فرانت‌اند public/ گذاشته شده و با بیلد منتشر می‌شود).
"""

import json
import logging
import threading
import urllib.request

from django.conf import settings

logger = logging.getLogger(__name__)

_ENDPOINT = "https://api.indexnow.org/indexnow"


def _post_payload(payload: dict) -> None:
    try:
        req = urllib.request.Request(
            _ENDPOINT,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json; charset=utf-8"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            logger.info("IndexNow %s → %s", payload.get("urlList"), resp.status)
    except Exception:
        logger.exception("IndexNow submission failed: %s", payload.get("urlList"))


def submit_urls(urls) -> None:
    """ارسال آسنکرون لیست URLها به IndexNow — بلاک‌کننده نیست."""
    key = getattr(settings, "INDEXNOW_KEY", "")
    base = getattr(settings, "SITE_URL", "").rstrip("/")
    urls = [u for u in urls if u]
    if not key or not base or not urls:
        return
    host = base.split("://", 1)[-1]
    payload = {
        "host": host,
        "key": key,
        "keyLocation": f"{base}/{key}.txt",
        "urlList": urls,
    }
    threading.Thread(target=_post_payload, args=(payload,), daemon=True).start()
