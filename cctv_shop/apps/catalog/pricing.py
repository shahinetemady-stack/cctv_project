"""
apps/catalog/pricing.py
───────────────────────
محاسبه قیمت فروش سایت از فرمول قیمت:
    (قیمت خرید یوان + حمل دسته + ترخیص دسته) × نرخ یوان × (۱ + درصد سود نوع فروش)
    × (۱ − درصد تخفیف واریانت)
    — تومان، رند به بالای هزار
قیمت نمایشی هر کاربر بر اساس سطح همکاری تعیین می‌شود:
    مهمان/عمومی → retail (مشتری عمومی)
    سیلور        → month1 (یکماهه)
    گلد          → credit (تو حسابی)
    پلاتینیوم    → credit + گزینه‌های cash و month1 در فرانت
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
    if tier == "silver":
        return "month1", tier
    if tier in ("gold", "platinum"):
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
        payload["options"] = {
            "credit": prices["credit"],
            "cash": prices["cash"],
            "month1": prices["month1"],
        }
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
    دوماهه (month2) فقط برای همکار پلاتینیوم و فقط برای واریانت‌هایی که فروش دوماهه دارند."""
    _, tier = user_price_key(user)
    if tier == "platinum":
        base = ["cash", "credit", "month1"]
        if variant is not None and not variant.month2_unavailable:
            base.append("month2")
        return base
    return ["cash"]


def price_for_settlement(variant, user, settlement_type):
    """قیمت واریانت بر اساس نوع تسویه انتخاب‌شده کاربر برای یک قلم.
    نقدی برای کاربر عمومی = قیمت مشتری عمومی (retail)، برای همکار = قیمت نقدی."""
    _, tier = user_price_key(user)
    prices = formula_prices(variant)
    if settlement_type == "cash":
        return prices["cash"] if tier else prices["retail"]
    return prices.get(settlement_type, prices["retail"])
