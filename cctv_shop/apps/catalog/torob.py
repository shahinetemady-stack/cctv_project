"""
apps/catalog/torob.py
─────────────────────
اتصال به ترب — Torob Product API v3 + Webhook اطلاع‌رسانی تغییرات.

- build_product_payload: ساخت آبجکت محصول مطابق قرارداد API v3 ترب
- verify_torob_token: بررسی JWT (EdDSA/ed25519) هدر X-Torob-Token با کلید عمومی ترب
- mark_product_dirty: ثبت محصول تغییرکرده در کش برای ارسال بعدی وب‌هوک
- send_webhook: ارسال بچ‌های حداکثر ۱۰۰تایی به api.torob.com (حد ۲۰ درخواست در دقیقه)
"""
import logging
import time

import jwt
import requests
from django.conf import settings
from django.core.cache import cache

from .pricing import formula_prices

logger = logging.getLogger(__name__)

SITE_BASE_URL = "https://doorbinkar.com"
WEBHOOK_URL = "https://api.torob.com/update/webhook/v1/"
DIRTY_CACHE_KEY = "torob:dirty"
WEBHOOK_BATCH_SIZE = 100
# حد ترب: ۲۰ درخواست در دقیقه — بین بچ‌ها مکث می‌کنیم
WEBHOOK_BATCH_INTERVAL = 3.1


def product_page_url(product):
    return f"{SITE_BASE_URL}/products/{product.slug}/"


def _sanitize_spec_value(value):
    """ترب فقط String/Integer برای spec می‌پذیرد — بولین‌ها به «دارد» تبدیل و
    False/None حذف می‌شوند؛ لیست‌ها با «، » به هم می‌چسبند."""
    if isinstance(value, bool):
        return "دارد" if value else None
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value) if value.is_integer() else str(value)
    if isinstance(value, str):
        lv = value.strip().lower()
        # بولین رشته‌ای (ذخیره اشتباه قدیمی) → «دارد» یا حذف
        if lv in ("true", "false"):
            return "دارد" if lv == "true" else None
        return value or None
    if isinstance(value, (list, tuple)):
        return "، ".join(str(v) for v in value) or None
    return str(value)


def build_product_payload(product, request):
    """آبجکت محصول مطابق Torob Product API v3 — قیمت ریال، تاریخ ISO8601 با timezone."""
    active_variants = [v for v in product.variants.all() if v.is_active]
    current_price = min((formula_prices(v)["retail"] for v in active_variants), default=0)
    available = product.sellable_stock > 0 and product.effective_availability == "auto"

    spec = {}
    for key, value in dict(product.dynamic_specs or {}).items():
        sv = _sanitize_spec_value(value)
        if sv is not None:
            spec[str(key)] = sv
    if product.brand:
        spec["برند"] = product.brand
    if product.model_number:
        spec["مدل"] = product.model_number

    return {
        "page_unique": str(product.pk),
        "page_url": product_page_url(product),
        "title": product.name,
        "subtitle": None,
        "product_group_id": None,
        "current_price": current_price,
        "old_price": None,
        "availability": available,
        "category_name": str(product.category),
        "image_links": [f"{SITE_BASE_URL}{img.image.url}" for img in product.images.all() if img.image],
        "short_desc": product.short_description or None,
        "spec": spec,
        "guarantee": None,
        "date_added": product.created_at.isoformat(),
        "date_updated": product.updated_at.isoformat(),
    }


def verify_torob_token(request):
    """بررسی امضای JWT ترب → (ok, error_message).
    اگر کلید عمومی تنظیم نشده باشد بررسی رد می‌شود (حالت توسعه).
    در DEBUG بودن هدر اختیاری است، ولی اگر هدر باشد حتماً بررسی می‌شود."""
    public_key = getattr(settings, "TOROB_PUBLIC_KEY", "")
    if not public_key:
        return True, ""
    token = request.headers.get("X-Torob-Token", "")
    if not token:
        if settings.DEBUG:
            return True, ""
        return False, "توکن ترب ارسال نشده است"
    try:
        jwt.decode(token, key=public_key, algorithms=["EdDSA"], audience=request.get_host())
    except jwt.PyJWTError as exc:
        return False, f"توکن ترب نامعتبر است: {exc}"
    return True, ""


def mark_product_dirty(product):
    """افزودن محصول به مجموعه تغییرکرده‌ها (best-effort، بدون قفل — برای کش locmem کافی است)."""
    if product is None or product.pk is None:
        return
    items = cache.get(DIRTY_CACHE_KEY) or []
    items.append({"page_url": product_page_url(product), "page_unique": str(product.pk)})
    cache.set(DIRTY_CACHE_KEY, items, timeout=None)


def send_webhook(items):
    """ارسال تغییرات به وب‌هوک ترب → (sent_count, message). توکن خالی یعنی no-op."""
    token = getattr(settings, "TOROB_WEBHOOK_TOKEN", "")
    if not token:
        logger.info("TOROB_WEBHOOK_TOKEN تنظیم نشده — ارسال وب‌هوک ترب رد شد")
        return 0, "توکن وب‌هوک ترب تنظیم نشده است"
    seen = set()
    unique_items = []
    for item in items:
        key = item["page_unique"]
        if key not in seen:
            seen.add(key)
            unique_items.append(item)
    sent = 0
    for i in range(0, len(unique_items), WEBHOOK_BATCH_SIZE):
        batch = unique_items[i:i + WEBHOOK_BATCH_SIZE]
        try:
            resp = requests.post(
                WEBHOOK_URL,
                json={"items": batch},
                headers={"Authorization": f"Bearer {token}"},
                timeout=10,
            )
            if resp.status_code >= 400:
                logger.warning("وب‌هوک ترب خطا داد: %s %s", resp.status_code, resp.text[:300])
                return sent, f"خطای ترب: HTTP {resp.status_code}"
            sent += len(batch)
        except requests.RequestException as exc:
            logger.warning("خطا در ارتباط با وب‌هوک ترب: %s", exc)
            return sent, f"خطای شبکه: {exc}"
        if i + WEBHOOK_BATCH_SIZE < len(unique_items):
            time.sleep(WEBHOOK_BATCH_INTERVAL)
    return sent, f"{sent} محصول به ترب اطلاع‌رسانی شد"
