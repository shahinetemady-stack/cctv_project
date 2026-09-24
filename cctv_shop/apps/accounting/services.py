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

from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


def total_debt_irr(user) -> int:
    """مجموع بدهی ریالی کاربر — مانده فاکتورهای باز + مانده اول دوره مثبت."""
    from .models import SaleInvoice
    debt = 0
    qs = (
        SaleInvoice.objects
        .filter(customer=user, status__in=["confirmed", "paid"])
        .prefetch_related("items", "sale_payments")
    )
    for inv in qs:
        if inv.currency == "IRR":
            remaining = inv.remaining_amount
            if remaining > 0:
                debt += remaining
    profile = getattr(user, "profile", None)
    opening = int(profile.opening_balance_irr) if profile else 0
    if opening > 0:
        debt += opening
    return debt


def open_invoice_debt_irr(user) -> int:
    """مجموع مانده فاکتورهای فروش باز (ریالی، تأییدشده) کاربر — بدون مانده اول دوره."""
    from .models import SaleInvoice
    debt = 0
    qs = (
        SaleInvoice.objects
        .filter(customer=user, status=SaleInvoice.Status.CONFIRMED, currency="IRR")
        .prefetch_related("items", "sale_payments")
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
    """
    کنترل سقف اعتبار پیش از فروش غیرنقدی.
    → None اگر مجاز است، وگرنه متن خطای فارسی.
    قانون ویژه: همکار پلاتینیوم (خودکار یا دستی/حساب دستی) تا وقتی سقف اعتبار
    ندارد، هیچ فاکتور اعتباری (توحسابی/یکماهه/دوماهه) نمی‌تواند داشته باشد.
    """
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
    """
    موعد مؤثر فاکتور برای ترتیب FIFO تخصیص وجه:
    قدیمی‌ترین موعد ردیف تسویهٔ باز → یا due_date فاکتور → یا موعد پیش‌فرض
    نوع تسویه از تاریخ صدور (نقدی = ۰ روز یعنی فوری).
    """
    from apps.orders.models import settlement_due_for
    dues = [l.due_date for l in invoice.settlement_lines.all() if l.is_active]
    if dues:
        return min(dues)
    if invoice.due_date:
        return invoice.due_date
    return settlement_due_for(invoice.settlement, invoice.issue_date)


def _settle_invoice(inv, budget, *, date, actor, method, to_account_id, reference, note, receipt, cheque=None):
    """
    تخصیص budget (ریال) به یک فاکتور مشخص:
    ردیف‌های تسویه را به ترتیب موعد می‌بندد (ReceiptAllocation)، یک SalePayment
    می‌سازد و اگر مانده صفر شد فاکتور (و سفارش سایتِ متعلق) paid می‌شود.
    خروجی: رکورد allocated.
    """
    from .models import SaleInvoice, SalePayment, SettlementLine, ReceiptAllocation

    lines = [l for l in inv.settlement_lines.all() if l.is_active]
    if not lines:
        # فاکتور دستی — ردیف تسویهٔ پیش‌فرض برای ردیابی و گزارش سررسید
        st = inv.settlement if inv.settlement in SettlementLine.SettlementType.values else "cash"
        lines = [SettlementLine.objects.create(
            invoice=inv, settlement_type=st,
            amount=inv.total_amount, due_date=_effective_due(inv),
        )]
    line_budget = budget
    for line in sorted(lines, key=lambda l: (l.due_date, l.id)):
        if line_budget <= 0:
            break
        line_remaining = line.remaining_amount
        if line_remaining <= 0:
            continue
        alloc = min(line_budget, line_remaining)
        ReceiptAllocation.objects.create(
            receipt=receipt, settlement_line=line, amount=alloc,
        )
        line_budget -= alloc
    sp = SalePayment.objects.create(
        invoice=inv, method=method, amount=budget, date=date,
        to_account_id=to_account_id, reference=reference, note=note,
        created_by=actor, cheque=cheque,
    )
    if inv.remaining_amount <= 0:
        inv.status = SaleInvoice.Status.PAID
        inv.save(update_fields=["status", "updated_at"])
        # فاکتور سفارش سایت — با بسته شدن همه ردیف‌ها، سفارش هم پرداخت‌شده می‌شود
        order = getattr(inv, "order", None)
        if order is not None and order.status in ("awaiting_payment", "confirmed") \
                and all(l.remaining_amount <= 0 for l in inv.settlement_lines.all()):
            order.status = order.Status.PAID
            order.paid_at = timezone.now()
            order.save(update_fields=["status", "paid_at", "updated_at"])
    return {
        "invoice_id": inv.id, "invoice_number": inv.invoice_number,
        "amount": budget, "payment_id": sp.id,
    }


def settle_single_invoice(invoice, amount, *, date, actor=None, method="transfer",
                          to_account_id=None, reference="", note="", receipt=None,
                          cheque=None):
    """
    تخصیص هدفمند وجه به یک فاکتور مشخص (درگاه آنلاین، چکِ لینک‌شده).
    سقف تخصیص = مانده فاکتور؛ مازاد با settle_customer_fifo به بقیه فاکتورهای
    باز مشتری می‌رود. فاکتور غیرریالی تسویه نمی‌شود.

    خروجی: {"allocated": [...], "leftover": int}
    """
    amount = int(amount or 0)
    if amount <= 0 or invoice.currency != "IRR":
        return {"allocated": [], "leftover": max(amount, 0)}

    with transaction.atomic():
        budget = min(amount, invoice.remaining_amount)
        allocated = []
        leftover = amount
        if budget > 0:
            allocated.append(_settle_invoice(
                invoice, budget, date=date, actor=actor, method=method,
                to_account_id=to_account_id, reference=reference, note=note,
                receipt=receipt, cheque=cheque,
            ))
            leftover -= budget
        if leftover > 0:
            r = settle_customer_fifo(
                invoice.customer, leftover, date=date, actor=actor, method=method,
                to_account_id=to_account_id, reference=reference, note=note,
                receipt=receipt, cheque=cheque,
            )
            allocated += r["allocated"]
            leftover = r["leftover"]
    return {"allocated": allocated, "leftover": leftover}


def unsettle_cheque(cheque):
    """
    برگشت تسویه‌های انجام‌شده با یک چک (برای وقتی چک برگشت از بانک می‌خورد):
    SalePaymentهای مرتبط حذف، تخصیص‌های ردیف تسویه به همان میزان از جدیدترین
    کم و وضعیت فاکتورها بازمحاسبه می‌شود.
    خروجی: لیست فاکتورهای برگشت‌خورده.
    """
    from .models import SaleInvoice, SalePayment, ReceiptAllocation

    affected = []
    sps = list(SalePayment.objects.filter(cheque=cheque).select_related("invoice"))
    with transaction.atomic():
        for sp in sps:
            inv = sp.invoice
            to_remove = sp.amount
            allocs = ReceiptAllocation.objects.filter(
                settlement_line__invoice=inv).order_by("-id")
            for a in allocs:
                if to_remove <= 0:
                    break
                take = min(a.amount, to_remove)
                if take == a.amount:
                    a.delete()
                else:
                    a.amount -= take
                    a.save(update_fields=["amount"])
                to_remove -= take
            sp.delete()
            if inv.status == SaleInvoice.Status.PAID and inv.remaining_amount > 0:
                inv.status = SaleInvoice.Status.CONFIRMED
                inv.save(update_fields=["status", "updated_at"])
            affected.append(inv.invoice_number)
            logger.info(f"[CHEQUE] تسویه {sp.amount:,} ریالی فاکتور {inv.invoice_number} با چک برگشت خورد")
    return affected


def settle_customer_fifo(user, amount, *, date, actor=None, method="transfer",
                         to_account_id=None, reference="", note="", receipt=None,
                         cheque=None):
    """
    وجه دریافتی user را به‌صورت FIFO (به ترتیب موعد مؤثر) روی فاکتورهای بازش
    تخصیص می‌دهد — هم فاکتورهای دستی و هم فاکتورهای سفارش سایت.
    فقط فاکتورهای ریالی تسویه می‌شوند (وجه دریافتی ریال است).

    - فاکتور دستی بدون ردیف تسویه، یک ردیف تسویهٔ پیش‌فرض می‌گیرد تا گزارش
      سررسید و ردیابی تخصیص (ReceiptAllocation) برایش کار کند.
    - فاکتور کامل‌تسویه‌شده status=paid می‌شود؛ اگر متعلق به سفارش سایت است و
      همه ردیف‌هایش بسته شدند، سفارش هم paid می‌شود.
    - مازاد مبلغ به «بستانکاری نقدی» مشتری (UserProfile.payment_credit_irr)
      می‌رود تا با apply_customer_credit به بدهی‌های بعدی تخصیص یابد.

    خروجی: {"allocated": [{"invoice_id", "invoice_number", "amount"}], "leftover": int}
    """
    from .models import SaleInvoice

    amount = int(amount or 0)
    if amount <= 0:
        return {"allocated": [], "leftover": 0}

    invoices = [
        inv for inv in (
            SaleInvoice.objects
            .filter(customer=user, status=SaleInvoice.Status.CONFIRMED, currency="IRR")
            .prefetch_related("settlement_lines")
        )
        if inv.remaining_amount > 0
    ]
    invoices.sort(key=lambda inv: (_effective_due(inv), inv.id))

    allocated = []
    leftover = amount
    with transaction.atomic():
        for inv in invoices:
            if leftover <= 0:
                break
            inv_budget = min(leftover, inv.remaining_amount)
            allocated.append(_settle_invoice(
                inv, inv_budget, date=date, actor=actor, method=method,
                to_account_id=to_account_id, reference=reference, note=note,
                receipt=receipt, cheque=cheque,
            ))
            leftover -= inv_budget

        if leftover > 0:
            from apps.users.models import UserProfile
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.payment_credit_irr = (profile.payment_credit_irr or 0) + leftover
            profile.save(update_fields=["payment_credit_irr", "updated_at"])
            logger.info(f"[CREDIT] مازاد {leftover:,} ریال به بستانکاری {user.phone} رفت")

    if allocated:
        logger.info(
            f"[SETTLE] {amount:,} ریال برای {user.phone} تخصیص یافت: "
            + ", ".join(f"{a['invoice_number']}←{a['amount']:,}" for a in allocated)
            + (f" | مازاد: {leftover:,}" if leftover else "")
        )
    return {"allocated": allocated, "leftover": leftover}


def consume_contact_credit(user, *, actor=None, date=None) -> dict:
    """
    بستانکاری کارتابل طرف حسابِ لینک‌شده به user (مانده منفی Paymentها — مثل
    پایهٔ بستانکاری سند انتقال یا دریافت دستیِ قبل از صدور فاکتور) را به
    فاکتورهای فروش باز او تخصیص می‌دهد (FIFO) — برای وقتی بستانکاری *قبل* از
    فاکتور ایجاد شده باشد.
    برای بستانکاریِ مصرف‌شده یک ردیف «پرداخت» خنثی‌کننده روی کارتابل ثبت
    می‌شود تا در خالص کارتابل/وضعیت مالی دوبار حساب نشود (سابقه حفظ می‌شود).
    خروجی: {"allocated": [...], "amount": int}
    """
    from .models import Payment

    profile = getattr(user, "profile", None)
    contact = getattr(profile, "linked_contact", None) if profile else None
    if contact is None:
        return {"allocated": [], "amount": 0}
    credit = -int(contact.balance_irr)
    if credit <= 0:
        return {"allocated": [], "amount": 0}
    budget = min(credit, open_invoice_debt_irr(user))
    if budget <= 0:
        return {"allocated": [], "amount": 0}

    settle_date = date or timezone.localdate()
    with transaction.atomic():
        r = settle_customer_fifo(
            user, budget, date=settle_date, actor=actor, method="transfer",
            note="تخصیص خودکار از بستانکاری کارتابل طرف حساب",
        )
        allocated_total = sum(a["amount"] for a in r["allocated"])
        if allocated_total > 0:
            Payment.objects.create(
                contact=contact, direction="out", payment_type="other",
                currency="IRR", amount=allocated_total, date=settle_date,
                note="مصرف بستانکاری کارتابل برای تسویه فاکتور فروش",
                created_by=actor,
            )
            logger.info(
                f"[CREDIT] {allocated_total:,} ریال از بستانکاری کارتابل {contact.name} "
                f"به فاکتورهای {user.phone} تخصیص یافت")
    return {"allocated": r["allocated"], "amount": allocated_total}
