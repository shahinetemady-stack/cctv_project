"""
apps/publisher/trendsources.py
──────────────────────────────
سیگنال‌های دنیای واقعی برای تولید ایدهٔ محتوا — به‌جای ایده‌های خشک محصول‌محور:

- google_trends_signals: کوئری‌های رو به رشد/برتر گوگل ترندز ایران از SerpAPI
  (engine=google_trends، همان کلید LeadSettings.serpapi_key لیدها). نتیجه ۲۴
  ساعت در یک فایل JSON زیر MEDIA_ROOT کش می‌شود تا سهمیهٔ محدود SerpAPI
  (۱۰۰ جستجو در ماه) هدر نرود. در هر خطایی بی‌صدا [] برمی‌گردد.
- customer_question_signals: سؤالات واقعی مشتریان — LearnedQA دستیار (سؤال‌هایی
  که مشتری از ربات پرسیده) + پیام‌های مشتری در چت پشتیبانی. بدون داده → [].
- rejected_signals: عنوان ایده‌ها/پست‌های ردشده به‌عنوان الگوی منفی.
"""

import json
import logging
import os
import time

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

SERP_URL = "https://serpapi.com/search.json"
SEED_QUERIES = ["دوربین مداربسته", "قیمت دوربین مداربسته", "نصب دوربین"]
CACHE_TTL_SECONDS = 24 * 3600


def _cache_path() -> str:
    path = os.path.join(settings.MEDIA_ROOT, "publisher")
    os.makedirs(path, exist_ok=True)
    return os.path.join(path, "trends_cache.json")


def _read_cache() -> tuple[list, float]:
    """(لیست کوئری‌ها، زمان کش) — بدون فایل یا JSON خراب → ([], 0)."""
    try:
        with open(_cache_path(), encoding="utf-8") as fh:
            data = json.load(fh)
        return list(data.get("queries") or []), float(data.get("ts") or 0)
    except (OSError, ValueError, TypeError):
        return [], 0.0


def _write_cache(queries: list) -> None:
    try:
        with open(_cache_path(), "w", encoding="utf-8") as fh:
            json.dump({"ts": time.time(), "queries": queries}, fh, ensure_ascii=False)
    except OSError as exc:
        logger.warning(f"[trendsources] نوشتن کش ترندها ناموفق: {exc}")


def google_trends_signals(limit: int = 8) -> list:
    """کوئری‌های rising+top گوگل ترندز (geo=IR) برای چند عبارت بذری.
    کش ۲۴ ساعته؛ در هر خطایی کش کهنه و در نبود آن [] برمی‌گردد."""
    cached, ts = _read_cache()
    if cached and time.time() - ts < CACHE_TTL_SECONDS:
        return cached[:limit]

    from apps.leads.models import LeadSettings

    api_key = LeadSettings.get_instance().serpapi_key.strip()
    if not api_key:
        return cached[:limit]

    queries = []
    try:
        for seed in SEED_QUERIES:
            resp = requests.get(SERP_URL, params={
                "engine": "google_trends",
                "q": seed,
                "geo": "IR",
                "hl": "fa",
                "data_type": "RELATED_QUERIES",
                "api_key": api_key,
            }, timeout=30)
            resp.raise_for_status()
            related = resp.json().get("related_queries") or {}
            for bucket in ("rising", "top"):
                for item in related.get(bucket) or []:
                    q = str(item.get("query") or "").strip()
                    if q and q not in queries:
                        queries.append(q)
    except Exception as exc:
        logger.warning(f"[trendsources] خواندن گوگل ترندز ناموفق: {exc}")
        return cached[:limit]

    if queries:
        _write_cache(queries)
    return queries[:limit]


def customer_question_signals(limit: int = 10) -> list:
    """سؤالات واقعی مشتریان از LearnedQA دستیار + پیام‌های مشتری در چت پشتیبانی."""
    from apps.assistant.models import LearnedQA
    from apps.chat.models import ChatMessage

    candidates = []
    try:
        candidates += list(
            LearnedQA.objects.order_by("-id").values_list("question", flat=True)[:30]
        )
    except Exception as exc:
        logger.warning(f"[trendsources] خواندن LearnedQA ناموفق: {exc}")
    try:
        candidates += list(
            ChatMessage.objects.filter(from_staff=False)
            .exclude(text="")
            .order_by("-id")
            .values_list("text", flat=True)[:30]
        )
    except Exception as exc:
        logger.warning(f"[trendsources] خواندن پیام‌های چت ناموفق: {exc}")

    seen = []
    for raw in candidates:
        text = " ".join(str(raw).split())
        if len(text) < 8 or text in seen:
            continue
        seen.append(text)
    return seen[:limit]


def rejected_signals(limit: int = 5) -> list:
    """عنوان ایده‌ها و پست‌های ردشده — الگوی منفی برای پرامپت."""
    from .models import ChannelPost, ContentIdea

    titles = []
    try:
        titles += list(
            ContentIdea.objects.filter(status=ContentIdea.Status.REJECTED)
            .order_by("-id").values_list("title", flat=True)[:limit]
        )
        titles += list(
            ChannelPost.objects.filter(approval_status=ChannelPost.ApprovalStatus.REJECTED)
            .order_by("-id").values_list("title", flat=True)[:limit]
        )
    except Exception as exc:
        logger.warning(f"[trendsources] خواندن موارد ردشده ناموفق: {exc}")

    seen = []
    for t in titles:
        t = " ".join(str(t).split())
        if t and t not in seen:
            seen.append(t)
    return seen[:limit]
