"""
دستیار هوشمند فروشگاه — چت‌بات + سرچ هوشمند با LLM لوکال (Ollama).

نکتهٔ مهم معماری: مدل هرگز از خودش قیمت/موجودی نمی‌گوید؛
محصولات مرتبط از دیتابیس پیدا و به‌عنوان context به مدل داده می‌شود (RAG ساده).
"""

import json
import logging
import re

import requests
from django.db.models import Q
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.models import Product

from .models import FAQ

logger = logging.getLogger(__name__)

OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
MODEL = "qwen2.5:3b"
TIMEOUT = 140  # روی CPU نسل پاسخ کند است — باید زیر nginx/gunicorn (150s) بماند

# اعداد فارسی/عربی → لاتین (کاربر «۲ مگاپیکسل» می‌نویسد)
FA_TO_EN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
# معادل حروفی اعداد رایج مگاپیکسل — در نام محصولات به حروف نوشته شده («پنج مگاپیکسل»)
MP_WORDS = {"1": "یک", "2": "دو", "3": "سه", "4": "چهار", "5": "پنج", "6": "شش", "8": "هشت", "12": "دوازده"}
# املای فارسی اصطلاحات → شکلی که در نام/مشخصات محصولات آمده
ALIASES = {"ای اچ دی": "AHD", "ای‌اچ‌دی": "AHD", "آی پی": "IP", "ای پی": "IP", "پی او ای": "POE"}

SYSTEM_PROMPT = """تو دستیار فروشگاه اینترنتی «دوربینکار» هستی (فروش تجهیزات دوربین مداربسته: دوربین، DVR، NVR، هارد، کابل و…).
قوانین سخت‌گیرانه:
- فقط فارسی جواب بده؛ کوتاه و مفید (حداکثر ۵ جمله) و محترمانه.
- درباره قیمت و موجودی «فقط» بر اساس لیست «اطلاعات محصولات» جواب بده. اگر محصول موردنظر در لیست نبود، صادقانه بگو در فروشگاه پیدا نکردی و پیشنهاد بده با فروش تماس بگیرند یا عبارت دیگری جستجو کنند.
- فقط محصولاتی را پیشنهاد بده که در لیست هستند؛ وضعیت موجودی را دقیقاً همان‌طور که در لیست آمده بگو و اگر ناموجود است، صادقانه اعلام کن.
- اگر مشتری مشخصات دقیق خواست (مثلاً مگاپیکسل یا مدل خاص)، فقط همان را پیشنهاد بده؛ اگر دقیقاً همان در لیست نبود، صادقانه بگو و نزدیک‌ترین گزینه موجود را معرفی کن.
- هرگز قیمت، موجودی یا مشخصات از خودت نساز.
- در انتخاب محصول راهنمایی کن (مثلاً تفاوت داهوا و هایک‌ویژن، DVR با NVR، دوربین داخلی با بیرونی).
- اگر سؤال مشاوره‌ای بود (مثلاً «برای پارکینگ» یا «برای مغازه»)، از روی «مشخصات» محصولات لیست راهنمایی کن؛ مثلاً فاصله کانونی کوچک‌تر (2.8mm) زاویه دید بازتر برای فاصله نزدیک است و بزرگ‌تر (8mm به بالا) برای فاصله دور، و سنسور استارلایت برای تاریکی بهتر است.
- اگر سؤال ربطی به فروشگاه نداشت، مؤدبانه بگو فقط درباره محصولات و خرید می‌توانی کمک کنی."""


def _product_dict(p: Product, user=None) -> dict:
    """خلاصهٔ محصول برای context مدل و پاسخ API.
    قیمت بر اساس سطح همکاری کاربر است (همان کلید min_price لیست محصولات) تا
    قیمت چت‌بات با بقیه بخش‌های سایت یکی باشد."""
    from apps.catalog.pricing import formula_prices, user_price_key
    variant = p.variants.filter(is_active=True).first()
    if variant:
        key, _ = user_price_key(user)
        price = formula_prices(variant)[key]
    else:
        price = None
    stock = p.available_stock
    return {
        "name": p.name,
        "brand": p.brand,
        "category": p.category.name if p.category else "",
        "price_irt": price,
        "in_stock": stock > 0,
        "url": f"/products/{p.slug}",
    }


def _spec_summary(p: Product) -> str:
    """خلاصهٔ مشخصات فنی محصول برای کانتکست مدل — فقط فیلدهای پر."""
    parts = []
    if p.board_system:
        parts.append(f"سیستم {p.board_system}")
    if p.board_resolution:
        parts.append(f"رزولوشن {p.board_resolution}")
    if p.sensor_name:
        parts.append(f"سنسور {p.sensor_name}" + (f" ({p.sensor_size})" if p.sensor_size else ""))
    if p.ai_processor:
        parts.append(f"پردازنده {p.ai_processor}")
    if p.board_dimensions:
        parts.append(f"ابعاد {p.board_dimensions}")
    if p.lens_resolution:
        parts.append(f"لنز {p.lens_resolution}")
    if p.lens_degree:
        parts.append(f"فاصله کانونی {p.lens_degree}")
    if p.lens_type:
        parts.append(f"لنز {p.lens_type}")
    if p.focal_ratio and p.focal_ratio != "معمولی":
        parts.append(p.focal_ratio)
    if p.housing_type:
        parts.append(f"بدنه {p.housing_type}")
    if p.housing_material:
        parts.append(p.housing_material)
    if p.has_microphone:
        parts.append("میکروفون دارد")
    if p.modem_type:
        parts.append(p.modem_type)
    if p.sim_card:
        parts.append("سیم‌کارت‌خور")
    if p.short_description:
        parts.append(p.short_description[:100])
    return "، ".join(parts)


def _find_products(query: str, limit: int = 4):  # limit کم = پرامپت کوتاه‌تر = پاسخ سریع‌تر روی CPU
    """جستجوی کلمات مهم عبارت در نام/برند/دسته/مدل محصولات فعال.

    خروجی: (لیست محصولات, is_fallback) — is_fallback یعنی هیچ تطابقی نبود و این‌ها فقط پیشنهاد کلی‌اند.
    رتبه‌بندی بر اساس امتیاز: تعداد کلمات تطابق‌یافته + تطابق دقیق مگاپیکسل + موجودی.
    (ناموجودها حذف نمی‌شوند — فعلاً انبار فروشگاه خالی است وگرنه هیچ جوابی نمی‌دهیم.)
    """
    query = query.translate(FA_TO_EN_DIGITS)
    for fa, en in ALIASES.items():
        query = query.replace(fa, en)
    # اعداد حروفی قبل از «مگاپیکسل» → رقم تا منطق تطابق رزولوشن فعال شود («دو مگاپیکسل» → «2 مگاپیکسل»)
    for d, w in MP_WORDS.items():
        query = query.replace(f"{w} مگاپیکسل", f"{d} مگاپیکسل").replace(f"{w}مگاپیکسل", f"{d} مگاپیکسل")
    # علائم نگارشی به فاصله — وگرنه به کلمه می‌چسبند («داری؟» ≠ «داری»)
    query = re.sub(r"[؟?!.,،؛:]", " ", query)
    stopwords = {"چی", "چه", "پیشنهاد", "پشنهاد", "میدی", "میده", "میخوام", "میخواهم", "دارید", "داری",
                 "قیمت", "قیمتش", "چقدر", "چقدره", "برای", "لطفا", "لطفاً", "خرید", "بفرمایید"}
    words = [w for w in re.split(r"\s+", query.strip()) if len(w) > 1 and w not in stopwords][:8]
    qs = Product.objects.filter(is_active=True).select_related("category").prefetch_related("variants")
    if not words:
        return [], False
    q = Q()
    for w in words:
        q |= Q(name__icontains=w) | Q(brand__icontains=w) | \
             Q(category__name__icontains=w) | Q(model_number__icontains=w) | \
             Q(short_description__icontains=w) | Q(keywords__icontains=w)
    # عبارت «N مگاپیکسل» در نام محصولات به این شکل‌ها آمده: «پنج مگاپیکسل»، «5 مگاپیکسل»، «5مگاپیکسل»، «دومگاپیکسل»
    mp_variants = []
    m = re.search(r"(\d+)\s*مگاپیکسل", query)
    if m:
        d = m.group(1)
        mp_variants = [f"{d} مگاپیکسل", f"{d}مگاپیکسل"]
        if d in MP_WORDS:
            mp_variants += [f"{MP_WORDS[d]} مگاپیکسل", f"{MP_WORDS[d]}مگاپیکسل"]
        for v in mp_variants:
            q |= Q(name__icontains=v)

    def score(p: Product) -> float:
        hay = f"{p.name} {p.brand or ''} {p.category.name if p.category else ''} " \
              f"{p.model_number or ''} {p.short_description or ''} {p.keywords or ''}"
        s = sum(1 for w in words if w in hay)
        if any(v in p.name for v in mp_variants):
            s += 3
        if p.available_stock > 0:
            s += 0.5
        return s

    pool = []
    if mp_variants:  # تطابق دقیق مگاپیکسل حتماً وارد pool شود — وگرنه ممکن است قبل از اسکورینگ حذف شود
        mp_q = Q()
        for v in mp_variants:
            mp_q |= Q(name__icontains=v)
        pool = list(qs.filter(mp_q)[:limit])
    pool += [p for p in qs.filter(q).distinct()[: limit * 6] if p not in pool]
    scored = sorted(((score(p), p) for p in pool), key=lambda t: -t[0])
    products = [p for s, p in scored if s > 0][:limit]
    if not products:  # هیچ تطابقی نبود — چند محصول جدید به‌عنوان پیشنهاد کلی
        return list(qs.order_by("-created_at")[:3]), True
    return products, False


def _find_faqs(message: str, limit: int = 2):
    """تطبیق سؤال مشتری با پرسش‌های متداول ثبت‌شده در پنل (question + keywords)."""
    query = message.translate(FA_TO_EN_DIGITS)
    query = re.sub(r"[؟?!.,،؛:]", " ", query)
    words = [w for w in re.split(r"\s+", query.strip()) if len(w) > 1][:8]
    if not words:
        return []
    scored = []
    for f in FAQ.objects.filter(is_active=True):
        hay = f"{f.question} {f.keywords}"
        s = sum(1 for w in words if w in hay)
        if s:
            scored.append((s, f))
    scored.sort(key=lambda t: (-t[0], t[1].order))
    return [f for _, f in scored[:limit]]


def _faq_context(faqs) -> str:
    """بلوک کانتکست پرسش‌های متداول برای تزریق به پرامپت مدل."""
    if not faqs:
        return ""
    body = "\n".join(f"س: {f.question}\nج: {f.answer[:300]}" for f in faqs)
    return "\n\nپاسخ‌های آماده فروشگاه (اگر سؤال مشتری به این‌ها مربوط است، «همین» را جواب بده وگرنه نادیده بگیر):\n" + body


def _ask_ollama(messages: list) -> str:
    resp = requests.post(
        OLLAMA_URL,
        json={"model": MODEL, "messages": messages, "stream": False,
              "keep_alive": "30m",  # مدل در حافظه بماند — درخواست‌های بعدی سریع‌تر
              "options": {"num_predict": 170, "temperature": 0.3}},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()["message"]["content"].strip()


class AssistantChatView(APIView):
    """POST /api/assistant/chat/  —  {message, history?} → پاسخ چت‌بات + محصولات مرتبط"""
    permission_classes = [AllowAny]

    def post(self, request):
        message = (request.data.get("message") or "").strip()
        if not message:
            return Response({"error": "پیام خالی است"}, status=400)
        history = request.data.get("history") or []
        if not isinstance(history, list):
            history = []

        products, is_fallback = _find_products(message)
        dicts = []
        for p in products:
            d = _product_dict(p, request.user)
            d["specs"] = _spec_summary(p)
            dicts.append(d)
        if dicts:
            lines = "\n".join(
                f"- {d['name']} | برند: {d['brand'] or '-'} | دسته: {d['category']} | "
                + (f"قیمت: {d['price_irt']:,} ریال" if d["price_irt"] else "قیمت: نامشخص")
                + f" | موجودی: {'دارد' if d['in_stock'] else 'ندارد'}"
                + (f" | مشخصات: {d['specs']}" if d["specs"] else "")
                for d in dicts
            )
            if is_fallback:
                lines = "(هیچ محصول مرتبطی با درخواست مشتری پیدا نشد؛ صادقانه بگو پیدا نکردی. " \
                        "این‌ها فقط چند محصول کلی فروشگاه‌اند، نه جواب درخواست مشتری:)\n" + lines
        else:
            lines = "(محصولی یافت نشد)"

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for h in history[-6:]:
            if isinstance(h, dict) and h.get("role") in ("user", "assistant") and h.get("content"):
                messages.append({"role": h["role"], "content": str(h["content"])[:500]})
        messages.append({
            "role": "user",
            "content": f"اطلاعات محصولات فروشگاه:\n{lines}{_faq_context(_find_faqs(message))}\n\nپیام مشتری: {message}",
        })

        try:
            reply = _ask_ollama(messages)
        except Exception as exc:
            logger.warning(f"[ASSISTANT] خطای Ollama: {exc}")
            return Response(
                {"error": "دستیار هوشمند موقتاً در دسترس نیست؛ کمی بعد دوباره تلاش کنید."},
                status=503,
            )
        return Response({
            "reply": reply,
            "products": dicts,
        })


class SmartSearchView(APIView):
    """POST /api/assistant/smart-search/  —  {query} → محصولات بر اساس نیت کاربر"""
    permission_classes = [AllowAny]

    def post(self, request):
        query = (request.data.get("query") or "").strip()
        if not query:
            return Response({"error": "عبارت جستجو خالی است"}, status=400)

        keywords = query  # پیش‌فرض: خود عبارت
        try:
            raw = _ask_ollama([
                {"role": "system", "content":
                    "تو استخراج‌کنندهٔ کلیدواژه هستی. از جملهٔ کاربر فقط کلیدواژه‌های جستجوی محصول "
                    "(نوع کالا، برند، مدل) را به‌صورت JSON با کلید keywords (رشته) برگردان. "
                    "هیچ متن دیگری ننویس. مثال: {\"keywords\": \"دوربین داهوا دام\"}"},
                {"role": "user", "content": query},
            ])
            m = re.search(r"\{.*\}", raw, re.S)
            if m:
                kw = json.loads(m.group(0)).get("keywords", "").strip()
                if kw:
                    keywords = kw
        except Exception as exc:
            logger.warning(f"[ASSISTANT] استخراج کلیدواژه ناموفق، از عبارت اصلی استفاده شد: {exc}")

        products, _ = _find_products(keywords, limit=12)
        return Response({
            "keywords": keywords,
            "results": [_product_dict(p, request.user) for p in products],
        })


class FAQListView(APIView):
    """GET /api/assistant/faqs/ — لیست پرسش‌های متداول فعال برای صفحه «سوالات متداول»"""
    permission_classes = [AllowAny]

    def get(self, request):
        faqs = FAQ.objects.filter(is_active=True)
        return Response([{"id": f.id, "question": f.question, "answer": f.answer} for f in faqs])
