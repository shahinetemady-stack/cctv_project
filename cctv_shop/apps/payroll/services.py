"""منطق محاسبه حقوق و دستمزد.

⚠️ قرارداد واحد مبالغ: همه مبالغ این ماژول و کل سامانه «ریال» است —
فیلدهای Payslip/Profile، رکوردها، پورسانت (مبنای آن فاکتورهای فروش ریالی
است) و سند Payment خروجی. هیچ تبدیل تومان↔ریال در این ماژول انجام نمی‌شود.
"""

import calendar
from datetime import date
from decimal import Decimal

from django.db.models import Q, Sum

from .models import (
    BonusPenaltyRecord,
    LeaveRecord,
    Payslip,
    PayslipPayment,
    PayrollProfile,
)


def _month_bounds(year, month):
    last = calendar.monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, last)


def _tier_amount(tiers, value):
    """پلکان پیش‌رونده با بازه و گامِ درصدی. tiers: [{from, to, step, percent}].

    برای هر بازه، بخشی از مقدار که داخل [from, to] است به گام‌های کامل تقسیم
    می‌شود و هر گامِ کامل «درصدی (percent) از مبلغ همان گام» پاداش دارد؛
    باقی‌مانده کمتر از یک گام پاداش ندارد. بازه‌ها تجمیع می‌شوند (پیش‌رونده).
    مثال: بازه‌ها (۰,۶۰B,۱۰B,۰.۵٪)،(۶۰B,۱۰۰B,۱۰B,۰.۷٪) با فروش ۸۰B →
    ۶×(۱۰B×۰.۵٪) + ۲×(۱۰B×۰.۷٪) = ۴۴۰M ریال.
    مقدار فراتر از بزرگ‌ترین «to» همان سقف را می‌گیرد. مقدار ≤ ۰ → ۰.
    """
    if value <= 0:
        return 0
    tiers = sorted((t for t in (tiers or [])
                    if t.get("to") and t.get("step") and t.get("percent")),
                   key=lambda t: float(t.get("from") or 0))
    total = 0.0
    for t in tiers:
        lo = float(t.get("from") or 0)
        hi = float(t["to"])
        step = float(t["step"])
        per = float(t["percent"]) / 100
        if value <= lo:
            break
        portion = min(value, hi) - lo
        if portion > 0:
            total += (portion // step) * (step * per)
        if value <= hi:
            break
    return int(round(total))


def month_sales_total(year, month):
    """مجموع فروش ریالی تسویه‌شده مجموعه در ماه (ریال)."""
    from apps.accounting.models import SaleInvoice

    start, end = _month_bounds(year, month)
    qs = SaleInvoice.objects.filter(
        status=SaleInvoice.Status.PAID,
        currency="IRR",
        issue_date__gte=start,
        issue_date__lte=end,
    ).prefetch_related("items")
    return sum(inv.total_amount for inv in qs)


def month_sales_of_seller(staff, year, month):
    """فروش شخصی یک پرسنل در ماه (ریال).

    فاکتورهایی که seller=پرسنل دارند برای او محسوب می‌شوند؛ برای فاکتورهایی که
    فروشنده ندارند، ثبت‌کننده فاکتور (created_by) محسوب است.
    """
    from apps.accounting.models import SaleInvoice

    start, end = _month_bounds(year, month)
    qs = SaleInvoice.objects.filter(
        Q(seller=staff) | Q(seller__isnull=True, created_by=staff),
        status=SaleInvoice.Status.PAID,
        currency="IRR",
        issue_date__gte=start,
        issue_date__lte=end,
    ).prefetch_related("items")
    return sum(inv.total_amount for inv in qs)


def leave_usage(staff, year, month):
    """مصرف مرخصی یک پرسنل در ماه به تفکیک نوع (روز)."""
    start, end = _month_bounds(year, month)
    agg = LeaveRecord.objects.filter(
        staff=staff, date__gte=start, date__lte=end,
    ).values("leave_type").annotate(total=Sum("days_count"))
    usage = {row["leave_type"]: Decimal(str(row["total"])) for row in agg}
    return {
        "entitled": usage.get(LeaveRecord.LeaveType.ENTITLED, Decimal("0")),
        "sick": usage.get(LeaveRecord.LeaveType.SICK, Decimal("0")),
        "unpaid": usage.get(LeaveRecord.LeaveType.UNPAID, Decimal("0")),
    }


def annual_bonus_amount(profile, year, month):
    """عیدی/پاداش پایان سال.

    فقط در ماه آخر سال (دسامبر ≈ اسفند) محاسبه می‌شود تا در فیش ماهانه دوبار
    پرداخت نشود. فرمول: حقوق پایه × مبنای عیدی × ماه‌های کارکرد ÷ ۱۲
    ماه‌های کارکرد از تاریخ عضویت تا پایین سال. در فرمول قانون کار نتیجه
    به حداکثر ۳ ماه حقوق پایه سقف می‌خورد؛ در فرمول توافقی سقف ندارد.
    """
    if not profile.has_annual_bonus or month != 12:
        return 0
    joined = profile.staff.date_joined
    if joined is None or joined.year > year:
        return 0
    months_worked = (year - joined.year) * 12 + (12 - joined.month) + 1
    months_worked = max(0, min(12, months_worked))
    if months_worked == 0:
        return 0
    bonus = Decimal(str(profile.base_amount)) * profile.annual_bonus_months \
        * Decimal(months_worked) / Decimal(12)
    if profile.annual_bonus_formula == "legal":
        bonus = min(bonus, Decimal(str(profile.base_amount)) * Decimal(3))
    return int(round(float(bonus)))


def recalculate_payslip(payslip):
    """بازمحاسبه ایدمپوتنت فیش بر اساس ماژول‌های فعال پروفایل پرسنل."""
    profile = getattr(payslip.staff, "payroll_profile", None)
    if not profile or not profile.is_active:
        for field in ("base_amount", "personal_commission_amount", "total_sales_share_amount",
                      "bonus_penalty_amount", "annual_bonus_amount", "leave_deduction",
                      "gross_amount", "net_amount"):
            setattr(payslip, field, 0)
        payslip.save()
        return payslip

    start, end = _month_bounds(payslip.year, payslip.month)

    # حقوق ثابت
    payslip.base_amount = profile.base_amount if profile.has_base_salary else 0

    # پورسانت فروش شخصی — پلکان پیش‌رونده با بازه روی فروش شخصی ماه
    personal_sales = month_sales_of_seller(payslip.staff, payslip.year, payslip.month) \
        if profile.has_commission_personal else 0
    payslip.personal_sales = personal_sales
    payslip.personal_commission_amount = \
        _tier_amount(profile.personal_commission_tiers, personal_sales) \
        if profile.has_commission_personal else 0

    # سهم فروش کل مجموعه — پلکان پیش‌رونده با بازه روی فروش کل ماه
    if profile.has_commission_total:
        total_sales = month_sales_total(payslip.year, payslip.month)
        share = _tier_amount(profile.total_share_tiers, total_sales)
    else:
        total_sales = 0
        share = 0
    payslip.total_sales = total_sales
    payslip.total_sales_share_amount = share

    # تشویقی/تنبیه دستی (جمع رکوردهای ماه)
    if profile.has_bonus_penalty:
        s = BonusPenaltyRecord.objects.filter(
            staff=payslip.staff, date__gte=start, date__lte=end,
        ).aggregate(total=Sum("amount"))["total"]
        payslip.bonus_penalty_amount = int(s) if s else 0
    else:
        payslip.bonus_penalty_amount = 0

    # مرخصی
    payslip.entitled_used = payslip.sick_used = payslip.unpaid_used = 0
    payslip.leave_deduction = 0
    if profile.has_leave_management:
        usage = leave_usage(payslip.staff, payslip.year, payslip.month)
        payslip.entitled_used = usage["entitled"]
        payslip.sick_used = usage["sick"]
        payslip.unpaid_used = usage["unpaid"]
        # مازاد استعلاجی از سقف ماهانه هم بدون حقوق محسوب می‌شود
        sick_excess = max(Decimal("0"), usage["sick"] - profile.leave_sick_days_per_month)
        unpaid_days = usage["unpaid"] + sick_excess
        daily = Decimal(str(profile.base_amount)) / Decimal(profile.working_days_divisor) \
            if profile.working_days_divisor else Decimal("0")
        payslip.leave_deduction = int(round(float(unpaid_days * daily))) \
            if profile.has_base_salary else 0

    # عیدی
    payslip.annual_bonus_amount = annual_bonus_amount(profile, payslip.year, payslip.month)

    payslip.gross_amount = (payslip.base_amount + payslip.personal_commission_amount
                            + payslip.total_sales_share_amount
                            + payslip.bonus_penalty_amount + payslip.annual_bonus_amount)
    payslip.net_amount = payslip.gross_amount - payslip.leave_deduction
    payslip.save()
    return payslip


def generate_month(year, month, actor=None):
    """ساخت/بازمحاسبه فیش همه پرسنل فعال برای یک ماه (ایدمپوتنت).

    فیش‌های «پرداخت شده» دست‌نخورده می‌مانند.
    """
    created = updated = skipped = 0
    profiles = PayrollProfile.objects.filter(is_active=True).select_related("staff")
    for profile in profiles:
        payslip, was_created = Payslip.objects.get_or_create(
            staff=profile.staff, year=year, month=month,
        )
        if payslip.status == Payslip.Status.PAID:
            skipped += 1
            continue
        recalculate_payslip(payslip)
        created += 1 if was_created else 0
        updated += 0 if was_created else 1
    return {"created": created, "updated": updated, "skipped": skipped}


def _staff_contact(staff):
    """طرف‌حساب کارمند — از لینک پروفایل یا ساخت خودکار (نوع کارمند).

    پس از یافتن/ساخت، لینک در UserProfile.linked_contact ذخیره می‌شود تا
    تشخیص پرسنل از روی طرف‌حساب در همه جا (مثل صفحه دریافت و پرداخت) قطعی باشد.
    """
    from apps.accounting.models import Contact

    profile = getattr(staff, "profile", None)
    if profile and profile.linked_contact_id:
        return profile.linked_contact
    contact = Contact.objects.filter(
        contact_type=Contact.ContactType.STAFF, name=staff.get_full_name() or staff.phone,
    ).first()
    if not contact:
        contact = Contact.objects.create(
            contact_type=Contact.ContactType.STAFF,
            name=staff.get_full_name() or staff.phone,
            phone=staff.phone or "",
            currency=Contact.Currency.IRR,
        )
    if profile and not profile.linked_contact_id:
        profile.linked_contact = contact
        profile.save(update_fields=["linked_contact"])
    return contact


def book_accrual(payslip, actor=None):
    """ثبت سند هزینه/بدهی حقوق آخر ماه — پرسنل بستانکار (طلبکار) می‌شود.

    در مدل مانده طرف‌حساب: سند جهتِ in (دریافت) ⇒ تراز منفی ⇒ «ما بدهکاریم».
    پرداخت‌های بعدی جهت out ⇒ بدهی کم می‌شود. سند فقط یکبار ساخته می‌شود و
    با بازمحاسبه فیش، مبلغش به‌روز می‌ماند.
    """
    from apps.accounting.models import Payment

    contact = _staff_contact(payslip.staff)
    last_day = date(payslip.year, payslip.month,
                    calendar.monthrange(payslip.year, payslip.month)[1])
    note = (f"سند هزینه حقوق {payslip.year}/{payslip.month:02d} — "
            f"{payslip.staff.get_full_name() or payslip.staff.phone} "
            f"(بدهی به پرسنل، پرداخت در اقساط)")

    if payslip.accrual_payment_id:
        acc = payslip.accrual_payment
        if acc.amount != Decimal(payslip.net_amount):
            acc.amount = Decimal(payslip.net_amount)
            acc.note = note
            acc.save(update_fields=["amount", "note"])
        return acc

    acc = Payment.objects.create(
        contact=contact,
        direction=Payment.Direction.IN,
        payment_type=Payment.PaymentType.OTHER,
        currency="IRR",
        amount=Decimal(payslip.net_amount),
        rate_irr=1,
        date=last_day,
        reference=f"حقوق {payslip.year}/{payslip.month:02d}",
        note=note,
        created_by=actor,
    )
    payslip.accrual_payment = acc
    payslip.status = Payslip.Status.CONFIRMED
    payslip.save(update_fields=["accrual_payment", "status"])
    return acc


def accrue_month(year, month, actor=None):
    """صدور سند هزینه/بدهی برای همه فیش‌های پرداخت‌نشده یک ماه."""
    booked = 0
    for slip in Payslip.objects.filter(year=year, month=month).exclude(
            status=Payslip.Status.PAID):
        book_accrual(slip, actor=actor)
        booked += 1
    return booked


def pay_payslip(payslip, account, date, actor=None, amount=None):
    """پرداخت حقوق (کامل یا قسطی) — کسر از بدهی پرسنل و خروج از حساب بانکی.

    هر قسط یک سند Payment جهت out با طرف‌حساب کارمند است (کاهش بدهی) و به
    فیش لینک می‌شود؛ وقتی مجموع اقساط به خالص رسید فیش paid می‌شود.
    """
    from apps.accounting.models import Payment

    if payslip.status == Payslip.Status.PAID:
        raise ValueError("این فیش قبلاً به‌طور کامل پرداخت شده است.")
    if payslip.status != Payslip.Status.CONFIRMED:
        raise ValueError("فیش باید ابتدا تأیید شود.")

    remaining = payslip.remaining_amount
    pay_amount = min(int(amount or remaining), remaining)
    if pay_amount <= 0:
        raise ValueError("مبلغ پرداخت نامعتبر است.")

    contact = _staff_contact(payslip.staff)
    payment = Payment.objects.create(
        contact=contact,
        from_account=account,
        direction=Payment.Direction.OUT,
        payment_type=Payment.PaymentType.TRANSFER,
        currency="IRR",
        amount=Decimal(pay_amount),  # مبالغ فیش و Payment هر دو ریال‌اند
        rate_irr=1,
        date=date,
        reference=f"پرداخت حقوق {payslip.year}/{payslip.month:02d}",
        note=f"پرداخت حقوق {payslip.staff.get_full_name() or payslip.staff.phone} — "
             f"قسط {payslip.installments.count() + 1} از فیش {payslip.net_amount:,} ریال",
        created_by=actor,
    )
    PayslipPayment.objects.create(payslip=payslip, payment=payment, amount=pay_amount)
    payslip.paid_amount += pay_amount
    if payslip.paid_amount >= payslip.net_amount:
        payslip.status = Payslip.Status.PAID
        payslip.payment = payment  # آخرین سند، برای نمایش
    payslip.save(update_fields=["paid_amount", "status", "payment"])
    return payment


def user_for_contact(contact):
    """کاربر پرسنلِ متناظر یک طرف‌حساب — از لینک پروفایل یا تطبیق شماره موبایل."""
    from apps.users.models import User, UserProfile

    prof = UserProfile.objects.filter(linked_contact=contact).select_related("user").first()
    if prof:
        return prof.user
    if contact.phone:
        user = User.objects.filter(phone=contact.phone, is_staff=True).first()
        if user:
            return user
    # فالبک: تطبیق نام با پرسنل
    return User.objects.filter(is_staff=True).extra(
        where=["(first_name || ' ' || last_name) = %s"], params=[contact.name],
    ).first() or None


def open_payslips_for_contact(contact):
    """فیش‌های باز (تأییدشده با مانده > ۰) کارمندِ متناظر یک طرف‌حساب."""
    user = user_for_contact(contact)
    if not user:
        return []
    return Payslip.objects.filter(
        staff=user, status=Payslip.Status.CONFIRMED,
    ).order_by("-year", "-month")


def allocate_payment_to_payslip(payment, payslip_id):
    """لینک یک سند پرداختِ ثبت‌شده (در صفحه دریافت و پرداخت) به فیش حقوقی.

    مبلغ سند نباید از مانده فیش بیشتر باشد؛ پس از تخصیص، paid_amount به‌روز و
    در صورت تکمیل، فیش paid می‌شود.
    """
    from apps.accounting.models import Payment

    if payment.direction != Payment.Direction.OUT or payment.currency != "IRR":
        raise ValueError("پرداخت حقوق باید سند ریالی «پرداختی» باشد")
    slip = Payslip.objects.filter(pk=payslip_id).first()
    if not slip:
        raise ValueError("فیش حقوقی یافت نشد")
    if slip.status == Payslip.Status.PAID:
        raise ValueError("این فیش قبلاً به‌طور کامل پرداخت شده است")
    pay_amount = int(payment.amount)
    if pay_amount <= 0:
        raise ValueError("مبلغ سند نامعتبر است")
    if pay_amount > slip.remaining_amount:
        raise ValueError(
            f"مبلغ سند ({pay_amount:,} ریال) از مانده فیش ({slip.remaining_amount:,} ریال) بیشتر است")

    PayslipPayment.objects.create(payslip=slip, payment=payment, amount=pay_amount)
    slip.paid_amount += pay_amount
    if slip.paid_amount >= slip.net_amount:
        slip.status = Payslip.Status.PAID
        slip.payment = payment
    slip.save(update_fields=["paid_amount", "status", "payment"])
    payment.note = (payment.note + " — " if payment.note else "") + \
        f"پرداخت حقوق فیش {slip.year}/{slip.month:02d}"
    payment.save(update_fields=["note"])
    return slip
