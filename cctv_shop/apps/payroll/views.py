from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.models import User

from .models import BonusPenaltyRecord, LeaveRecord, Payslip, PayrollProfile
from .serializers import (
    BonusPenaltyRecordSerializer,
    LeaveRecordSerializer,
    PayslipDetailSerializer,
    PayslipSerializer,
    PayrollProfileSerializer,
)
from .services import generate_month, pay_payslip, recalculate_payslip


def _has_perm(user, code):
    if user.is_superuser or user.is_staff and not hasattr(user, "staff_profile"):
        # کارمند بدون نقش: دسترسی کامل (مطابق رفتار سایر ماژول‌ها)
        return True
    sp = getattr(user, "staff_profile", None)
    if sp is None:
        return False
    return sp.has_perm(code)


def _forbidden():
    return Response({"error": "دسترسی ندارید"}, status=status.HTTP_403_FORBIDDEN)


class StaffListView(APIView):
    """لیست پرسنل (کاربران is_staff) با پروفایل حقوقی‌شان."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _has_perm(request.user, "payroll_view"):
            return _forbidden()
        staff = User.objects.filter(is_staff=True, is_active=True).order_by("first_name", "last_name")
        data = []
        for u in staff:
            profile = getattr(u, "payroll_profile", None)
            data.append({
                "id": u.id,
                "name": u.get_full_name() or u.phone,
                "phone": u.phone,
                "date_joined": u.date_joined.date().isoformat() if u.date_joined else None,
                "profile": PayrollProfileSerializer(profile).data if profile else None,
            })
        return Response(data)


class PayrollProfileListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _has_perm(request.user, "payroll_view"):
            return _forbidden()
        qs = PayrollProfile.objects.select_related("staff").order_by("staff__first_name")
        return Response(PayrollProfileSerializer(qs, many=True).data)

    def post(self, request):
        if not _has_perm(request.user, "payroll_edit"):
            return _forbidden()
        serializer = PayrollProfileSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"error": serializer.errors}, status=400)
        try:
            profile = serializer.save()
            profile.full_clean()
        except ValidationError as exc:
            return Response({"error": exc.messages[0] if exc.messages else str(exc)}, status=400)
        return Response(PayrollProfileSerializer(profile).data, status=201)


class PayrollProfileDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        if not _has_perm(request.user, "payroll_edit"):
            return _forbidden()
        try:
            profile = PayrollProfile.objects.get(pk=pk)
        except PayrollProfile.DoesNotExist:
            return Response({"error": "یافت نشد"}, status=404)
        serializer = PayrollProfileSerializer(profile, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response({"error": serializer.errors}, status=400)
        try:
            profile = serializer.save()
            profile.full_clean()
        except ValidationError as exc:
            return Response({"error": exc.messages[0] if exc.messages else str(exc)}, status=400)
        return Response(PayrollProfileSerializer(profile).data)


class LeaveListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _has_perm(request.user, "payroll_view"):
            return _forbidden()
        qs = LeaveRecord.objects.select_related("staff").order_by("-date")
        staff_id = request.query_params.get("staff")
        if staff_id:
            qs = qs.filter(staff_id=staff_id)
        return Response(LeaveRecordSerializer(qs[:200], many=True).data)

    def post(self, request):
        if not _has_perm(request.user, "payroll_edit"):
            return _forbidden()
        serializer = LeaveRecordSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"error": serializer.errors}, status=400)
        serializer.save()
        return Response(serializer.data, status=201)


class LeaveDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        if not _has_perm(request.user, "payroll_edit"):
            return _forbidden()
        try:
            LeaveRecord.objects.get(pk=pk).delete()
        except LeaveRecord.DoesNotExist:
            return Response({"error": "یافت نشد"}, status=404)
        return Response({"ok": True})


class BonusPenaltyListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _has_perm(request.user, "payroll_view"):
            return _forbidden()
        qs = BonusPenaltyRecord.objects.select_related("staff").order_by("-date")
        staff_id = request.query_params.get("staff")
        if staff_id:
            qs = qs.filter(staff_id=staff_id)
        return Response(BonusPenaltyRecordSerializer(qs[:200], many=True).data)

    def post(self, request):
        if not _has_perm(request.user, "payroll_edit"):
            return _forbidden()
        serializer = BonusPenaltyRecordSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"error": serializer.errors}, status=400)
        serializer.save()
        return Response(serializer.data, status=201)


class BonusPenaltyDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        if not _has_perm(request.user, "payroll_edit"):
            return _forbidden()
        try:
            BonusPenaltyRecord.objects.get(pk=pk).delete()
        except BonusPenaltyRecord.DoesNotExist:
            return Response({"error": "یافت نشد"}, status=404)
        return Response({"ok": True})


class PayslipListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _has_perm(request.user, "payroll_view"):
            return _forbidden()
        year = int(request.query_params.get("year", 0))
        month = int(request.query_params.get("month", 0))
        if not (2000 <= year <= 2100 and 1 <= month <= 12):
            return Response({"error": "سال و ماه (میلادی) الزامی است"}, status=400)
        slips = Payslip.objects.filter(year=year, month=month).select_related("staff")
        return Response(PayslipSerializer(slips, many=True).data)


class PayslipGenerateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not _has_perm(request.user, "payroll_pay"):
            return _forbidden()
        try:
            year = int(request.data.get("year"))
            month = int(request.data.get("month"))
            assert 2000 <= year <= 2100 and 1 <= month <= 12
        except (TypeError, ValueError, AssertionError):
            return Response({"error": "سال و ماه معتبر وارد کنید"}, status=400)
        result = generate_month(year, month, actor=request.user)
        return Response(result)


class PayslipDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        if not _has_perm(request.user, "payroll_view"):
            return _forbidden()
        try:
            slip = Payslip.objects.select_related("staff").get(pk=pk)
        except Payslip.DoesNotExist:
            return Response({"error": "یافت نشد"}, status=404)
        return Response(PayslipDetailSerializer(slip).data)


class PayslipRecalculateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if not _has_perm(request.user, "payroll_pay"):
            return _forbidden()
        try:
            slip = Payslip.objects.get(pk=pk)
        except Payslip.DoesNotExist:
            return Response({"error": "یافت نشد"}, status=404)
        if slip.status == Payslip.Status.PAID:
            return Response({"error": "فیش پرداخت‌شده قابل بازمحاسبه نیست"}, status=400)
        recalculate_payslip(slip)
        return Response(PayslipSerializer(slip).data)


class PayslipConfirmView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if not _has_perm(request.user, "payroll_pay"):
            return _forbidden()
        try:
            slip = Payslip.objects.get(pk=pk)
        except Payslip.DoesNotExist:
            return Response({"error": "یافت نشد"}, status=404)
        if slip.status == Payslip.Status.PAID:
            return Response({"error": "فیش قبلاً پرداخت شده"}, status=400)
        slip.status = Payslip.Status.CONFIRMED
        slip.save(update_fields=["status"])
        return Response(PayslipSerializer(slip).data)


class OpenPayslipsView(APIView):
    """فیش‌های حقوقی باز یک طرف‌حساب پرسنل — برای صفحه دریافت و پرداخت."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.accounting.models import Contact
        from .services import open_payslips_for_contact

        contact_id = str(request.query_params.get("contact_id") or "")
        # id پیشونددار لیست ادغام (c_) را نرمال می‌کند
        contact_id = contact_id[2:] if contact_id.startswith("c_") else contact_id
        contact = Contact.objects.filter(pk=contact_id).first() if contact_id else None
        if not contact:
            return Response({"error": "طرف حساب نامعتبر"}, status=400)
        slips = open_payslips_for_contact(contact)
        return Response([{
            "id": s.id, "year": s.year, "month": s.month,
            "net_amount": s.net_amount, "paid_amount": s.paid_amount,
            "remaining_amount": s.remaining_amount,
        } for s in slips])


class PayslipPayView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if not _has_perm(request.user, "payroll_pay"):
            return _forbidden()
        from apps.accounting.models import Account

        try:
            slip = Payslip.objects.get(pk=pk)
        except Payslip.DoesNotExist:
            return Response({"error": "یافت نشد"}, status=404)
        account_id = request.data.get("account_id")
        date = request.data.get("date")
        if not account_id or not date:
            return Response({"error": "حساب بانکی و تاریخ الزامی است"}, status=400)
        account = Account.objects.filter(pk=account_id).first()
        if not account:
            return Response({"error": "حساب یافت نشد"}, status=400)
        amount = request.data.get("amount")
        try:
            payment = pay_payslip(slip, account, date, actor=request.user,
                                  amount=int(amount) if amount else None)
        except (ValueError, TypeError) as exc:
            return Response({"error": str(exc)}, status=400)
        return Response({
            "ok": True, "payment_id": payment.id,
            "paid_amount": slip.paid_amount, "remaining_amount": slip.remaining_amount,
            "status": slip.status,
        }, status=201)
