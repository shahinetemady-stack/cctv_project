"""
apps/accounting/services.py
───────────────────────────
محاسبه بدهی و کنترل سقف اعتبار مشتریان + تخصیص خودکار وجه دریافتی.

بدهی = مانده فاکتورهای فروش باز (حساب باز، اعتباری، چک وصول‌نشده — هر بدهی ثبت‌شده)
     + مانده اول دوره مثبت (بدهی منتقل‌شده)
همه مقادیر ریال است.

settle_customer_fifo — تخصیص وجه دریافتی مشتری به فاکتورهای باز او به ترتیب
«موعد مؤثر» (FIFO): فاکتور سررسیدگذشته همیشه اول؛ فاکتور نقدی وقتی بدهی
سررسیدگذشته‌ای نیست اول می‌آید (موعدش فوری است) و سرریز به قدیمی‌ترین می‌رود.
"""

import logging
from decimal import Decimal

from django.db import transaction
from django.db.models import Q, Sum
from django.utils import timezone

logger = logging.getLogger(__name__)


def _profile_and_contact(user):
    profile = getattr(user, "profile", None)
    contact = getattr(profile, "linked_contact", None) if profile else None
    return profile, contact


def opening_balance(user, currency="IRR"):
    """مانده اول دورهٔ اصلی؛ برای کاربر لینک‌شده Contact مرجع است."""
    profile, contact = _profile_and_contact(user)
    source = contact if contact is not None else profile
    if source is None:
        return 0 if currency == "IRR" else Decimal("0")
    field = "opening_balance_irr" if currency == "IRR" else "opening_balance_cny"
    value = getattr(source, field, 0) or 0
    return int(value) if currency == "IRR" else Decimal(str(value))


def opening_remaining(user, currency="IRR"):
    """مانده اول دوره پس از اسناد صریح تسویه/مصرف مانده اول دوره."""
    from .models import Payment

    _, contact = _profile_and_contact(user)
    qs = Payment.objects.filter(settlement_target=Payment.SettlementTarget.OPENING,
                                currency=currency)
    if contact is not None:
        qs = qs.filter(contact=contact)
    else:
        qs = qs.filter(opening_user=user)
    totals = qs.aggregate(
        incoming=Sum("amount", filter=Q(direction="in")),
        outgoing=Sum("amount", filter=Q(direction="out")),
    )
    remaining = Decimal(str(opening_balance(user, currency)))
    remaining += Decimal(str(totals["outgoing"] or 0))
    remaining -= Decimal(str(totals["incoming"] or 0))
    return int(remaining) if currency == "IRR" else remaining


def opening_remaining_irr(user):
    return opening_remaining(user, "IRR")


def opening_remaining_cny(user):
    return opening_remaining(user, "CNY")


def contact_operational_balance(contact, currency="IRR"):
    """اثر اسناد طرف حساب، جدا از مانده اول دوره و تسویه‌های صریح آن."""
    from .models import Payment

    if contact is None:
        return 0 if currency == "IRR" else Decimal("0")
    qs = contact.payments.filter(currency=currency).exclude(
        settlement_target=Payment.SettlementTarget.OPENING)
    incoming = qs.filter(direction="in").aggregate(s=Sum("amount"))["s"] or 0
    outgoing = qs.filter(direction="out").aggregate(s=Sum("amount"))["s"] or 0
    value = Decimal(str(outgoing)) - Decimal(str(incoming))
    return int(value) if currency == "IRR" else value


def customer_balance(user, currency="IRR"):
    """مانده علامت‌دار مشتری؛ مثبت بدهی مشتری و منفی بستانکاری اوست."""
    from .models import SaleInvoice

    profile, contact = _profile_and_contact(user)
    balance = Decimal(str(opening_remaining(user, currency)))
    balance += Decimal(str(contact_operational_balance(contact, currency)))
    invoices = SaleInvoice.objects.filter(
        customer=user, currency=currency, status__in=["confirmed", "paid"],
    )
    for inv in invoices:
        balance += Decimal(str(inv.remaining_amount))
    if currency == "IRR":
        balance -= Decimal(str(sale_overpayment_irr(user)))
        balance -= Decimal(str(profile.payment_credit_irr or 0)) if profile else Decimal(0)
        return int(balance)
    return balance


def customer_balance_irr(user):
    return customer_balance(user, "IRR")


def customer_balance_cny(user):
    return customer_balance(user, "CNY")


def available_customer_credit_irr(user) -> int:
    """ذخایر بستانکاری قابل مصرف؛ بدهی‌های باز این ذخایر را کم نمی‌کنند."""
    profile, contact = _profile_and_contact(user)
    credit = max(0, -opening_remaining_irr(user))
    credit += max(0, -int(contact_operational_balance(contact, "IRR")))
    credit += sale_overpayment_irr(user)
    if profile:
        credit += int(profile.payment_credit_irr or 0)
    return int(credit)


def total_debt_irr(user) -> int:
    """مجموع بدهی ریالی کاربر — مانده فاکتورهای باز + مانده اول دوره مثبت."""
    return max(0, customer_balance_irr(user))


def open_invoice_debt_irr(user) -> int:
    """مجموع مانده فاکتورهای فروش باز (ریالی، تأییدشده) کاربر — بدون مانده اول دوره."""
    from .models import SaleInvoice

    debt = 0
    qs = SaleInvoice.objects.filter(
        customer=user, status=SaleInvoice.Status.CONFIRMED, currency="IRR",
    )
    for inv in qs:
        if inv.remaining_amount > 0:
            debt += inv.remaining_amount
    return debt


def credit_limit_of(user) -> int:
    """سقف اعتبار کاربر (ریال) — از پروفایل، یا از طرف حساب لینک‌شده. ۰ = نامحدود."""
    profile = getattr(user, "profile", None)
    if profile is None:
        return 0
    if profile.credit_limit:
        return int(profile.credit_limit)
    linked = getattr(profile, "linked_contact", None)
    if linked is not None and linked.credit_limit_irr:
        return int(linked.credit_limit_irr)
    return 0


# انواع تسویه غیرنقدی — برای سطح پلاتینیوم بدون سقف اعتبار همه مسدودند
CREDIT_SETTLEMENTS = {"credit", "month1", "month2"}


def check_credit_limit(user, new_credit_amount: int, settlement: str = "credit"):
    """کنترل سقف اعتبار پیش از فروش غیرنقدی؛ None یعنی مجاز است."""
    if new_credit_amount <= 0:
        return None
    limit = credit_limit_of(user)
    profile = getattr(user, "profile", None)
    tier = (profile.partner_tier or "") if profile is not None else ""
    if settlement in CREDIT_SETTLEMENTS and tier == "platinum" and not limit:
        return (
            "این همکار در سطح پلاتینیوم است و هنوز سقف اعتبار ندارد؛ "
            "صدور فاکتور توحسابی/یکماهه/دوماهه برای او تا تعیین سقف اعتبار ممکن نیست. "
            "ابتدا از «طرف حساب‌ها ← ویرایش» سقف اعتبار او را تعیین کنید."
        )
    if not limit:
        return None
    debt = total_debt_irr(user)
    if debt + new_credit_amount > limit:
        return (
            f"مجموع بدهی فعلی مشتری ({debt:,} ریال) + این فروش اعتباری ({new_credit_amount:,} ریال) "
            f"از سقف اعتبار او ({limit:,} ریال) بیشتر می‌شود. "
            f"ابتدا بدهی تسویه شود یا سقف اعتبار از کارت طرف حساب افزایش یابد."
        )
    return None


# ─── تخصیص خودکار وجه دریافتی (FIFO بر اساس موعد مؤثر) ────────────────────────

def _effective_due(invoice):
    """موعد مؤثر فاکتور برای ترتیب FIFO تخصیص وجه."""
    from apps.orders.models import settlement_due_for

    dues = [
        line.due_date for line in invoice.settlement_lines.all()
        if line.is_active and line.remaining_amount > 0
    ]
    if dues:
        return min(dues)
    if invoice.due_date:
        return invoice.due_date
    return settlement_due_for(invoice.settlement, invoice.issue_date)


def _lock_invoice(invoice):
    from .models import SaleInvoice

    pk = invoice.pk if hasattr(invoice, "pk") else invoice
    return SaleInvoice.objects.select_for_update().select_related("customer", "order").get(pk=pk)


def recompute_invoice_status(invoice):
    """هم‌ترازسازی وضعیت یک فاکتور و سفارش لینک‌شده با تخصیص‌های واقعی."""
    from .models import SaleInvoice

    inv = invoice
    if inv.status != SaleInvoice.Status.CANCELLED:
        active_lines = list(inv.settlement_lines.filter(is_active=True))
        for line in active_lines:
            if line.paid_amount > line.amount:
                raise ValueError(f"تخصیص ردیف تسویه فاکتور {inv.invoice_number} از مبلغ آن بیشتر است")
        if active_lines and sum(line.amount for line in active_lines) != inv.total_amount:
            raise ValueError(f"جمع ردیف‌های تسویه فاکتور {inv.invoice_number} با مبلغ کل آن ناسازگار است")
        if inv.total_amount < 0:
            raise ValueError("مبلغ کل فاکتور نمی‌تواند منفی باشد")
        if inv.paid_amount > inv.total_amount:
            raise ValueError(f"تخصیص‌های فاکتور {inv.invoice_number} از مبلغ کل آن بیشتر است")

    remaining = inv.remaining_amount
    if remaining > 0 and inv.status == SaleInvoice.Status.PAID:
        inv.status = SaleInvoice.Status.CONFIRMED
        inv.save(update_fields=["status", "updated_at"])
    elif remaining == 0 and inv.status == SaleInvoice.Status.CONFIRMED:
        inv.status = SaleInvoice.Status.PAID
        inv.save(update_fields=["status", "updated_at"])
    elif remaining < 0 and inv.status != SaleInvoice.Status.CANCELLED:
        raise ValueError("مانده فاکتور نمی‌تواند منفی باشد")

    order = getattr(inv, "order", None)
    if order is not None and order.status not in ("cancelled", "refunded", "rejected"):
        update_fields = ["paid_amount", "payment_method", "paid_at", "updated_at"]
        order.paid_amount = max(0, inv.paid_amount)
        latest = inv.sale_payments.filter(
            allocations__settlement_line__invoice=inv,
        ).order_by("-date", "-id").first()
        if latest:
            order.payment_method = {"cheque": "check", "card": "transfer"}.get(
                latest.method, latest.method,
            )
        elif not order.paid_amount:
            order.payment_method = ""
        if inv.status == SaleInvoice.Status.PAID:
            if not order.paid_at:
                order.paid_at = timezone.now()
            if order.status in ("awaiting_payment", "confirmed"):
                order.status = order.Status.PAID
                update_fields.append("status")
        elif order.status == order.Status.PAID:
            order.status = order.Status.AWAITING_PAYMENT
            order.paid_at = None
            update_fields.append("status")
        order.save(update_fields=list(dict.fromkeys(update_fields)))
        if inv.status == SaleInvoice.Status.PAID:
            from apps.orders.services import complete_order_inventory

            complete_order_inventory(order)
    return inv


def recompute_invoices(invoices):
    """بازمحاسبه مشترک برای همه فاکتورهای دست‌کاری‌شده، نه فقط فاکتور لنگر."""
    from .models import SaleInvoice

    ids = {inv.pk if hasattr(inv, "pk") else inv for inv in invoices if inv}
    recomputed = []
    for pk in ids:
        inv = SaleInvoice.objects.select_for_update().select_related("order").get(pk=pk)
        recomputed.append(recompute_invoice_status(inv))
    return recomputed


def _validate_sale_receipt(invoice, amount, to_account_id):
    from .models import Account, SaleInvoice

    if amount <= 0:
        raise ValueError("مبلغ دریافت باید بیشتر از صفر باشد")
    if invoice.currency != "IRR":
        raise ValueError("دریافت فروش از این مسیر فقط برای فاکتور ریالی مجاز است")
    if invoice.status not in (SaleInvoice.Status.CONFIRMED, SaleInvoice.Status.PAID):
        raise ValueError("دریافت فقط برای فاکتور تأییدشده یا تسویه‌شده مجاز است")
    if to_account_id:
        account = Account.objects.filter(pk=to_account_id, is_active=True).first()
        if account is None:
            raise ValueError("حساب مقصد معتبر نیست")
        if account.currency != "IRR":
            raise ValueError("ارز حساب مقصد با دریافت ریالی ناسازگار است")


def _settle_invoice(inv, budget, *, date, actor, method, to_account_id, reference, note, receipt,
                    sale_payment=None):
    """تخصیص واقعی budget به ردیف‌های باز یک فاکتور قفل‌شده."""
    from .models import SettlementLine, ReceiptAllocation

    lines = list(
        SettlementLine.objects.select_for_update()
        .filter(invoice=inv, is_active=True)
        .order_by("due_date", "id")
    )
    if not lines:
        st = inv.settlement if inv.settlement in SettlementLine.SettlementType.values else "cash"
        lines = [SettlementLine.objects.create(
            invoice=inv, settlement_type=st,
            amount=inv.total_amount, due_date=_effective_due(inv),
        )]

    allocated_total = 0
    line_budget = min(int(budget), max(0, inv.remaining_amount))
    for line in lines:
        if line_budget <= 0:
            break
        line_remaining = line.remaining_amount
        if line_remaining <= 0:
            continue
        alloc = min(line_budget, line_remaining)
        ReceiptAllocation.objects.create(
            receipt=receipt, sale_payment=sale_payment, settlement_line=line, amount=alloc,
        )
        line_budget -= alloc
        allocated_total += alloc
    recompute_invoice_status(inv)
    return {
        "invoice_id": inv.id, "invoice_number": inv.invoice_number,
        "amount": allocated_total, "payment_id": sale_payment.id if sale_payment else None,
    }


def settle_single_invoice(invoice, amount, *, date, actor=None, method="transfer",
                          to_account_id=None, reference="", note="", receipt=None,
                          cheque=None, source_payment=None):
    """ثبت یک سند واقعی و تخصیص آن ابتدا به فاکتور انتخابی و سپس FIFO."""
    from .models import SalePayment

    amount = int(amount or 0)
    with transaction.atomic():
        inv = _lock_invoice(invoice)
        _validate_sale_receipt(inv, amount, to_account_id)
        sp = SalePayment.objects.create(
            invoice=inv, method=method, amount=amount, date=date,
            to_account_id=to_account_id, reference=reference, note=note,
            created_by=actor, cheque=cheque, source_payment=source_payment,
        )
        allocated = []
        budget = min(amount, max(0, inv.remaining_amount))
        if budget > 0:
            row = _settle_invoice(
                inv, budget, date=date, actor=actor, method=method,
                to_account_id=to_account_id, reference=reference, note=note,
                receipt=receipt, sale_payment=sp,
            )
            if row["amount"]:
                allocated.append(row)
        allocated_total = sum(row["amount"] for row in allocated)
        leftover = amount - allocated_total
        if leftover > 0:
            for other in _open_sale_invoices(inv.customer):
                if leftover <= 0:
                    break
                if other.pk == inv.pk:
                    continue
                other_budget = min(leftover, max(0, other.remaining_amount))
                if other_budget <= 0:
                    continue
                row = _settle_invoice(
                    other, other_budget, date=date, actor=actor, method=method,
                    to_account_id=to_account_id, reference=reference, note=note,
                    receipt=receipt, sale_payment=sp,
                )
                if row["amount"]:
                    allocated.append(row)
                    leftover -= row["amount"]
        return {"allocated": allocated, "leftover": leftover, "payment_id": sp.id}


def _delete_sale_payment(sp, *, legacy_unlinked=False):
    from .models import ReceiptAllocation

    linked = list(sp.allocations.select_related("settlement_line__invoice").order_by("id"))
    touched = {sp.invoice_id}
    touched.update(a.settlement_line.invoice_id for a in linked)
    amount = sp.amount
    anchor_id = sp.invoice_id
    receipts = list(sp.receipts.all())
    sp.delete()
    for receipt in receipts:
        receipt.status = receipt.Status.PENDING
        receipt.sale_payment = None
        receipt.reviewed_by = None
        receipt.reviewed_at = None
        receipt.save(update_fields=["status", "sale_payment", "reviewed_by", "reviewed_at", "updated_at"])
    if legacy_unlinked and not linked:
        to_remove = amount
        for allocation in ReceiptAllocation.objects.select_for_update().filter(
                settlement_line__invoice_id=anchor_id, sale_payment__isnull=True).order_by("-id"):
            if to_remove <= 0:
                break
            take = min(allocation.amount, to_remove)
            if take == allocation.amount:
                allocation.delete()
            else:
                allocation.amount -= take
                allocation.save(update_fields=["amount"])
            to_remove -= take
    return recompute_invoices(touched)


def delete_sale_payment(sp):
    """حذف سند و بازمحاسبه تمام فاکتورها/سفارش‌هایی که از آن تخصیص گرفته‌اند."""
    from .models import SalePayment

    with transaction.atomic():
        locked = SalePayment.objects.select_for_update().select_related("invoice").get(pk=sp.pk)
        return _delete_sale_payment(locked)


def reverse_sale_payments_for_source(payment):
    """برگشت تخصیص‌های فروش مشتق از یک Payment هنگام برگشت/حذف منبع."""
    from .models import SalePayment

    affected = []
    with transaction.atomic():
        ids = list(SalePayment.objects.filter(source_payment=payment).values_list("id", flat=True))
        for sp_id in ids:
            sp = SalePayment.objects.select_for_update().get(pk=sp_id)
            affected.extend(_delete_sale_payment(sp))
    return affected


def unsettle_cheque(cheque):
    """برگشت همه تخصیص‌های یک چک و اثر خنثی‌کنندهٔ کارتابل وصول آن."""
    from .models import Payment, SalePayment

    affected = {}
    with transaction.atomic():
        sps = list(SalePayment.objects.select_for_update().filter(cheque=cheque).order_by("id"))
        for sp in sps:
            source_id = sp.source_payment_id
            for inv in _delete_sale_payment(sp, legacy_unlinked=True):
                affected[inv.id] = inv.invoice_number
            if source_id:
                source = Payment.objects.filter(pk=source_id).first()
                if source and source.settlement_target == Payment.SettlementTarget.CHEQUE:
                    source.delete()
            logger.info(f"[CHEQUE] تسویه سند واریز #{sp.id} با چک برگشت خورد")
    return list(affected.values())


def _open_sale_invoices(user):
    """فاکتورهای فروش باز (ریالی) مشتری — به ترتیب موعد مؤثر (FIFO)."""
    from .models import SaleInvoice

    invoices = [
        inv for inv in (
            SaleInvoice.objects.select_for_update()
            .filter(customer=user, status=SaleInvoice.Status.CONFIRMED, currency="IRR")
            .select_related("customer", "order")
        )
        if inv.remaining_amount > 0
    ]
    invoices.sort(key=lambda inv: (_effective_due(inv), inv.id))
    return invoices


def settle_customer_fifo(user, amount, *, date, actor=None, method="transfer",
                         to_account_id=None, reference="", note="", receipt=None,
                         cheque=None, source_payment=None):
    """تخصیص FIFO وجه ریالی با یک SalePayment قابل‌ردیابی برای کل واریز."""
    from .models import SalePayment

    amount = int(amount or 0)
    if amount <= 0:
        return {"allocated": [], "leftover": 0, "payment_id": None}

    with transaction.atomic():
        invoices = _open_sale_invoices(user)
        allocated = []
        sp = None
        if invoices:
            _validate_sale_receipt(invoices[0], amount, to_account_id)
            sp = SalePayment.objects.create(
                invoice=invoices[0], method=method, amount=amount, date=date,
                to_account_id=to_account_id, reference=reference, note=note,
                created_by=actor, cheque=cheque, source_payment=source_payment,
            )
            for inv in invoices:
                budget = min(amount - sum(row["amount"] for row in allocated),
                             max(0, inv.remaining_amount))
                if budget <= 0:
                    continue
                row = _settle_invoice(
                    inv, budget, date=date, actor=actor, method=method,
                    to_account_id=to_account_id, reference=reference, note=note,
                    receipt=receipt, sale_payment=sp,
                )
                if row["amount"]:
                    allocated.append(row)

        allocated_total = sum(row["amount"] for row in allocated)
        leftover = amount - allocated_total
        if leftover > 0 and not allocated:
            from apps.users.models import UserProfile

            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.payment_credit_irr = (profile.payment_credit_irr or 0) + leftover
            profile.save(update_fields=["payment_credit_irr", "updated_at"])
            logger.info(f"[CREDIT] مازاد {leftover:,} ریال به بستانکاری {user.phone} رفت")

    if allocated:
        logger.info(
            f"[SETTLE] {amount:,} ریال برای {user.phone} تخصیص یافت: "
            + ", ".join(f"{a['invoice_number']}←{a['amount']:,}" for a in allocated)
            + (f" | مازاد داخل سند: {leftover:,}" if leftover else "")
        )
    return {"allocated": allocated, "leftover": leftover, "payment_id": sp.id if sp else None}


def reallocate_sale_payment(sp, *, actor=None):
    """هم‌ترازسازی تخصیص‌های یک سند پس از تغییر مبلغ و بازمحاسبه همه فاکتورها."""
    from .models import SalePayment

    result = {"allocated": [], "released": 0}
    with transaction.atomic():
        sp = SalePayment.objects.select_for_update().select_related("invoice__customer").get(pk=sp.pk)
        if sp.source_payment_id or sp.cheque_id:
            raise ValueError("این دریافت به سند منبع/چک لینک است؛ اصلاح باید از سند منبع انجام شود")
        allocs = list(
            sp.allocations.select_for_update()
            .select_related("settlement_line__invoice").order_by("id")
        )
        used = sum(int(a.amount) for a in allocs)
        target = int(sp.amount or 0)
        if target <= 0:
            raise ValueError("مبلغ دریافت باید بیشتر از صفر باشد")
        touched = {sp.invoice_id}
        touched.update(a.settlement_line.invoice_id for a in allocs)

        if target > used:
            leftover = target - used
            for inv in _open_sale_invoices(sp.invoice.customer):
                if leftover <= 0:
                    break
                budget = min(leftover, max(0, inv.remaining_amount))
                if budget <= 0:
                    continue
                row = _settle_invoice(
                    inv, budget, date=sp.date, actor=actor, method=sp.method,
                    to_account_id=sp.to_account_id, reference=sp.reference,
                    note=sp.note, receipt=None, sale_payment=sp,
                )
                if row["amount"]:
                    result["allocated"].append(row)
                    touched.add(inv.id)
                    leftover -= row["amount"]
        elif target < used:
            to_release = used - target
            released = 0
            for allocation in sorted(allocs, key=lambda x: -x.id):
                if to_release <= 0:
                    break
                take = min(int(allocation.amount), to_release)
                if take == int(allocation.amount):
                    allocation.delete()
                else:
                    allocation.amount -= take
                    allocation.save(update_fields=["amount"])
                to_release -= take
                released += take
            result["released"] = released

        recompute_invoices(touched)

    if result["allocated"] or result["released"]:
        logger.info(
            f"[REALLOC] سند واریز #{sp.id} به {target:,} ریال هم‌تراز شد: "
            + ", ".join(f"{a['invoice_number']}←{a['amount']:,}" for a in result["allocated"])
            + (f" | آزادشده: {result['released']:,}" if result["released"] else "")
        )
    return result


def sale_overpayment_irr(user) -> int:
    """مازاد تخصیص‌نیافتة واریزهای ریالی مشتری."""
    from .models import SalePayment

    total = 0
    for sp in SalePayment.objects.filter(invoice__customer=user, invoice__currency="IRR"):
        used = sp.allocations.aggregate(s=Sum("amount"))["s"] or 0
        total += max(0, sp.amount - used)
    return int(total)


def sale_payment_breakdown(sp) -> str:
    """شرح تخصیص/مصرف یک سند واریز — برای ستون توضیحات کاردکس."""
    parts = []
    used = 0
    for allocation in sp.allocations.select_related("settlement_line__invoice").order_by("id"):
        used += allocation.amount
        parts.append(f"{allocation.amount:,} ← فاکتور {allocation.settlement_line.invoice.invoice_number}")
    remaining = sp.amount - used
    if remaining > 0:
        parts.append(f"{remaining:,} بستانکاری (برای خرید بعدی)")
    return " | ".join(parts)


def consume_sale_overpayment(user, *, date=None) -> dict:
    """مصرف مازاد واریزهای قبلی روی فاکتورهای باز، بدون سند مالی جدید."""
    from .models import SalePayment

    result = {"allocated": [], "amount": 0}
    with transaction.atomic():
        sps = list(
            SalePayment.objects.select_for_update()
            .filter(invoice__customer=user, invoice__currency="IRR")
            .annotate(used=Sum("allocations__amount"))
            .order_by("date", "id")
        )
        available = [[sp, sp.amount - (sp.used or 0)] for sp in sps]
        available = [row for row in available if row[1] > 0]
        if not available:
            return result

        for inv in _open_sale_invoices(user):
            for row in available:
                sp, remaining = row
                if remaining <= 0 or inv.remaining_amount <= 0:
                    continue
                budget = min(remaining, inv.remaining_amount)
                settled = _settle_invoice(
                    inv, budget, date=date or sp.date, actor=None, method=sp.method,
                    to_account_id=sp.to_account_id, reference=sp.reference,
                    note=sp.note, receipt=None, sale_payment=sp,
                )
                if settled["amount"]:
                    row[1] -= settled["amount"]
                    result["amount"] += settled["amount"]
                    result["allocated"].append(settled)
    if result["amount"]:
        logger.info(f"[SETTLE] {result['amount']:,} ریال از مازاد واریزهای {user.phone} مصرف شد")
    return result


def consume_contact_credit(user, *, actor=None, date=None) -> dict:
    """مصرف بستانکاری صریح مانده اول دوره و کارتابل با لینک پایدار به سند منبع."""
    from .models import Payment

    settle_date = date or timezone.localdate()
    allocated_rows = []
    allocated_total = 0

    with transaction.atomic():
        profile, contact = _profile_and_contact(user)
        if profile is not None:
            from apps.users.models import UserProfile

            profile = UserProfile.objects.select_for_update().select_related(
                "linked_contact",
            ).get(pk=profile.pk)
            contact = profile.linked_contact
        if contact is not None:
            from .models import Contact

            contact = Contact.objects.select_for_update().get(pk=contact.pk)
        opening_credit = max(0, -opening_remaining_irr(user))
        budget = min(opening_credit, open_invoice_debt_irr(user))
        if budget > 0:
            source = Payment.objects.create(
                contact=contact, opening_user=None if contact else user,
                direction="out", payment_type="other", currency="IRR", amount=budget,
                date=settle_date, settlement_target=Payment.SettlementTarget.OPENING,
                note="مصرف بستانکاری مانده اول دوره برای تسویه فاکتور فروش",
                created_by=actor,
            )
            settled = settle_customer_fifo(
                user, budget, date=settle_date, actor=actor, method="credit",
                note="تخصیص خودکار از بستانکاری مانده اول دوره", source_payment=source,
            )
            actual = sum(row["amount"] for row in settled["allocated"])
            if actual != budget:
                raise ValueError("بستانکاری مانده اول دوره به‌طور کامل تخصیص نیافت؛ عملیات برگشت خورد")
            allocated_rows.extend(settled["allocated"])
            allocated_total += actual

        if contact is not None:
            contact_credit = max(0, -contact_operational_balance(contact, "IRR"))
            budget = min(contact_credit, open_invoice_debt_irr(user))
            if budget > 0:
                source = Payment.objects.create(
                    contact=contact, direction="out", payment_type="other",
                    currency="IRR", amount=budget, date=settle_date,
                    settlement_target=Payment.SettlementTarget.CONTACT,
                    note="مصرف بستانکاری کارتابل برای تسویه فاکتور فروش",
                    created_by=actor,
                )
                settled = settle_customer_fifo(
                    user, budget, date=settle_date, actor=actor, method="credit",
                    note="تخصیص خودکار از بستانکاری کارتابل طرف حساب", source_payment=source,
                )
                actual = sum(row["amount"] for row in settled["allocated"])
                if actual != budget:
                    raise ValueError("بستانکاری کارتابل به‌طور کامل تخصیص نیافت؛ عملیات برگشت خورد")
                allocated_rows.extend(settled["allocated"])
                allocated_total += actual

    if allocated_total:
        logger.info(f"[CREDIT] {allocated_total:,} ریال بستانکاری {user.phone} به فاکتورها تخصیص یافت")
    return {"allocated": allocated_rows, "amount": allocated_total}
