from django.utils import timezone

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    ExpenseCategory,
    ExpenseCharge,
    Investor,
    InvestorMovement,
    RecurringExpense,
)
from .serializers import (
    ExpenseCategorySerializer,
    ExpenseChargeDetailSerializer,
    ExpenseChargeSerializer,
    InvestorMovementSerializer,
    InvestorSerializer,
    RecurringExpenseSerializer,
)
from .services import accrue_month, book_charge_accrual, investor_principal_at, pay_charge


def _has_perm(user, code):
    if user.is_superuser:
        return True
    sp = getattr(user, "staff_profile", None)
    return bool(sp and sp.has_perm(code))


def _forbidden():
    return Response({"error": "دسترسی ندارید"}, status=status.HTTP_403_FORBIDDEN)


# ─── سر فصل‌ها ───

class CategoryListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _has_perm(request.user, "expenses_view"):
            return _forbidden()
        qs = ExpenseCategory.objects.all()
        ct = request.query_params.get("type")
        if ct:
            qs = qs.filter(category_type=ct)
        return Response(ExpenseCategorySerializer(qs, many=True).data)

    def post(self, request):
        if not _has_perm(request.user, "expenses_edit"):
            return _forbidden()
        ser = ExpenseCategorySerializer(data=request.data)
        if not ser.is_valid():
            return Response({"error": ser.errors}, status=400)
        ser.save()
        return Response(ser.data, status=201)


class CategoryDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        if not _has_perm(request.user, "expenses_edit"):
            return _forbidden()
        try:
            obj = ExpenseCategory.objects.get(pk=pk)
        except ExpenseCategory.DoesNotExist:
            return Response({"error": "یافت نشد"}, status=404)
        ser = ExpenseCategorySerializer(obj, data=request.data, partial=True)
        if not ser.is_valid():
            return Response({"error": ser.errors}, status=400)
        ser.save()
        return Response(ser.data)

    def delete(self, request, pk):
        if not _has_perm(request.user, "expenses_edit"):
            return _forbidden()
        try:
            ExpenseCategory.objects.get(pk=pk).delete()
        except ExpenseCategory.DoesNotExist:
            return Response({"error": "یافت نشد"}, status=404)
        return Response({"ok": True})


# ─── هزینه‌های تکرارشونده ───

class CategoryContactsView(APIView):
    """طرف‌حساب‌های مرتبط با یک سر فصل هزینه (از روی هزینه‌های ثبت‌شده)."""

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        if not _has_perm(request.user, "expenses_view"):
            return _forbidden()
        from apps.accounting.models import Contact
        contacts = Contact.objects.filter(expense_charges__category_id=pk).distinct()
        return Response([{"id": c.id, "name": c.name, "phone": c.phone,
                          "contact_type": c.contact_type,
                          "contact_type_display": c.get_contact_type_display()}
                         for c in contacts])


class RecurringListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _has_perm(request.user, "expenses_view"):
            return _forbidden()
        qs = RecurringExpense.objects.select_related("category", "contact")
        return Response(RecurringExpenseSerializer(qs, many=True).data)

    def post(self, request):
        if not _has_perm(request.user, "expenses_edit"):
            return _forbidden()
        ser = RecurringExpenseSerializer(data=request.data)
        if not ser.is_valid():
            return Response({"error": ser.errors}, status=400)
        ser.save()
        return Response(ser.data, status=201)


class RecurringDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        if not _has_perm(request.user, "expenses_edit"):
            return _forbidden()
        try:
            obj = RecurringExpense.objects.get(pk=pk)
        except RecurringExpense.DoesNotExist:
            return Response({"error": "یافت نشد"}, status=404)
        ser = RecurringExpenseSerializer(obj, data=request.data, partial=True)
        if not ser.is_valid():
            return Response({"error": ser.errors}, status=400)
        ser.save()
        return Response(ser.data)

    def delete(self, request, pk):
        if not _has_perm(request.user, "expenses_edit"):
            return _forbidden()
        try:
            RecurringExpense.objects.get(pk=pk).delete()
        except RecurringExpense.DoesNotExist:
            return Response({"error": "یافت نشد"}, status=404)
        return Response({"ok": True})


class RecurringKardexView(APIView):
    """کارت هزینه تکرارشونده — فیش‌های ماهانه با وضعیت پرداخت."""

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        if not _has_perm(request.user, "expenses_view"):
            return _forbidden()
        try:
            rec = RecurringExpense.objects.get(pk=pk)
        except RecurringExpense.DoesNotExist:
            return Response({"error": "یافت نشد"}, status=404)
        charges = rec.charges.order_by("-year", "-month")
        return Response({
            "recurring": RecurringExpenseSerializer(rec).data,
            "charges": ExpenseChargeSerializer(charges, many=True).data,
        })


# ─── هزینه‌های ماهانه (شارژها) ───

class ChargeListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _has_perm(request.user, "expenses_view"):
            return _forbidden()
        qs = ExpenseCharge.objects.select_related("category", "contact", "investor")
        source = request.query_params.get("source")
        # بازه جلالی: date_from/date_to (ماه جلالی ممکن است دو ماه میلادی را بپوشاند)
        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")
        if date_from and date_to:
            qs = qs.filter(date__gte=date_from, date__lte=date_to)
        if source:
            qs = qs.filter(source=source)
        return Response(ExpenseChargeSerializer(qs[:300], many=True).data)

    def post(self, request):
        """ثبت هزینه متفرقه — بلافاصله سند بدهی صادر می‌شود."""
        if not _has_perm(request.user, "expenses_edit"):
            return _forbidden()
        d = request.data
        date_str = d.get("date")
        if not date_str:
            return Response({"error": "تاریخ الزامی است"}, status=400)
        y, m, _ = str(date_str).split("-")
        amount = int(d.get("amount") or 0)
        if amount <= 0:
            return Response({"error": "مبلغ نامعتبر است"}, status=400)
        charge = ExpenseCharge.objects.create(
            source=ExpenseCharge.Source.GENERAL,
            title=d.get("title", ""),
            category_id=d.get("category") or None,
            contact_id=d.get("contact") or None,
            year=int(y), month=int(m),
            date=date_str,
            amount=amount,
            notes=d.get("notes", ""),
        )
        book_charge_accrual(charge, actor=request.user)
        return Response(ExpenseChargeSerializer(charge).data, status=201)


class OpenChargesView(APIView):
    """هزینه‌های باز یک طرف‌حساب — برای صفحه دریافت و پرداخت."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.accounting.models import Contact
        from .services import open_charges_for_contact

        contact_id = str(request.query_params.get("contact_id") or "")
        # id پیشونددار لیست ادغام (c_) را نرمال می‌کند
        contact_id = contact_id[2:] if contact_id.startswith("c_") else contact_id
        contact = Contact.objects.filter(pk=contact_id).first() if contact_id else None
        if not contact:
            return Response({"error": "طرف حساب نامعتبر"}, status=400)
        charges = open_charges_for_contact(contact)
        return Response([{
            "id": c.id, "title": c.title, "source": c.source,
            "year": c.year, "month": c.month,
            "amount": c.amount, "paid_amount": c.paid_amount,
            "remaining_amount": c.remaining_amount,
        } for c in charges])


class ChargeDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        if not _has_perm(request.user, "expenses_view"):
            return _forbidden()
        try:
            charge = ExpenseCharge.objects.select_related(
                "category", "contact", "investor").get(pk=pk)
        except ExpenseCharge.DoesNotExist:
            return Response({"error": "یافت نشد"}, status=404)
        return Response(ExpenseChargeDetailSerializer(charge).data)


class ChargeDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        if not _has_perm(request.user, "expenses_edit"):
            return _forbidden()
        from .services import reverse_charge

        try:
            charge = ExpenseCharge.objects.get(pk=pk)
        except ExpenseCharge.DoesNotExist:
            return Response({"error": "یافت نشد"}, status=404)
        title = reverse_charge(charge, actor=request.user)
        return Response({"ok": True, "message": f"هزینه «{title}» لغو شد و سندهایش برگشت خوردند"})


class ChargePayView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        from apps.accounting.models import Account

        if not _has_perm(request.user, "expenses_edit"):
            return _forbidden()
        try:
            charge = ExpenseCharge.objects.get(pk=pk)
        except ExpenseCharge.DoesNotExist:
            return Response({"error": "یافت نشد"}, status=404)
        account = Account.objects.filter(pk=request.data.get("account_id")).first()
        date_ = request.data.get("date")
        if not account or not date_:
            return Response({"error": "حساب و تاریخ الزامی است"}, status=400)
        amount = request.data.get("amount")
        try:
            payment = pay_charge(charge, account, date_, actor=request.user,
                                 amount=int(amount) if amount else None)
        except (ValueError, TypeError) as exc:
            return Response({"error": str(exc)}, status=400)
        return Response({
            "ok": True, "payment_id": payment.id,
            "paid_amount": charge.paid_amount, "remaining_amount": charge.remaining_amount,
            "status": charge.status,
        }, status=201)


# ─── سرمایه‌گذاران ───

class InvestorListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _has_perm(request.user, "expenses_view"):
            return _forbidden()
        qs = Investor.objects.select_related("contact")
        return Response(InvestorSerializer(qs, many=True).data)

    def post(self, request):
        if not _has_perm(request.user, "expenses_edit"):
            return _forbidden()
        from apps.accounting.models import Contact

        d = request.data
        contact_id = d.get("contact")
        if contact_id:
            contact = Contact.objects.filter(pk=contact_id).first()
            if not contact:
                return Response({"error": "طرف حساب یافت نشد"}, status=400)
        else:
            name = (d.get("name") or "").strip()
            if not name:
                return Response({"error": "نام سرمایه‌گذار الزامی است"}, status=400)
            contact = Contact.objects.create(
                contact_type=Contact.ContactType.OTHER, name=name,
                phone=d.get("phone", ""), currency=Contact.Currency.IRR,
            )
        if Investor.objects.filter(contact=contact).exists():
            return Response({"error": "برای این طرف حساب سرمایه‌گذار وجود دارد"}, status=400)
        ser = InvestorSerializer(data={"contact": contact.id,
                                       "annual_rate": d.get("annual_rate", 0),
                                       "is_active": d.get("is_active", True)})
        if not ser.is_valid():
            return Response({"error": ser.errors}, status=400)
        ser.save()
        return Response(ser.data, status=201)


class InvestorDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        if not _has_perm(request.user, "expenses_edit"):
            return _forbidden()
        try:
            obj = Investor.objects.get(pk=pk)
        except Investor.DoesNotExist:
            return Response({"error": "یافت نشد"}, status=404)
        ser = InvestorSerializer(obj, data=request.data, partial=True)
        if not ser.is_valid():
            return Response({"error": ser.errors}, status=400)
        ser.save()
        return Response(ser.data)


class InvestorKardexView(APIView):
    """کارت سرمایه‌گذار — گردش اصل + سودهای ماهانه + مانده‌ها."""

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        if not _has_perm(request.user, "expenses_view"):
            return _forbidden()
        try:
            inv = Investor.objects.select_related("contact").get(pk=pk)
        except Investor.DoesNotExist:
            return Response({"error": "یافت نشد"}, status=404)
        movements = inv.movements.order_by("-date", "-id")
        profits = inv.profit_charges.order_by("-year", "-month")
        return Response({
            "investor": InvestorSerializer(inv).data,
            "principal": investor_principal_at(inv, timezone.localdate()),
            "movements": InvestorMovementSerializer(movements, many=True).data,
            "profits": ExpenseChargeSerializer(profits, many=True).data,
        })


class InvestorMovementListView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """واریز/برداشت اصل سرمایه — با سند نقدی متناظر."""
        from apps.accounting.models import Account, Payment

        if not _has_perm(request.user, "expenses_edit"):
            return _forbidden()
        d = request.data
        try:
            inv = Investor.objects.get(pk=d.get("investor"))
        except Investor.DoesNotExist:
            return Response({"error": "سرمایه‌گذار یافت نشد"}, status=404)
        amount = int(d.get("amount") or 0)
        if amount <= 0 or not d.get("date"):
            return Response({"error": "مبلغ و تاریخ الزامی است"}, status=400)
        account = Account.objects.filter(pk=d.get("account")).first() if d.get("account") else None

        mvt = InvestorMovement.objects.create(
            investor=inv, movement_type=d.get("movement_type"), date=d["date"],
            amount=amount, account=account, note=d.get("note", ""),
        )
        # سند نقدی آینه‌ای: واریز = دریافت از سرمایه‌گذار به حساب ؛ برداشت = پرداخت
        if mvt.movement_type == InvestorMovement.MovementType.DEPOSIT:
            Payment.objects.create(
                contact=inv.contact, to_account=account,
                direction=Payment.Direction.IN, payment_type=Payment.PaymentType.TRANSFER,
                currency="IRR", amount=amount, rate_irr=1, date=d["date"],
                reference="سرمایه مشارکت",
                note=f"واریز سرمایه {inv.contact.name}",
                created_by=request.user,
            )
        else:
            if not account:
                return Response({"error": "برای برداشت، حساب الزامی است"}, status=400)
            Payment.objects.create(
                contact=inv.contact, from_account=account,
                direction=Payment.Direction.OUT, payment_type=Payment.PaymentType.TRANSFER,
                currency="IRR", amount=amount, rate_irr=1, date=d["date"],
                reference="برداشت سرمایه",
                note=f"برداشت سرمایه {inv.contact.name}",
                created_by=request.user,
            )
        return Response(InvestorMovementSerializer(mvt).data, status=201)


# ─── صدور سند سر ماه (دستی/کرون) ───

class AccrueMonthView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not _has_perm(request.user, "expenses_edit"):
            return _forbidden()
        try:
            year = int(request.data.get("year"))
            month = int(request.data.get("month"))
            assert 2000 <= year <= 2100 and 1 <= month <= 12
        except (TypeError, ValueError, AssertionError):
            return Response({"error": "سال و ماه معتبر وارد کنید"}, status=400)
        booked = accrue_month(year, month, actor=request.user)
        return Response(booked)
