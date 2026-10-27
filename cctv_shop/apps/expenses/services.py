"""منطق ماژول هزینه‌ها — سند بدهی، پرداخت قسطی و سود روزشمار مشارکت.

قرارداد مانده (مثل حقوق): سند جهت in ⇒ تراز طرف‌حساب منفی ⇒ «ما بدهکاریم»
(طرف بستانکار/طلبکار). پرداخت جهت out از حساب بانکی ⇒ بدهی کم و پول خارج می‌شود.
مبالغ همه ریال.
"""

import calendar
from datetime import date, timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import F, Sum

from apps.accounting.models import Payment

from .models import (
    ExpenseCharge,
    ExpenseChargePayment,
    ExpenseCategory,
    Investor,
    InvestorMovement,
    RecurringExpense,
)


def _month_bounds(year, month):
    last = calendar.monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, last)


@transaction.atomic
def book_charge_accrual(charge, actor=None):
    """ثبت سند هزینه/بدهی یک هزینه ماهانه (یک‌بار؛ با تغییر مبلغ به‌روز می‌شود)."""
    from apps.accounting.models import Payment

    charge = ExpenseCharge.objects.select_for_update().get(pk=charge.pk)
    if charge.amount < 0:
        raise ValueError("مبلغ هزینه نمی‌تواند منفی باشد")
    if charge.amount == 0 and not charge.accrual_payment_id:
        charge.status = ExpenseCharge.Status.DRAFT
        charge.save(update_fields=["status", "updated_at"])
        return None
    contact = charge.contact
    note = f"سند هزینه {charge.title} — {charge.year}/{charge.month:02d}"

    if charge.accrual_payment_id:
        acc = charge.accrual_payment
        if int(acc.amount) != charge.amount:
            acc.amount = Decimal(charge.amount)
            acc.note = note
            acc.save(update_fields=["amount", "note"])
        return acc

    last_day = date(charge.year, charge.month,
                    calendar.monthrange(charge.year, charge.month)[1])
    acc = Payment.objects.create(
        contact=contact,
        direction=Payment.Direction.IN,
        payment_type=Payment.PaymentType.OTHER,
        currency="IRR",
        amount=Decimal(charge.amount),
        rate_irr=1,
        date=last_day,
        reference=f"هزینه {charge.year}/{charge.month:02d}",
        note=note,
        created_by=actor,
    )
    charge.accrual_payment = acc
    charge.status = ExpenseCharge.Status.CONFIRMED
    charge.save(update_fields=["accrual_payment", "status"])
    return acc


@transaction.atomic
def pay_charge(charge, account, date_, actor=None, amount=None):
    """پرداخت هزینه (کامل یا قسطی) — کسر از بدهی و خروج از حساب بانکی."""
    from apps.accounting.models import Payment

    charge = ExpenseCharge.objects.select_for_update().get(pk=charge.pk)
    if charge.status == ExpenseCharge.Status.PAID:
        raise ValueError("این هزینه قبلاً به‌طور کامل پرداخت شده است.")
    if charge.status != ExpenseCharge.Status.CONFIRMED or not charge.accrual_payment_id:
        raise ValueError("ابتدا سند هزینه/بدهی باید صادر شود.")
    if account is None or not account.is_active or account.currency != "IRR":
        raise ValueError("پرداخت هزینه فقط از حساب ریالی فعال انجام می‌شود")
    recorded = charge.installments.aggregate(total=Sum("amount"))["total"] or 0
    charge.paid_amount = recorded
    remaining = max(0, charge.amount - recorded)
    requested = remaining if amount is None else int(amount)
    pay_amount = min(requested, remaining)
    if pay_amount <= 0:
        raise ValueError("مبلغ پرداخت نامعتبر است.")

    payment = Payment.objects.create(
        contact=charge.contact,
        from_account=account,
        direction=Payment.Direction.OUT,
        payment_type=Payment.PaymentType.TRANSFER,
        currency="IRR",
        amount=Decimal(pay_amount),
        rate_irr=1,
        date=date_,
        reference=f"پرداخت هزینه {charge.year}/{charge.month:02d}",
        note=f"پرداخت «{charge.title}» — قسط {charge.installments.count() + 1}",
        created_by=actor,
    )
    ExpenseChargePayment.objects.create(charge=charge, payment=payment, amount=pay_amount)
    charge.paid_amount = recorded + pay_amount
    if charge.paid_amount >= charge.amount:
        charge.status = ExpenseCharge.Status.PAID
        charge.payment = payment
    charge.save(update_fields=["paid_amount", "status", "payment", "updated_at"])
    return payment


# ───────────────────────────── سود مشارکت ─────────────────────────────

def investor_profit_for_month(investor, year, month):
    """سود روزشمار یک ماه: برای هر روز، مانده اصل پایان آن روز × نرخ ÷ ۳۶۵.

    گردش همان روز از ابتدای آن روز معتبر است. مبالغ به ریال.
    """
    start, end = _month_bounds(year, month)
    signed = 0
    for m in InvestorMovement.objects.filter(investor=investor, date__lt=start):
        signed += m.signed_amount

    moves = {}
    for m in InvestorMovement.objects.filter(investor=investor, date__gte=start, date__lte=end):
        moves.setdefault(m.date, 0)
        moves[m.date] += m.signed_amount

    rate = Decimal(str(investor.annual_rate)) / Decimal(100)
    balance = Decimal(signed)
    profit = Decimal(0)
    day = start
    while day <= end:
        balance += Decimal(moves.get(day, 0))
        profit += balance * rate / Decimal(365)
        day += timedelta(days=1)
    return int(round(float(profit)))


def accrue_month(year, month, actor=None):
    """صدور سند هزینه سر ماه برای ماه داده‌شده:

    ۱) هزینه‌های تکرارشونده فعال → ساخت/به‌روز فیش + سند بدهی
    ۲) سرمایه‌گذاران فعال → محاسبه سود روزشمار + فیش + سند بدهی
    """
    booked = {"recurring": 0, "investor": 0}

    for rec in RecurringExpense.objects.filter(is_active=True).select_related("category"):
        if (year, month) < (rec.start_date.year, rec.start_date.month):
            continue
        last_day = date(year, month, calendar.monthrange(year, month)[1])
        charge, _ = ExpenseCharge.objects.get_or_create(
            source=ExpenseCharge.Source.RECURRING, recurring=rec,
            year=year, month=month,
            defaults={
                "title": rec.title, "category": rec.category,
                "contact": rec.contact, "amount": rec.monthly_amount,
                "date": last_day,
            },
        )
        if charge.title != rec.title:
            charge.title = rec.title
            charge.save(update_fields=["title", "updated_at"])
        if charge.status != ExpenseCharge.Status.PAID:
            if charge.amount != rec.monthly_amount:
                charge.amount = rec.monthly_amount
                charge.save(update_fields=["amount", "updated_at"])
            book_charge_accrual(charge, actor=actor)
            booked["recurring"] += 1

    for inv in Investor.objects.filter(is_active=True).select_related("contact"):
        profit = investor_profit_for_month(inv, year, month)
        last_day = date(year, month, calendar.monthrange(year, month)[1])
        charge, created = ExpenseCharge.objects.get_or_create(
            source=ExpenseCharge.Source.INVESTOR, investor=inv,
            year=year, month=month,
            defaults={
                "title": f"سود مشارکت {inv.contact.name}",
                "contact": inv.contact, "amount": profit,
                "date": last_day,
            },
        )
        if not created and charge.status != ExpenseCharge.Status.PAID:
            charge.amount = profit
            charge.save(update_fields=["amount", "updated_at"])
        if charge.status != ExpenseCharge.Status.PAID and (profit > 0 or charge.accrual_payment_id):
            book_charge_accrual(charge, actor=actor)
            booked["investor"] += 1

    return booked


def investor_principal_at(investor, at_date):
    """اصل سرمایه در یک تاریخ (پایان آن روز)."""
    signed = 0
    for m in InvestorMovement.objects.filter(investor=investor, date__lte=at_date):
        signed += m.signed_amount
    return signed


def open_charges_for_contact(contact):
    """هزینه‌های باز (تأییدشده با مانده > ۰) متعلق به یک طرف‌حساب."""
    return ExpenseCharge.objects.filter(
        contact=contact, status=ExpenseCharge.Status.CONFIRMED,
        paid_amount__lt=F("amount"), accrual_payment__isnull=False,
    ).order_by("-year", "-month")


@transaction.atomic
def allocate_payment_to_charge(payment, charge_id):
    """لینک سند پرداخت به هزینه همان طرف‌حساب و با سند بدهی معتبر."""
    from apps.accounting.models import Payment

    if payment.direction != Payment.Direction.OUT or payment.currency != "IRR":
        raise ValueError("پرداخت هزینه باید سند ریالی «پرداختی» باشد")
    charge = ExpenseCharge.objects.select_for_update().filter(pk=charge_id).first()
    if not charge:
        raise ValueError("هزینه یافت نشد")
    if charge.status != ExpenseCharge.Status.CONFIRMED or not charge.accrual_payment_id:
        raise ValueError("هزینه باید تأیید شده و سند بدهی داشته باشد")
    if payment.contact_id != charge.contact_id:
        raise ValueError("طرف حساب سند با هزینه ناسازگار است")
    pay_amount = int(payment.amount)
    if pay_amount <= 0:
        raise ValueError("مبلغ سند نامعتبر است")
    recorded = charge.installments.aggregate(total=Sum("amount"))["total"] or 0
    remaining = max(0, charge.amount - recorded)
    if pay_amount > remaining:
        raise ValueError(
            f"مبلغ سند ({pay_amount:,} ریال) از مانده هزینه ({remaining:,} ریال) بیشتر است")

    ExpenseChargePayment.objects.create(charge=charge, payment=payment, amount=pay_amount)
    charge.paid_amount = recorded + pay_amount
    if charge.paid_amount >= charge.amount:
        charge.status = ExpenseCharge.Status.PAID
        charge.payment = payment
    charge.save(update_fields=["paid_amount", "status", "payment", "updated_at"])
    payment.note = (payment.note + " — " if payment.note else "") + \
        f"پرداخت هزینه «{charge.title}» {charge.year}/{charge.month:02d}"
    payment.save(update_fields=["note"])
    return charge


@transaction.atomic
def reverse_payment_from_charge(payment):
    installment = ExpenseChargePayment.objects.select_related("charge").filter(payment=payment).first()
    if not installment:
        return False
    charge = ExpenseCharge.objects.select_for_update().get(pk=installment.charge_id)
    installment.delete()
    installments = charge.installments.select_related("payment").order_by("id")
    charge.paid_amount = sum(item.amount for item in installments)
    charge.status = ExpenseCharge.Status.CONFIRMED if charge.accrual_payment_id else ExpenseCharge.Status.DRAFT
    last = installments.last()
    charge.payment = last.payment if last else None
    charge.save(update_fields=["paid_amount", "status", "payment", "updated_at"])
    return True


@transaction.atomic
def reverse_charge_accrual(payment):
    charge = ExpenseCharge.objects.filter(accrual_payment=payment).first()
    if not charge:
        return False
    if charge.installments.exists():
        raise ValueError("برای برگشت سند بدهی هزینه، ابتدا اقساط را برگشت بزنید")
    charge = ExpenseCharge.objects.select_for_update().get(pk=charge.pk)
    charge.accrual_payment = None
    charge.status = ExpenseCharge.Status.DRAFT
    charge.paid_amount = 0
    charge.payment = None
    charge.save(update_fields=["accrual_payment", "status", "paid_amount", "payment", "updated_at"])
    return True


@transaction.atomic
def create_paid_charge_from_payment(payment, category_id, title=None):
    """ثبت یکجای هزینه متفرقه هنگام پرداخت (از صفحه دریافت و پرداخت).

    هزینه با همان مبلغ/تاریخ/طرف‌حساب سند ساخته و بلافاصله «پرداخت شده»
    لحاظ می‌شود (بدون سند بدهی جدا — چون پول همان لحظه خارج شده) و در
    کارت سر فصل و صفحه هزینه‌ها قابل ردیابی است.
    """
    from apps.accounting.models import Payment

    if payment.direction != Payment.Direction.OUT or payment.currency != "IRR":
        raise ValueError("ثبت هزینه فقط روی سند ریالی «پرداختی» ممکن است")
    cat = ExpenseCategory.objects.filter(
        pk=category_id, category_type=ExpenseCategory.CategoryType.GENERAL).first()
    if not cat:
        raise ValueError("سر فصل هزینه نامعتبر است")
    amount = int(payment.amount)
    if amount <= 0:
        raise ValueError("مبلغ سند نامعتبر است")

    # صفحه پرداخت‌ها تاریخ را رشته ISO می‌فرستد؛ مدل هنگام خواندن به date تبدیل
    # می‌کند ولی شیء حافظه‌ای همان رشته می‌ماند — اینجا مطمئن تبدیل می‌کنیم
    pay_date = payment.date
    if isinstance(pay_date, str):
        pay_date = date.fromisoformat(pay_date)
    charge = ExpenseCharge.objects.create(
        source=ExpenseCharge.Source.GENERAL,
        title=(title or "").strip() or cat.name,
        category=cat,
        contact=payment.contact,
        year=pay_date.year, month=pay_date.month,
        date=pay_date,
        amount=amount, status=ExpenseCharge.Status.PAID,
        paid_amount=amount, payment=payment,
    )
    ExpenseChargePayment.objects.create(charge=charge, payment=payment, amount=amount)
    payment.note = (payment.note + " — " if payment.note else "") + f"هزینه {cat.name}"
    payment.save(update_fields=["note"])
    return charge


def reverse_charge(charge, actor=None):
    """لغو اصولی یک هزینه ثبت‌شده — بدون حذف سندهای حسابداری.

    برای هر سند مرتبط (بدهی accrual + همه پرداخت‌ها) سند معکوس ثبت می‌شود
    (الگوی برگشت سند حسابداری — reversal_of) تا مانده‌ها اصلاح شوند و سابقه
    بماند؛ سپس خود رکورد هزینه و لینک‌های پرداخت حذف می‌شوند.
    سند برگشت‌خورده قابل لغو مجدد نیست.
    """
    from django.utils import timezone
    from .models import ExpenseChargePayment

    payments = [p for p in [charge.accrual_payment, charge.payment] if p]
    payments += [inst.payment for inst in charge.installments.select_related("payment")]
    seen = set()
    for t in payments:
        if t.id in seen:
            continue
        seen.add(t.id)
        if t.reversal_of_id:
            continue
        if t.reversals.exists():
            continue  # قبلاً برگشت خورده — اثرش صفر است
        Payment.objects.create(
            contact_id=t.contact_id,
            invoice_id=t.invoice_id,
            direction="in" if t.direction == "out" else "out",
            from_account_id=t.to_account_id,
            to_account_id=t.from_account_id,
            payment_type=t.payment_type,
            currency=t.currency,
            amount=t.amount,
            rate_irr=t.rate_irr,
            date=timezone.localdate(),
            reference=t.reference,
            note=f"برگشت سند #{t.id} مورخ {t.date}" + (f" — {t.note}" if t.note else ""),
            reversal_of=t,
            created_by=actor,
        )
    ExpenseChargePayment.objects.filter(charge=charge).delete()
    title = charge.title
    charge.delete()
    return title
