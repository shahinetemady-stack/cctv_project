"""
apps/leads/keywords.py — کلیدواژه‌های مشترک اسکرپرها + نگاشت دسته‌بندی

هر کلیدواژه به یک دسته (Lead.Category) وصل است تا کمپین‌ها هدفمند شوند:
  installer → نصاب و مجری (مشتری عمده بالقوه — تجهیزات از ما می‌خرد)
  seller    → فروشگاه و فروشنده (همکار/بازار اقتصادی فروش مجدد)
  company   → شرکت نظارتی/حفاظتی
  other     → سایر
"""
from .models import Lead

# (کلیدواژه، دسته)
KEYWORDS = [
    ("نصب دوربین مداربسته",  Lead.Category.INSTALLER),
    ("نصاب دوربین",          Lead.Category.INSTALLER),
    ("نصب دزدگیر اماکن",     Lead.Category.INSTALLER),
    ("دزدگیر اماکن",         Lead.Category.INSTALLER),
    ("سیستم حفاظتی",         Lead.Category.INSTALLER),
    ("آیفون تصویری",         Lead.Category.INSTALLER),
    ("فروش دوربین مداربسته", Lead.Category.SELLER),
    ("دوربین تحت شبکه",      Lead.Category.SELLER),
    ("داهوا",                Lead.Category.SELLER),
    ("هایک ویژن",            Lead.Category.SELLER),
    ("شرکت نظارت تصویری",    Lead.Category.COMPANY),
    ("سیستم امنیتی",         Lead.Category.COMPANY),
]

KEYWORD_CATEGORY = dict(KEYWORDS)

DEFAULT_KEYWORDS = [kw for kw, _ in KEYWORDS]


def category_for(keyword: str) -> str:
    """دسته متناسب با کلیدواژه؛ ناشناخته → other"""
    return KEYWORD_CATEGORY.get(keyword, Lead.Category.OTHER)


# شهرهای هدف برای اسکرپر گوگل (گوگل مپ برخلاف دیوار شهرمحور است)
GOOGLE_CITIES = [
    "تهران", "مشهد", "اصفهان", "شیراز", "تبریز",
    "کرج", "اهواز", "قم", "رشت", "یزد",
]
