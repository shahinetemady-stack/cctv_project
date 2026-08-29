"""
apps/accounting/views.py — v4
─────────────────────────────
تغییرات:
- مرحله ۱ (POST purchase-invoices/): shipping_contact_id, warehouse_id (انبار در راه) اجباری
- مرحله ۲ (POST receive/): destination_warehouse_id اجباری
- ویرایش فاکتور خرید/فروش (PATCH سرفاکتور + جایگزینی آیتم‌ها با برگشت/اعمال موجودی)
- CRUD کامل پرداخت‌ها، دریافت‌های فروش و حساب‌ها + گزارش گردش حساب
"""
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from django.db.models import Sum, Q
from django.db import transaction
from decimal import Decimal

from .models import Contact, PurchaseInvoice, PurchaseItem, ExtraCost, Payment
from apps.users.models import UserProfile

logger = logging.getLogger(__name__)


def _safe_decimal(value, default="0"):
    if value is None or value == "":
        return Decimal(default)
    try:
        return Decimal(str(value).strip())
    except Exception:
        return Decimal(default)


def _safe_int(value, default=0):
    if value is None or value == "":
        return default
    try:
        return int(value)
    except Exception:
        return default


def _days_since(d):
    if d is None:
        return 0
    import datetime
    today = datetime.date.today()
    if isinstance(d, datetime.datetime):
        d = d.date()
    try:
        return (today - d).days
    except Exception:
        return 0


# ─── RBAC helpers ────────────────────────────────────────────

def _has_perm(user, code):
    if user.is_superuser:
        return True
    sp = getattr(user, 'staff_profile', None)
    return bool(sp and sp.is_active and sp.has_perm(code))


def _forbidden(msg='شما دسترسی لازم برای این عملیات را ندارید'):
    return Response({'error': msg}, status=403)


def _allowed_contact_types(user):
    """نوع‌های مجاز طرف حساب برای کاربر — None یعنی بدون محدودیت (همه نوع‌ها)."""
    if user.is_superuser:
        return None
    sp = getattr(user, 'staff_profile', None)
    if not sp or not sp.is_active or not sp.role:
        return None
    return (sp.role.allowed_contact_types or []) or None


def _creatable_contact_types(user):
    """نوع‌های طرف حسابی که کاربر مجاز به «ساخت» آن‌هاست — ساخت طرف حساب جدید
    (از هر نوع، حتی مشتری عمومی) فقط برای گروه‌های مجاز است:
    None = بدون محدودیت (سوپریوزر) | [] = هیچ نوعی (ساخت ممنوع)"""
    if user.is_superuser:
        return None
    sp = getattr(user, 'staff_profile', None)
    if not sp or not sp.is_active or not sp.role:
        return []
    return sp.role.allowed_contact_types or []


# ─── Accounts ────────────────────────────────────────────────

class AccountListView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        if not _has_perm(request.user, 'balance_view'):
            return _forbidden()
        from .models import Account
        accounts = Account.objects.filter(is_active=True)
        return Response([{
            "id": a.id, "name": a.name,
            "account_type": a.account_type,
            "account_type_display": a.get_account_type_display(),
            "currency": a.currency, "bank_name": a.bank_name,
            "account_number": a.account_number,
            "balance": a.balance,
        } for a in accounts])

    def post(self, request):
        if not _has_perm(request.user, 'accounts_edit'):
            return _forbidden()
        from .models import Account
        d = request.data
        a = Account.objects.create(
            name=d["name"],
            account_type=d.get("account_type", "cash"),
            currency=d.get("currency", "IRR"),
            bank_name=d.get("bank_name", ""),
            account_number=d.get("account_number", ""),
            initial_balance=d.get("initial_balance", 0),
            note=d.get("note", ""),
        )
        return Response({"id": a.id, "name": a.name}, status=201)


class AccountDetailView(APIView):
    """GET/PATCH/DELETE روی یک حساب"""
    permission_classes = [IsAdminUser]

    def get(self, request, pk):
        if not _has_perm(request.user, 'balance_view'):
            return _forbidden()
        from .models import Account
        try:
            a = Account.objects.get(pk=pk)
        except Account.DoesNotExist:
            return Response({"error": "یافت نشد"}, status=404)
        return Response({
            "id": a.id, "name": a.name,
            "account_type": a.account_type,
            "account_type_display": a.get_account_type_display(),
            "currency": a.currency, "bank_name": a.bank_name,
            "account_number": a.account_number,
            "initial_balance": float(a.initial_balance),
            "balance": a.balance,
            "is_active": a.is_active,
            "note": a.note,
        })

    def patch(self, request, pk):
        if not _has_perm(request.user, 'accounts_edit'):
            return _forbidden()
        from .models import Account
        try:
            a = Account.objects.get(pk=pk)
        except Account.DoesNotExist:
            return Response({"error": "یافت نشد"}, status=404)
        d = request.data
        for f in ["name", "account_type", "currency", "bank_name",
                  "account_number", "note", "is_active"]:
            if f in d:
                setattr(a, f, d[f])
        if "initial_balance" in d:
            a.initial_balance = _safe_decimal(d["initial_balance"], "0")
        a.save()
        return Response({"id": a.id, "name": a.name, "balance": a.balance, "message": "حساب به‌روز شد"})

    def delete(self, request, pk):
        if not _has_perm(request.user, 'accounts_edit'):
            return _forbidden()
        from .models import Account, SalePayment
        try:
            a = Account.objects.get(pk=pk)
        except Account.DoesNotExist:
            return Response({"error": "یافت نشد"}, status=404)
        has_payment = Payment.objects.filter(Q(from_account=a) | Q(to_account=a)).exists()
        has_sale_payment = SalePayment.objects.filter(to_account=a).exists()
        if has_payment or has_sale_payment:
            return Response({"error": "این حساب دارای تراکنش است و قابل حذف نیست"}, status=400)
        a.delete()
        return Response(status=204)


class AccountTransactionsView(APIView):
    """GET → گردش تراکنش‌های یک حساب (پرداخت‌ها + دریافت‌های فروش) + خلاصه"""
    permission_classes = [IsAdminUser]

    def get(self, request, pk):
        if not _has_perm(request.user, 'balance_view'):
            return _forbidden()
        from .models import Account, SalePayment
        try:
            acc = Account.objects.get(pk=pk)
        except Account.DoesNotExist:
            return Response({"error": "یافت نشد"}, status=404)

        rows = []
        payments = Payment.objects.filter(
            Q(from_account=acc) | Q(to_account=acc)
        ).select_related("contact", "invoice", "created_by")
        for p in payments:
            direction = "out" if p.from_account_id == acc.id else "in"
            rows.append({
                "kind": "payment",
                "id": p.id,
                "direction": direction,
                "amount": float(p.amount),
                "currency": p.currency,
                "rate_irr": p.rate_irr,
                "amount_irr": p.amount_irr,
                "date": str(p.date),
                "reference": p.reference,
                "note": p.note,
                "counterparty": p.contact.name if p.contact else "",
                "invoice_label": (p.invoice.invoice_number or str(p.invoice_id)) if p.invoice else None,
                "created_by": _user_label(p.created_by),
            })

        receipts = SalePayment.objects.filter(to_account=acc).select_related("invoice", "invoice__customer", "created_by")
        for sp in receipts:
            rows.append({
                "kind": "sale_payment",
                "id": sp.id,
                "direction": "in",
                "amount": float(sp.amount),
                "currency": "IRR",
                "rate_irr": None,
                "amount_irr": int(sp.amount),
                "date": str(sp.date),
                "reference": sp.reference,
                "note": sp.note,
                "counterparty": sp.invoice.customer_name or str(sp.invoice.customer),
                "invoice_label": sp.invoice.invoice_number,
                "created_by": _user_label(sp.created_by),
            })

        rows.sort(key=lambda r: (r["date"], r["id"]), reverse=True)

        total_in = sum(r["amount_irr"] for r in rows if r["direction"] == "in")
        total_out = sum(r["amount_irr"] for r in rows if r["direction"] == "out")
        return Response({
            "account": {"id": acc.id, "name": acc.name, "currency": acc.currency},
            "transactions": rows,
            "summary": {
                "total_in_irr": total_in,
                "total_out_irr": total_out,
                "balance": acc.balance,
                "count": len(rows),
            },
        })


# ─── Contacts ────────────────────────────────────────────────
# علاوه بر Contactهای دستی، کاربران ثبت‌نامی سایت هم به‌صورت مجازی در لیست
# مشتریان/همکاران دیده می‌شوند (id پیشونددار «u_» — رکورد Contact ندارند).

def _registered_users_qs():
    from django.contrib.auth import get_user_model
    return (
        get_user_model().objects
        .filter(is_active=True, is_staff=False, is_superuser=False)
        # کاربران سایه (لینک‌شده به یک طرف حساب دستی) جداگانه نمایش داده نمی‌شوند
        .exclude(profile__linked_contact__isnull=False)
        .select_related('profile')
        .order_by('first_name', 'last_name', 'phone')
    )


def _user_is_partner(u):
    profile = getattr(u, 'profile', None)
    return bool(profile and profile.user_type == 'partner' and profile.is_approved)


def _user_tier(u):
    """سطح مشتری برای فرم فاکتور — public یا silver/gold/platinum"""
    p = getattr(u, 'profile', None)
    if p and p.is_approved and p.user_type == 'partner':
        return p.partner_tier or 'partner'
    return 'public'


def _user_display_name(u):
    profile = getattr(u, 'profile', None)
    return u.get_full_name() or (profile.company_name if profile else '') or u.phone


def _sale_debt_map(user_ids):
    """جمع بدهی فاکتورهای فروش تسویه‌نشده هر کاربر — تفکیک ریال/یوان — بدون اثر روی مانده طرف حساب"""
    from .models import SaleInvoice
    debts = {}
    qs = (SaleInvoice.objects
          .filter(customer_id__in=user_ids, status__in=['confirmed', 'paid'])
          .prefetch_related('items', 'sale_payments'))
    for inv in qs:
        remaining = inv.remaining_amount
        if remaining > 0:
            d = debts.setdefault(inv.customer_id, {'irr': 0, 'cny': 0})
            d['cny' if inv.currency == 'CNY' else 'irr'] += remaining
    return debts


def _linked_user(contact):
    """کاربر سایهٔ لینک‌شده به طرف حساب (در صورت وجود) — برای نمایش اسناد فروش در کاردکس طرف حساب"""
    profile = contact.linked_users.select_related('user').first()
    return profile.user if profile else None


def _sale_invoices_payload(u):
    from .models import SaleInvoice
    return [{
        "id": inv.id, "invoice_number": inv.invoice_number,
        "date": str(inv.issue_date or inv.created_at.date()), "status": inv.status,
        "status_display": inv.get_status_display(),
        "currency": inv.currency,
        "total_amount": inv.total_amount,
        "paid_amount": inv.paid_amount,
        "remaining_amount": inv.remaining_amount,
        "items": [{
            "product_name": it.variant.product.name,
            "sku": it.variant.sku,
            "quantity": it.quantity,
            "unit_price": it.unit_price,
        } for it in inv.items.select_related("variant__product").all()],
    } for inv in SaleInvoice.objects.filter(customer=u).order_by("-created_at")[:20]]


def _sale_payments_payload(u):
    from .models import SalePayment
    return [{
        "id": p.id, "date": str(p.date),
        "method_display": p.get_method_display(),
        "amount": p.amount,
        "currency": p.invoice.currency if p.invoice_id else "IRR",
        "account_name": p.to_account.name if p.to_account else "",
        "reference": p.reference,
    } for p in SalePayment.objects.filter(invoice__customer=u).select_related("to_account", "invoice").order_by("-date")[:50]]


def _registered_contact_payload(u, debts=None):
    is_partner = _user_is_partner(u)
    profile = getattr(u, 'profile', None)
    debts = debts or {}
    ob_irr = profile.opening_balance_irr if profile else 0
    ob_cny = float(profile.opening_balance_cny) if profile else 0
    return {
        "id": f"u_{u.id}", "user_id": u.id, "is_registered": True,
        "name": _user_display_name(u),
        "contact_type": "partner" if is_partner else "customer",
        "contact_type_display": "همکار" if is_partner else "مشتری",
        "partner_tier": (profile.partner_tier if profile and is_partner else None),
        "partner_tier_display": (profile.get_partner_tier_display() if profile and is_partner and profile.partner_tier else ""),
        "currency": "IRR",
        "phone": u.phone, "wechat": "",
        "opening_balance_irr": ob_irr, "opening_balance_cny": ob_cny,
        "balance_irr": 0, "balance_cny": 0,
        # بدهی فاکتور فروش + مانده اول دوره — مثبت = مشتری به ما بدهکار
        "sale_debt": debts.get('irr', 0) + ob_irr,
        "sale_debt_cny": debts.get('cny', 0) + ob_cny,
    }


def _get_registered_user(pk):
    from django.contrib.auth import get_user_model
    try:
        return _registered_users_qs().get(pk=int(str(pk)[2:]))
    except (get_user_model().DoesNotExist, ValueError, TypeError):
        return None


class ContactListView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        if not _has_perm(request.user, 'contacts_view'):
            return _forbidden()
        ct = request.query_params.get("type") or ""
        include_registered = request.query_params.get("include_registered") == "1"
        allowed = _allowed_contact_types(request.user)

        qs = Contact.objects.filter(is_active=True)
        if ct:
            qs = qs.filter(contact_type=ct)
        if allowed is not None:
            qs = qs.filter(contact_type__in=allowed)

        # حالت سازگار — فقط Contactهای دستی با id عددی (مصرف‌کننده‌های قدیمی)
        if not include_registered:
            return Response([{
                "id": c.id, "name": c.name,
                "contact_type": c.contact_type,
                "contact_type_display": c.get_contact_type_display(),
            "partner_tier": c.partner_tier,
            "partner_tier_display": c.get_partner_tier_display(),
                "currency": c.currency,
                "phone": c.phone, "wechat": c.wechat, "address": c.address,
                "opening_balance_irr": c.opening_balance_irr,
                "opening_balance_cny": float(c.opening_balance_cny),
                "balance_irr": c.balance_irr,
                "balance_cny": float(c.balance_cny),
            } for c in qs])

        # حالت ادغام — id پیشونددار + کاربران ثبت‌نامی سایت
        # بدهی فروش کاربر سایهٔ لینک‌شده به هر طرف حساب، روی همان طرف حساب نشان داده می‌شود
        linked_map = {}   # contact_id -> user_id
        for prof in UserProfile.objects.filter(linked_contact__isnull=False).select_related('user'):
            if prof.user.is_active:
                linked_map[prof.linked_contact_id] = prof.user_id
        linked_debts = _sale_debt_map(list(linked_map.values())) if linked_map else {}

        def _contact_payload(c):
            debts = linked_debts.get(linked_map.get(c.id)) or {}
            return {
                "id": f"c_{c.id}", "user_id": None, "is_registered": False,
                "name": c.name,
                "contact_type": c.contact_type,
                "contact_type_display": c.get_contact_type_display(),
                "partner_tier": c.partner_tier,
                "partner_tier_display": c.get_partner_tier_display(),
                "currency": c.currency,
                "phone": c.phone, "wechat": c.wechat, "address": c.address,
                "opening_balance_irr": c.opening_balance_irr,
                "opening_balance_cny": float(c.opening_balance_cny),
                "balance_irr": c.balance_irr,
                "balance_cny": float(c.balance_cny),
                "sale_debt": debts.get('irr', 0),
                "sale_debt_cny": debts.get('cny', 0),
            }

        data = [_contact_payload(c) for c in qs]

        # کاربران ثبت‌نامی — پیش‌فرض فقط همکارهای تأییدشده؛ با registered_filter=all همه می‌آیند
        if ct in ("", "customer", "partner"):
            reg_filter = request.query_params.get("registered_filter") or "partners"
            users = list(_registered_users_qs())
            if reg_filter != "all":
                users = [u for u in users if _user_is_partner(u)]
            debts = _sale_debt_map([u.id for u in users])
            for u in users:
                payload = _registered_contact_payload(u, debts.get(u.id, 0))
                if ct and payload["contact_type"] != ct:
                    continue
                if allowed is not None and payload["contact_type"] not in allowed:
                    continue
                data.append(payload)

        data.sort(key=lambda x: x["name"])
        return Response(data)

    def post(self, request):
        if not _has_perm(request.user, 'contacts_create'):
            return _forbidden()
        d = request.data
        if d.get("contact_type") not in Contact.ContactType.values:
            return Response({"error": "نوع طرف حساب نامعتبر است"}, status=400)
        creatable = _creatable_contact_types(request.user)
        if creatable is not None and d["contact_type"] not in creatable:
            if not creatable:
                return _forbidden('ساخت طرف حساب جدید فقط برای گروه‌های مجاز است')
            return _forbidden('شما مجاز به ساخت این نوع طرف حساب نیستید')
        if not str(d.get("phone") or "").strip():
            return Response({"error": "موبایل الزامی است"}, status=400)
        tier = d.get("partner_tier") or ""
        if d["contact_type"] == "partner":
            if tier not in Contact.PartnerTier.values:
                return Response({"error": "سطح همکار را انتخاب کنید (سیلور/گلد/پلاتینیوم)"}, status=400)
        else:
            tier = ""
        c = Contact.objects.create(
            name=d["name"],
            contact_type=d["contact_type"],
            currency=d.get("currency", "CNY"),
            phone=d.get("phone", ""),
            wechat=d.get("wechat", ""),
            address=d.get("address", ""),
            partner_tier=tier,
            note=d.get("note", ""),
            opening_balance_irr=int(d.get("opening_balance_irr") or 0),
            opening_balance_cny=d.get("opening_balance_cny") or 0,
        )
        return Response({"id": c.id, "name": c.name, "phone": c.phone}, status=201)


class ContactDetailView(APIView):
    permission_classes = [IsAdminUser]

    def _registered_detail(self, u):
        profile = getattr(u, 'profile', None)
        payload = _registered_contact_payload(u, _sale_debt_map([u.id]).get(u.id) or {})
        payload.update({
            "email": u.email or "",
            "first_name": u.first_name,
            "last_name": u.last_name,
            "company_name": profile.company_name if profile else "",
            "address": profile.address if profile else "",
            "province": profile.province if profile else "",
            "note": "",
            "partner_approved": _user_is_partner(u),
            "date_joined": str(u.date_joined.date()),
            "payments": [], "invoices": [],
            "sale_invoices": _sale_invoices_payload(u),
            "sale_payments": _sale_payments_payload(u),
        })
        return Response(payload)

    def get(self, request, pk):
        if not _has_perm(request.user, 'contacts_view'):
            return _forbidden()
        allowed = _allowed_contact_types(request.user)
        if str(pk).startswith("u_"):
            u = _get_registered_user(pk)
            if u is None:
                return Response({"error": "یافت نشد"}, status=404)
            u_type = "partner" if _user_is_partner(u) else "customer"
            if allowed is not None and u_type not in allowed:
                return _forbidden()
            return self._registered_detail(u)
        real_pk = str(pk)[2:] if str(pk).startswith("c_") else pk
        try:
            c = Contact.objects.get(pk=real_pk)
        except Contact.DoesNotExist:
            return Response({"error": "یافت نشد"}, status=404)
        if allowed is not None and c.contact_type not in allowed:
            return _forbidden()

        payments = [{
            "id": p.id, "date": str(p.date),
            "direction": p.direction,
            "direction_display": p.get_direction_display(),
            "payment_type_display": p.get_payment_type_display(),
            "amount": float(p.amount), "currency": p.currency,
            "amount_irr": p.amount_irr, "rate_irr": p.rate_irr,
            "reference": p.reference, "note": p.note,
            "from_account_name": p.from_account.name if p.from_account else "",
            "to_account_name": p.to_account.name if p.to_account else "",
            "invoice_id": p.invoice_id,
        } for p in c.payments.select_related("from_account", "to_account").order_by("-date")[:50]]

        supplier_invoices = [{
            "id": inv.id, "invoice_number": inv.invoice_number,
            "date": str(inv.date), "status": inv.status,
            "status_display": inv.get_status_display(), "role": "supplier",
            "description": f"فاکتور خرید {inv.invoice_number or inv.id}",
            "purchase_type": inv.purchase_type,
            "amount_cny": float(sum(float(it.unit_price_cny) * it.quantity for it in inv.items.all())),
            # خرید داخلی — مبلغ ریالی فاکتور در ستون ریال کاردکس لحاظ می‌شود
            "amount_irr": sum(it.unit_price_irr * it.quantity for it in inv.items.all()) if inv.purchase_type == "domestic" else 0,
            # ریز اقلام فاکتور — برای نمایش جزئیات با کلیک و لیست ریز اقلام
            "items": [{
                "product_name": it.variant.product.name,
                "sku": it.variant.sku,
                "quantity": it.quantity,
                "unit_price_cny": float(it.unit_price_cny),
                "unit_price_irr": it.unit_price_irr,
            } for it in inv.items.select_related("variant__product").all()],
        } for inv in c.purchase_invoices.order_by("-date")[:20]]

        shipping_invoices = [{
            "id": inv.id, "invoice_number": inv.invoice_number,
            "date": str(inv.date), "status": inv.status,
            "status_display": inv.get_status_display(), "role": "shipper",
            "description": f"حمل و ترخیص — فاکتور {inv.invoice_number or inv.id}",
            "amount_cny": float(inv.shipping_cost_cny),
            "amount_irr": inv.clearance_cost_irr,
        } for inv in c.shipping_invoices.order_by("-date")[:20]]

        invoices = sorted(supplier_invoices + shipping_invoices,
                          key=lambda x: x["date"], reverse=True)

        # اسناد فروش کاربر سایهٔ لینک‌شده — در کاردکس همین طرف حساب دیده می‌شود
        linked_u = _linked_user(c)
        sale_invoices = _sale_invoices_payload(linked_u) if linked_u else []
        sale_payments = _sale_payments_payload(linked_u) if linked_u else []
        return Response({
            "id": f"c_{c.id}", "user_id": None, "is_registered": False,
            "name": c.name,
            "contact_type": c.contact_type,
            "contact_type_display": c.get_contact_type_display(),
            "partner_tier": c.partner_tier,
            "partner_tier_display": c.get_partner_tier_display(),
            "currency": c.currency, "phone": c.phone, "wechat": c.wechat,
            "address": c.address,
            "province": c.province,
            "note": c.note,
            "partner_approved": None,
            "opening_balance_irr": c.opening_balance_irr,
            "opening_balance_cny": float(c.opening_balance_cny),
            "balance_irr": c.balance_irr, "balance_cny": float(c.balance_cny),
            "payments": payments, "invoices": invoices,
            "sale_invoices": sale_invoices, "sale_payments": sale_payments,
            # حساب کاربری سایت مرتبط با این طرف حساب (برای فعال‌سازی/تعیین رمز)
            "linked_user_phone": linked_u.phone if linked_u else "",
            "linked_user_active": bool(linked_u and linked_u.has_usable_password()),
        })

    def patch(self, request, pk):
        d = request.data

        # کاربر ثبت‌نامی — تأیید/لغو همکار + تعیین سطح (partner_approve)
        # ویرایش کامل اطلاعات (contacts_edit)
        if str(pk).startswith("u_"):
            can_approve = _has_perm(request.user, 'partner_approve')
            can_edit = _has_perm(request.user, 'contacts_edit')
            if not (can_approve or can_edit):
                return _forbidden()
            status_keys = {"partner_approved", "partner_tier"} & set(d)
            edit_keys = {"first_name", "last_name", "phone", "email", "company_name", "address", "province",
                         "opening_balance_irr", "opening_balance_cny"} & set(d)
            if not status_keys and not edit_keys:
                return Response({"error": "فیلد قابل ویرایشی ارسال نشده است"}, status=400)
            if edit_keys and not can_edit:
                return _forbidden('ویرایش اطلاعات نیازمند دسترسی ویرایش طرف حساب است')
            if status_keys and not (can_approve or can_edit):
                return _forbidden()
            u = _get_registered_user(pk)
            if u is None:
                return Response({"error": "یافت نشد"}, status=404)
            from apps.users.models import UserProfile
            profile, _ = UserProfile.objects.get_or_create(user=u)
            old_tier = profile.partner_tier
            old_approved = bool(profile.user_type == UserProfile.UserType.PARTNER and profile.is_approved)
            if "partner_tier" in d:
                tier = d["partner_tier"] or ""
                if tier and tier not in ("silver", "gold", "platinum"):
                    return Response({"error": "سطح همکار نامعتبر است"}, status=400)
                profile.partner_tier = tier
            if d.get("partner_approved"):
                profile.user_type = UserProfile.UserType.PARTNER
                profile.is_approved = True
            elif "partner_approved" in d:
                profile.is_approved = False
            if "first_name" in d:
                u.first_name = (d["first_name"] or "").strip()
            if "last_name" in d:
                u.last_name = (d["last_name"] or "").strip()
            if "phone" in d:
                phone = str(d["phone"] or "").strip()
                if not phone:
                    return Response({"error": "موبایل نمی‌تواند خالی باشد"}, status=400)
                from django.contrib.auth import get_user_model
                if get_user_model().objects.filter(phone=phone).exclude(pk=u.pk).exists():
                    return Response({"error": "این شماره موبایل برای کاربر دیگری ثبت شده است"}, status=400)
                u.phone = phone
            if "email" in d:
                email = (d["email"] or "").strip()
                from django.contrib.auth import get_user_model
                if email and get_user_model().objects.filter(email=email).exclude(pk=u.pk).exists():
                    return Response({"error": "این ایمیل برای کاربر دیگری ثبت شده است"}, status=400)
                u.email = email or None
            if "company_name" in d:
                profile.company_name = (d["company_name"] or "").strip()
            if "address" in d:
                profile.address = d["address"] or ""
            if "province" in d:
                profile.province = d["province"] or ""
            if "opening_balance_irr" in d:
                try:
                    profile.opening_balance_irr = int(d["opening_balance_irr"] or 0)
                except (ValueError, TypeError):
                    return Response({"error": "مانده اول دوره (ریال) نامعتبر است"}, status=400)
            if "opening_balance_cny" in d:
                try:
                    profile.opening_balance_cny = d["opening_balance_cny"] or 0
                except (ValueError, TypeError):
                    return Response({"error": "مانده اول دوره (یوان) نامعتبر است"}, status=400)
            u.save()
            profile.save()

            # پیامک تغییر سطح / تأیید همکار — best-effort
            if profile.partner_tier != old_tier:
                from apps.notifications.services import notify_tier_change_sms
                tier_display = profile.get_partner_tier_display() if profile.partner_tier else "مشتری عمومی"
                notify_tier_change_sms(u.phone, f"{u.first_name} {u.last_name}".strip(), tier_display)
            new_approved = bool(profile.user_type == UserProfile.UserType.PARTNER and profile.is_approved)
            if new_approved and not old_approved:
                from apps.notifications.services import notify_partner_approved_sms
                notify_partner_approved_sms(u)

            is_partner = bool(
                profile.user_type == UserProfile.UserType.PARTNER and profile.is_approved
            )
            return Response({
                "id": f"u_{u.id}",
                "partner_approved": is_partner,
                "partner_tier": profile.partner_tier,
                "contact_type": "partner" if is_partner else "customer",
                "name": _user_display_name(u),
                "first_name": u.first_name,
                "last_name": u.last_name,
                "phone": u.phone,
                "email": u.email or "",
                "company_name": profile.company_name,
                "address": profile.address,
                "province": profile.province,
                "opening_balance_irr": profile.opening_balance_irr,
                "opening_balance_cny": float(profile.opening_balance_cny),
            })

        real_pk = str(pk)[2:] if str(pk).startswith("c_") else pk
        if not _has_perm(request.user, 'contacts_edit'):
            return _forbidden()
        try:
            c = Contact.objects.get(pk=real_pk)
        except Contact.DoesNotExist:
            return Response({"error": "یافت نشد"}, status=404)

        allowed = _allowed_contact_types(request.user)
        if allowed is not None and c.contact_type not in allowed:
            return _forbidden()

        if "name" in d:
            c.name = str(d["name"]).strip() or c.name
        if "contact_type" in d:
            if d["contact_type"] not in Contact.ContactType.values:
                return Response({"error": "نوع طرف حساب نامعتبر است"}, status=400)
            if allowed is not None and d["contact_type"] not in allowed:
                return _forbidden('شما مجاز به تعیین این نوع طرف حساب نیستید')
            c.contact_type = d["contact_type"]
        old_tier_c = c.partner_tier
        if "partner_tier" in d:
            tier = d["partner_tier"] or ""
            if tier and tier not in Contact.PartnerTier.values:
                return Response({"error": "سطح همکار نامعتبر است"}, status=400)
            c.partner_tier = tier
        if "currency" in d:
            if d["currency"] not in Contact.Currency.values:
                return Response({"error": "ارز نامعتبر است"}, status=400)
            c.currency = d["currency"]
        for f in ("phone", "wechat", "address", "province", "note"):
            if f in d:
                setattr(c, f, d[f] or "")
        if "opening_balance_irr" in d:
            try:
                c.opening_balance_irr = int(d["opening_balance_irr"] or 0)
            except (ValueError, TypeError):
                return Response({"error": "مانده اول دوره (ریال) نامعتبر است"}, status=400)
        if "opening_balance_cny" in d:
            try:
                c.opening_balance_cny = d["opening_balance_cny"] or 0
            except (ValueError, TypeError):
                return Response({"error": "مانده اول دوره (یوان) نامعتبر است"}, status=400)
        c.save()

        # پیامک تغییر سطح همکار — best-effort
        if "partner_tier" in d and c.partner_tier != old_tier_c:
            from apps.notifications.services import notify_tier_change_sms
            tier_display = c.get_partner_tier_display() if c.partner_tier else "مشتری عمومی"
            notify_tier_change_sms(c.phone, c.name, tier_display)

        return Response({
            "id": f"c_{c.id}", "name": c.name,
            "opening_balance_irr": c.opening_balance_irr,
            "opening_balance_cny": float(c.opening_balance_cny),
            "balance_irr": c.balance_irr, "balance_cny": float(c.balance_cny),
        })

    def delete(self, request, pk):
        """حذف طرف حساب — اگر سند دارد غیرفعال (soft) می‌شود تا سابقه حسابداری حفظ شود."""
        if not _has_perm(request.user, 'contacts_edit'):
            return _forbidden()
        # کاربر ثبت‌نامی — اگر سند/سفارش دارد غیرفعال می‌شود، وگرنه حذف کامل
        if str(pk).startswith("u_"):
            u = _get_registered_user(pk)
            if u is None:
                return Response({"error": "یافت نشد"}, status=404)
            from .models import SaleInvoice, SalePayment
            has_docs = (SaleInvoice.objects.filter(customer=u).exists()
                        or SalePayment.objects.filter(invoice__customer=u).exists()
                        or u.orders.exists())
            if has_docs:
                u.is_active = False
                u.save(update_fields=["is_active"])
                logger.warning(f"[CONTACT] کاربر {u.id} ({u.phone}) غیرفعال شد — دارای سند")
                return Response({"deleted": True, "deactivated": True,
                                 "message": "کاربر سند داشت و به‌جای حذف، غیرفعال شد تا سابقه حفظ شود"})
            u.delete()
            logger.warning(f"[CONTACT] کاربر ثبت‌نامی {pk} توسط {request.user} حذف شد")
            return Response({"deleted": True, "deactivated": False})
        real_pk = str(pk)[2:] if str(pk).startswith("c_") else pk
        try:
            c = Contact.objects.get(pk=real_pk)
        except Contact.DoesNotExist:
            return Response({"error": "یافت نشد"}, status=404)
        has_docs = (c.purchase_invoices.exists() or c.shipping_invoices.exists()
                    or c.payments.exists() or c.extra_costs.exists())
        if has_docs:
            c.is_active = False
            c.save(update_fields=["is_active"])
            logger.warning(f"[CONTACT] طرف حساب {c.id} ({c.name}) غیرفعال شد — دارای سند")
            return Response({"deleted": True, "deactivated": True,
                             "message": "طرف حساب سند داشت و به‌جای حذف، غیرفعال شد تا سابقه حفظ شود"})
        c.delete()
        logger.warning(f"[CONTACT] طرف حساب {real_pk} توسط {request.user} حذف شد")
        return Response({"deleted": True, "deactivated": False})


class ContactUserActivationView(APIView):
    """
    POST /api/accounting/contacts/<pk>/activate-user/ — فعال‌سازی/تعیین رمز حساب کاربری
    سایت برای طرف حساب حضوری. مشتری حضوری‌ای که برایش طرف حساب ساخته‌ایم و بعداً
    بخواهد وارد سایت شود، رمز ندارد (کاربر سایه رمز ندارد) و ثبت‌نام با شماره تکراری
    هم ممکن نیست — ادمین این‌جا رمز تعیین می‌کند و مشتری با موبایل + رمز لاگین می‌کند.
    اگر کاربر سایه وجود نداشته باشد و موبایل معتبر باشد، همین‌جا ساخته و لینک می‌شود.
    بدنه: { "password": "..." }  (حداقل ۸ کاراکتر)
    """
    permission_classes = [IsAdminUser]

    def post(self, request, pk):
        if not _has_perm(request.user, 'contacts_edit'):
            return _forbidden()
        from apps.users.models import User, UserProfile
        real_pk = str(pk)[2:] if str(pk).startswith("c_") else pk
        try:
            c = Contact.objects.get(pk=real_pk)
        except (Contact.DoesNotExist, ValueError):
            return Response({"error": "طرف حساب یافت نشد"}, status=404)

        password = (request.data.get('password') or '').strip()
        if len(password) < 8:
            return Response({"error": "رمز عبور باید حداقل ۸ کاراکتر باشد"}, status=400)

        with transaction.atomic():
            u = _linked_user(c)
            if u is None:
                phone = (c.phone or '').strip()
                if not (phone.startswith('09') and len(phone) == 11 and phone.isdigit()):
                    return Response({'error': 'ابتدا در ویرایش طرف حساب، موبایل معتبر (09...) وارد کنید'}, status=400)
                existing = User.objects.filter(phone=phone).first()
                if existing:
                    u = existing
                    profile = getattr(u, 'profile', None)
                    if profile is None:
                        profile = UserProfile.objects.create(user=u)
                    if not profile.linked_contact_id:
                        profile.linked_contact = c
                        profile.save(update_fields=['linked_contact', 'updated_at'])
                else:
                    parts = c.name.split()
                    u = User(phone=phone,
                             first_name=' '.join(parts[:-1]) if len(parts) > 1 else c.name,
                             last_name=parts[-1] if len(parts) > 1 else '')
                    u.save()
                    UserProfile.objects.create(
                        user=u, linked_contact=c,
                        address=c.address, province=c.province,
                    )
            u.set_password(password)
            u.save(update_fields=['password'])
        logger.info(f"[CONTACT] حساب سایت برای طرف حساب {c.id} ({c.name}) فعال/تغییر رمز شد — {u.phone} توسط {request.user}")
        return Response({"ok": True, "phone": u.phone,
                         "message": f"حساب کاربری با موبایل {u.phone} فعال شد. مشتری با همین شماره و رمزی که تعیین کردید وارد سایت می‌شود."})


# ═══════════════════════════════════════════════════════════════
# Purchase Invoices — workflow دو مرحله‌ای
# ═══════════════════════════════════════════════════════════════

class PurchaseInvoiceListView(APIView):
    """
    GET  → لیست همه فاکتورها
    POST → ثبت سفارش جدید (مرحله ۱):
           supplier_id, date, rate_purchase_cny, warehouse_id (انبار در راه)
           اختیاری: shipping_contact_id (شرکت حمل)، invoice_number
           items
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        if not _has_perm(request.user, 'purchase_view'):
            return _forbidden()
        qs = PurchaseInvoice.objects.select_related(
            "supplier", "warehouse", "warehouse_destination", "shipping_contact",
            "created_by", "updated_by",
        ).order_by("-date")
        st = request.query_params.get("status")
        if st:
            qs = qs.filter(status=st)
        return Response([{
            "id": inv.id,
            "invoice_number": inv.invoice_number,
            "purchase_type": inv.purchase_type,
            "purchase_type_display": inv.get_purchase_type_display(),
            "supplier_id": inv.supplier_id,
            "supplier_name": inv.supplier.name,
            "shipping_contact_id": inv.shipping_contact_id,
            "shipping_contact_name": inv.shipping_contact.name if inv.shipping_contact else "",
            "warehouse_name": inv.warehouse.name if inv.warehouse else "—",
            "warehouse_destination_name": inv.warehouse_destination.name if inv.warehouse_destination else "—",
            "date": str(inv.date),
            "status": inv.status,
            "status_display": inv.get_status_display(),
            "rate_purchase_cny": inv.rate_purchase_cny,
            "rate_shipping_cny": inv.rate_shipping_cny or 0,
            "shipping_cost_cny": float(inv.shipping_cost_cny or 0),
            "clearance_cost_irr": inv.clearance_cost_irr or 0,
            "total_weight": inv.total_weight,
            "total_cny": float(inv.total_cny),
            "total_irr": inv.total_irr,
            "items_count": inv.items.count(),
            "inventory_applied": inv.inventory_applied,
            "is_complete": inv.is_complete,
            "received_at": inv.received_at.isoformat() if inv.received_at else None,
            **_audit_row(inv),
        } for inv in qs[:100]])

    @transaction.atomic
    def post(self, request):
        if not _has_perm(request.user, 'purchase_create'):
            return _forbidden()
        d = request.data
        try:
            ptype = d.get("purchase_type") or "foreign"
            if ptype not in ("foreign", "domestic"):
                return Response({"error": "نوع خرید نامعتبر است"}, status=400)
            if not d.get("supplier_id"):
                return Response({"error": "تامین‌کننده الزامی است"}, status=400)
            if not d.get("date"):
                return Response({"error": "تاریخ سفارش الزامی است"}, status=400)
            if ptype == "foreign" and not d.get("rate_purchase_cny"):
                return Response({"error": "نرخ یوان خرید الزامی است"}, status=400)
            if not d.get("warehouse_id"):
                return Response(
                    {"error": "انبار الزامی است" if ptype == "domestic" else "انبار در راه الزامی است"},
                    status=400,
                )
            items = d.get("items", [])
            if not items:
                return Response({"error": "حداقل یک آیتم باید وارد شود"}, status=400)

            inv = PurchaseInvoice.objects.create(
                supplier_id=d["supplier_id"],
                purchase_type=ptype,
                invoice_number=d.get("invoice_number", ""),
                date=d["date"],
                warehouse_id=d["warehouse_id"],
                rate_purchase_cny=_safe_int(d.get("rate_purchase_cny"), 0),
                rate_shipping_cny=_safe_int(d.get("rate_shipping_cny"), 0),
                shipping_contact_id=d.get("shipping_contact_id") or None,
                shipping_cost_cny=_safe_decimal(d.get("shipping_cost_cny"), "0"),
                clearance_cost_irr=_safe_int(d.get("clearance_cost_irr"), 0),
                note=d.get("note", ""),
                status=PurchaseInvoice.Status.ORDERED,
                created_by=request.user,
            )
            for it in items:
                PurchaseItem.objects.create(
                    invoice=inv,
                    variant_id=it["variant_id"],
                    quantity=_safe_int(it["quantity"]),
                    carton_count=_safe_int(it.get("carton_count"), 1),
                    carton_weight=_safe_decimal(it.get("carton_weight"), "0") or None,
                    unit_price_cny=_safe_decimal(it.get("unit_price_cny"), "0"),
                    unit_price_irr=_safe_int(it.get("unit_price_irr"), 0),
                    note=it.get("note", ""),
                )
            for extra in d.get("extra_costs", []):
                ExtraCost.objects.create(
                    invoice=inv,
                    cost_type=extra["cost_type"],
                    contact_id=extra.get("contact_id") or None,
                    amount_irr=_safe_int(extra["amount_irr"]),
                    description=extra.get("description", ""),
                    date=extra.get("date") or inv.date,
                )

            # خرید داخلی — بدون مرحله «منتظر رسیدن»؛ مستقیم رسیده می‌شود
            if ptype == "domestic":
                from django.utils import timezone
                inv.status = PurchaseInvoice.Status.RECEIVED
                inv.received_at = timezone.now()
                inv.received_by = request.user
                inv.save(update_fields=["status", "received_at", "received_by", "updated_at"])

            # اعمال موجودی به انبار در راه
            try:
                inv.apply_to_inventory(user=request.user)
                msg = " — موجودی به انبار اضافه شد" if ptype == "domestic" else " — موجودی به انبار در راه اضافه شد"
            except Exception as inv_err:
                logger.error(f"[PURCHASE] apply_to_inventory ناموفق: {inv_err}")
                msg = f" — هشدار: اعمال موجودی شکست خورد ({inv_err})"

            return Response({
                "id": inv.id,
                "status": inv.status,
                "inventory_applied": inv.inventory_applied,
                "message": f"سفارش ثبت شد{msg}",
            }, status=201)
        except Exception as e:
            logger.exception(f"[PURCHASE] خطا در ثبت سفارش: {e}")
            return Response({"error": str(e)}, status=400)


class PurchaseLastPriceView(APIView):
    """
    GET /api/accounting/purchase-invoices/last-price/?variant_id=&supplier_id=
    آخرین قیمت خرید یک کالا از یک تامین‌کننده + تاریخ — راهنمای فیلد قیمت در فرم فاکتور
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        variant_id = request.query_params.get("variant_id")
        supplier_id = request.query_params.get("supplier_id")
        item = (PurchaseItem.objects
                .filter(variant_id=variant_id, invoice__supplier_id=supplier_id)
                .exclude(invoice__status=PurchaseInvoice.Status.CANCELLED)
                .select_related("invoice")
                .order_by("-invoice__date", "-id")
                .first())
        if item is None:
            return Response({"found": False})
        return Response({
            "found": True,
            "unit_price_cny": float(item.unit_price_cny),
            "unit_price_irr": item.unit_price_irr,
            "date": str(item.invoice.date),
        })


class PurchaseInvoicePendingReceiveView(APIView):
    """GET → لیست فاکتورهای ORDERED (منتظر رسیدن)"""
    permission_classes = [IsAdminUser]

    def get(self, request):
        if not _has_perm(request.user, 'purchase_view'):
            return _forbidden()
        qs = PurchaseInvoice.objects.select_related(
            "supplier", "warehouse", "shipping_contact", "created_by"
        ).filter(status=PurchaseInvoice.Status.ORDERED).order_by("date")
        return Response([{
            "id": inv.id,
            "invoice_number": inv.invoice_number,
            "supplier_name": inv.supplier.name,
            "shipping_contact_name": inv.shipping_contact.name if inv.shipping_contact else "—",
            "warehouse_name": inv.warehouse.name if inv.warehouse else "—",
            "date": str(inv.date),
            "created_by": _user_label(inv.created_by),
            "items_count": inv.items.count(),
            "total_cny": float(inv.total_cny),
            "needs_data": {
                "rate_shipping_cny": not bool(inv.rate_shipping_cny),
                "shipping_cost_cny": not bool(inv.shipping_cost_cny),
                "clearance_cost_irr": not bool(inv.clearance_cost_irr),
                "carton_weight": any(not it.carton_weight for it in inv.items.all()),
            },
            "days_pending": _days_since(inv.date),
        } for inv in qs])


class PurchaseInvoiceReceiveView(APIView):
    """
    POST /api/accounting/purchase-invoices/<id>/receive/

    مرحله ۲: ثبت رسیدن کالا + انتقال به انبار مقصد

    body:
      destination_warehouse_id: int *
      rate_shipping_cny: int
      shipping_cost_cny: decimal
      clearance_cost_irr: int
      items: [{id, carton_weight, carton_count}]
      extra_costs: [...]
    """
    permission_classes = [IsAdminUser]

    @transaction.atomic
    def post(self, request, pk):
        if not _has_perm(request.user, 'purchase_edit'):
            return _forbidden()
        try:
            inv = PurchaseInvoice.objects.get(pk=pk)
        except PurchaseInvoice.DoesNotExist:
            return Response({"error": "یافت نشد"}, status=404)

        if inv.status == PurchaseInvoice.Status.RECEIVED:
            return Response({"error": "این فاکتور قبلاً RECEIVED شده"}, status=400)

        d = request.data
        dest_id = d.get("destination_warehouse_id")
        if not dest_id:
            return Response({"error": "انبار مقصد الزامی است"}, status=400)

        from apps.inventory.models import Warehouse
        try:
            destination = Warehouse.objects.get(id=dest_id)
        except Warehouse.DoesNotExist:
            return Response({"error": "انبار مقصد یافت نشد"}, status=400)

        # به‌روز کردن اطلاعات حمل
        if "rate_shipping_cny" in d:
            inv.rate_shipping_cny = _safe_int(d["rate_shipping_cny"], 0)
        if "shipping_contact_id" in d:
            inv.shipping_contact_id = d["shipping_contact_id"] or None
        if "shipping_cost_cny" in d:
            inv.shipping_cost_cny = _safe_decimal(d["shipping_cost_cny"], "0")
        if "clearance_cost_irr" in d:
            inv.clearance_cost_irr = _safe_int(d["clearance_cost_irr"], 0)
        if "note" in d:
            inv.note = d["note"]
        inv.updated_by = request.user
        inv.save()

        # وزن نهایی هر آیتم
        for it_data in d.get("items", []):
            try:
                item = PurchaseItem.objects.get(id=it_data["id"], invoice=inv)
                if "carton_weight" in it_data:
                    item.carton_weight = _safe_decimal(it_data["carton_weight"], "0")
                if "carton_count" in it_data:
                    item.carton_count = _safe_int(it_data["carton_count"], 1)
                item.save()
            except PurchaseItem.DoesNotExist:
                continue

        # هزینه‌های جانبی
        for extra in d.get("extra_costs", []):
            ExtraCost.objects.create(
                invoice=inv,
                cost_type=extra["cost_type"],
                contact_id=extra.get("contact_id") or None,
                amount_irr=_safe_int(extra["amount_irr"]),
                description=extra.get("description", ""),
                date=extra.get("date") or inv.date,
            )

        # اعمال رسیدن
        try:
            inv.mark_received(destination_warehouse=destination, user=request.user)
            return Response({
                "id": inv.id,
                "status": inv.status,
                "warehouse_destination": destination.name,
                "message": f"کالا تحویل گرفته شد و به انبار {destination.name} منتقل شد",
            }, status=200)
        except Exception as exc:
            logger.exception(f"[PURCHASE] mark_received ناموفق: {exc}")
            return Response({"error": str(exc)}, status=400)


class PurchaseInvoiceDetailView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, pk):
        if not _has_perm(request.user, 'purchase_view'):
            return _forbidden()
        try:
            inv = PurchaseInvoice.objects.select_related(
                "supplier", "warehouse", "warehouse_destination", "shipping_contact"
            ).get(pk=pk)
        except PurchaseInvoice.DoesNotExist:
            return Response({"error": "یافت نشد"}, status=404)

        items = [{
            "id": it.id,
            "variant_id": it.variant_id,
            "variant_sku": it.variant.sku,
            "product_name": it.variant.product.name,
            "quantity": it.quantity,
            "carton_count": it.carton_count,
            "carton_weight": float(it.carton_weight) if it.carton_weight else 0,
            "total_weight": it.total_weight,
            "unit_price_cny": float(it.unit_price_cny),
            "unit_price_irr": it.unit_price_irr,
            "subtotal_cny": float(it.subtotal_cny),
            "shipping_cost_irr": it.shipping_cost_irr,
            "clearance_cost_irr": it.clearance_cost_irr,
            "extra_cost_irr": it.extra_cost_irr,
            "unit_cost_irr": it.unit_cost_irr,
            "note": it.note,
        } for it in inv.items.select_related("variant__product").all()]

        extra_costs = [{
            "id": e.id, "cost_type": e.cost_type,
            "cost_type_display": e.get_cost_type_display(),
            "contact_id": e.contact_id,
            "contact_name": e.contact.name if e.contact else "",
            "amount_irr": e.amount_irr,
            "description": e.description,
        } for e in inv.extra_costs.all()]

        payments = [{
            "id": p.id, "date": str(p.date),
            "direction": p.direction,
            "direction_display": p.get_direction_display(),
            "payment_type_display": p.get_payment_type_display(),
            "amount": float(p.amount), "currency": p.currency,
            "amount_irr": p.amount_irr, "reference": p.reference,
        } for p in inv.payments.all()]

        return Response({
            "id": inv.id,
            "invoice_number": inv.invoice_number,
            "purchase_type": inv.purchase_type,
            "purchase_type_display": inv.get_purchase_type_display(),
            "supplier": {"id": inv.supplier_id, "name": inv.supplier.name},
            "date": str(inv.date),
            "status": inv.status,
            "status_display": inv.get_status_display(),
            "warehouse": {"id": inv.warehouse_id, "name": inv.warehouse.name} if inv.warehouse else None,
            "warehouse_destination": {"id": inv.warehouse_destination_id, "name": inv.warehouse_destination.name} if inv.warehouse_destination else None,
            "rate_purchase_cny": inv.rate_purchase_cny,
            "rate_shipping_cny": inv.rate_shipping_cny or 0,
            "shipping_contact": {"id": inv.shipping_contact_id, "name": inv.shipping_contact.name} if inv.shipping_contact else None,
            "shipping_cost_cny": float(inv.shipping_cost_cny or 0),
            "clearance_cost_irr": inv.clearance_cost_irr or 0,
            "total_weight": inv.total_weight,
            "total_cny": float(inv.total_cny),
            "total_irr": inv.total_irr,
            "note": inv.note,
            "is_complete": inv.is_complete,
            "inventory_applied": inv.inventory_applied,
            "received_at": inv.received_at.isoformat() if inv.received_at else None,
            **_audit_row(inv),
            "items": items,
            "extra_costs": extra_costs,
            "payments": payments,
        })

    def patch(self, request, pk):
        if not _has_perm(request.user, 'purchase_edit'):
            return _forbidden()
        try:
            inv = PurchaseInvoice.objects.get(pk=pk)
        except PurchaseInvoice.DoesNotExist:
            return Response({"error": "یافت نشد"}, status=404)

        d = request.data
        status_before = inv.status

        # آیتم‌ها و هزینه‌های جانبی فقط در وضعیت «سفارش داده شده» قابل ویرایش‌اند
        if ("items" in d or "extra_costs" in d) and status_before != PurchaseInvoice.Status.ORDERED:
            return Response(
                {"error": "آیتم‌های فاکتور رسیده/تسویه/لغو شده قابل ویرایش نیستند"},
                status=400,
            )
        if "items" in d and not d["items"]:
            return Response({"error": "حداقل یک آیتم باید وارد شود"}, status=400)

        header_fields = [
            "supplier_id", "date", "invoice_number", "rate_purchase_cny",
            "rate_shipping_cny", "shipping_contact_id", "shipping_cost_cny",
            "clearance_cost_irr", "warehouse_id", "warehouse_destination_id", "note",
        ]
        has_header = any(f in d for f in header_fields)
        if has_header and status_before == PurchaseInvoice.Status.CANCELLED:
            return Response({"error": "فاکتور لغو شده قابل ویرایش نیست"}, status=400)

        try:
            with transaction.atomic():
                # ── سرفاکتور ──
                if "supplier_id" in d:
                    inv.supplier_id = d["supplier_id"]
                if "date" in d:
                    inv.date = d["date"]
                if "invoice_number" in d:
                    inv.invoice_number = d["invoice_number"]
                if "rate_purchase_cny" in d:
                    inv.rate_purchase_cny = _safe_int(d["rate_purchase_cny"])
                if "rate_shipping_cny" in d:
                    inv.rate_shipping_cny = _safe_int(d["rate_shipping_cny"], 0)
                if "shipping_contact_id" in d:
                    inv.shipping_contact_id = d["shipping_contact_id"] or None
                if "shipping_cost_cny" in d:
                    inv.shipping_cost_cny = _safe_decimal(d["shipping_cost_cny"], "0")
                if "clearance_cost_irr" in d:
                    inv.clearance_cost_irr = _safe_int(d["clearance_cost_irr"], 0)
                if "warehouse_id" in d:
                    inv.warehouse_id = d["warehouse_id"]
                if "warehouse_destination_id" in d:
                    inv.warehouse_destination_id = d["warehouse_destination_id"] or None
                if "note" in d:
                    inv.note = d["note"]
                if "status" in d:
                    inv.status = d["status"]
                inv.save()

                # ── آیتم‌ها (جایگزینی کامل) ──
                if "items" in d:
                    self._replace_items(inv, d["items"], request.user)

                # ── هزینه‌های جانبی (جایگزینی کامل) ──
                if "extra_costs" in d:
                    inv.extra_costs.all().delete()
                    for extra in d["extra_costs"]:
                        ExtraCost.objects.create(
                            invoice=inv,
                            cost_type=extra["cost_type"],
                            contact_id=extra.get("contact_id") or None,
                            amount_irr=_safe_int(extra["amount_irr"]),
                            description=extra.get("description", ""),
                            date=extra.get("date") or inv.date,
                        )

                if has_header or "items" in d or "extra_costs" in d:
                    inv.calculate_items_cost()
        except ValueError as e:
            return Response({"error": str(e)}, status=400)
        except Exception as e:
            logger.exception(f"[PURCHASE] خطا در ویرایش فاکتور: {e}")
            return Response({"error": str(e)}, status=400)

        return Response({"id": inv.id, "status": inv.status})

    def _replace_items(self, inv, items_data, user=None):
        """جایگزینی آیتم‌ها با برگشت/اعمال موجودی (فقط در وضعیت ordered)"""
        from apps.catalog.models import ProductVariant
        from apps.inventory.models import StockMovement

        old_items = list(inv.items.all())
        if inv.inventory_applied:
            # برگشت موجودی آیتم‌های قبلی
            for item in old_items:
                variant = ProductVariant.objects.get(id=item.variant_id)
                variant.stock_quantity = max(0, variant.stock_quantity - item.quantity)
                variant.save(update_fields=["stock_quantity"])
                if inv.warehouse is not None:
                    StockMovement.record(
                        warehouse=inv.warehouse,
                        variant=variant,
                        movement_type=StockMovement.MovementType.ADJUSTMENT,
                        quantity=-item.quantity,
                        unit_price=int(item.unit_cost_irr or 0),
                        reference=inv.invoice_number or str(inv.id),
                        note="ویرایش فاکتور — برگشت موجودی",
                        user=user,
                    )

        inv.items.all().delete()

        new_items = []
        for it in items_data:
            new_items.append(PurchaseItem.objects.create(
                invoice=inv,
                variant_id=it["variant_id"],
                quantity=_safe_int(it["quantity"]),
                carton_count=_safe_int(it.get("carton_count"), 1),
                carton_weight=_safe_decimal(it.get("carton_weight"), "0") or None,
                unit_price_cny=_safe_decimal(it.get("unit_price_cny"), "0"),
                unit_price_irr=_safe_int(it.get("unit_price_irr"), 0),
                note=it.get("note", ""),
            ))

        if inv.inventory_applied:
            # اعمال موجودی آیتم‌های جدید
            for item in new_items:
                variant = ProductVariant.objects.get(id=item.variant_id)
                variant.stock_quantity += item.quantity
                variant.save(update_fields=["stock_quantity"])
                if inv.warehouse is not None:
                    StockMovement.record(
                        warehouse=inv.warehouse,
                        variant=variant,
                        movement_type=StockMovement.MovementType.PURCHASE,
                        quantity=item.quantity,
                        unit_price=int(item.unit_cost_irr or 0),
                        reference=inv.invoice_number or str(inv.id),
                        note="ویرایش فاکتور",
                        user=user,
                    )

    @transaction.atomic
    def delete(self, request, pk):
        """حذف فاکتور خرید + برگشت موجودی انبار و کاردکس — فقط بدون پرداخت ثبت‌شده."""
        if not _has_perm(request.user, 'purchase_edit'):
            return _forbidden()
        try:
            inv = PurchaseInvoice.objects.get(pk=pk)
        except PurchaseInvoice.DoesNotExist:
            return Response({"error": "یافت نشد"}, status=404)
        if inv.payments.exists():
            return Response({"error": "این فاکتور پرداخت ثبت‌شده دارد — اول پرداخت‌ها را حذف کنید"}, status=400)

        from apps.inventory.models import StockMovement, WarehouseStock
        from apps.catalog.models import ProductVariant
        from collections import defaultdict

        if inv.inventory_applied:
            refs = {inv.invoice_number or "", str(inv.id)}
            movements = StockMovement.objects.filter(reference__in=refs)
            # برگشت موجودی انبارها بر اساس خالص حرکت‌های همین فاکتور
            nets = defaultdict(int)
            for m in movements:
                nets[(m.warehouse_id, m.variant_id)] += m.quantity
            for (wid, vid), qty in nets.items():
                if not qty:
                    continue
                ws = WarehouseStock.objects.filter(warehouse_id=wid, variant_id=vid).first()
                if ws:
                    ws.quantity = max(0, ws.quantity - qty)
                    ws.save(update_fields=["quantity"])
            movements.delete()
            # برگشت موجودی کلی واریانت‌ها (در مرحله ۱ به ازای هر آیتم اضافه شده بود)
            for item in inv.items.all():
                v = ProductVariant.objects.filter(pk=item.variant_id).first()
                if v:
                    v.stock_quantity = max(0, v.stock_quantity - item.quantity)
                    v.save(update_fields=["stock_quantity"])

        inv.delete()
        logger.warning(f"[PURCHASE] فاکتور {pk} توسط {request.user} حذف شد")
        return Response({"deleted": True})


# ─── Payments ────────────────────────────────────────────────

from apps.core.utils import user_label as _user_label, audit_row as _audit_row


def _payment_row(p):
    """سطر خروجی یک پرداخت (مشترک بین لیست و جزئیات)"""
    row = {
        "id": p.id,
        "contact_id": p.contact_id,
        "contact_name": p.contact.name if p.contact else "",
        "invoice_id": p.invoice_id,
        "invoice_label": (p.invoice.invoice_number or str(p.invoice_id)) if p.invoice else None,
        "from_account_id": p.from_account_id,
        "from_account_name": p.from_account.name if p.from_account else "",
        "to_account_id": p.to_account_id,
        "to_account_name": p.to_account.name if p.to_account else "",
        "direction": p.direction,
        "payment_type": p.payment_type,
        "currency": p.currency,
        "amount": float(p.amount),
        "rate_irr": p.rate_irr,
        "amount_irr": p.amount_irr,
        "date": str(p.date),
        "reference": p.reference,
        "note": p.note,
    }
    row.update(_audit_row(p))
    return row


class PaymentListView(APIView):
    """
    GET  → لیست پرداخت‌ها (فیلتر: account_id, direction, contact_id, invoice_id)
    POST → ثبت پرداخت جدید
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        if not _has_perm(request.user, 'purchase_view'):
            return _forbidden()
        qs = Payment.objects.select_related(
            "contact", "from_account", "to_account", "invoice"
        ).order_by("-date", "-id")
        account_id = request.query_params.get("account_id")
        if account_id:
            qs = qs.filter(Q(from_account_id=account_id) | Q(to_account_id=account_id))
        direction = request.query_params.get("direction")
        if direction:
            qs = qs.filter(direction=direction)
        contact_id = request.query_params.get("contact_id")
        if contact_id:
            qs = qs.filter(contact_id=contact_id)
        invoice_id = request.query_params.get("invoice_id")
        if invoice_id:
            qs = qs.filter(invoice_id=invoice_id)
        return Response([_payment_row(p) for p in qs[:200]])

    def post(self, request):
        if not _has_perm(request.user, 'purchase_create'):
            return _forbidden()
        d = request.data
        try:
            p = Payment.objects.create(
                contact_id=d.get("contact_id") or None,  # اختیاری — سند حسابداری/جابجایی درون بانکی بدون طرف حساب
                invoice_id=d.get("invoice_id") or None,
                from_account_id=d.get("from_account_id") or None,
                to_account_id=d.get("to_account_id") or None,
                direction=d["direction"],
                payment_type=d.get("payment_type", "transfer"),
                currency=d["currency"],
                amount=_safe_decimal(d["amount"]),
                rate_irr=_safe_int(d.get("rate_irr"), 0),
                date=d["date"],
                reference=d.get("reference", ""),
                note=d.get("note", ""),
                created_by=request.user,
            )
            return Response({"id": p.id, "amount_irr": p.amount_irr, "message": "پرداخت ثبت شد"}, status=201)
        except Exception as e:
            return Response({"error": str(e)}, status=400)


class PaymentDetailView(APIView):
    """GET/PATCH/DELETE روی یک پرداخت"""
    permission_classes = [IsAdminUser]

    def get(self, request, pk):
        if not _has_perm(request.user, 'purchase_view'):
            return _forbidden()
        try:
            p = Payment.objects.select_related(
                "contact", "from_account", "to_account", "invoice"
            ).get(pk=pk)
        except Payment.DoesNotExist:
            return Response({"error": "یافت نشد"}, status=404)
        return Response(_payment_row(p))

    def patch(self, request, pk):
        if not _has_perm(request.user, 'payment_edit'):
            return _forbidden()
        try:
            p = Payment.objects.get(pk=pk)
        except Payment.DoesNotExist:
            return Response({"error": "یافت نشد"}, status=404)
        d = request.data
        try:
            if "contact_id" in d:
                p.contact_id = d["contact_id"] or None
            if "invoice_id" in d:
                p.invoice_id = d["invoice_id"] or None
            if "from_account_id" in d:
                p.from_account_id = d["from_account_id"] or None
            if "to_account_id" in d:
                p.to_account_id = d["to_account_id"] or None
            if "direction" in d:
                p.direction = d["direction"]
            if "payment_type" in d:
                p.payment_type = d["payment_type"]
            if "currency" in d:
                p.currency = d["currency"]
            if "amount" in d:
                p.amount = _safe_decimal(d["amount"])
            if "rate_irr" in d:
                p.rate_irr = _safe_int(d["rate_irr"], 0)
            if "date" in d:
                p.date = d["date"]
            if "reference" in d:
                p.reference = d["reference"]
            if "note" in d:
                p.note = d["note"]
            p.updated_by = request.user
            p.save()
            return Response({"id": p.id, "amount_irr": p.amount_irr, "message": "پرداخت به‌روز شد"})
        except Exception as e:
            return Response({"error": str(e)}, status=400)

    def delete(self, request, pk):
        if not _has_perm(request.user, 'payment_edit'):
            return _forbidden()
        try:
            p = Payment.objects.get(pk=pk)
        except Payment.DoesNotExist:
            return Response({"error": "یافت نشد"}, status=404)
        p.delete()
        return Response(status=204)


# ─── Reports ─────────────────────────────────────────────────

class BalanceReportView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        contacts = Contact.objects.filter(is_active=True)
        data = []
        for c in contacts:
            bal_irr = c.balance_irr
            bal_cny = float(c.balance_cny)
            if bal_irr != 0 or bal_cny != 0:
                data.append({
                    "id": c.id, "name": c.name,
                    "contact_type_display": c.get_contact_type_display(),
            "partner_tier": c.partner_tier,
            "partner_tier_display": c.get_partner_tier_display(),
                    "balance_irr": bal_irr, "balance_cny": bal_cny,
                    "status_irr": "بستانکار" if bal_irr > 0 else "بدهکار",
                    "status_cny": "بستانکار" if bal_cny > 0 else "بدهکار",
                })
        return Response({"contacts": data})


class SalesChannelReportView(APIView):
    """
    GET /api/accounting/reports/sales-channels/ — سهم کانال‌های فروش:
    حضوری (فاکتور دستی، source=manual) در برابر سایت (source=order).
    پارامترهای اختیاری: from / to (تاریخ ISO) بر اساس تاریخ ساخت فاکتور.
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        if not _has_perm(request.user, 'sale_view'):
            return _forbidden()
        from .models import SaleInvoice
        qs = SaleInvoice.objects.filter(status__in=['confirmed', 'paid']).prefetch_related('items')
        date_from = request.query_params.get('from')
        date_to = request.query_params.get('to')
        if date_from:
            qs = qs.filter(issue_date__gte=date_from)
        if date_to:
            qs = qs.filter(issue_date__lte=date_to)

        buckets = {'manual': {'count': 0, 'total_irr': 0, 'total_cny': 0.0},
                   'order':  {'count': 0, 'total_irr': 0, 'total_cny': 0.0}}
        for inv in qs:
            b = buckets['order' if inv.source == 'order' else 'manual']
            b['count'] += 1
            if inv.currency == 'CNY':
                b['total_cny'] += inv.total_amount
            else:
                b['total_irr'] += inv.total_amount

        total_count = sum(b['count'] for b in buckets.values())
        total_irr = sum(b['total_irr'] for b in buckets.values())
        channels = []
        for key, label in (('manual', 'فروش حضوری'), ('order', 'فروش سایت')):
            b = buckets[key]
            channels.append({
                'key': key, 'label': label,
                'count': b['count'],
                'total_irr': b['total_irr'],
                'total_cny': round(b['total_cny'], 2),
                'count_percent': round(b['count'] / total_count * 100, 1) if total_count else 0,
                'amount_percent': round(b['total_irr'] / total_irr * 100, 1) if total_irr else 0,
            })
        return Response({'channels': channels, 'total_count': total_count, 'total_irr': total_irr})


# ─── Sale Invoices ───────────────────────────────────────────

class SaleInvoiceListView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        if not _has_perm(request.user, 'sale_view'):
            return _forbidden()
        from .models import SaleInvoice
        qs = SaleInvoice.objects.select_related('customer', 'created_by', 'updated_by', 'order').order_by('-created_at')[:100]
        if request.query_params.get('due') == '1':
            from django.utils import timezone
            qs = [i for i in qs if i.settlement == 'credit' and i.due_date
                  and i.due_date <= timezone.now().date() and i.remaining_amount > 0]
        return Response([{
            'id': inv.id, 'invoice_number': inv.invoice_number,
            'source': inv.source, 'source_display': inv.get_source_display(),
            'sale_type': inv.sale_type, 'sale_type_display': inv.get_sale_type_display(),
            'currency': inv.currency,
            'settlement': inv.settlement, 'settlement_display': inv.get_settlement_display(),
            'due_date': str(inv.due_date) if inv.due_date else '',
            'issue_date': str(inv.issue_date) if inv.issue_date else '',
            'customer_name': inv.customer_name or str(inv.customer),
            'customer_phone': inv.customer_phone,
            'status': inv.status, 'status_display': inv.get_status_display(),
            'subtotal': inv.subtotal, 'discount_amount': inv.discount_amount,
            'shipping_cost': inv.shipping_cost,
            'total_amount': inv.total_amount, 'paid_amount': inv.paid_amount,
            'remaining_amount': inv.remaining_amount,
            'total_cost': inv.total_cost, 'gross_profit': inv.gross_profit,
            'items_count': inv.items.count(),
            'stock_deducted': inv.stock_deducted,
            'order_number': inv.order.order_number if inv.order else '',
            **_audit_row(inv),
        } for inv in qs])

    @transaction.atomic
    def post(self, request):
        if not _has_perm(request.user, 'sale_create'):
            return _forbidden()
        from .models import SaleInvoice, SaleItem
        d = request.data
        try:
            from apps.users.models import User
            customer_id = d.get('customer_id')
            if not customer_id:
                return Response({'error': 'customer_id الزامی است'}, status=400)
            customer = User.objects.get(id=customer_id)

            from django.utils import timezone
            inv = SaleInvoice.objects.create(
                source=d.get('source', 'manual'),
                sale_type=d.get('sale_type', 'domestic'),
                currency=d.get('currency', 'IRR'),
                settlement=d.get('settlement', 'cash'),
                due_date=d.get('due_date') or None,
                issue_date=d.get('issue_date') or timezone.localdate(),
                order_id=d.get('order_id') or None,
                customer=customer,
                customer_name=d.get('customer_name', str(customer)),
                customer_phone=d.get('customer_phone', ''),
                discount_amount=_safe_int(d.get('discount_amount'), 0),
                shipping_cost=_safe_int(d.get('shipping_cost'), 0),
                tax_amount=_safe_int(d.get('tax_amount'), 0),
                note=d.get('note', ''),
                status=d.get('status', 'draft'),
                created_by=request.user,
            )
            for it_d in d.get('items', []):
                SaleItem.objects.create(
                    invoice=inv,
                    variant_id=it_d['variant_id'],
                    quantity=_safe_int(it_d['quantity']),
                    unit_price=_safe_int(it_d['unit_price']),
                    discount_percent=_safe_decimal(it_d.get('discount_percent'), "0"),
                )

            try:
                inv.deduct_from_inventory(user=request.user)
                stock_msg = " — موجودی کسر شد"
            except ValueError as ve:
                inv.delete()
                return Response({"error": str(ve)}, status=400)
            except Exception as deduct_err:
                logger.error(f"[SALE] deduct_from_inventory ناموفق: {deduct_err}")
                stock_msg = " — هشدار: کسر موجودی شکست خورد"

            # پیامک اطلاعات حساب پرداخت برای فاکتور دستی تأییدشده — best-effort
            if inv.status == 'confirmed':
                from apps.notifications.services import notify_invoice_account_info_sms
                notify_invoice_account_info_sms(inv)

            return Response({
                'id': inv.id, 'invoice_number': inv.invoice_number,
                'total_amount': inv.total_amount,
                'stock_deducted': inv.stock_deducted,
                'message': f'فاکتور صادر شد{stock_msg}',
            }, status=201)
        except Exception as e:
            logger.exception(f"[SALE] خطا: {e}")
            return Response({'error': str(e)}, status=400)


class SaleInvoiceDetailView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, pk):
        if not _has_perm(request.user, 'sale_view'):
            return _forbidden()
        from .models import SaleInvoice
        try:
            inv = SaleInvoice.objects.select_related('customer', 'created_by', 'order').get(pk=pk)
        except SaleInvoice.DoesNotExist:
            return Response({'error': 'یافت نشد'}, status=404)

        items = [{
            'id': it.id, 'variant_id': it.variant_id,
            'variant_sku': it.variant.sku,
            'product_name': it.variant.product.name,
            'quantity': it.quantity, 'unit_price': it.unit_price,
            'discount_percent': float(it.discount_percent),
            'subtotal': it.subtotal, 'unit_cost': it.unit_cost,
            'total_cost': it.total_cost, 'profit': it.profit,
        } for it in inv.items.select_related('variant__product').all()]

        payments = [{
            'id': p.id, 'method': p.method,
            'method_display': p.get_method_display(),
            'amount': p.amount, 'date': str(p.date),
            'reference': p.reference,
            'to_account': p.to_account.name if p.to_account else '',
            'created_by': str(p.created_by) if p.created_by else '',
            'created_at': p.created_at.strftime('%Y-%m-%d %H:%M'),
        } for p in inv.sale_payments.all()]

        return Response({
            'id': inv.id, 'invoice_number': inv.invoice_number,
            'source': inv.source, 'source_display': inv.get_source_display(),
            'sale_type': inv.sale_type, 'sale_type_display': inv.get_sale_type_display(),
            'currency': inv.currency,
            'settlement': inv.settlement, 'settlement_display': inv.get_settlement_display(),
            'due_date': str(inv.due_date) if inv.due_date else '',
            'issue_date': str(inv.issue_date) if inv.issue_date else '',
            'customer_id': inv.customer_id,
            'customer_name': inv.customer_name or str(inv.customer),
            'customer_phone': inv.customer_phone,
            'status': inv.status, 'status_display': inv.get_status_display(),
            'subtotal': inv.subtotal, 'discount_amount': inv.discount_amount,
            'shipping_cost': inv.shipping_cost, 'tax_amount': inv.tax_amount,
            'total_amount': inv.total_amount, 'paid_amount': inv.paid_amount,
            'remaining_amount': inv.remaining_amount,
            'total_cost': inv.total_cost, 'gross_profit': inv.gross_profit,
            'stock_deducted': inv.stock_deducted, 'note': inv.note,
            'order_number': inv.order.order_number if inv.order else '',
            **_audit_row(inv),
            'items': items, 'payments': payments,
        })

    def patch(self, request, pk):
        if not _has_perm(request.user, 'sale_edit'):
            return _forbidden()
        from .models import SaleInvoice, SaleItem
        try:
            inv = SaleInvoice.objects.get(pk=pk)
        except SaleInvoice.DoesNotExist:
            return Response({'error': 'یافت نشد'}, status=404)

        d = request.data
        editable = inv.status in ('draft', 'confirmed')

        # آیتم‌ها فقط در draft/confirmed و فقط برای فاکتورهای دستی
        if 'items' in d:
            if inv.source != SaleInvoice.InvoiceSource.MANUAL:
                return Response({'error': 'آیتم‌های فاکتور سفارش سایت قابل ویرایش نیستند'}, status=400)
            if not editable:
                return Response({'error': 'آیتم‌های فاکتور تسویه/لغو شده قابل ویرایش نیستند'}, status=400)
            if not d['items']:
                return Response({'error': 'حداقل یک آیتم باید وارد شود'}, status=400)

        # سرفاکتور فقط در draft/confirmed — در paid/cancelled فقط تغییر وضعیت
        header_fields = ['customer_name', 'customer_phone', 'discount_amount',
                         'shipping_cost', 'tax_amount', 'note', 'issue_date']
        if any(f in d for f in header_fields) and not editable:
            return Response({'error': 'فاکتور تسویه/لغو شده فقط تغییر وضعیت می‌گیرد'}, status=400)

        try:
            with transaction.atomic():
                if 'customer_name' in d:
                    inv.customer_name = d['customer_name']
                if 'customer_phone' in d:
                    inv.customer_phone = d['customer_phone']
                if 'discount_amount' in d:
                    inv.discount_amount = _safe_int(d['discount_amount'], 0)
                if 'shipping_cost' in d:
                    inv.shipping_cost = _safe_int(d['shipping_cost'], 0)
                if 'tax_amount' in d:
                    inv.tax_amount = _safe_int(d['tax_amount'], 0)
                if 'note' in d:
                    inv.note = d['note']
                if 'issue_date' in d:
                    inv.issue_date = d['issue_date'] or inv.issue_date
                old_inv_status = inv.status
                if 'status' in d:
                    inv.status = d['status']
                inv.updated_by = request.user
                inv.save()

                # پیامک تأیید فاکتور/پیش‌فاکتور به مشتری — best-effort
                if inv.status == 'confirmed' and old_inv_status == 'draft':
                    from apps.notifications.services import (
                        notify_invoice_confirmed_sms, notify_invoice_account_info_sms)
                    notify_invoice_confirmed_sms(inv)
                    if inv.source == 'manual':
                        notify_invoice_account_info_sms(inv)

                if 'items' in d:
                    self._replace_items(inv, d['items'], request.user)
        except ValueError as e:
            return Response({'error': str(e)}, status=400)
        except Exception as e:
            logger.exception(f"[SALE] خطا در ویرایش فاکتور: {e}")
            return Response({'error': str(e)}, status=400)

        return Response({'id': inv.id, 'status': inv.status})

    def _replace_items(self, inv, items_data, user=None):
        """جایگزینی آیتم‌ها با برگشت/کسر مجدد موجودی (فقط فاکتور دستی)"""
        from apps.catalog.models import ProductVariant
        from apps.inventory.models import Warehouse, StockMovement
        from .models import SaleItem

        # انبار پیش‌فرض فروش — همان منطق _record_warehouse_outflow
        warehouse = (
            Warehouse.objects.filter(is_public=True, is_active=True).first()
            or Warehouse.objects.filter(is_active=True).first()
        )

        old_items = list(inv.items.all())
        if inv.stock_deducted:
            # برگشت موجودی آیتم‌های قبلی
            for item in old_items:
                variant = ProductVariant.objects.get(id=item.variant_id)
                variant.stock_quantity += item.quantity
                variant.save(update_fields=["stock_quantity"])
                if warehouse is not None:
                    StockMovement.record(
                        warehouse=warehouse,
                        variant=variant,
                        movement_type=StockMovement.MovementType.ADJUSTMENT,
                        quantity=item.quantity,
                        unit_price=int(item.unit_price),
                        reference=inv.invoice_number,
                        note="ویرایش فاکتور فروش — برگشت موجودی",
                        user=user,
                    )

        inv.items.all().delete()

        new_items = []
        for it in items_data:
            new_items.append(SaleItem.objects.create(
                invoice=inv,
                variant_id=it['variant_id'],
                quantity=_safe_int(it['quantity']),
                unit_price=_safe_int(it['unit_price']),
                discount_percent=_safe_decimal(it.get('discount_percent'), "0"),
            ))

        if inv.stock_deducted:
            # چک موجودی قبل از کسر
            for item in new_items:
                variant = ProductVariant.objects.get(id=item.variant_id)
                if variant.available_stock < item.quantity:
                    raise ValueError(
                        f"موجودی کافی برای '{variant.sku}' وجود ندارد. "
                        f"موجود: {variant.available_stock} | لازم: {item.quantity}"
                    )
            # کسر موجودی آیتم‌های جدید
            for item in new_items:
                variant = ProductVariant.objects.get(id=item.variant_id)
                variant.deduct_stock(item.quantity)
                inv._record_warehouse_outflow(item, user)

    @transaction.atomic
    def delete(self, request, pk):
        """حذف فاکتور فروش + برگشت موجودی — فقط پیش‌نویس و بدون دریافت ثبت‌شده."""
        if not _has_perm(request.user, 'sale_edit'):
            return _forbidden()
        from .models import SaleInvoice
        try:
            inv = SaleInvoice.objects.get(pk=pk)
        except SaleInvoice.DoesNotExist:
            return Response({'error': 'یافت نشد'}, status=404)
        if inv.status != SaleInvoice.Status.DRAFT:
            return Response({'error': 'فاکتور تأییدشده قابل حذف نیست — از ابطال استفاده کنید'}, status=400)
        if inv.sale_payments.exists():
            return Response({'error': 'این فاکتور دریافت ثبت‌شده دارد — اول دریافت‌ها را حذف کنید'}, status=400)

        from apps.inventory.models import StockMovement, WarehouseStock
        from apps.catalog.models import ProductVariant
        from collections import defaultdict

        if inv.stock_deducted:
            movements = StockMovement.objects.filter(
                movement_type=StockMovement.MovementType.SALE,
                reference=inv.invoice_number,
            )
            # برگشت موجودی انبارها بر اساس خالص حرکت‌های همین فاکتور (منفی = خروج)
            nets = defaultdict(int)
            for m in movements:
                nets[(m.warehouse_id, m.variant_id)] += m.quantity
            for (wid, vid), qty in nets.items():
                if not qty:
                    continue
                ws = WarehouseStock.objects.filter(warehouse_id=wid, variant_id=vid).first()
                if ws:
                    ws.quantity = max(0, ws.quantity - qty)
                    ws.save(update_fields=["quantity"])
            movements.delete()
            # برگشت موجودی کلی واریانت‌ها
            for item in inv.items.all():
                v = ProductVariant.objects.filter(pk=item.variant_id).first()
                if v:
                    v.stock_quantity += item.quantity
                    v.save(update_fields=["stock_quantity"])

        inv.delete()
        logger.warning(f"[SALE] فاکتور {inv.invoice_number} توسط {request.user} حذف شد")
        return Response({"deleted": True})


class SaleInvoiceVoidView(APIView):
    """
    POST /api/accounting/sale-invoices/<pk>/void/
    ابطال فاکتور فروش — وضعیت به cancelled می‌رود و همه ردیف‌های تسویه غیرفعال می‌شوند.
    """
    permission_classes = [IsAdminUser]

    @transaction.atomic
    def post(self, request, pk):
        if not _has_perm(request.user, 'sale_edit'):
            return _forbidden()
        from .models import SaleInvoice
        try:
            inv = SaleInvoice.objects.get(pk=pk)
        except SaleInvoice.DoesNotExist:
            return Response({'error': 'یافت نشد'}, status=404)
        if inv.status == SaleInvoice.Status.CANCELLED:
            return Response({'error': 'این فاکتور قبلاً باطل شده است'}, status=400)

        inv.status = SaleInvoice.Status.CANCELLED
        inv.updated_by = request.user
        inv.save(update_fields=['status', 'updated_by', 'updated_at'])
        inv.settlement_lines.update(is_active=False)
        logger.warning(f"[SALE] فاکتور {inv.invoice_number} توسط {request.user} باطل شد")
        return Response({
            'id': inv.id,
            'invoice_number': inv.invoice_number,
            'status': inv.status,
        })


class SaleInvoiceSendAccountInfoView(APIView):
    """
    POST /api/accounting/sale-invoices/<pk>/send-account-info/
    ارسال دستی پیامک اطلاعات حساب پرداخت برای فاکتور فروش. حساب‌ها دستی وارد می‌شوند (accounts: [{account_number, holder}]) و هرکدام در یک پیامک جدا می‌روند.
    """
    permission_classes = [IsAdminUser]

    def post(self, request, pk):
        if not _has_perm(request.user, 'sale_view'):
            return _forbidden()
        from .models import SaleInvoice
        try:
            inv = SaleInvoice.objects.select_related('customer').get(pk=pk)
        except SaleInvoice.DoesNotExist:
            return Response({'error': 'یافت نشد'}, status=404)

        phone = (getattr(inv.customer, 'phone', '') or '') or (inv.customer_phone or '')
        if not phone:
            return Response({'error': 'شماره موبایل مشتری ثبت نشده است'}, status=400)

        # حساب‌ها به‌صورت دستی وارد می‌شوند؛ هر حساب در یک پیامک جدا ارسال می‌شود
        raw_accounts = request.data.get('accounts') or []
        accounts = []
        for item in raw_accounts:
            acc_num = (item.get('account_number') or '').strip()
            holder = (item.get('holder') or '').strip()
            if acc_num:
                accounts.append({'account_number': acc_num, 'holder': holder})
        if not accounts:
            return Response({'error': 'حداقل یک شماره حساب باید وارد شود'}, status=400)

        from apps.notifications.services import notify_account_info_sms
        for acc in accounts:
            notify_account_info_sms(
                phone, inv.customer_name,
                acc['account_number'], acc['holder'] or '—',
                amount=inv.total_amount,
                user=inv.customer,
            )
        return Response({'ok': True, 'phone': phone, 'sent': len(accounts)})


class SaleLastPriceView(APIView):
    """
    GET /api/accounting/sale-invoices/last-price/?variant_id=&customer_id=
    آخرین قیمت فروش یک کالا به یک مشتری + نحوه تسویه و تاریخ — راهنمای فیلد قیمت
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        from .models import SaleItem
        item = (SaleItem.objects
                .filter(variant_id=request.query_params.get('variant_id'),
                        invoice__customer_id=request.query_params.get('customer_id'))
                .exclude(invoice__status='cancelled')
                .select_related('invoice')
                .order_by('-invoice__created_at', '-id')
                .first())
        if item is None:
            return Response({'found': False})
        return Response({
            'found': True,
            'unit_price': item.unit_price,
            'settlement': item.invoice.settlement,
            'settlement_display': item.invoice.get_settlement_display(),
            'sale_type': item.invoice.sale_type,
            'date': item.invoice.created_at.strftime('%Y-%m-%d'),
        })


class SalePaymentCreateView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        if not _has_perm(request.user, 'sale_payment'):
            return _forbidden()
        from .models import SaleInvoice, SalePayment
        d = request.data
        try:
            inv = SaleInvoice.objects.get(id=d['invoice_id'])
            p = SalePayment.objects.create(
                invoice=inv,
                to_account_id=d.get('to_account_id') or None,
                method=d.get('method', 'transfer'),
                amount=_safe_int(d['amount']),
                date=d['date'],
                reference=d.get('reference', ''),
                note=d.get('note', ''),
                created_by=request.user,
            )
            if inv.remaining_amount <= 0:
                inv.status = 'paid'
                inv.save()
            return Response({'id': p.id, 'remaining': inv.remaining_amount, 'message': 'پرداخت ثبت شد'}, status=201)
        except Exception as e:
            return Response({'error': str(e)}, status=400)


class SalePaymentDetailView(APIView):
    """GET/PATCH/DELETE روی یک دریافت فروش + بازمحاسبه وضعیت فاکتور"""
    permission_classes = [IsAdminUser]

    def _row(self, p):
        return {
            'id': p.id,
            'invoice_id': p.invoice_id,
            'invoice_number': p.invoice.invoice_number,
            'to_account_id': p.to_account_id,
            'to_account_name': p.to_account.name if p.to_account else '',
            'method': p.method,
            'method_display': p.get_method_display(),
            'amount': p.amount,
            'date': str(p.date),
            'reference': p.reference,
            'note': p.note,
            'created_at': p.created_at.strftime('%Y-%m-%d %H:%M'),
        }

    def _recompute_invoice_status(self, inv):
        """بازمحاسبه وضعیت فاکتور بر اساس مانده (مثل منطق ثبت دریافت)"""
        if inv.remaining_amount > 0 and inv.status == 'paid':
            inv.status = 'confirmed'
            inv.save(update_fields=['status', 'updated_at'])
        elif inv.remaining_amount <= 0 and inv.status in ('draft', 'confirmed'):
            inv.status = 'paid'
            inv.save(update_fields=['status', 'updated_at'])

    def get(self, request, pk):
        if not _has_perm(request.user, 'sale_view'):
            return _forbidden()
        from .models import SalePayment
        try:
            p = SalePayment.objects.select_related('invoice', 'to_account').get(pk=pk)
        except SalePayment.DoesNotExist:
            return Response({'error': 'یافت نشد'}, status=404)
        return Response(self._row(p))

    def patch(self, request, pk):
        if not _has_perm(request.user, 'sale_edit'):
            return _forbidden()
        from .models import SalePayment
        try:
            p = SalePayment.objects.select_related('invoice').get(pk=pk)
        except SalePayment.DoesNotExist:
            return Response({'error': 'یافت نشد'}, status=404)
        d = request.data
        try:
            if 'to_account_id' in d:
                p.to_account_id = d['to_account_id'] or None
            if 'method' in d:
                p.method = d['method']
            if 'amount' in d:
                p.amount = _safe_int(d['amount'])
            if 'date' in d:
                p.date = d['date']
            if 'reference' in d:
                p.reference = d['reference']
            if 'note' in d:
                p.note = d['note']
            p.save()
            self._recompute_invoice_status(p.invoice)
            return Response({
                'id': p.id, 'remaining': p.invoice.remaining_amount,
                'invoice_status': p.invoice.status, 'message': 'پرداخت به‌روز شد',
            })
        except Exception as e:
            return Response({'error': str(e)}, status=400)

    def delete(self, request, pk):
        if not _has_perm(request.user, 'sale_edit'):
            return _forbidden()
        from .models import SalePayment
        try:
            p = SalePayment.objects.select_related('invoice').get(pk=pk)
        except SalePayment.DoesNotExist:
            return Response({'error': 'یافت نشد'}, status=404)
        inv = p.invoice
        p.delete()
        self._recompute_invoice_status(inv)
        return Response(status=204)


# ─── Pending Orders ─────────────────────────────────────────

class PendingOrdersView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        from apps.orders.models import Order
        qs = Order.objects.filter(
            status__in=['pending', 'confirmed', 'awaiting_payment']
        ).select_related('user').prefetch_related('items__variant__product')[:50]
        return Response([{
            'id': o.id, 'order_number': o.order_number,
            'customer_name': str(o.user),
            'customer_phone': getattr(o.user, 'phone', ''),
            'order_type': o.order_type,
            'order_type_display': o.get_order_type_display(),
            'status': o.status, 'status_display': o.get_status_display(),
            'total_amount': o.effective_amount,
            'has_invoice': hasattr(o, 'sale_invoice'),
            'created_at': o.created_at.strftime('%Y-%m-%d %H:%M'),
            'items': [{
                'variant_id': it.variant_id,
                'product_name': it.variant.product.name,
                'sku': it.variant.sku,
                'quantity': it.quantity,
                'unit_price': it.confirmed_unit_price or it.unit_price,
            } for it in o.items.all()],
        } for o in qs])


# ─── Profit & Balance ────────────────────────────────────────

class ProfitReportView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        from .models import SaleInvoice
        from apps.catalog.models import ExchangeRateSetting

        invoices = SaleInvoice.objects.filter(
            status__in=['confirmed', 'paid']
        ).prefetch_related('items__variant__purchase_items__invoice')

        total_revenue = total_cost = total_profit = 0
        items_report = []
        # rate_cny_to_irt به ریال ذخیره می‌شود
        rate = ExchangeRateSetting.get_instance().rate_cny_to_irt

        for inv in invoices:
            for it in inv.items.all():
                revenue = it.subtotal
                cost = it.total_cost
                profit = it.profit
                profit_cny = profit / rate if rate else 0
                total_revenue += revenue
                total_cost += cost
                total_profit += profit
                items_report.append({
                    'product': it.variant.product.name,
                    'sku': it.variant.sku,
                    'invoice_number': inv.invoice_number,
                    'quantity': it.quantity,
                    'unit_price': it.unit_price,
                    'unit_cost': it.unit_cost,
                    'profit_per_unit': it.profit // it.quantity if it.quantity else 0,
                    'profit_total': profit,
                    'profit_cny': round(profit_cny, 2),
                })

        return Response({
            'summary': {
                'total_revenue': total_revenue,
                'total_cost': total_cost,
                'total_profit': total_profit,
                'profit_margin': round(total_profit / total_revenue * 100, 1) if total_revenue else 0,
                'exchange_rate': rate,
                'total_profit_cny': round(total_profit / rate, 2) if rate else 0,
            },
            'items': items_report,
        })


class BalanceSheetView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        from .models import SaleInvoice, Account
        from apps.inventory.models import WarehouseStock, get_variant_cost_irr
        from apps.catalog.models import ExchangeRateSetting

        # rate_cny_to_irt به ریال ذخیره می‌شود
        rate = ExchangeRateSetting.get_instance().rate_cny_to_irt

        stock_value = 0
        for stock in WarehouseStock.objects.select_related('variant').filter(quantity__gt=0):
            stock_value += get_variant_cost_irr(stock.variant) * stock.quantity

        receivable = sum(
            inv.remaining_amount
            for inv in SaleInvoice.objects.filter(status__in=['confirmed', 'paid'])
            if inv.remaining_amount > 0
        )

        accounts = Account.objects.filter(is_active=True)
        cash_total = sum(a.balance for a in accounts if a.currency == 'IRR')
        cash_cny = sum(a.balance for a in accounts if a.currency == 'CNY')
        total_assets = stock_value + receivable + cash_total + int(cash_cny * rate)

        # balance > 0 = طرف حساب به ما بدهکار (بستانکار ما) => receivable
        # balance < 0 = ما به طرف حساب بدهکاریم => payable
        receivable_irr = sum(c.balance_irr for c in Contact.objects.filter(is_active=True) if c.balance_irr > 0)
        receivable_cny = sum(c.balance_cny for c in Contact.objects.filter(is_active=True) if c.balance_cny > 0)
        payable_irr = sum(abs(c.balance_irr) for c in Contact.objects.filter(is_active=True) if c.balance_irr < 0)
        payable_cny = sum(abs(c.balance_cny) for c in Contact.objects.filter(is_active=True) if c.balance_cny < 0)
        total_assets = stock_value + receivable + cash_total + int(cash_cny * rate) + receivable_irr + int(receivable_cny * rate)
        total_liabilities = payable_irr + int(payable_cny * rate)

        paid = SaleInvoice.objects.filter(status__in=['confirmed', 'paid'])
        total_revenue = sum(inv.total_amount for inv in paid)
        total_cost_sold = sum(inv.total_cost for inv in paid)
        gross_profit = total_revenue - total_cost_sold

        return Response({
            'assets': {
                'stock_value': stock_value, 'receivable_sale': receivable,
                'receivable_irr': receivable_irr, 'receivable_cny': receivable_cny,
                'receivable_cny_irr': int(receivable_cny * rate),
                'cash_irr': cash_total, 'cash_cny': cash_cny,
                'cash_cny_irr': int(cash_cny * rate),
                'total': total_assets,
            },
            'liabilities': {
                'payable_irr': payable_irr, 'payable_cny': payable_cny,
                'payable_cny_irr': int(payable_cny * rate),
                'total': total_liabilities,
            },
            'equity': total_assets - total_liabilities,
            'profit': {
                'total_revenue': total_revenue,
                'total_cost': total_cost_sold,
                'gross_profit': gross_profit,
                'margin': round(gross_profit / total_revenue * 100, 1) if total_revenue else 0,
                'gross_profit_cny': round(gross_profit / rate, 2) if rate else 0,
            },
            'exchange_rate': rate,
        })


# ─── Misc ────────────────────────────────────────────────────

class CustomerQuickCreateView(APIView):
    """
    POST /api/accounting/customers/ — ساخت سریع مشتری از فرم فاکتور فروش.
    رکورد اصلی در کاردکس اشخاص (Contact) ساخته می‌شود؛ چون SaleInvoice.customer
    FK به User است، یک «کاربر سایه» با linked_contact به همان طرف حساب ساخته
    می‌شود تا id آن در فاکتور برود. کاربر سایه در لیست مشتریان سایت دیده نمی‌شود.
    اگر شماره موبایل قبلاً ثبت شده باشد همان کاربر برمی‌گردد (Contact تکراری ساخته نمی‌شود).
    """
    permission_classes = [IsAdminUser]

    def post(self, request):
        if not _has_perm(request.user, 'sale_create'):
            return _forbidden()
        from apps.users.models import User, UserProfile
        d = request.data
        name = (d.get('name') or '').strip()
        phone = (d.get('phone') or '').strip()
        if not name:
            return Response({'error': 'نام مشتری الزامی است'}, status=400)
        if not phone.startswith('09') or len(phone) != 11 or not phone.isdigit():
            return Response({'error': 'شماره موبایل معتبر نیست (مثال: 09123456789)'}, status=400)

        # اگر contact_id ارسال شده (انتخاب طرف حساب موجود از جستجو) کاربر سایه
        # به همان طرف حساب لینک می‌شود — رکورد تکراری ساخته نمی‌شود
        contact = None
        contact_id = str(d.get('contact_id') or '')
        if contact_id:
            real = contact_id[2:] if contact_id.startswith('c_') else contact_id
            try:
                contact = Contact.objects.get(pk=real, is_active=True)
            except (Contact.DoesNotExist, ValueError):
                return Response({'error': 'طرف حساب یافت نشد'}, status=404)
            if not contact.phone:
                contact.phone = phone
                contact.save(update_fields=['phone', 'updated_at'])
        else:
            contact_type = d.get('contact_type') or Contact.ContactType.CUSTOMER
            if contact_type not in Contact.ContactType.values:
                return Response({'error': 'نوع طرف حساب نامعتبر است'}, status=400)
            creatable = _creatable_contact_types(request.user)
            if creatable is not None and contact_type not in creatable:
                if not creatable:
                    return _forbidden('ساخت طرف حساب جدید فقط برای گروه‌های مجاز است')
                return _forbidden('شما مجاز به ساخت این نوع طرف حساب نیستید')
            tier = d.get('partner_tier') or ''
            if contact_type == Contact.ContactType.PARTNER:
                if tier not in Contact.PartnerTier.values:
                    return Response({'error': 'سطح همکار را انتخاب کنید (سیلور/گلد/پلاتینیوم)'}, status=400)
            else:
                tier = ''

        existing = User.objects.filter(phone=phone).first()
        if existing:
            if contact is not None:
                # کاربر موجود را به طرف حساب انتخاب‌شده لینک کن (اگر لینک دیگری ندارد)
                profile = getattr(existing, 'profile', None)
                if profile:
                    changed = []
                    if not profile.linked_contact_id:
                        profile.linked_contact = contact
                        changed.append('linked_contact')
                    # سطح همکار طرف حساب به پروفایل کاربر منتقل شود — قیمت و نحوه تسویه فاکتور بر اساس آن است
                    if contact.contact_type == Contact.ContactType.PARTNER and not (
                            profile.is_approved and profile.user_type == UserProfile.UserType.PARTNER):
                        profile.user_type = UserProfile.UserType.PARTNER
                        profile.is_approved = True
                        profile.partner_tier = contact.partner_tier
                        changed += ['user_type', 'is_approved', 'partner_tier']
                    if changed:
                        changed.append('updated_at')
                        profile.save(update_fields=changed)
            return Response({
                'id': existing.id,
                'name': existing.get_full_name() or name,
                'phone': existing.phone,
                'tier': _user_tier(existing),
                'existing': True,
            })

        with transaction.atomic():
            if contact is None:
                contact = Contact.objects.create(
                    name=name,
                    contact_type=contact_type,
                    currency=d.get('currency') if d.get('currency') in Contact.Currency.values else Contact.Currency.IRR,
                    phone=phone,
                    wechat=(d.get('wechat') or '').strip(),
                    address=d.get('address') or '',
                    province=(d.get('province') or '').strip(),
                    partner_tier=tier,
                    note=d.get('note') or d.get('notes') or '',
                    opening_balance_irr=int(d.get('opening_balance_irr') or 0),
                    opening_balance_cny=_safe_decimal(d.get('opening_balance_cny')),
                )
            parts = name.split()
            first_name = ' '.join(parts[:-1]) if len(parts) > 1 else name
            last_name = parts[-1] if len(parts) > 1 else ''
            email = (d.get('email') or '').strip() or None
            if email and User.objects.filter(email=email).exists():
                email = None
            user = User(phone=phone, first_name=first_name, last_name=last_name, email=email)
            user.set_unusable_password()
            user.save()
            is_partner = contact.contact_type == Contact.ContactType.PARTNER
            UserProfile.objects.create(
                user=user,
                # برای همکار، سطح به پروفایل کاربر سایه هم منتقل می‌شود تا قیمت‌گذاری
                # و نحوه تسویهٔ فاکتور بر اساس همان سطح باشد (سازنده تأییدشده است)
                user_type=UserProfile.UserType.PARTNER if is_partner else UserProfile.UserType.PUBLIC,
                is_approved=is_partner,
                partner_tier=contact.partner_tier if is_partner else '',
                company_name=(d.get('company_name') or '').strip(),
                national_id=(d.get('national_id') or '').strip(),
                address=d.get('address') or '',
                province=(d.get('province') or '').strip(),
                notes=d.get('note') or d.get('notes') or '',
                linked_contact=contact,
            )
        logger.info(f"[SALE] طرف حساب سریع ساخته شد: {name} ({contact.contact_type}) — {phone} توسط {request.user}")
        return Response({'id': user.id, 'name': name, 'phone': phone,
                         'contact_id': contact.id,
                         'tier': contact.partner_tier if is_partner else 'public',
                         'existing': False}, status=201)


class CustomerSearchView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        if not _has_perm(request.user, 'sale_view'):
            return _forbidden()
        from apps.users.models import User
        # نرمال‌سازی ارقام فارسی/عربی → لاتین و حروف عربی — جستجو با هر کیبورد
        q = request.query_params.get('q', '')
        q = q.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789"))
        q = q.replace('ك', 'ک').replace('ي', 'ی').strip()
        if len(q) < 2:
            return Response([])
        users = User.objects.filter(
            Q(phone__icontains=q) | Q(first_name__icontains=q)
            | Q(last_name__icontains=q) | Q(profile__company_name__icontains=q)
        ).select_related('profile')[:15]
        def _tier(u):
            p = getattr(u, 'profile', None)
            if p and p.is_approved and p.user_type == 'partner':
                return p.partner_tier or 'partner'
            return 'public'
        results = [{
            'id': u.id,
            'name': f"{u.first_name} {u.last_name}".strip() or str(u),
            'phone': getattr(u, 'phone', ''),
            'display': f"{(u.first_name + ' ' + u.last_name).strip() or str(u)} | {getattr(u, 'phone', '')}",
            'tier': _tier(u),
            'is_contact': False,
        } for u in users]
        # طرف حساب‌های دستی (مشتری‌های غیر ثبت‌نامی) — با انتخاب، کاربر برایشان ساخته می‌شود
        # طرف حساب‌هایی که کاربر سایه دارند در همان بخش کاربران می‌آیند — تکراری نشان داده نمی‌شوند
        from .models import Contact
        for c in Contact.objects.filter(is_active=True, name__icontains=q, linked_users__isnull=True)[:10]:
            is_partner = c.contact_type == Contact.ContactType.PARTNER
            results.append({
                'id': f"c_{c.id}",
                'name': c.name,
                'phone': c.phone,
                'display': f"{c.name} | {c.phone} (طرف حساب)",
                'tier': (c.partner_tier or 'partner') if is_partner else 'public',
                'is_contact': True,
            })
        return Response(results)


class VariantPriceView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, variant_id):
        from apps.catalog.models import ProductVariant
        try:
            v = ProductVariant.objects.get(id=variant_id, is_active=True)
            public_price = v.final_price
            partner_price = None
            if request.user.is_authenticated:
                try:
                    disc = float(request.user.profile.discount_percent or 0)
                    if disc > 0:
                        import math
                        partner_price = math.ceil(public_price * (1 - disc / 100))
                except Exception:
                    pass
            return Response({
                'variant_id': variant_id, 'sku': v.sku,
                'public_price': public_price,
                'partner_price': partner_price,
                'suggested_price': partner_price or public_price,
            })
        except ProductVariant.DoesNotExist:
            return Response({'error': 'یافت نشد'}, status=404)


# ─── RBAC ────────────────────────────────────────────────────

class RoleListView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        from apps.users.models import Role, PERMISSIONS
        return Response({
            'roles': [{
                'id': r.id, 'name': r.name,
                'description': r.description,
                'permissions': r.permissions,
                'allowed_contact_types': r.allowed_contact_types or [],
                'perm_count': r.perm_count(),
                'staff_count': r.staff_members.filter(is_active=True).count(),
                'is_active': r.is_active,
            } for r in Role.objects.all()],
            'all_permissions': [{'code': k, 'label': v} for k, v in PERMISSIONS],
            'contact_types': [{'code': k, 'label': v} for k, v in Contact.ContactType.choices],
        })

    def post(self, request):
        from apps.users.models import Role
        d = request.data
        r = Role.objects.create(
            name=d['name'],
            description=d.get('description', ''),
            permissions=d.get('permissions', []),
            allowed_contact_types=d.get('allowed_contact_types', []),
        )
        return Response({'id': r.id, 'name': r.name}, status=201)


class RoleDetailView(APIView):
    permission_classes = [IsAdminUser]

    def patch(self, request, pk):
        from apps.users.models import Role
        try:
            role = Role.objects.get(pk=pk)
        except Role.DoesNotExist:
            return Response({'error': 'یافت نشد'}, status=404)
        for f in ['name', 'description', 'permissions', 'is_active', 'allowed_contact_types']:
            if f in request.data:
                setattr(role, f, request.data[f])
        role.save()
        return Response({'id': role.id, 'name': role.name, 'permissions': role.permissions})

    def delete(self, request, pk):
        from apps.users.models import Role
        try:
            Role.objects.get(pk=pk).delete()
            return Response({'deleted': True})
        except Role.DoesNotExist:
            return Response({'error': 'یافت نشد'}, status=404)


class StaffListView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        from apps.users.models import StaffProfile
        staff = StaffProfile.objects.select_related('user', 'role').filter(is_active=True)
        return Response([{
            'id': s.id, 'user_id': s.user_id,
            'name': s.user.get_full_name() or s.user.phone,
            'first_name': s.user.first_name, 'last_name': s.user.last_name,
            'phone': s.user.phone,
            'role_id': s.role_id, 'role_name': s.role.name if s.role else '',
            'employee_id': s.employee_id, 'department': s.department,
            'is_active': s.is_active,
        } for s in staff])

    def post(self, request):
        from apps.users.models import StaffProfile, User
        d = request.data
        try:
            user = User.objects.get(id=d['user_id'])
            staff, created = StaffProfile.objects.get_or_create(
                user=user,
                defaults={
                    'role_id': d.get('role_id') or None,
                    'employee_id': d.get('employee_id', ''),
                    'department': d.get('department', ''),
                }
            )
            if not created:
                if d.get('role_id'):
                    staff.role_id = d['role_id']
                staff.employee_id = d.get('employee_id', staff.employee_id)
                staff.department = d.get('department', staff.department)
                staff.is_active = True
                staff.save()
            user.is_staff = True
            user.save(update_fields=['is_staff'])
            return Response({'id': staff.id, 'message': 'پرسنل ثبت شد'}, status=201)
        except User.DoesNotExist:
            return Response({'error': 'کاربر یافت نشد'}, status=404)
        except Exception as e:
            return Response({'error': str(e)}, status=400)


class StaffDetailView(APIView):
    permission_classes = [IsAdminUser]

    def patch(self, request, pk):
        from apps.users.models import StaffProfile, User
        try:
            staff = StaffProfile.objects.select_related('user').get(pk=pk)
        except StaffProfile.DoesNotExist:
            return Response({'error': 'یافت نشد'}, status=404)
        d = request.data
        password = (d.get('password') or '').strip()
        if password and len(password) < 6:
            return Response({'error': 'رمز عبور حداقل ۶ کاراکتر'}, status=400)
        user = staff.user
        phone = (d.get('phone') or '').strip()
        if phone and phone != user.phone and User.objects.filter(phone=phone).exists():
            return Response({'error': 'این شماره قبلاً ثبت شده'}, status=400)
        for f in ['role_id', 'employee_id', 'department', 'is_active']:
            if f in d:
                setattr(staff, f, d[f] if f != 'role_id' else (d[f] or None))
        staff.save()
        changed = []
        for f in ['first_name', 'last_name']:
            if f in d:
                setattr(user, f, d[f])
                changed.append(f)
        if phone and phone != user.phone:
            user.phone = phone
            changed.append('phone')
        if password:
            user.set_password(password)
            changed.append('password')
        if changed:
            user.save(update_fields=changed)
        return Response({'id': staff.id})


class MyPermissionsView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        if request.user.is_superuser:
            from apps.users.models import PERMISSIONS
            return Response({
                'is_superuser': True,
                'permissions': [p[0] for p in PERMISSIONS],
                'allowed_contact_types': [],
                # None معادل بدون محدودیت است — در فرانت is_superuser چک می‌شود
                'creatable_contact_types': [k for k, _ in Contact.ContactType.choices],
            })
        try:
            staff = request.user.staff_profile
            return Response({
                'is_superuser': False,
                'role': staff.role.name if staff.role else '',
                'permissions': staff.role.permissions if staff.role else [],
                'allowed_contact_types': (staff.role.allowed_contact_types or []) if staff.role else [],
                # ساخت طرف حساب جدید فقط برای گروه‌های مجاز — لیست خالی یعنی هیچ نوعی
                'creatable_contact_types': (staff.role.allowed_contact_types or []) if staff.role else [],
            })
        except Exception:
            return Response({'permissions': [], 'role': '', 'allowed_contact_types': [], 'creatable_contact_types': []})


class StaffCreateUserView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        from apps.users.models import User
        d = request.data
        phone = d.get('phone', '').strip()
        password = d.get('password', '').strip()
        if not phone:
            return Response({'error': 'شماره موبایل الزامی است'}, status=400)
        if not password or len(password) < 6:
            return Response({'error': 'رمز عبور حداقل ۶ کاراکتر'}, status=400)
        if User.objects.filter(phone=phone).exists():
            return Response({'error': 'این شماره قبلاً ثبت شده'}, status=400)
        try:
            user = User.objects.create_user(
                phone=phone, password=password,
                first_name=d.get('first_name', ''),
                last_name=d.get('last_name', ''),
                is_staff=True,
            )
            return Response({
                'user_id': user.id,
                'name': user.get_full_name() or phone,
                'phone': phone,
                'message': f'کاربر ساخته شد',
            }, status=201)
        except Exception as e:
            return Response({'error': str(e)}, status=400)


# ═══════════════════════════════════════════════════════════════
# SystemResetView — فقط superuser از طریق API
# ═══════════════════════════════════════════════════════════════

class SystemResetView(APIView):
    """
    POST /api/accounting/system-reset/
    {"confirm": "RESET_ALL_TEST_DATA"}
    فقط superuser می‌تواند صدا بزند. در frontend هیچ دکمه‌ای نمایش داده نمی‌شود.
    """
    permission_classes = [IsAdminUser]

    def post(self, request):
        if not request.user.is_superuser:
            return Response({"error": "فقط superuser می‌تواند ریست کند"}, status=403)

        confirm = request.data.get("confirm", "")
        if confirm != "RESET_ALL_TEST_DATA":
            return Response({
                "error": "برای تأیید باید بفرستید: {\"confirm\": \"RESET_ALL_TEST_DATA\"}",
            }, status=400)

        purge_contacts = request.data.get("purge_contacts", False)
        purge_accounts = request.data.get("purge_accounts", False)

        try:
            with transaction.atomic():
                from .models import (
                    PurchaseInvoice, PurchaseItem, ExtraCost,
                    SaleInvoice, SaleItem, SalePayment, Payment, Account,
                )
                from apps.orders.models import Order, OrderItem, StockReservation, PaymentLog
                from apps.catalog.models import ProductVariant
                from apps.inventory.models import StockMovement, WarehouseStock, StockTransfer

                report = {
                    "purchase_invoices": PurchaseInvoice.objects.count(),
                    "sale_invoices": SaleInvoice.objects.count(),
                    "payments": Payment.objects.count(),
                    "orders": Order.objects.count(),
                    "stock_movements": StockMovement.objects.count(),
                }

                ExtraCost.objects.all().delete()
                PurchaseItem.objects.all().delete()
                PurchaseInvoice.objects.all().delete()

                SalePayment.objects.all().delete()
                SaleItem.objects.all().delete()
                SaleInvoice.objects.all().delete()

                Payment.objects.all().delete()

                PaymentLog.objects.all().delete()
                StockReservation.objects.all().delete()
                OrderItem.objects.all().delete()
                Order.objects.all().delete()

                StockTransfer.objects.all().delete()
                StockMovement.objects.all().delete()

                WarehouseStock.objects.all().update(quantity=0)
                ProductVariant.objects.all().update(stock_quantity=0, reserved_qty=0)

                if purge_contacts:
                    Contact.objects.all().delete()
                if purge_accounts:
                    Account.objects.all().delete()

                logger.warning(f"[SYSTEM RESET] انجام شد توسط {request.user} — {report}")

            return Response({
                "success": True,
                "message": "همه داده‌های تستی پاک شدند.",
                "report": report,
            }, status=200)
        except Exception as e:
            logger.exception(f"[SYSTEM RESET] خطا: {e}")
            return Response({"error": str(e)}, status=500)


# ═══════════════════════════════════════════════════════════════
# پنل مشتری — داشبورد عملکرد + کاردکس حساب (فقط داده‌های خود کاربر)
# ═══════════════════════════════════════════════════════════════
class MyDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.orders.models import Order
        from .models import SaleInvoice
        from django.db.models import Sum, Count
        from django.db.models.functions import TruncMonth
        from django.utils import timezone
        from datetime import timedelta

        u = request.user
        profile = getattr(u, 'profile', None)
        is_partner = bool(
            profile and profile.user_type == 'partner' and profile.is_approved
        )

        orders = Order.objects.filter(user=u)
        valid_orders = orders.exclude(status__in=['cancelled', 'refunded'])
        total_spent = valid_orders.aggregate(s=Sum('total_amount'))['s'] or 0
        pending_orders = orders.exclude(status__in=['paid', 'cancelled', 'refunded']).count()

        # بدهی فاکتورها + مانده اول دوره — مثبت = مشتری بدهکار
        debt_irr = (profile.opening_balance_irr if profile else 0)
        debt_cny = float(profile.opening_balance_cny) if profile else 0.0
        for inv in SaleInvoice.objects.filter(customer=u):
            if inv.currency == 'CNY':
                debt_cny += float(inv.remaining_amount)
            else:
                debt_irr += inv.remaining_amount

        # نمودار خرید ۶ ماه اخیر
        since = timezone.now() - timedelta(days=183)
        monthly = list(
            valid_orders.filter(created_at__gte=since)
            .annotate(m=TruncMonth('created_at'))
            .values('m').annotate(total=Sum('total_amount'), count=Count('id'))
            .order_by('m')
        )
        monthly = [{
            'month': row['m'].strftime('%Y-%m'),
            'total': row['total'], 'count': row['count'],
        } for row in monthly]

        recent = [{
            'order_number': o.order_number,
            'date': str(o.created_at.date()),
            'status': o.status,
            'status_display': o.get_status_display(),
            'total_amount': o.total_amount,
        } for o in orders.order_by('-created_at')[:5]]

        return Response({
            'is_partner': is_partner,
            'partner_tier': profile.partner_tier if profile and is_partner else '',
            'partner_tier_display': (profile.get_partner_tier_display()
                                     if profile and is_partner and profile.partner_tier else ''),
            'total_orders': orders.count(),
            'pending_orders': pending_orders,
            'total_spent': total_spent,
            'debt_irr': debt_irr,
            'debt_cny': debt_cny,
            'monthly': monthly,
            'recent_orders': recent,
        })


class MyKardexView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from .models import SaleInvoice, SalePayment

        u = request.user
        profile = getattr(u, 'profile', None)
        ob_irr = profile.opening_balance_irr if profile else 0
        ob_cny = float(profile.opening_balance_cny) if profile else 0.0

        # دیدگاه مشتری: بدهکار = بدهی بیشتر شد (فاکتور) | بستانکار = پرداخت (کاهش بدهی)
        items = []
        if ob_irr or ob_cny:
            items.append({
                'date': '', 'type': 'opening', 'type_label': 'مانده اول دوره',
                'description': 'مانده منتقل‌شده از دوره قبل',
                'inv_number': '',
                'debit_irr': max(ob_irr, 0), 'credit_irr': max(-ob_irr, 0),
                'debit_cny': max(ob_cny, 0.0), 'credit_cny': max(-ob_cny, 0.0),
                'inv_items': [],
            })

        for inv in SaleInvoice.objects.filter(customer=u).order_by('created_at'):
            cny = inv.currency == 'CNY'
            items.append({
                'date': str(inv.created_at.date()),
                'type': 'invoice', 'type_label': 'فاکتور فروش',
                'description': f'فاکتور {inv.invoice_number} | {inv.get_status_display()}',
                'inv_number': inv.invoice_number,
                'debit_irr': 0 if cny else inv.total_amount, 'credit_irr': 0,
                'debit_cny': float(inv.total_amount) if cny else 0.0, 'credit_cny': 0.0,
                'inv_items': [{
                    'product_name': it.variant.product.name,
                    'sku': it.variant.sku,
                    'quantity': it.quantity,
                    'unit_price': it.unit_price,
                } for it in inv.items.select_related('variant__product').all()],
            })

        for p in SalePayment.objects.filter(invoice__customer=u).select_related('to_account', 'invoice').order_by('date'):
            cny = bool(p.invoice_id and p.invoice.currency == 'CNY')
            items.append({
                'date': str(p.date), 'type': 'payment',
                'type_label': f'پرداخت — {p.get_method_display()}',
                'description': ' | '.join(filter(None, [
                    'پرداخت',
                    p.to_account.name if p.to_account else '',
                    p.reference or '',
                ])),
                'inv_number': p.invoice.invoice_number if p.invoice_id else '',
                'debit_irr': 0, 'credit_irr': 0.0 if cny else float(p.amount),
                'debit_cny': 0.0, 'credit_cny': float(p.amount) if cny else 0.0,
                'inv_items': [],
            })

        items.sort(key=lambda x: x['date'])

        bal_irr = bal_cny = 0.0
        for it in items:
            bal_irr += it['debit_irr'] - it['credit_irr']
            bal_cny += it['debit_cny'] - it['credit_cny']
            it['bal_irr'] = bal_irr
            it['bal_cny'] = bal_cny
        items.reverse()

        return Response({
            'items': items,
            'balance_irr': bal_irr,
            'balance_cny': bal_cny,
        })


# ─── Aging Report ────────────────────────────────────────────

class AgingReportView(APIView):
    """
    GET /api/accounting/reports/aging/
    گزارش سررسید ردیف‌های تسویهٔ باز به تفکیک مشتری:
    not_due (موعد نرسیده) / overdue_1_15 (۱ تا ۱۵ روز گذشته) / overdue_15_plus (بیش از ۱۵ روز).
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        if not _has_perm(request.user, 'reports_view'):
            return _forbidden()
        from django.utils import timezone
        from .models import SettlementLine

        today = timezone.now().date()
        lines = (
            SettlementLine.objects
            .filter(is_active=True)
            .exclude(invoice__status='cancelled')
            .select_related('invoice__customer')
            .prefetch_related('allocations')
        )
        buckets = {}  # user_id → تجمیع
        for line in lines:
            paid = sum(a.amount for a in line.allocations.all())
            remaining = line.amount - paid
            if remaining <= 0:
                continue
            user = line.invoice.customer
            b = buckets.setdefault(user.id, {
                'user_id': user.id,
                'name': user.get_full_name() or '',
                'phone': user.phone or '',
                'not_due': 0, 'overdue_1_15': 0, 'overdue_15_plus': 0, 'total': 0,
            })
            days_past = (today - line.due_date).days
            if days_past <= 0:
                b['not_due'] += remaining
            elif days_past <= 15:
                b['overdue_1_15'] += remaining
            else:
                b['overdue_15_plus'] += remaining
            b['total'] += remaining

        data = sorted(buckets.values(), key=lambda b: b['total'], reverse=True)
        return Response(data)


# ─── Returns (برگشت از فروش و خرید) ─────────────────────────────

def _return_row(inv, with_items=False):
    """سطر خروجی سند برگشت (مشترک بین لیست و جزئیات)"""
    row = {
        'id': inv.id,
        'invoice_number': inv.invoice_number,
        'return_type': inv.return_type,
        'return_type_display': inv.get_return_type_display(),
        'warehouse_id': inv.warehouse_id,
        'warehouse_name': inv.warehouse.name if inv.warehouse_id else '',
        'date': str(inv.date),
        'note': inv.note,
        'status': inv.status,
        'status_display': inv.get_status_display(),
        'total_amount': inv.total_amount,
        'items_count': inv.items.count(),
        'sale_invoice_id': inv.sale_invoice_id,
        'sale_invoice_number': inv.sale_invoice.invoice_number if inv.sale_invoice_id else '',
        'purchase_invoice_id': inv.purchase_invoice_id,
        'purchase_invoice_number': inv.purchase_invoice.invoice_number if inv.purchase_invoice_id else '',
        **_audit_row(inv),
    }
    if with_items:
        row['items'] = [{
            'id': it.id,
            'variant_id': it.variant_id,
            'sku': it.variant.sku,
            'product_name': it.variant.product.name,
            'variant_name': it.variant.name_suffix,
            'quantity': it.quantity,
            'unit_price': it.unit_price,
            'subtotal': it.subtotal,
        } for it in inv.items.select_related('variant__product').all()]
    return row


class ReturnInvoiceListView(APIView):
    """
    GET  /api/accounting/returns/          — لیست اسناد برگشت (فیلتر ?type=sale|purchase)
    POST /api/accounting/returns/          — صدور سند برگشت + اعمال موجودی در یک تراکنش
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        if not _has_perm(request.user, 'return_view'):
            return _forbidden()
        from .models import ReturnInvoice
        qs = (ReturnInvoice.objects
              .select_related('warehouse', 'sale_invoice', 'purchase_invoice')
              .order_by('-created_at'))
        t = request.query_params.get('type')
        if t in ('sale', 'purchase'):
            qs = qs.filter(return_type=t)
        return Response([_return_row(inv) for inv in qs[:100]])

    @transaction.atomic
    def post(self, request):
        if not _has_perm(request.user, 'return_create'):
            return _forbidden()
        from .models import ReturnInvoice, ReturnItem
        d = request.data
        try:
            return_type = d.get('return_type')
            if return_type not in ('sale', 'purchase'):
                return Response({'error': 'نوع برگشت نامعتبر است'}, status=400)

            from apps.inventory.models import Warehouse
            warehouse = Warehouse.objects.filter(pk=d.get('warehouse_id'), is_active=True).first()
            if warehouse is None:
                return Response({'error': 'انبار معتبر انتخاب کنید'}, status=400)

            items_d = d.get('items') or []
            if not items_d:
                return Response({'error': 'حداقل یک آیتم لازم است'}, status=400)

            sale_id = (d.get('sale_invoice_id') or None) if return_type == 'sale' else None
            purchase_id = (d.get('purchase_invoice_id') or None) if return_type == 'purchase' else None

            from django.utils import timezone
            inv = ReturnInvoice.objects.create(
                return_type=return_type,
                sale_invoice_id=sale_id,
                purchase_invoice_id=purchase_id,
                warehouse=warehouse,
                date=d.get('date') or timezone.now().date(),
                note=d.get('note', ''),
                created_by=request.user,
            )
            for it_d in items_d:
                qty = _safe_int(it_d.get('quantity'))
                if qty <= 0:
                    raise ValueError('تعداد هر آیتم باید بزرگ‌تر از صفر باشد')
                ReturnItem.objects.create(
                    invoice=inv,
                    variant_id=it_d['variant_id'],
                    quantity=qty,
                    unit_price=_safe_int(it_d.get('unit_price')),
                )

            # اعمال موجودی — در صورت خطا (مثل موجودی ناکافی) کل تراکنش rollback می‌شود
            inv.apply_to_inventory(user=request.user)

            return Response({
                'id': inv.id,
                'invoice_number': inv.invoice_number,
                'total_amount': inv.total_amount,
                'message': 'سند برگشت صادر و موجودی اعمال شد',
            }, status=201)
        except ValueError as ve:
            return Response({'error': str(ve)}, status=400)
        except Exception as e:
            logger.exception(f"[RETURN] خطا در صدور سند برگشت: {e}")
            return Response({'error': str(e)}, status=400)


class ReturnInvoiceDetailView(APIView):
    """GET /api/accounting/returns/<pk>/ — جزئیات سند برگشت با آیتم‌ها"""
    permission_classes = [IsAdminUser]

    def get(self, request, pk):
        if not _has_perm(request.user, 'return_view'):
            return _forbidden()
        from .models import ReturnInvoice
        inv = (ReturnInvoice.objects
               .select_related('warehouse', 'sale_invoice', 'purchase_invoice')
               .filter(pk=pk).first())
        if inv is None:
            return Response({'error': 'سند یافت نشد'}, status=404)
        return Response(_return_row(inv, with_items=True))


class ReturnInvoiceCancelView(APIView):
    """POST /api/accounting/returns/<pk>/cancel/ — لغو سند و برگرداندن موجودی"""
    permission_classes = [IsAdminUser]

    def post(self, request, pk):
        if not _has_perm(request.user, 'return_edit'):
            return _forbidden()
        from .models import ReturnInvoice
        inv = (ReturnInvoice.objects
               .select_related('warehouse', 'sale_invoice', 'purchase_invoice')
               .filter(pk=pk).first())
        if inv is None:
            return Response({'error': 'سند یافت نشد'}, status=404)
        try:
            inv.cancel(user=request.user)
        except ValueError as ve:
            return Response({'error': str(ve)}, status=400)
        return Response(_return_row(inv, with_items=True))
