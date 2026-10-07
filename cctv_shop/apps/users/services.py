"""
apps/users/services.py
──────────────────────
منطق باشگاه همکاران — محاسبه مجموع خرید و ارتقای خودکار سطوح.

ملاک سطح (همگی ریال) = سابقه خرید قبلی خارج از سایت (legacy_purchase_total)
         + مجموع خریدهای آنلاین پرداخت‌شده در N ماه اخیر

توجه: مبالغ Order در سیستم «تومان» ذخیره می‌شود؛ این ماژول همه‌چیز را به ریال تبدیل می‌کند
تا با آستانه‌های باشگاه (ریال) یکدست باشد.

قانون: فقط ارتقای خودکار انجام می‌شود؛ تنزل سطح هرگز خودکار نیست (دستی با ادمین است).
"""

import logging
import time
from datetime import timedelta

from django.utils import timezone

logger = logging.getLogger(__name__)

# رتبه سطوح برای مقایسه ارتقا
TIER_RANK = {"": 0, "silver": 1, "gold": 2, "platinum": 3}

_settings_cache = {"obj": None, "at": 0.0}
_CACHE_TTL = 60


def get_club_settings():
    """تنظیمات باشگاه (با کش ۶۰ ثانیه‌ای)."""
    from .models import PartnerClubSettings
    now = time.monotonic()
    if _settings_cache["obj"] is None or now - _settings_cache["at"] > _CACHE_TTL:
        _settings_cache["obj"] = PartnerClubSettings.get_instance()
        _settings_cache["at"] = now
    return _settings_cache["obj"]


def invalidate_club_settings_cache():
    _settings_cache["obj"] = None


def online_purchase_total(user, months) -> int:
    """مجموع خریدهای آنلاین پرداخت‌شده کاربر در N ماه اخیر (ریال).
    مبالغ Order ریال‌اند (لیبل «تومان» در مدل legacy است). وضعیت قدیمی 'shipped' هم حساب می‌شود."""
    from apps.orders.models import Order
    since = timezone.now() - timedelta(days=30 * months)
    statuses = [Order.Status.PAID, Order.Status.READY_TO_SHIP, "shipped"]
    return sum(
        o.effective_amount
        for o in Order.objects.filter(user=user, status__in=statuses, created_at__gte=since)
    )


def manual_purchase_total(user, months) -> int:
    """مجموع فاکتورهای فروش دستی (حضوری/غیرسایتی) پرداخت‌شده یا تأییدشده در N ماه اخیر (ریال).
    فقط منبع manual — فاکتور سفارش‌های آنلاین از مسیر Order شمرده می‌شوند و اینجا دوباره نیایند."""
    from apps.accounting.models import SaleInvoice
    since = (timezone.now() - timedelta(days=30 * months)).date()
    return sum(
        i.total_amount
        for i in SaleInvoice.objects.filter(
            customer=user,
            source=SaleInvoice.InvoiceSource.MANUAL,
            status__in=["paid", "confirmed"],
            issue_date__gte=since,
        )
    )


def partner_total_purchase(profile) -> int:
    """ملاک سطح (ریال): سابقه خرید قبلی + خرید آنلاین بازه اخیر + فاکتورهای دستی (حضوری) بازه اخیر."""
    st = get_club_settings()
    return (
        int(profile.legacy_purchase_total or 0)
        + online_purchase_total(profile.user, st.period_months)
        + manual_purchase_total(profile.user, st.period_months)
    )


def eligible_tier(total: int) -> str:
    """سطحی که این مجموع خرید مستحق آن است (صرف‌نظر از سابقه همکاری)."""
    st = get_club_settings()
    if st.gold_to_platinum_amount and total >= st.gold_to_platinum_amount:
        return "platinum"
    if st.silver_to_gold_amount and total >= st.silver_to_gold_amount:
        return "gold"
    return "silver"


PLATINUM_MIN_TENURE_MONTHS = 6


def _months_since(dt) -> int:
    now = timezone.now()
    months = (now.year - dt.year) * 12 + (now.month - dt.month)
    if now.day < dt.day:
        months -= 1
    return months


def platinum_tenure_ok(profile) -> bool:
    """شرط ارتقای خودکار به پلاتینیوم: حداقل ۶ ماه از شروع همکاری گذشته باشد."""
    created = profile.created_at or profile.user.date_joined
    return _months_since(created) >= PLATINUM_MIN_TENURE_MONTHS


def evaluate_partner_tiers() -> dict:
    """
    ارزیابی سطح همه همکاران تأییدشده — فقط ارتقا اعمال می‌شود (تنزل خودکار نداریم).
    همکارانی که مجموع خرید بازه‌شان پایین‌تر از سطح فعلی است در at_risk گزارش می‌شوند
    (هشدار برای تنزل دستی توسط ادمین).
    برای هر ارتقا پیامک تغییر سطح ارسال می‌شود (best-effort).
    → {"checked": n, "upgraded": n, "at_risk": [...], "details": [...]}
    """
    from .models import UserProfile
    from apps.notifications.services import notify_tier_change_sms

    result = {"checked": 0, "upgraded": 0, "at_risk": [], "details": []}
    profiles = (
        UserProfile.objects
        .filter(user_type=UserProfile.UserType.PARTNER, is_approved=True)
        .select_related("user")
    )
    for profile in profiles:
        result["checked"] += 1
        total = partner_total_purchase(profile)
        new_tier = eligible_tier(total)
        current = profile.partner_tier or "silver"
        if TIER_RANK.get(new_tier, 0) > TIER_RANK.get(current, 0):
            # شرط سابقه: پلاتینیوم فقط برای همکاری با حداقل ۶ ماه سابقه — وگرنه سقف فعلی گلد
            apply_tier = new_tier
            if new_tier == "platinum" and not platinum_tenure_ok(profile):
                apply_tier = "gold"
            if TIER_RANK.get(apply_tier, 0) > TIER_RANK.get(current, 0):
                profile.partner_tier = apply_tier
                profile.platinum_auto_granted = apply_tier == "platinum"
                profile.save(update_fields=["partner_tier", "platinum_auto_granted", "updated_at"])
                notify_tier_change_sms(
                    profile.user.phone,
                    f"{profile.user.first_name} {profile.user.last_name}".strip(),
                    profile.get_partner_tier_display(),
                )
                result["upgraded"] += 1
                result["details"].append({
                    "phone": profile.user.phone,
                    "from": current,
                    "to": apply_tier,
                    "total": total,
                })
                logger.info(
                    f"[CLUB] ارتقای سطح {profile.user.phone}: {current} → {apply_tier} (مجموع خرید {total:,} ریال)"
                )
            else:
                maybe_notify_near_tier(profile)
        elif TIER_RANK.get(new_tier, 0) < TIER_RANK.get(current, 0):
            # تنزل خودکار نمی‌شود — فقط هشدار برای ادمین (مگر اینکه ادمین موقتاً پنهان کرده باشد)
            snoozed = profile.club_risk_snoozed_until and profile.club_risk_snoozed_until > timezone.now()
            if not snoozed:
                result["at_risk"].append({
                    "phone": profile.user.phone,
                    "name": f"{profile.user.first_name} {profile.user.last_name}".strip(),
                    "tier": current,
                    "tier_display": profile.get_partner_tier_display(),
                    "eligible_tier": new_tier,
                    "total": total,
                })
                logger.info(
                    f"[CLUB] هشدار تنزل {profile.user.phone}: سطح {current}، مجموع خرید {total:,} ریال (متناسب {new_tier})"
                )
        else:
            maybe_notify_near_tier(profile)
    return result


def find_downgrade_risks(limit=100) -> list:
    """همکارانی که مجموع خرید بازه‌شان پایین‌تر از سطح فعلی است (کاندیدای تنزل دستی) —
    کسانی که هشدارشان توسط ادمین موقتاً پنهان شده (snooze) در لیست نمی‌آیند."""
    from .models import UserProfile

    risks = []
    now = timezone.now()
    profiles = (
        UserProfile.objects
        .filter(user_type=UserProfile.UserType.PARTNER, is_approved=True)
        .exclude(partner_tier__in=["", "silver"])
        .exclude(club_risk_snoozed_until__gt=now)
        .select_related("user")
    )
    for profile in profiles:
        total = partner_total_purchase(profile)
        new_tier = eligible_tier(total)
        current = profile.partner_tier
        if TIER_RANK.get(new_tier, 0) < TIER_RANK.get(current, 0):
            risks.append({
                "phone": profile.user.phone,
                "name": f"{profile.user.first_name} {profile.user.last_name}".strip(),
                "tier": current,
                "tier_display": profile.get_partner_tier_display(),
                "eligible_tier": new_tier,
                "total": total,
            })
    return risks[:limit]


def snoozed_risk_count() -> int:
    """تعداد همکارانی که هشدار تنزل‌شان فعلاً پنهان است."""
    from .models import UserProfile
    return UserProfile.objects.filter(
        user_type=UserProfile.UserType.PARTNER,
        is_approved=True,
        club_risk_snoozed_until__gt=timezone.now(),
    ).count()


def snooze_downgrade_risk(phones: list, days: int = 30) -> int:
    """پنهان کردن موقت هشدار تنزل برای لیستی از موبایل‌ها — تا N روز دیگر."""
    from .models import UserProfile
    until = timezone.now() + timedelta(days=days)
    return UserProfile.objects.filter(
        user_type=UserProfile.UserType.PARTNER,
        user__phone__in=phones,
    ).update(club_risk_snoozed_until=until)


def maybe_notify_near_tier(profile) -> bool:
    """اگر همکار به ۸۰٪ آستانه سطح بعدی رسیده و هنوز ارتقا نگرفته، یک‌بار در هر بازه پیامک بده."""
    from .models import UserProfile
    from apps.notifications.services import notify_near_tier_sms

    if profile.user_type != UserProfile.UserType.PARTNER or not profile.is_approved:
        return False

    total = partner_total_purchase(profile)
    current = profile.partner_tier or "silver"
    next_tier = eligible_tier(total)
    if TIER_RANK.get(next_tier, 0) > TIER_RANK.get(current, 0):
        # مسیر ارتقا توسط evaluate_partner_tiers هندل می‌شود
        return False

    st = get_club_settings()
    if current == "silver":
        threshold = st.silver_to_gold_amount
        next_tier = "gold"
    elif current == "gold":
        threshold = st.gold_to_platinum_amount
        next_tier = "platinum"
    else:
        return False

    if not threshold or total < 0.8 * threshold:
        return False

    now = timezone.now()
    if profile.club_near_notified_at and profile.club_near_notified_at > now - timedelta(days=30 * st.period_months):
        return False

    remaining = max(threshold - total, 0)
    remaining_display = f"{remaining:,}"
    tier_display = dict(UserProfile._meta.get_field("partner_tier").choices).get(next_tier, next_tier)
    name = f"{profile.user.first_name} {profile.user.last_name}".strip()

    try:
        notify_near_tier_sms(profile.user.phone, name, tier_display, remaining_display)
    except Exception as e:
        logger.exception(f"[CLUB] خطا در پیامک نزدیکی به آستانه {profile.user.phone}: {e}")

    profile.club_near_notified_at = now
    profile.save(update_fields=["club_near_notified_at", "updated_at"])
    return True


# ─── محدودیت خودکار معوقات (روز کاری، بدون جمعه و تعطیلات رسمی) ──────────────

_holidays_cache = {}


def _ir_holidays(year):
    """تعطیلات رسمی ایران برای یک سال (با کش) — پکیج holidays."""
    if year not in _holidays_cache:
        import holidays as holidays_lib
        _holidays_cache[year] = holidays_lib.Iran(years=[year])
    return _holidays_cache[year]


def is_workday(d) -> bool:
    """روز کاری = غیر جمعه و غیر تعطیل رسمی."""
    return d.weekday() != 4 and d not in _ir_holidays(d.year)


def add_workdays(start, n):
    """تاریخ شمول n روز کاری بعد از start (خود start حساب نمی‌شود)."""
    d = start
    remaining = n
    while remaining > 0:
        d += timedelta(days=1)
        if is_workday(d):
            remaining -= 1
    return d


# سطوح محدودیت — به ترتیب شدت
RESTRICTION_LEVELS = ["warning", "cash_only", "blocked"]


def partner_restriction(user):
    """
    وضعیت محدودیت معوقات کاربر.

    → None اگر محدودیتی ندارد (معوقه ندارد یا ادمین دستی باز کرده)
    → {"level": "warning" | "cash_only" | "blocked", "days_overdue": n, "total": مبلغ, "count": n}

    مراحل (آستانه‌ها در تنظیمات باشگاه):
      warning   تا N روز کاری پس از سررسید — فقط هشدار
      cash_only پس از آن تا M روز تقویمی — فقط خرید نقدی
      blocked   پس از آن — ثبت سفارش کاملاً بسته
    """
    try:
        profile = user.profile
    except Exception:
        return None
    if profile.restriction_override:
        return None
    # باز کردن دستی روی طرف حساب لینک‌شده (ثبت حضوری در پنل) هم معتبر است
    if profile.linked_contact_id and profile.linked_contact.restriction_override:
        return None

    lines = user.overdue_settlement_lines()
    if not lines:
        return None

    st = get_club_settings()
    today = timezone.localdate()
    worst = "warning"
    for line in lines:
        from datetime import date as date_cls
        due = date_cls.fromisoformat(line["due_date"]) if isinstance(line["due_date"], str) else line["due_date"]
        warn_end = add_workdays(due, st.overdue_warn_workdays)
        block_date = warn_end + timedelta(days=st.overdue_cash_only_days)
        if today > block_date:
            worst = "blocked"
            break
        if today > warn_end:
            worst = "cash_only"

    return {
        "level": worst,
        "count": len(lines),
        "total": sum(l["remaining"] for l in lines),
        "days_overdue": max(l["days_overdue"] for l in lines),
    }
