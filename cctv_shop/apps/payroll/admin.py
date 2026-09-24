from django.contrib import admin

from .models import (
    BonusPenaltyRecord,
    LeaveRecord,
    Payslip,
    PayslipPayment,
    PayrollProfile,
)


@admin.register(PayrollProfile)
class PayrollProfileAdmin(admin.ModelAdmin):
    list_display = (
        "staff", "is_active", "has_base_salary", "has_commission_personal",
        "has_commission_total", "has_bonus_penalty", "has_annual_bonus",
        "has_leave_management", "base_amount",
    )
    list_filter = ("is_active", "has_base_salary", "has_commission_personal")
    search_fields = ("staff__first_name", "staff__last_name", "staff__phone")


@admin.register(LeaveRecord)
class LeaveRecordAdmin(admin.ModelAdmin):
    list_display = ("staff", "leave_type", "date", "days_count", "reason")
    list_filter = ("leave_type",)
    search_fields = ("staff__first_name", "staff__last_name", "staff__phone")
    date_hierarchy = "date"


@admin.register(BonusPenaltyRecord)
class BonusPenaltyRecordAdmin(admin.ModelAdmin):
    list_display = ("staff", "date", "amount", "note")
    search_fields = ("staff__first_name", "staff__last_name", "staff__phone")
    date_hierarchy = "date"


@admin.register(Payslip)
class PayslipAdmin(admin.ModelAdmin):
    list_display = (
        "staff", "year", "month", "status", "gross_amount", "leave_deduction", "net_amount",
    )
    list_filter = ("year", "month", "status")
    exclude = ("payment", "accrual_payment")
    search_fields = ("staff__first_name", "staff__last_name", "staff__phone")


@admin.register(PayslipPayment)
class PayslipPaymentAdmin(admin.ModelAdmin):
    list_display = ("payslip", "amount", "payment")
    search_fields = ("payslip__staff__first_name", "payslip__staff__last_name")
