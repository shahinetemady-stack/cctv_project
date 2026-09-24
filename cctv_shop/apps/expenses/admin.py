from django.contrib import admin

from .models import (
    ExpenseCategory,
    ExpenseCharge,
    ExpenseChargePayment,
    Investor,
    InvestorMovement,
    RecurringExpense,
)


@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "category_type", "is_active")
    list_filter = ("category_type",)


@admin.register(RecurringExpense)
class RecurringExpenseAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "monthly_amount", "deposit_amount", "is_active")
    search_fields = ("title",)


@admin.register(ExpenseCharge)
class ExpenseChargeAdmin(admin.ModelAdmin):
    list_display = ("title", "source", "year", "month", "amount", "status", "paid_amount")
    list_filter = ("source", "year", "month", "status")
    exclude = ("payment", "accrual_payment")


@admin.register(Investor)
class InvestorAdmin(admin.ModelAdmin):
    list_display = ("contact", "annual_rate", "is_active")


@admin.register(InvestorMovement)
class InvestorMovementAdmin(admin.ModelAdmin):
    list_display = ("investor", "movement_type", "date", "amount")
    date_hierarchy = "date"


@admin.register(ExpenseChargePayment)
class ExpenseChargePaymentAdmin(admin.ModelAdmin):
    list_display = ("charge", "amount", "payment")
