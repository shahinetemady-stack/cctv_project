"""
RAG برداری روی داده‌های فنی فروشگاه — مشخصات، توضیحات و متن دیتاشیت محصولات.

- چانک‌ها: به‌ازای هر محصول فعال یک چانک «مشخصات»، یک چانک «توضیحات» و چند چانک «دیتاشیت»
  (از datasheets.json — خروجی کامند extract_datasheets).
- بردارها: Gemini Embedding (پیش‌فرض text-embedding-004) از مسیر GEMINI_BASE_URL
  (همان رله مینی‌پی‌سی که چت‌بات از آن استفاده می‌کند).
- کش: فایل rag_embeddings.json کنار manage.py؛ بازسازی فقط با کامند build_rag
  (دیپلوی/کران) انجام می‌شود، نه در مسیر درخواست کاربر.
- بازیابی: کوسینوس pure-python روی بردارهای کش‌شده در حافظه (با mtime). اگر فایل
  بردار نبود یا فراخوانی embedding کوئری خطا داد، None برمی‌گردد تا سیستم به
  جستجوی کلیدواژه‌ای قبلی فالبک کند — RAG برداری هرگز نباید چت را بشکند.
"""

import hashlib
import json
import logging
import math
import time

import requests
from django.conf import settings as dj_settings

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIMS = 768    # خروجی پیش‌فرض ۳۰۷۲ است؛ با outputDimensionality جمع‌وجورش می‌کنیم
CACHE_PATH_NAME = "rag_embeddings.json"
_CHUNK_SIZE = 900       # طول هر چانک دیتاشیت
_CHUNK_OVERLAP = 150
_QUERY_TIMEOUT = 15
_BATCH_TIMEOUT = 60
_BUILD_WORKERS = 2      # embedContent تکی است؛ سهمیه رایگان با ترد زیاد 429 می‌دهد
# آستانه شباهت کوسینوس — پایین‌تر از این یعنی نامرتبط (نویز به کانتکست مدل اضافه نمی‌شود)
MIN_SCORE = 0.55

_store = {"mtime": 0, "data": None, "norms": None}


# ─── متن چانک‌ها ──────────────────────────────────────────────

def full_spec_text(p) -> str:
    """متن کامل مشخصات محصول برای چانک «مشخصات» — همه فیلدهای پر + dynamic_specs."""
    from apps.catalog.models import CategorySpecField
    parts = [f"نام: {p.name}"]
    if p.model_number:
        parts.append(f"مدل: {p.model_number}")
    if p.brand:
        parts.append(f"برند: {p.brand}")
    if p.category_id:
        parts.append(f"دسته: {p.category.name}")
    labeled = [
        ("سیستم برد", p.board_system), ("رزولوشن برد", p.board_resolution),
        ("نام سنسور", p.sensor_name), ("اندازه سنسور", p.sensor_size),
        ("پردازنده (ISP)", p.ai_processor), ("ابعاد برد", p.board_dimensions),
        ("نرخ فریم", p.board_fps), ("اطلاعات فنی برد", p.board_tech_notes),
        ("نام لنز", p.lens_name), ("رزولوشن لنز", p.lens_resolution),
        ("فاصله کانونی", p.lens_degree), ("نوع لنز", p.lens_type),
        ("کلاس نوری لنز", p.focal_ratio), ("ضریب دیافراگم", p.lens_aperture),
        ("سایز سنسور سازگار لنز", p.lens_image_size), ("مانت لنز", p.lens_mount),
        ("اقلام همراه", p.lens_kit), ("فاصله پیچ هولدر", p.lens_holder_pitch),
        ("زاویه دید افقی", p.lens_fov),
        ("مدل", p.modem_model), ("نوع", p.modem_type), ("تعداد پین", p.pin_count),
        ("ولتاژ کاری", p.voltage), ("آمپر خروجی", p.ampere_output),
        ("تعداد پورت خروجی", p.output_ports), ("سایز", p.modem_size),
        ("جنس بدنه", p.housing_material), ("سایز دوربین", p.housing_size),
    ]
    for label, val in labeled:
        if val not in (None, ""):
            parts.append(f"{label}: {val}")
    if p.sim_card:
        parts.append("سیم‌کارت‌خور: دارد")
    if p.has_microphone:
        parts.append("میکروفون: دارد")
    # مشخصات داینامیک با برچسب فارسی فیلد (نه کلید انگلیسی) تا برای مدل خوانا باشد
    dyn = p.dynamic_specs or {}
    if dyn:
        # برچسب فارسی فیلدها از دسته محصول و اجدادش (فیلدها روی دسته مادر هم تعریف می‌شوند)
        cats, cat = [], p.category
        while cat is not None:
            cats.append(cat)
            cat = cat.parent
        try:
            labels = dict(CategorySpecField.objects.filter(category__in=cats)
                          .values_list("key", "label"))
        except Exception:
            labels = {}
        for k, v in dyn.items():
            if isinstance(v, str) and v.strip().lower() in ("true", "false"):
                v = v.strip().lower() == "true"
            if v in (None, "", False):
                continue
            parts.append(f"{labels.get(k, k)}: {'دارد' if v is True else v}")
    return "\n".join(parts)


def _description_text(p) -> str:
    import re
    desc = re.sub(r"<[^>]+>", " ", p.description or "")
    desc = re.sub(r"\s+", " ", desc).strip()
    body = f"{p.short_description or ''} {desc}".strip()
    if not body:
        return ""
    return f"توضیحات محصول «{p.name}»:\n{body[:1500]}"


def _datasheet_chunks() -> list:
    """چانک‌های متن دیتاشیت از datasheets.json (همان منبعی که چت‌بات استفاده می‌کند)."""
    path = dj_settings.BASE_DIR / "datasheets.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    chunks = []
    for slug, entry in data.items():
        text = (entry or {}).get("text") or ""
        name = (entry or {}).get("name") or slug
        if not text.strip():
            continue
        step = _CHUNK_SIZE - _CHUNK_OVERLAP
        for i in range(0, len(text), step):
            piece = text[i:i + _CHUNK_SIZE].strip()
            if len(piece) > 120:
                chunks.append({"slug": slug, "kind": "datasheet",
                               "text": f"بخشی از دیتاشیت «{name}»:\n{piece}"})
    return chunks


def build_chunks() -> list:
    """ساخت همه چانک‌ها از دیتابیس + datasheets.json."""
    from apps.catalog.models import Product
    chunks = []
    qs = (Product.objects.filter(is_active=True)
          .select_related("category").prefetch_related("variants"))
    for p in qs:
        chunks.append({"slug": p.slug, "kind": "specs", "text": full_spec_text(p)})
        desc = _description_text(p)
        if desc:
            chunks.append({"slug": p.slug, "kind": "description", "text": desc})
    chunks.extend(_datasheet_chunks())
    return chunks


def chunks_fingerprint(chunks: list) -> str:
    """اثر انگشت محتوای چانک‌ها — برای مقایسه با کش و بازسازی فقط هنگام تغییر."""
    h = hashlib.sha256()
    for c in chunks:
        h.update(c["slug"].encode())
        h.update(c["kind"].encode())
        h.update(hashlib.sha256(c["text"].encode()).digest())
    return h.hexdigest()


# ─── فراخوانی Gemini Embedding (از رله) ───────────────────────

def _gemini_conf():
    from decouple import config as env
    from .models import AssistantSettings
    st = AssistantSettings.get_instance()
    api_key = st.gemini_api_key or env("GEMINI_API_KEY", default="")
    base = env("GEMINI_BASE_URL", default="https://generativelanguage.googleapis.com").rstrip("/")
    relay_token = env("GEMINI_RELAY_TOKEN", default="")
    model = env("EMBEDDING_MODEL", default=EMBEDDING_MODEL)
    return api_key, base, relay_token, model


def _embed_one(text: str, task_type: str) -> list:
    """بردارسازی یک متن با embedContent — مدل‌های gemini-embedding بچ همگام ندارند."""
    api_key, base, relay_token, model = _gemini_conf()
    if not api_key:
        raise RuntimeError("کلید Gemini برای embedding تنظیم نشده")
    headers = {"X-Relay-Token": relay_token} if relay_token else None
    resp = requests.post(
        f"{base}/v1beta/models/{model}:embedContent",
        params={"key": api_key},
        headers=headers,
        json={"model": f"models/{model}", "taskType": task_type,
              "outputDimensionality": EMBEDDING_DIMS,
              "content": {"parts": [{"text": text[:9000]}]}},
        timeout=_BATCH_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()["embedding"]["values"]


def _embed(texts: list, task_type: str, library: dict | None = None) -> list:
    """بردارسازی لیست متن‌ها — تکی برای کوئری، موازیِ محدود برای بازسازی کامل.
    library (هش متن → بردار) کش افزایشی است: متن‌های بدون تغییر دوباره embed نمی‌شوند
    و با ریت‌لیمیت، اجرای بعدی از همان‌جا ادامه می‌یابد."""
    if len(texts) == 1:
        return [_embed_one(texts[0], task_type)]
    from concurrent.futures import ThreadPoolExecutor
    if library is None:
        library = {}

    def key(t):
        return hashlib.sha256(t.encode()).hexdigest()

    def work(t):
        k = key(t)
        if k in library:
            return
        for attempt in (1, 2, 3, 4, 5):
            try:
                library[k] = _embed_one(t, task_type)
                time.sleep(0.15)  # آرامش به ریت‌لیمیت سهمیه رایگان
                return
            except requests.HTTPError as exc:
                if exc.response is not None and exc.response.status_code == 429:
                    time.sleep(15 * attempt)
                    continue
                if attempt == 5:
                    raise
                time.sleep(3 * attempt)
            except Exception:
                if attempt == 5:
                    raise
                time.sleep(3 * attempt)

    pending = [t for t in dict.fromkeys(texts) if key(t) not in library]
    with ThreadPoolExecutor(max_workers=_BUILD_WORKERS) as pool:
        list(pool.map(work, pending))
    return [library[key(t)] for t in texts]


# ─── ساخت و بارگذاری کش ──────────────────────────────────────

def rebuild() -> dict:
    """بازسازی بردارها از داده فعلی — فقط از کامند build_rag صدا زده می‌شود.
    افزایشی است: بردار متن‌های بدون تغییر از library کش قبلی خوانده می‌شود تا
    در برابر ریت‌لیمیت/قطعی، اجرای دوباره از ادامه برود نه از صفر."""
    chunks = build_chunks()
    if not chunks:
        raise RuntimeError("هیچ چانکی ساخته نشد")
    fingerprint = chunks_fingerprint(chunks)
    path = dj_settings.BASE_DIR / CACHE_PATH_NAME
    old = None
    try:
        old = json.loads(path.read_text(encoding="utf-8"))
        if old.get("fingerprint") == fingerprint:
            return {"chunks": len(chunks), "rebuilt": False}
    except (OSError, json.JSONDecodeError):
        pass
    library = (old or {}).get("library", {})
    model = _gemini_conf()[3]
    try:
        vectors = _embed([c["text"] for c in chunks], "RETRIEVAL_DOCUMENT", library)
    except Exception:
        # پیشرفت تا همین‌جا ذخیره شود — اجرای بعدی از ادامه می‌رود
        partial = {"model": model, "fingerprint": None, "chunks": (old or {}).get("chunks", []),
                   "vectors": (old or {}).get("vectors", []), "library": library}
        path.write_text(json.dumps(partial, ensure_ascii=False), encoding="utf-8")
        raise
    payload = {"model": model, "fingerprint": fingerprint,
               "chunks": chunks, "vectors": vectors, "library": library}
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    _store["mtime"] = 0  # کش حافظه بی‌اعتبار شود
    return {"chunks": len(chunks), "rebuilt": True}


def _load():
    """بارگذاری کش بردار در حافظه با چک mtime — روی هر درخواست دیسک خوانده نمی‌شود."""
    path = dj_settings.BASE_DIR / CACHE_PATH_NAME
    try:
        mtime = path.stat().st_mtime
    except OSError:
        _store.update(mtime=0, data=None, norms=None)
        return None
    if mtime == _store["mtime"] and _store["data"] is not None:
        return _store["data"]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning(f"[RAG] خواندن {CACHE_PATH_NAME} ناموفق: {exc}")
        _store.update(mtime=0, data=None, norms=None)
        return None
    if not data.get("fingerprint") or len(data.get("vectors", [])) != len(data.get("chunks", [])):
        # فایل ناقص (ریت‌لیمیت وسط بازسازی) — تا بازسازی کامل فالبک کلیدواژه
        _store.update(mtime=mtime, data=None, norms=None)
        return None
    norms = [math.sqrt(sum(x * x for x in v)) or 1.0 for v in data["vectors"]]
    _store.update(mtime=mtime, data=data, norms=norms)
    return data


def search(query: str, top_k: int = 6) -> list | None:
    """بازیابی برداری — خروجی: لیست [{slug, kind, text, score}] مرتب‌شده، یا None اگر
    بردار در دسترس نبود (فایل کش نیست یا embedding کوئری خطا داد) تا فالبک کلیدواژه شود."""
    data = _load()
    if not data or not data.get("vectors"):
        return None
    try:
        qv = _embed([query[:2000]], "RETRIEVAL_QUERY")[0]
    except Exception as exc:
        logger.warning(f"[RAG] embedding کوئری ناموفق — فالبک به کلیدواژه: {exc}")
        return None
    qnorm = math.sqrt(sum(x * x for x in qv)) or 1.0
    vectors, norms, chunks = data["vectors"], _store["norms"], data["chunks"]
    scored = []
    for i, v in enumerate(vectors):
        dot = sum(a * b for a, b in zip(qv, v))
        score = dot / (qnorm * norms[i])
        if score >= MIN_SCORE:
            scored.append((score, i))
    scored.sort(key=lambda t: -t[0])
    return [{**chunks[i], "score": round(s, 3)} for s, i in scored[:top_k]]
