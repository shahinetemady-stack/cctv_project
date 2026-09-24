from rest_framework import serializers

from .models import (
    BonusPenaltyRecord,
    LeaveRecord,
    Payslip,
    PayslipPayment,
    PayrollProfile,
)


class PayrollProfileSerializer(serializers.ModelSerializer):
    staff_name = serializers.SerializerMethodField()
    staff_phone = serializers.CharField(source="staff.phone", read_only=True)

    class Meta:
        model = PayrollProfile
        fields = [
            "id", "staff", "staff_name", "staff_phone",
            "has_base_salary", "has_commission_personal", "has_commission_total",
            "has_bonus_penalty", "has_annual_bonus", "has_leave_management",
            "base_amount",
            "personal_commission_tiers", "total_share_tiers",
            "annual_bonus_months", "annual_bonus_formula",
            "working_days_divisor", "leave_entitled_days_per_month",
            "leave_sick_days_per_month",
            "is_active",
        ]

    def get_staff_name(self, obj):
        return obj.staff.get_full_name() or obj.staff.phone


class LeaveRecordSerializer(serializers.ModelSerializer):
    staff_name = serializers.SerializerMethodField()

    class Meta:
        model = LeaveRecord
        fields = ["id", "staff", "staff_name", "leave_type", "date", "days_count", "reason"]

    def get_staff_name(self, obj):
        return obj.staff.get_full_name() or obj.staff.phone


class BonusPenaltyRecordSerializer(serializers.ModelSerializer):
    staff_name = serializers.SerializerMethodField()

    class Meta:
        model = BonusPenaltyRecord
        fields = ["id", "staff", "staff_name", "date", "amount", "note"]

    def get_staff_name(self, obj):
        return obj.staff.get_full_name() or obj.staff.phone


class PayslipSerializer(serializers.ModelSerializer):
    staff_name = serializers.SerializerMethodField()

    class Meta:
        model = Payslip
        fields = [
            "id", "staff", "staff_name", "year", "month", "status",
            "base_amount", "personal_commission_amount", "total_sales_share_amount",
            "bonus_penalty_amount", "annual_bonus_amount", "leave_deduction",
            "gross_amount", "net_amount", "paid_amount",
            "entitled_used", "sick_used", "unpaid_used",
            "personal_sales", "total_sales",
            "payment_id", "notes",
        ]

    def get_staff_name(self, obj):
        return obj.staff.get_full_name() or obj.staff.phone


class PayslipPaymentSerializer(serializers.ModelSerializer):
    date = serializers.DateField(source="payment.date", read_only=True)
    account_name = serializers.CharField(source="payment.from_account.name", read_only=True)
    payment_id = serializers.IntegerField(source="payment.id", read_only=True)

    class Meta:
        model = PayslipPayment
        fields = ["id", "payment_id", "amount", "date", "account_name"]


class PayslipDetailSerializer(PayslipSerializer):
    """فیش کامل با ریز اجزا — برای نمایش/چاپ فیش حقوقی."""
    leave_records = serializers.SerializerMethodField()
    bonus_penalty_records = serializers.SerializerMethodField()
    installments = PayslipPaymentSerializer(many=True, read_only=True)
    remaining_amount = serializers.IntegerField(read_only=True)
    accrual_payment_id = serializers.IntegerField(read_only=True)

    class Meta(PayslipSerializer.Meta):
        fields = PayslipSerializer.Meta.fields + [
            "leave_records", "bonus_penalty_records",
            "installments", "remaining_amount", "accrual_payment_id",
        ]

    def get_leave_records(self, obj):
        from .services import _month_bounds
        start, end = _month_bounds(obj.year, obj.month)
        qs = obj.staff.leave_records.filter(date__gte=start, date__lte=end)
        return LeaveRecordSerializer(qs, many=True).data

    def get_bonus_penalty_records(self, obj):
        from .services import _month_bounds
        start, end = _month_bounds(obj.year, obj.month)
        qs = obj.staff.bonus_penalty_records.filter(date__gte=start, date__lte=end)
        return BonusPenaltyRecordSerializer(qs, many=True).data
