"""
دستیار هوشمند فروشگاه — چت‌بات + سرچ هوشمند با LLM لوکال (Ollama).

نکتهٔ مهم معماری: مدل هرگز از خودش قیمت/موجودی نمی‌گوید؛
محصولات مرتبط از دیتابیس پیدا و به‌عنوان context به مدل داده می‌شود (RAG ساده).
"""

import json
import logging
import re
import time

from django.conf import settings as dj_settings
from django.core.cache import cache
from django.db.models import Q
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.models import Product

from .engine import _ask_ollama, _engine_chain
from .models import FAQ, AssistantSettings, LearnedQA

logger = logging.getLogger(__name__)


# ─── RBAC helpers ────────────────────────────────────────────

def _has_perm(user, code):
    if user.is_superuser:
        return True
    sp = getattr(user, 'staff_profile', None)
    return bool(sp and sp.is_active and sp.has_perm(code))


def _has_any_perm(user, *codes):
    return any(_has_perm(user, c) for c in codes)


def _forbidden(msg='شما دسترسی لازم برای این عملیات را ندارید'):
    return Response({'error': msg}, status=403)

# اعداد فارسی/عربی → لاتین (کاربر «۲ مگاپیکسل» می‌نویسد)
FA_TO_EN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
# معادل حروفی اعداد رایج مگاپیکسل — در نام محصولات به حروف نوشته شده («پنج مگاپیکسل»)
MP_WORDS = {"1": "یک", "2": "دو", "3": "سه", "4": "چهار", "5": "پنج", "6": "شش", "8": "هشت", "12": "دوازده"}
# املای فارسی اصطلاحات → شکلی که در نام/مشخصات محصولات آمده
ALIASES = {"ای اچ دی": "AHD", "ای‌اچ‌دی": "AHD", "آی پی": "IP", "ای پی": "IP", "پی او ای": "POE"}
# اصطلاحات دوزبانه — برخی محصولات اسم انگلیسی دارند؛ هر دو شکل جستجو می‌شود (به‌جای جایگزینی، اضافه می‌شود)
ALIASES_BILINGUAL = {
    "دارک لایت": "dark light", "دارک‌لایت": "dark light",
    "استار لایت": "star light", "استارلایت": "starlight",
    "باکس دوربین": "housing", "توربو": "turbo",
}

SYSTEM_PROMPT = """تو دستیار فروشگاه اینترنتی «دوربینکار» هستی (فروش تجهیزات دوربین مداربسته: دوربین، DVR، NVR، هارد، کابل و…).
قوانین سخت‌گیرانه:
- فقط فارسی جواب بده؛ کوتاه و مفید (حداکثر ۵ جمله) و محترمانه.
- درباره قیمت و موجودی «فقط» بر اساس لیست «اطلاعات محصولات» جواب بده. اگر محصول موردنظر در لیست نبود، صادقانه بگو در فروشگاه پیدا نکردی و پیشنهاد بده با فروش تماس بگیرند یا عبارت دیگری جستجو کنند.
- قیمت‌ها در لیست و کاتالوگ به «ریال» است؛ همیشه با همان واحد ریال اعلام کن و به تومان تبدیل نکن.
- فقط محصولاتی را پیشنهاد بده که در لیست هستند؛ وضعیت موجودی را دقیقاً همان‌طور که در لیست آمده بگو و اگر ناموجود است، صادقانه اعلام کن.
- اگر مشتری مشخصات دقیق خواست (مثلاً مگاپیکسل یا مدل خاص)، فقط همان را پیشنهاد بده؛ اگر دقیقاً همان در لیست نبود، صادقانه بگو و نزدیک‌ترین گزینه موجود را معرفی کن.
- اگر سؤال بله/خیر یا سؤال درباره یک مشخصه بود (مثل «کیس K6 فلزیه؟» یا «ابعادش چقدره؟»)، اول مستقیم و کوتاه از روی «مشخصات» همان محصول جواب بده، بعد درباره موجودی یا جایگزین بگو.
- در پیشنهاد محصول اولویت با اقلام «موجود» است؛ محصول ناموجود را فقط وقتی معرفی کن که دقیقاً همان خواسته مشتری است یا جایگزین موجودی ندارد — و همیشه صریح بگو ناموجود است.
- اگر مشتری «ارزان‌ترین» یا «گران‌ترین» خواست، فقط از قیمت‌های لیست استفاده کن و ارزان‌ترین/گران‌ترین «موجود» را معرفی کن؛ اگر ارزان‌ترینِ لیست ناموجود بود، بگو ناموجود است و ارزان‌ترین موجود را پیشنهاد بده.
- «مگ»، «مگا»، «mp»، «meg» و «megapixel» همگی به معنای «مگاپیکسل» (رزولوشن سنسور) هستند؛ مثلاً «۲ مگ» یعنی ۲ مگاپیکسل (فول‌اچ‌دی 1080p). اگر کاربر معنی این اصطلاح‌ها را پرسید، کوتاه توضیح بده و محصولات همان رزولوشن از لیست را پیشنهاد بده.
- هرگز قیمت، موجودی یا مشخصات از خودت نساز.
- اگر بخش «بخش‌های مرتبط با سؤال مشتری از دیتاشیت‌ها» در اطلاعات بود، برای سؤال‌های فنی (ولتاژ، پروتکل، NPU، قابلیت‌ها و…) اول از همان جواب بده؛ اگر چیزی در آن نبود، صادقانه بگو در دیتاشیت محصول نیامده.
- در انتخاب محصول راهنمایی کن (مثلاً تفاوت داهوا و هایک‌ویژن، DVR با NVR، دوربین داخلی با بیرونی).
- اگر سؤال مشاوره‌ای بود (مثلاً «برای پارکینگ» یا «برای مغازه»)، از روی «مشخصات» محصولات لیست راهنمایی کن؛ مثلاً فاصله کانونی کوچک‌تر (2.8mm) زاویه دید بازتر برای فاصله نزدیک است و بزرگ‌تر (8mm به بالا) برای فاصله دور، و سنسور استارلایت برای تاریکی بهتر است.
- اگر سؤال ربطی به فروشگاه نداشت، مؤدبانه بگو فقط درباره محصولات و خرید می‌توانی کمک کنی.
- اگر پیام مشتری فقط سلام و احوال‌پرسی یا تشکر بود (مثل «سلام»، «ممنون»، «خداحافظ»)، کوتاه و محترمانه جواب بده و «هیچ محصولی پیشنهاد نده» و از کاتالوگ چیزی معرفی نکن — فقط بپرس چه قطعه‌ای برای مونتاژ لازم دارد.
- پیام‌های کوتاه پیگیری (مثل «مدلای بیشتری بده»، «ارزان‌ترش چی؟»، «کدومش موجوده؟») ادامهٔ همان موضوع قبلی گفتگو هستند — از روی تاریخچه گفتگو بفهم منظور مشتری چیست و همان موضوع را ادامه بده، موضوع را عوض نکن.
- در پایان «هر» پاسخ فنی، قدم بعدی مشتری را حدس بزن و با یک جمله کوتاه پیشنهادش بده — مثلاً اگر برد خواست، به لنز و کیس سازگارش اشاره کن («این برد با لنز ۵ مگاپیکسل و کیس ۳۸ سازگار است؛ دام می‌خواهی یا بولت؟»)؛ اگر لنز خواست، به هولدر و کابل اشاره کن. هدف این است که مشتری برای کامل‌کردن سفارشش راهنمایی شود — فقط یک جمله، کوتاه و طبیعی، نه لیست تبلیغاتی.
- اگر سؤال «مقایسه» دو یا چند محصول بود (مثل «h4p با h2p چه فرقی دارد؟»)، محور پاسخ «تفاوت‌ها»ست نه شباهت‌ها: هر محصول را جداگانه و با نام دقیق خودش بررسی کن و تفاوت‌ها را نقطه‌وار بگو (سنسور، پردازنده، رزولوشن، قابلیت‌ها، قیمت، کاربرد)؛ از شباهت‌ها حداکثر در نیم‌جمله بگو. هرگز وسط پاسخ از یکی به دیگری بپری یا محصول سوم را جای یکی از آن‌ها تحلیل نکن — و اگر دیتاشیت یکی از آن‌ها در کانتکست نیست، صادقانه بگو اطلاعاتش در دسترس نیست.
- هرگز خطوط «اطلاعات محصولات» را عیناً یا با همان قالب تکرار نکن؛ با جمله‌های خودت، کوتاه و طبیعی جواب بده و جواب را با کلماتی مثل «همین» یا «بله،» شروع نکن.
- اگر از هویت یا توانایی‌هایت پرسیدند، بگو: «من ربات هوشمند دوربینکار هستم و به دیتاشیت‌های سایت دسترسی دارم؛ می‌توانم منطبق‌ترین محصول با خواسته شما را پیدا کنم.»
لحن و سبک (پرسنای نگارش):
- مخاطب تو هرگز مصرف‌کنندهٔ خانگی نیست؛ مخاطب اصلی مونتاژکار، تعمیرکار و تولیدکننده دوربین مداربسته است (B2B) که جنس را برای مونتاژ و فروش مجدد می‌خرد، نه برای نصب در خانه.
- با اصطلاحات دنیای کارگاه صحبت کن: برد، سنسور، IR-cut، FPC، کیس، QC، لحیم‌کاری، تست اتاق تاریک، فلت، باک کالیبراسیون.
- هرگز با زبان تبلیغاتی مصرف‌کننده جواب نده (مثل «مناسب خانه شما»، «خرید آسان»، «امنیت خانواده»). به‌جایش فنی و عملی حرف بزن: سازگاری برد با سنسور و لنز، ابعاد برد و کیس، نوع خروجی تصویر، شرایط نوری سنسور.
- وقتی پیشنهاد محصول می‌دهی، دلیل فنی بگو (مثلاً «این برد سنسور سونی ۳۳۵ دارد و برای نور کم مناسب است») نه دلیل بازاریابی.
- کاملاً انسان‌نویس بنویس: طول جمله‌ها متنوع، قضاوت فنی صریح و تجربه‌محور، توصیه عملی قابل اجرا. بدون کلیشه‌های ماشینی مثل «در دنیای امروز»، «با پیشرفت فناوری»، «همان‌طور که می‌دانید»، «در نهایت».
- ادعای فنی باید دقیق و محتاطانه باشد؛ مدل و عدد واقعی بزن و چیزی جعل نکن.
- هرگز تخفیف، گارانتی یا شرایطی که تعریف نشده وعده نده.
- نصب انجام نمی‌دهیم؛ فقط فروش قطعات (عمده و تک). اگر درباره نصب پرسیدند مؤدبانه بگو فقط فروش قطعات هستیم.

مثال‌ها (فقط برای یادگیری لحن و قالب — جواب واقعی را از روی «اطلاعات محصولات» همان گفتگو بده):
- مشتری: «سلام برد 2053 موجوده؟» (در لیست موجود است) → «بله، 2053 موجود است — برای مونتاژ دوربین ۲ مگاپیکسل برد پرفروشی است. قیمتش را در کارت محصول می‌بینی.»
- مشتری: «قیمتش چنده؟» (بدون محصول مشخص) → «کدام برد یا قطعه را می‌خواهید؟ مدلش را بفرستید تا قیمت دقیقش را بگویم.»
- مشتری: «نصب هم دارید؟» → «نه، ما فقط فروش قطعات و بردهای دوربین مداربسته هستیم و نصب انجام نمی‌دهیم. اگر قطعه‌ای برای مونتاژ نیاز دارید در خدمتیم.»
- مشتری: «برد فلان‌مدل موجوده؟» (در لیست نیست) → «این مدل را متأسفانه در فروشگاه پیدا نکردم. کد دقیق روی برچسب برد را بفرستید تا دوباره بررسی کنم.»"""


# ─── دیتاشیت‌های استخراج‌شده (datasheets.json — کامند extract_datasheets) ───
_DS_CACHE = {"mtime": 0, "data": {}}


def _datasheets() -> dict:
    """خواندن datasheets.json با کش مبتنی بر mtime — روی هر درخواست دیسک خوانده نمی‌شود."""
    path = dj_settings.BASE_DIR / "datasheets.json"
    try:
        mtime = path.stat().st_mtime
        if mtime != _DS_CACHE["mtime"]:
            _DS_CACHE["data"] = json.loads(path.read_text(encoding="utf-8"))
            _DS_CACHE["mtime"] = mtime
    except OSError:
        _DS_CACHE["data"] = {}
    return _DS_CACHE["data"]


def _datasheet_context(products, per_product: int = 1500) -> str:
    """متن دیتاشیت محصولات مرتبط برای کانتکست مدل — مرجع معتبر فنی (RAG)."""
    ds = _datasheets()
    blocks = []
    for p in products:
        entry = ds.get(p.slug)
        if entry and entry.get("text"):
            blocks.append(f"### دیتاشیت «{entry['name']}»:\n{entry['text'][:per_product]}")
    if not blocks:
        return ""
    return ("\n\nمتن دیتاشیت محصول (مرجع معتبر فنی — برای سؤال‌های فنی از همین استفاده کن و "
            "اگر چیزی در آن نیست بگو در دیتاشیت نیامده):\n" + "\n\n".join(blocks))


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
        "stock_qty": stock,
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
    if p.housing_material:
        parts.append(p.housing_material)
    if p.has_microphone:
        parts.append("میکروفون دارد")
    if p.modem_type:
        parts.append(p.modem_type)
    if p.sim_card:
        parts.append("سیم‌کارت‌خور")
    # مشخصات داینامیک دسته (رزولوشن، نوع لنز، دید در شب و…) — همان دیتاشیت صفحه محصول
    for k, v in (p.dynamic_specs or {}).items():
        if isinstance(v, str) and v.strip().lower() in ("true", "false"):
            v = v.strip().lower() == "true"
        if v not in (None, "", False) and len(parts) < 14:
            parts.append(f"{k}: {'دارد' if v is True else v}")
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
    # شکل انگلیسی اصطلاحات دوزبانه به عبارت اضافه می‌شود تا محصولات اسم‌انگلیسی هم پیدا شوند
    for fa, en in ALIASES_BILINGUAL.items():
        if fa in query:
            query += " " + en
    # اعداد حروفی قبل از «مگاپیکسل» → رقم تا منطق تطابق رزولوشن فعال شود («دو مگاپیکسل» → «2 مگاپیکسل»)
    for d, w in MP_WORDS.items():
        query = query.replace(f"{w} مگاپیکسل", f"{d} مگاپیکسل").replace(f"{w}مگاپیکسل", f"{d} مگاپیکسل")
    # حالت خلاصه با حروف («دو مگ») — بعد از تبدیل کامل تا دوباره‌کاری نشود
    for d, w in MP_WORDS.items():
        query = query.replace(f"{w} مگ", f"{d} مگاپیکسل").replace(f"{w}مگ", f"{d} مگاپیکسل")
    # معادل‌های رایج مگاپیکسل → شکل کامل تا تطابق رزولوشن فعال شود («2مگ»، «2 مگا»، «2mp»)
    query = re.sub(r"(?i)(\d+)\s*(?:megapixels?|mega|mp)\b", r"\1 مگاپیکسل ", query)
    query = re.sub(r"(\d+)\s*مگاپیکسل", r"\1 مگاپیکسل ", query)
    query = re.sub(r"(\d+)\s*مگا(?!پیکسل)", r"\1 مگاپیکسل ", query)
    query = re.sub(r"(\d+)\s*مگ(?![اپیکسلا])", r"\1 مگاپیکسل ", query)
    # علائم نگارشی به فاصله — وگرنه به کلمه می‌چسبند («داری؟» ≠ «داری»)
    query = re.sub(r"[؟?!.,،؛:]", " ", query)
    stopwords = {"چی", "چه", "پیشنهاد", "پشنهاد", "میدی", "میده", "میخوام", "میخواهم", "دارید", "داری",
                 "قیمت", "قیمتش", "چقدر", "چقدره", "برای", "لطفا", "لطفاً", "خرید", "بفرمایید",
                 "هست", "هستن", "یعنی", "چیه", "چیست"}
    words = [w.lower() for w in re.split(r"\s+", query.strip()) if len(w) > 1 and w not in stopwords][:8]
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
              f"{p.model_number or ''} {p.short_description or ''} {p.keywords or ''}".lower()
        matched = sum(1 for w in words if w in hay)
        mp_hit = any(v in p.name for v in mp_variants)
        if not matched and not mp_hit:
            return 0
        # تطابق کلمات مهم‌ترین فاکتور است؛ موجودی فقط امتیاز تشویقی می‌گیرد تا
        # محصول نامرتبطِ موجود بالاتر از تطابق دقیقِ ناموجود قرار نگیرد
        base = matched * 2 + (3 if mp_hit else 0) + (1 if p.available_stock > 0 else 0)
        # تطابق توکنِ کامل در مدل/نام — کوئری مدل دقیق (مثل «2053») باید فقط همان
        # محصول را بدهد، نه هر محصولی که «2053» در توضیح/سنسورش آمده (مثل F38)
        model = (p.model_number or "").lower()
        name = p.name.lower()
        for w in words:
            if not w:
                continue
            if w == model:
                base += 30
            elif re.search(rf"(^|[^a-z0-9]){re.escape(w)}([^a-z0-9]|$)", model):
                base += 15
            elif re.search(rf"(^|[^a-z0-9]){re.escape(w)}([^a-z0-9]|$)", name):
                base += 8
        return base

    pool = []
    if mp_variants:  # تطابق دقیق مگاپیکسل حتماً وارد pool شود — وگرنه ممکن است قبل از اسکورینگ حذف شود
        mp_q = Q()
        for v in mp_variants:
            mp_q |= Q(name__icontains=v)
        pool = list(qs.filter(mp_q)[:limit])
    pool += [p for p in qs.filter(q).distinct()[: limit * 6] if p not in pool]
    # توکن‌های مدل‌مانند (لاتین/عددی مثل h5as یا 2053) — تطابق مدل هرگز نباید قربانی
    # برش pool شود؛ کوئری کلی «برد» صدها محصول را می‌گیرد و محصول قدیمی‌تر جا می‌ماند
    for w in words:
        if re.search(r"[a-z]", w) or re.search(r"\d", w):
            pool += [p for p in qs.filter(Q(model_number__icontains=w) | Q(name__icontains=w))[:4]
                     if p not in pool]
    scored = sorted(((score(p), p) for p in pool), key=lambda t: -t[0])
    # اگر تطابق قوی (توکن کامل در مدل/نام) هست، تطابق‌های ضعیف (فقط توضیح/کلمات‌کلیدی) حذف شوند
    strong = [p for s, p in scored if s >= 10]
    products = strong[:limit] if strong else [p for s, p in scored if s > 0][:limit]
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


CATALOG_CACHE_TTL = 30 * 60  # کاتالوگ نیم‌ساعته بازسازی می‌شود

def _catalog_payload(user=None) -> str:
    """کاتالوگ فشردهٔ JSON همه محصولات فعال — در اختیار جمینای (تزریق به پرامپت)
    و Qwen و هر ابزار دیگر روی سرور (فایل catalog.json کنار manage.py) قرار می‌گیرد.
    قیمت‌ها بر اساس سطح کاربر درخواست‌دهنده است تا با بقیه سایت یکی باشد.
    نسخهٔ روی دیسک با قیمت مشتری عمومی نوشته می‌شود."""
    from apps.catalog.pricing import user_price_key
    price_key, _ = user_price_key(user)
    cache_key = f"assistant_catalog_{price_key}"
    data = cache.get(cache_key)
    if data is None:
        qs = (Product.objects.filter(is_active=True)
              .select_related("category").prefetch_related("variants"))
        items = []
        for p in qs:
            d = _product_dict(p, user)
            items.append({
                "name": d["name"], "brand": d["brand"], "category": d["category"],
                "price_irt": d["price_irt"], "in_stock": d["in_stock"],
                "specs": _spec_summary(p), "url": d["url"],
            })
        data = json.dumps(items, ensure_ascii=False)
        cache.set(cache_key, data, CATALOG_CACHE_TTL)
        if price_key == "retail":  # فایل مرجع روی دیسک همیشه با قیمت عمومی
            try:
                with open(dj_settings.BASE_DIR / "catalog.json", "w", encoding="utf-8") as f:
                    f.write(data)
            except OSError as exc:
                logger.warning(f"[ASSISTANT] نوشتن catalog.json ناموفق: {exc}")
    return data


def _catalog_compact(user=None) -> str:
    """نسخهٔ جمع‌وجور کاتالوگ برای تزریق به موتورهای ابری — فقط نام/دسته/قیمت/موجودی.
    نسخهٔ کامل با مشخصات (catalog.json) روی دیسک در دسترس است؛ تزریق نسخهٔ کامل به
    مدل‌های رایگان پاسخ را بیش از یک دقیقه کند می‌کرد."""
    from apps.catalog.pricing import user_price_key
    price_key, _ = user_price_key(user)
    cache_key = f"assistant_catalog_compact_{price_key}"
    data = cache.get(cache_key)
    if data is None:
        items = json.loads(_catalog_payload(user))
        data = json.dumps(
            [{k: it[k] for k in ("name", "category", "price_irt", "in_stock")} for it in items],
            ensure_ascii=False)
        cache.set(cache_key, data, CATALOG_CACHE_TTL)
    return data


def _learned_context(message: str, limit: int = 2) -> str:
    """پاسخ‌های یادگرفته‌شده از جمینای که به سؤال فعلی شبیه‌اند — برای تزریق به پرامپت."""
    query = re.sub(r"[؟?!.,،؛:]", " ", message.translate(FA_TO_EN_DIGITS))
    words = [w for w in re.split(r"\s+", query.strip()) if len(w) > 1][:8]
    if not words:
        return ""
    scored = []
    for qa in LearnedQA.objects.all()[:1000]:
        s = sum(1 for w in words if w in qa.question)
        if s:
            scored.append((s, qa))
    scored.sort(key=lambda t: (-t[0], -t[1].id))
    top = [qa for _, qa in scored[:limit]]
    if not top:
        return ""
    body = "\n".join(f"س: {qa.question}\nج: {qa.answer[:300]}" for qa in top)
    return ("\n\nپاسخ‌هایی که ربات قبلاً یاد گرفته (اگر به سؤال مشتری مربوط است از آن استفاده کن، وگرنه نادیده بگیر):\n"
            + body)


def _learn_from_answer(question: str, answer: str, engine: str):
    """ذخیرهٔ پاسخ موتورهای ابری برای استفاده در سؤال‌های مشابه بعدی (یادگیری ربات)."""
    if engine in ("qwen", "rules") or not question.strip() or not answer.strip():
        return
    try:
        if LearnedQA.objects.filter(question=question[:300]).exists():
            return
        LearnedQA.objects.create(question=question[:300], answer=answer[:2000], engine=engine)
    except Exception as exc:
        logger.warning(f"[ASSISTANT] ذخیره پاسخ یادگرفته‌شده ناموفق: {exc}")


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

        # سلام و احوال‌پرسی — پاسخ فوری بدون مدل و بدون کارت محصول
        # «سلام خوبی؟» و «سلام وقت بخیر» هم گرفته می‌شوند، ولی «سلام، برد ۵ مگا دارین؟» نه
        if ((re.match(r"^(سلام|درود|علیکم سلام|سلام علیکم|صبح بخیر|ظهر بخیر|عصر بخیر|شب بخیر|وقت بخیر|وقتتون بخیر|هی|های|hello|hi|hey)\b", message.strip(), re.I)
                and len(message) <= 30
                and not re.search(r"برد|لنز|کیس|سنسور|دوربین|کابل|مودم|هارد|پاور|فیش|قیمت|خرید|موجود|سفارش", message))
                or re.fullmatch(r"(ممنون|مرسی|متشکرم|تشکر|خداحافظ|خدانگهدار|فعلا|بای|ممنونم|مرسى)[\s!؟?.,،]*", message.strip())):
            return Response({
                "reply": "سلام، وقت بخیر! چه قطعه‌ای برای مونتاژ لازم دارید؟ (برد، لنز، کیس، سنسور، کابل و…)",
                "products": [],
                "engine": "rules",
            })

        # پرسش درباره هویت/توانایی ربات — پاسخ آماده و فوری، بدون فراخوانی مدل
        # «قابلیت» فقط وقتی که به خود ربات برگردد (داری/داری؟) — «برد X چه قابلیت‌هایی دارد» سؤال محصولی است
        if re.search(r"توانایی|کی هستی|چه کسی هستی|بلدی|چیکار می|چه کار می|خودت را معرفی|خودتو معرفی|معرفی خودت|قابلیت.{0,12}داری", message):
            return Response({
                "reply": "من ربات هوشمند دوربینکار هستم و به دیتاشیت‌های سایت دسترسی دارم؛ "
                         "می‌توانم منطبق‌ترین محصول با خواسته شما را پیدا کنم. "
                         "اگر سوالی راجع به قطعات داری، در خدمتم.",
                "products": [],
                "engine": "rules",
            })

        # نیت قیمتی: ارزان‌ترین/گران‌ترین — کل کاتالوگ بررسی شود تا گزینه ارزانِ موجود گم نشود
        wants_cheap = bool(re.search(r"ارزان", message))
        wants_expensive = bool(re.search(r"گران", message)) and not wants_cheap
        price_intent = wants_cheap or wants_expensive

        # کد قطعهٔ تنها (مثل «2053» یا «MC-F46») → فقط جستجوی هوشمند، بدون هوش مصنوعی
        code_q = message.translate(FA_TO_EN_DIGITS).strip()
        if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9\-+]{1,19}", code_q):
            products, is_fallback = _find_products(code_q, limit=4)
            dicts = []
            for p in products:
                d = _product_dict(p, request.user)
                d["specs"] = _spec_summary(p)
                dicts.append(d)
            if dicts and not is_fallback:
                # متن فقط برچسب باشد — نام/قیمت در کارت محصول می‌آید و تکرار نشود
                return Response({
                    "reply": f"نتیجه برای «{message}»:",
                    "products": dicts,
                    "engine": "search",
                })
            return Response({
                "reply": f"محصولی با کد «{message}» پیدا نشد — می‌توانید از جستجوی پیشرفته سایت (doorbinkar.com/products) استفاده کنید.",
                "products": [],
                "engine": "search",
            })

        products, is_fallback = _find_products(message, limit=200 if price_intent else 4)

        # سؤال پیگیری بدون کلمهٔ محصولی («مدلای بیشتری بده»، «ارزان‌ترش چی؟»، «چه رنگاییش داری؟»)
        # — با کلمات سؤال‌های قبلی گفتگو جستجو کن و اقلامی که قبلاً معرفی شده‌اند را کنار بگذار
        if is_fallback and history:
            prev_users = [str(h.get("content", "")) for h in history[-6:]
                          if isinstance(h, dict) and h.get("role") == "user" and h.get("content")]
            for prev in reversed(prev_users):
                p2, fb2 = _find_products(prev, limit=12)
                if not fb2:
                    # نوع قطعه از سؤال قبلی ارث ببر — «مدلای بیشتری برد» نباید لنز بیاورد
                    prev_types = [w for w in ("برد", "لنز", "کیس", "سنسور", "هولدر", "مودم", "پکیج") if w in prev]
                    if prev_types:
                        typed = [p for p in p2 if any(
                            w in p.name or (p.category and w in p.category.name) for w in prev_types)]
                        if typed:
                            p2 = typed
                    last_answers = " ".join(str(h.get("content", "")) for h in history[-6:]
                                            if isinstance(h, dict) and h.get("role") == "assistant")
                    fresh = [p for p in p2 if p.name not in last_answers]
                    products, is_fallback = (fresh or p2), False
                    break

        # بازیابی برداری (RAG) روی مشخصات + توضیحات + دیتاشیت‌ها — محصولاتی که
        # جستجوی کلیدواژه گم کرده (کوئری مفهومی مثل «برد پلاک‌خوان با NPU») و
        # چانک‌های فنی مرتبط برای تزریق به کانتکست. خرابی embedding هرگز چت را
        # نمی‌شکند: hits=None یعنی همان مسیر کلیدواژه‌ای قبلی ادامه می‌یابد.
        rag_hits = None
        if not price_intent:
            try:
                from . import rag
                rag_hits = rag.search(message, top_k=6)
            except Exception as exc:
                logger.warning(f"[ASSISTANT] RAG خطا داد: {exc}")
        if rag_hits:
            rag_slugs = []
            for h in rag_hits:
                if h["slug"] not in rag_slugs:
                    rag_slugs.append(h["slug"])
            if is_fallback:
                # کلیدواژه چیزی پیدا نکرد — نتایج برداری جای محصولات تصادفی بنشیند
                rag_products = list(Product.objects.filter(slug__in=rag_slugs[:4], is_active=True)
                                    .select_related("category").prefetch_related("variants"))
                if rag_products:
                    rag_products.sort(key=lambda p: rag_slugs.index(p.slug))
                    products, is_fallback = rag_products, False
            elif len(products) < 6:
                have = {p.slug for p in products}
                extra_slugs = [s for s in rag_slugs if s not in have][: 6 - len(products)]
                if extra_slugs:
                    products = list(products) + list(
                        Product.objects.filter(slug__in=extra_slugs, is_active=True)
                        .select_related("category").prefetch_related("variants"))

        dicts = []
        for p in products:
            d = _product_dict(p, request.user)
            d["specs"] = _spec_summary(p)
            dicts.append(d)

        # فیلتر نوع قطعه: اگر سؤال نوع مشخصی خواسته (برد، لنز، کیس...)،
        # کارت‌ها و جواب فقط از همان نوع باشند — نه محصول نامرتبط
        type_words = [w for w in ("برد", "لنز", "کیس", "سنسور", "هولدر", "مودم", "پکیج") if w in message]
        if type_words and dicts and not is_fallback:
            pairs = [(p, d) for p, d in zip(products, dicts)
                     if any(w in d["name"] or w in d["category"] for w in type_words)]
            if pairs:
                products = [p for p, _ in pairs]
                dicts = [d for _, d in pairs]

        if price_intent:
            # مرتب‌سازی زوجی تا products و dicts هم‌تراز بمانند
            pairs = sorted(zip(products, dicts), key=lambda t: (
                not t[1]["in_stock"],
                -(t[1]["price_irt"] or 0) if wants_expensive else (t[1]["price_irt"] or 999_000_000_000),
            ))
            products = [p for p, _ in pairs]
            dicts = [d for _, d in pairs]
            # جواب قطعی از دیتا — ارزان‌ترین/گران‌ترین را به مدل نسپار
            in_stock = [d for d in dicts if d["in_stock"] and d["price_irt"]]
            # فیلتر رزولوشن و سیستم اگر در سؤال آمده باشد (۵ مگاپیکسل، IP، AHD...)
            fa_msg = message.translate(FA_TO_EN_DIGITS)
            for fa, en in ALIASES.items():
                fa_msg = fa_msg.replace(fa, en)
            mm = re.search(r"(\d+)\s*(?:مگاپیکسل|مگا|مگ(?![اپیکسلا])|mp|megapixel)", fa_msg)
            if mm:
                d = mm.group(1)
                pats = [f"{d}مگاپیکسل"]
                if d in MP_WORDS:
                    pats.append(f"{MP_WORDS[d]}مگاپیکسل")
                squeezed = [x for x in in_stock
                            if any(pt in x["name"].translate(FA_TO_EN_DIGITS).replace("‌", "").replace(" ", "") for pt in pats)]
                if squeezed:
                    in_stock = squeezed
            sys_m = re.search(r"\b(ip|ahd)\b", fa_msg.lower())
            if sys_m:
                sysw = sys_m.group(1)
                same_sys = [x for x in in_stock if sysw in f"{x['name']} {x['category']} {x['specs']}".lower()]
                if same_sys:
                    in_stock = same_sys
            if in_stock and not is_fallback:
                best = in_stock[0]
                label = "ارزان‌ترین" if wants_cheap else "گران‌ترین"
                return Response({
                    "reply": f"{label} گزینه موجود فروشگاه «{best['name']}» با قیمت {best['price_irt']:,} ریال است.",
                    # کارت‌ها همان لیست فیلترشده (رزولوشن/سیستم) باشند — نه ارزان‌ترین‌های کلی
                    "products": in_stock[:8],
                    "engine": "rules",
                })
            # اگر جواب قطعی نشد، کانتکست مدل را منفجر نکن
            products, dicts = products[:4], dicts[:4]

        # جواب واقعی سریع از دیتابیس برای سؤالات مشخص (قیمت/موجودی/ابعاد/جنس بدنه)
        # — بدون فراخوانی مدل: هم فوری است هم غیرممکن است که جمله‌اش خراب شود
        if dicts and not is_fallback:
            top_p, top_d = products[0], dicts[0]
            fa_msg = message.translate(FA_TO_EN_DIGITS)
            quick = None
            if re.search(r"ابعاد|اندازه|سایز", fa_msg) and top_p.board_dimensions:
                quick = f"ابعاد «{top_p.name}» برابر {top_p.board_dimensions} میلی‌متر است"
                quick += "." if top_d["in_stock"] else "، ولی فعلاً ناموجود است."
            elif re.search(r"فلزی|پلاستیکی", fa_msg) and top_p.housing_material:
                if "فلز" in top_p.housing_material:
                    quick = f"بله، بدنه «{top_p.name}» فلزی است."
                else:
                    quick = f"نه، بدنه «{top_p.name}» {top_p.housing_material} است."
            elif re.search(r"قیمت|چنده|چند تومن|چند ریال", fa_msg) and top_d["price_irt"]:
                quick = f"قیمت «{top_p.name}» {top_d['price_irt']:,} ریال است"
                quick += "." if top_d["in_stock"] else "، ولی فعلاً ناموجود است."
            elif re.search(r"موجود", fa_msg):
                quick = f"«{top_p.name}» {'موجود است.' if top_d['in_stock'] else 'فعلاً ناموجود است.'}"
            if quick:
                return Response({"reply": quick, "products": dicts, "engine": "rules"})
        if dicts:
            lines = "\n".join(
                f"محصول: {d['name']}. برند: {d['brand'] or '-'}. دسته: {d['category']}. "
                + (f"قیمت: {d['price_irt']:,} ریال." if d["price_irt"] else "قیمت: نامشخص.")
                + (f" موجودی: دارد ({d['stock_qty']} عدد)." if d["in_stock"] else " موجودی: ندارد (ناموجود).")
                + (f" مشخصات: {d['specs']}." if d["specs"] else "")
                for d in dicts
            )
            if wants_cheap:
                lines = "(لیست از ارزان‌ترین به گران‌ترین مرتب شده و اقلام موجود اول آمده‌اند)\n" + lines
            elif wants_expensive:
                lines = "(لیست از گران‌ترین به ارزان‌ترین مرتب شده و اقلام موجود اول آمده‌اند)\n" + lines
            if is_fallback:
                lines = "(هیچ محصول مرتبطی با درخواست مشتری پیدا نشد؛ صادقانه بگو پیدا نکردی. " \
                        "این‌ها فقط چند محصول کلی فروشگاه‌اند، نه جواب درخواست مشتری:)\n" + lines
        else:
            lines = "(محصولی یافت نشد)"

        # چانک‌های دیتاشیت بازیابی‌شده با RAG برداری — مکمل _datasheet_context
        # (آن فقط دیتاشیت محصولات پیداشده را می‌دهد؛ این بخش‌های دقیقاً مرتبط با سؤال است)
        rag_block = ""
        if rag_hits:
            final_slugs = {p.slug for p in products}
            pieces = []
            for h in rag_hits:
                if h["kind"] == "datasheet" and h["slug"] in final_slugs and len(pieces) < 3:
                    pieces.append(h["text"][:800])
            if pieces:
                rag_block = ("\n\nبخش‌های مرتبط با سؤال مشتری از دیتاشیت‌ها (مرجع فنی):\n"
                             + "\n---\n".join(pieces))

        user_content = (f"اطلاعات محصولات فروشگاه:\n{lines}"
                        f"{_datasheet_context(products)}"
                        f"{rag_block}"
                        f"{_faq_context(_find_faqs(message))}"
                        f"{_learned_context(message)}"
                        f"\n\nپیام مشتری: {message}")
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for h in history[-6:]:
            if isinstance(h, dict) and h.get("role") in ("user", "assistant") and h.get("content"):
                messages.append({"role": h["role"], "content": str(h["content"])[:500]})
        messages.append({"role": "user", "content": user_content})

        # زنجیرهٔ موتورها: موتور انتخاب‌شده در پنل اول است؛ اگر خطا داد بقیهٔ کلیددارها
        # و در نهایت Qwen لوکال. موتورهای ابری کاتالوگ جمع‌وجور (نام/قیمت/موجودی) را هم
        # می‌گیرند — تزریق نسخهٔ کامل به مدل‌های رایگان پاسخ را بیش از یک دقیقه کند می‌کرد؛
        # مشخصات فنی از کانتکست متمرکز محصولات مرتبط می‌آید و catalog.json کامل روی دیسک است.
        st = AssistantSettings.get_instance()
        _catalog_payload(request.user)  # catalog.json روی دیسک همیشه تازه بماند
        cloud_messages = messages[:-1] + [{
            "role": "user",
            "content": user_content + "\n\nکاتالوگ محصولات فروشگاه (JSON):\n" + _catalog_compact(request.user),
        }]
        reply, engine, elapsed = None, None, None
        # ۸۰۰ توکن تا جواب فارسی وسط جمله بریده نشود (پیش‌فرض ۵۰۰ برای متن فارسی کم بود)
        for name, call in _engine_chain(st, max_tokens=800):
            try:
                t0 = time.monotonic()
                reply = call(cloud_messages if name != "qwen" else messages)
                engine, elapsed = name, round(time.monotonic() - t0, 1)
                break
            except Exception as exc:
                logger.warning(f"[ASSISTANT] موتور {name} خطا داد — تلاش با موتور بعدی: {exc}")
        if reply is None:
            return Response(
                {"error": "دستیار هوشمند موقتاً در دسترس نیست؛ کمی بعد دوباره تلاش کنید."},
                status=503,
            )
        if st.learn_from_gemini:
            _learn_from_answer(message, reply, engine)

        # کارت‌ها = محصولاتی که مدل واقعاً در جواب نام برده — مدل از کاتالوگ کامل جواب می‌دهد
        # و ممکن است محصولی را بگوید که جستجوی کلیدواژه پیدا نکرده (اسم انگلیسی و…)
        if not is_fallback:
            try:
                catalog_items = json.loads(_catalog_compact(request.user))
                def _name_codes(nm):
                    # کدهای مدل داخل اسم (YT-10035، H55Y، GC1084…) — مدل معمولاً فقط کد را می‌گوید
                    return [t for t in re.findall(r"[A-Za-z][A-Za-z0-9]*-?[A-Za-z0-9]*\d+[A-Za-z0-9\-]*", nm) if len(t) >= 3]
                mentioned = [
                    it for it in catalog_items
                    if it.get("name") and (it["name"] in reply or any(c in reply for c in _name_codes(it["name"])))
                ]
                if mentioned:
                    # اقلام کارت‌های قبلی که مدل نام برده اول بیایند، بعد بقیهٔ نام‌برده‌شده‌ها
                    mentioned_names = {it["name"] for it in mentioned}
                    dicts = mentioned + [d for d in dicts if d["name"] not in mentioned_names]
                    dicts = dicts[:8]
            except Exception:
                pass  # خرابی هماهنگ‌سازی کارت نباید جواب را بشکند

        # آخرین موتور پاسخ‌دهنده — در صفحه «تنظیمات ربات» پنل ادمین نمایش داده می‌شود
        from django.utils import timezone as tz
        cache.set("assistant_last_engine", {"engine": engine, "at": tz.now().isoformat(), "elapsed": elapsed}, None)
        return Response({
            "reply": reply,
            # محصولات fallback (نامرتبط) کارت نشان داده نمی‌شوند — فقط در کانتکست مدل بوده‌اند
            "products": [] if is_fallback else dicts,
            "engine": engine,
            "elapsed": elapsed,
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


# ─── راهنمای هوشمند حسابداری (فقط پنل مدیریت) ────────────────────────────────
# پایگاه دانش ساخت‌یافته در accounting_guide.json (کنار همین فایل) — موضوع‌ها با
# کلمات کلیدی، مسیر دقیق منوها و نمونه سؤال/جواب. برای به‌روزرسانی راهنما فقط
# همان فایل را ویرایش کن.
def _load_accounting_guide() -> str:
    import os.path
    path = os.path.join(os.path.dirname(__file__), "accounting_guide.json")
    try:
        with open(path, encoding="utf-8") as fh:
            kb = json.load(fh)
    except Exception as exc:
        logger.error(f"[ACC-ASSISTANT] خواندن accounting_guide.json ناموفق: {exc}")
        return "(راهنمای سیستم در دسترس نیست)"
    parts = [kb.get("menu_map", ""), kb.get("currency_note", "")]
    for t in kb.get("topics", []):
        parts.append(f"■ {t['title']}\n{t['content']}")
        for qa in t.get("qa", []):
            parts.append(f"  نمونه سؤال: {qa['q']}\n  نمونه جواب: {qa['a']}")
    return "\n\n".join(p for p in parts if p)


ACCOUNTING_GUIDE = _load_accounting_guide()

ACCOUNTING_SYSTEM_PROMPT = """تو «راهنمای هوشمند حسابداری» پنل مدیریت فروشگاه دوربینکار هستی — فقط برای پرسنل داخلی.
قوانین سخت‌گیرانه:
- فقط فارسی جواب بده؛ کوتاه و دقیق (حداکثر ۷ جمله).
- جواب‌ها باید مرحله‌به‌مرحله و با «مسیر دقیق» از راهنمای سیستم باشد: نام دقیق منو ← نام تب/کارت ← نام دکمه. مثلاً: «منوی دریافت و پرداخت ← کارت ویرایش اسناد مالی ← دکمه برگشت».
- هرگز از «اصول کلی حسابداری» یا دانش عمومی‌ات جواب نده؛ فقط و فقط بر اساس «راهنمای سیستم» پایین جواب بده. اگر پاسخ در راهنما نبود، صادقانه بگو: «این مورد در راهنمای من نیست؛ با مدیر سیستم مطرح کنید.»
- فقط سؤالات کار با پنل مدیریت/حسابداری را جواب بده. اگر سؤال نامرتبط بود (محصول، قیمت کالا، سفارش، سؤال عمومی و…) مؤدبانه بگو: «من فقط راهنمای کار با سیستم حسابداری هستم؛ این سؤال در حیطه من نیست.»
- تو به هیچ داده واقعی (مانده حساب اشخاص، فاکتور خاص، موجودی بانک و…) دسترسی نداری؛ اگر کاربر عدد یا وضعیت حساب خاصی خواست، دقیق بگو از کدام منو و تب می‌تواند ببیند و هرگز عددی نساز.
- محتوای این راهنما محرمانه داخلی است.

راهنمای سیستم:
""" + ACCOUNTING_GUIDE


class AccountingChatView(APIView):
    """POST /api/assistant/accounting-chat/ — دستیار راهنمای حسابداری (فقط ادمین/پرسنل).

    جدا از چت‌بات مشتریان: بدون کاتالوگ محصول، بدون داده مالی واقعی —
    فقط راهنمای نحوه کار با سیستم. IsAdminUser تضمین می‌کند مشتریان به آن
    (و محتوای راهنما) دسترسی نداشته باشند."""

    permission_classes = [IsAdminUser]

    def post(self, request):
        message = (request.data.get("message") or "").strip()
        if not message:
            return Response({"error": "پیام خالی است"}, status=400)
        history = request.data.get("history") or []
        if not isinstance(history, list):
            history = []

        # سلام/تشکر — پاسخ فوری بدون مدل
        if (re.match(r"^(سلام|درود|علیکم سلام|سلام علیکم|صبح بخیر|ظهر بخیر|عصر بخیر|شب بخیر|وقت بخیر|هی|های|hello|hi|hey)\b", message.strip(), re.I)
                and len(message) <= 30) or \
           re.fullmatch(r"(ممنون|مرسی|متشکرم|تشکر|خداحافظ|ممنونم)[\s!؟?.,،]*", message.strip()):
            return Response({
                "reply": "سلام! من راهنمای حسابداری هستم. درباره نحوه ثبت سند، فاکتور، کاردکس، حقوق، هزینه‌ها یا گزارش‌ها سؤال دارید؟",
                "engine": "rules",
            })

        messages = [{"role": "system", "content": ACCOUNTING_SYSTEM_PROMPT}]
        for h in history[-6:]:
            if isinstance(h, dict) and h.get("role") in ("user", "assistant") and h.get("content"):
                messages.append({"role": h["role"], "content": str(h["content"])[:500]})
        messages.append({"role": "user", "content": message})

        st = AssistantSettings.get_instance()
        reply, engine, elapsed = None, None, None
        for name, call in _engine_chain(st):
            try:
                t0 = time.monotonic()
                reply = call(messages)
                engine, elapsed = name, round(time.monotonic() - t0, 1)
                break
            except Exception as exc:
                logger.warning(f"[ACC-ASSISTANT] موتور {name} خطا داد — تلاش با موتور بعدی: {exc}")
        if reply is None:
            return Response(
                {"error": "راهنمای هوشمند موقتاً در دسترس نیست؛ کمی بعد دوباره تلاش کنید."},
                status=503,
            )
        return Response({"reply": reply, "engine": engine, "elapsed": elapsed})


class FAQListView(APIView):
    """GET /api/assistant/faqs/ — لیست پرسش‌های متداول فعال برای صفحه «سوالات متداول»"""
    permission_classes = [AllowAny]

    def get(self, request):
        faqs = FAQ.objects.filter(is_active=True)
        return Response([{"id": f.id, "question": f.question, "answer": f.answer} for f in faqs])


class AssistantSettingsView(APIView):
    """GET/PUT /api/assistant/settings/ — تنظیمات ربات هوشمند (کلیدها، موتور اصلی و…) + آخرین موتور پاسخ‌دهنده"""
    permission_classes = [IsAdminUser]

    FIELDS = ["provider", "gemini_api_key", "gemini_model", "gemini_enabled", "gemini_proxy",
              "ms_api_key", "ms_model", "zai_api_key", "zai_model", "ds_api_key", "ds_model",
              "learn_from_gemini"]

    def get(self, request):
        if not _has_perm(request.user, 'assistant_settings_view'):
            return _forbidden()
        st = AssistantSettings.get_instance()
        return Response({
            **{f: getattr(st, f) for f in self.FIELDS},
            "last_engine": cache.get("assistant_last_engine"),
            "learned_count": LearnedQA.objects.count(),
        })

    def put(self, request):
        if not _has_perm(request.user, 'assistant_settings_view'):
            return _forbidden()
        st = AssistantSettings.get_instance()
        data = request.data
        if "provider" in data and data["provider"] in dict(AssistantSettings.PROVIDERS):
            st.provider = data["provider"]
        for f in self.FIELDS:
            if f == "provider":
                continue
            if f in data:
                setattr(st, f, bool(data[f]) if f in ("gemini_enabled", "learn_from_gemini") else str(data[f]).strip())
        st.save()
        logger.info(f"[ASSISTANT] تنظیمات ربات توسط {request.user} به‌روز شد (provider={st.provider})")
        return self.get(request)
