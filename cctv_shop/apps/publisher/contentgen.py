"""
apps/publisher/contentgen.py
─────────────────────────────
تولید ایده و کپشن محتوای اینستاگرام با LLM — مشترک بین کامند generate_content_ideas
و API ثبت ایدهٔ دستی. خروجی مدل همیشه JSON سخت‌گیرانه است و اینجا پارس می‌شود.
"""

import json
import re

from apps.assistant.engine import ask_llm

CONTENT_CATEGORIES = {"product_showcase", "educational", "offer", "trend", "behind_scenes"}

SYSTEM_PROMPT = """تو تولیدکنندهٔ محتوای اینستاگرام فروشگاه «دوربین‌کار» (doorbinkar.com) هستی — فروش عمده قطعات و بردهای دوربین مداربسته.
مخاطب تو مصرف‌کنندهٔ خانگی نیست؛ مونتاژکار، تعمیرکار و فروشندهٔ تجهیزات دوربین مداربسته است (B2B) که جنس را برای مونتاژ و فروش مجدد می‌خرد.

قوانین سخت‌گیرانه خروجی:
- فقط فارسی بنویس؛ لحن فنی و کارگاهی (برد، سنسور، لنز، کیس، IR-cut، QC، تست اتاق تاریک) نه تبلیغاتی مصرف‌کننده.
- خروجی فقط و فقط یک آرایهٔ JSON معتبر باشد — بدون هیچ متن، توضیح یا ``` قبل و بعد.
- هر عضو آرایه این کلیدها را دارد: title (رشته کوتاه)، category (یکی از product_showcase/educational/offer/trend/behind_scenes)، product_name (نام دقیق محصول از لیست یا null)، caption (رشته)، hashtags (آرایهٔ ۵ تا ۱۰ رشته بدون #).

قوانین کپشن (الگوریتم اینستاگرام):
- خط اول قلاب (hook) باشد — جمله‌ای که اسکرول را نگه می‌دارد؛ سؤال یا ادعای فنی جذاب.
- کپشن حداکثر ۱۵۰ کلمه؛ جمله‌ها کوتاه و انسان‌نویس، بدون کلیشه‌های ماشینی مثل «در دنیای امروز».
- یک CTA مشخص در انتها (مثلاً «برای قیمت عمده دایرکت بده» یا «با فروش تماس بگیر»).
- هشتگ‌ها ترکیبی باشند: چند هشتگ پرطرفدار کلی (مثل دوربین_مداربسته)، چند تخصصی (مثل برد_دوربین، مونتاژ_دوربین) و برند (دوربین‌کار).
- ادعای فنی فقط بر اساس اطلاعات محصولاتی که به تو داده می‌شود؛ مدل و عدد از خودت نساز."""


def _products_block(products) -> str:
    lines = []
    for p in products:
        parts = [p.name]
        if p.brand:
            parts.append(f"برند {p.brand}")
        if p.category:
            parts.append(f"دسته {p.category.name}")
        specs = p.short_description or ""
        if specs:
            parts.append(specs[:120])
        lines.append("- " + " | ".join(parts))
    return "\n".join(lines)


def _articles_block(articles) -> str:
    return "\n".join(f"- {a.title}" + (f" | {a.description[:120]}" if a.description else "") for a in articles)


_FA_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def _fa_num(value) -> str:
    return str(value).translate(_FA_DIGITS)


def _top_posts_block(top_posts) -> str:
    """بلوک فارسی پست‌های برتر — top_posts: لیست دیکشنری {title, views, saved}"""
    lines = [
        f"{_fa_num(i)}) «{p['title']}» — بازدید {_fa_num(p.get('views', 0))}، ذخیره {_fa_num(p.get('saved', 0))}"
        for i, p in enumerate(top_posts, 1)
    ]
    return (
        f"{_fa_num(len(top_posts))} پست برتر اخیر (بر اساس بازدید):\n"
        + "\n".join(lines)
        + "\nایده‌های مشابه یا بهتر از این الگوها بساز."
    )


def build_ideas_messages(products, articles, count: int, content_type: str, top_posts=None) -> list:
    type_label = {"reel": "ریل", "post": "پست", "story": "استوری"}.get(content_type, "ریل")
    insights_section = f"\n\n{_top_posts_block(top_posts)}" if top_posts else ""
    user = f"""محصولات فعال فروشگاه:
{_products_block(products) or "(محصولی موجود نیست)"}

مقالات آموزشی منتشرشده:
{_articles_block(articles) or "(مقاله‌ای موجود نیست)"}

{count} ایدهٔ محتوای اینستاگرام از نوع «{type_label}» بساز. برای هر ایده اگر به یکی از محصولات لیست مربوط است، نام دقیق همان محصول را در product_name بنویس. خروجی فقط آرایهٔ JSON باشد.{insights_section}"""
    return [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user}]


def build_caption_messages(title: str, description: str, category: str, product=None) -> list:
    product_line = ""
    if product is not None:
        specs = f" | {product.short_description[:150]}" if product.short_description else ""
        product_line = f"\nمحصول مرتبط: {product.name}{specs}"
    user = f"""برای این ایدهٔ محتوا یک کپشن اینستاگرام بساز:
عنوان ایده: {title}
توضیح: {description or "-"}
دسته: {category}{product_line}

خروجی فقط یک آبجکت JSON با این کلیدها باشد: caption (رشته)، hashtags (آرایهٔ ۵ تا ۱۰ رشته بدون #)."""
    return [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user}]


def parse_json_payload(raw: str):
    """خروجی مدل را به آبجکت JSON تبدیل می‌کند — فنس ``` و متن اضافی دور آرایه/آبجکت حذف می‌شود."""
    text = raw.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.S).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"(\[.*\]|\{.*\})", text, re.S)
        if m:
            return json.loads(m.group(1))
        raise


def generate_ideas(products, articles, count: int, content_type: str, top_posts=None) -> list:
    """N ایده از LLM می‌گیرد و به لیست دیکشنری نرمال‌شده برمی‌گرداند.
    top_posts اختیاری است: آمار پست‌های برتر برای تزریق به پرامپت."""
    raw, _engine = ask_llm(build_ideas_messages(products, articles, count, content_type, top_posts), max_tokens=3000)
    data = parse_json_payload(raw)
    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list):
        raise ValueError("خروجی مدل آرایهٔ JSON نیست")
    ideas = []
    for item in data:
        if not isinstance(item, dict) or not item.get("title"):
            continue
        hashtags = item.get("hashtags") or []
        if isinstance(hashtags, str):
            hashtags = hashtags.split()
        ideas.append({
            "title": str(item["title"])[:255],
            "category": item.get("category") if item.get("category") in CONTENT_CATEGORIES else "product_showcase",
            "product_name": (item.get("product_name") or "").strip() or None,
            "caption": str(item.get("caption") or "").strip(),
            "hashtags": [str(h).lstrip("#").strip() for h in hashtags if str(h).strip()][:10],
        })
    return ideas[:count]


def generate_caption(title: str, description: str, category: str, product=None) -> dict:
    """برای ایدهٔ دستی کپشن + هشتگ تولید می‌کند — خروجی: {"caption":…, "hashtags":[…]}"""
    raw, _engine = ask_llm(build_caption_messages(title, description, category, product), max_tokens=1200)
    data = parse_json_payload(raw)
    if isinstance(data, list):
        data = data[0] if data else {}
    if not isinstance(data, dict):
        raise ValueError("خروجی مدل آبجکت JSON نیست")
    hashtags = data.get("hashtags") or []
    if isinstance(hashtags, str):
        hashtags = hashtags.split()
    return {
        "caption": str(data.get("caption") or "").strip(),
        "hashtags": [str(h).lstrip("#").strip() for h in hashtags if str(h).strip()][:10],
    }
