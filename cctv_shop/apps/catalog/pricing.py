"""
apps/catalog/pricing.py
───────────────────────
محاسبه قیمت فروش سایت از فرمول قیمت:
    (قیمت خرید یوان + حمل دسته + ترخیص دسته) × نرخ یوان × (۱ + درصد سود نوع فروش)
    × (۱ − درصد تخفیف واریانت)
    — تومان، رند به بالای هزار
قیمت نمایشی هر کاربر بر اساس سطح همکاری تعیین می‌شود:
    مهمان/عمومی → retail (مشتری عمومی)
    سیلور        → silver (ستون مشتری سیلور)
    گلد          → gold (ستون مشتری گلد)
    پلاتینیوم    → credit + گزینه‌های cash و month1/month2 در فرانت (سرگروه مشتری پلاتینیوم)
توجه: این ستون‌ها فقط مبنای «قیمت» هستند — تسویه سیلور/گلد/عمومی همیشه نقدی است و
انتخاب نوع تسویه (نقدی/توحسابی/یکماهه/دوماهه) فقط برای پلاتینیوم معنا دارد.
تخفیف واریانت (discount_percent) روی همه انواع قیمت اعمال می‌شود و در
variant_pricing_payload قیمت اصلی (original_price) برای نمایش خط‌خورده برمی‌گردد.
"""
import math
from decimal import Decimal

from .models import ExchangeRateSetting

PROFIT_FIELDS = {
    "cash":   "profit_cash_percent",
    "credit": "profit_credit_percent",
    "month1": "profit_month1_percent",
    "month2": "profit_month2_percent",
    "gold":   "profit_gold_percent",
    "silver": "profit_silver_percent",
    "retail": "profit_retail_percent",
}

TIER_LABELS = {"silver": "همکار سیلور", "gold": "همکار گلد", "platinum": "همکار پلاتینیوم"}


def _effective_values(category):
    """مقادیر مؤثر دسته — صفر یعنی ارث از والد."""
    fields = ["shipping_cost_cny", "clearance_cost_cny"] + list(PROFIT_FIELDS.values())
    parent = category.parent if category else None
    out = {}
    for f in fields:
        own = getattr(category, f, Decimal("0")) if category else Decimal("0")
        out[f] = own or (getattr(parent, f, Decimal("0")) if parent else Decimal("0"))
    return out


def base_prices(variant):
    """قیمت‌های فرمول یک واریانت بدون تخفیف (ریال، رند به بالای ده‌هزار)."""
    eff = _effective_values(variant.product.category)
    rate_irt = Decimal(ExchangeRateSetting.get_instance().rate_cny_to_irt)
    cost = (variant.purchase_price_cny + eff["shipping_cost_cny"] + eff["clearance_cost_cny"]) * rate_irt
    return {
        key: int(math.ceil(float(cost * (1 + eff[field] / 100)) / 10000.0) * 10000)
        for key, field in PROFIT_FIELDS.items()
    }


def formula_prices(variant):
    """همه قیمت‌های فرمول یک واریانت (ریال، رند به بالای ده‌هزار) — با اعمال تخفیف واریانت."""
    base = base_prices(variant)
    disc = 1 - float(getattr(variant, "discount_percent", 0) or 0) / 100
    if disc >= 1:
        return base
    return {
        key: int(math.ceil(price * disc / 10000.0) * 10000)
        for key, price in base.items()
    }


def user_price_key(user):
    """کلید قیمت پیش‌فرض کاربر + سطح همکار (None برای عمومی)."""
    if not user or not user.is_authenticated:
        return "retail", None
    profile = getattr(user, "profile", None)
    is_partner = bool(
        profile and profile.is_approved
        and profile.user_type == profile.UserType.PARTNER
    )
    if not is_partner:
        return "retail", None
    tier = profile.partner_tier or ""
    if tier in ("silver", "gold"):
        return tier, tier
    if tier == "platinum":
        return "credit", tier
    return "retail", None


def variant_pricing_payload(variant, user):
    """پیلود pricing برای سریالایزر — قیمت نمایشی + گزینه‌های پرداخت پلاتینیوم."""
    prices = formula_prices(variant)
    key, tier = user_price_key(user)
    payload = {"key": key, "price": prices[key], "tier": tier}
    d = float(getattr(variant, "discount_percent", 0) or 0)
    if d > 0:
        payload["discount_percent"] = d
        payload["original_price"] = base_prices(variant)[key]
    if tier == "platinum":
        payload["options"] = {}
        if not variant.credit_unavailable:
            payload["options"]["credit"] = prices["credit"]
        payload["options"]["cash"] = prices["cash"]
        if not variant.month1_unavailable:
            payload["options"]["month1"] = prices["month1"]
        if not variant.month2_unavailable:
            payload["options"]["month2"] = prices["month2"]
    return payload


def price_for_user(variant, user):
    """قیمت فروش یک واریانت برای کاربر مشخص — همان قیمتی که در صفحه محصول می‌بیند.
    در سبد خرید/سفارش استفاده می‌شود تا قیمت ثبت‌شده با قیمت نمایشی یکی باشد."""
    key, _ = user_price_key(user)
    return formula_prices(variant)[key]


def allowed_settlements(user, variant=None):
    """انواع تسویه مجاز برای کاربر — هر قلم سفارش می‌تواند تسویه متفاوت داشته باشد.
    دوماهه (month2) فقط برای همکار پلاتینیوم و فقط برای واریانت‌هایی که فروش دوماهه دارند.
    برای واریانت‌هایی که در لیست قیمت «ندارد» خورده‌اند، توحسابی/یکماهه/دوماهه حذف می‌شوند.
    اگر کاربر به‌خاطر معوقات در مرحله «فقط نقدی» یا «مسدود» است، فقط نقدی برمی‌گردد."""
    if not user.is_anonymous:
        try:
            from apps.users.services import partner_restriction
            if partner_restriction(user):
                return ["cash"]
        except Exception:
            pass  # خطا در چک محدودیت نباید قیمت‌نمایشی را بشکند
    _, tier = user_price_key(user)
    if tier == "platinum":
        base = ["cash"]
        if variant is None or not variant.credit_unavailable:
            base.append("credit")
        if variant is None or not variant.month1_unavailable:
            base.append("month1")
        if variant is not None and not variant.month2_unavailable:
            base.append("month2")
        return base
    return ["cash"]


def price_for_settlement(variant, user, settlement_type):
    """قیمت واریانت بر اساس نوع تسویه انتخاب‌شده کاربر برای یک قلم.
    عمومی: قیمت مشتری عمومی (retail). سیلور/گلد: تسویه همیشه نقدی است و قیمت از
    ستون خودشان می‌آید (سیلور=silver، گلد=gold) — انتخاب ستون قیمت بر اساس
    تسویه فقط برای پلاتینیوم است."""
    key, tier = user_price_key(user)
    prices = formula_prices(variant)
    if tier in ("silver", "gold"):
        return prices[key]
    if settlement_type == "cash":
        return prices["cash"] if tier else prices["retail"]
    return prices.get(settlement_type, prices["retail"])
