from rest_framework import serializers

from .models import (
    ExpenseCategory,
    ExpenseCharge,
    ExpenseChargePayment,
    Investor,
    InvestorMovement,
    RecurringExpense,
)


class ExpenseCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseCategory
        fields = ["id", "name", "category_type", "is_active"]


class RecurringExpenseSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    contact_name = serializers.CharField(source="contact.name", read_only=True, default="")

    class Meta:
        model = RecurringExpense
        fields = ["id", "title", "category", "category_name", "monthly_amount",
                  "contact", "contact_name", "deposit_amount", "start_date", "is_active"]


class ExpenseChargePaymentSerializer(serializers.ModelSerializer):
    date = serializers.DateField(source="payment.date", read_only=True)
    account_name = serializers.CharField(source="payment.from_account.name", read_only=True)

    class Meta:
        model = ExpenseChargePayment
        fields = ["id", "amount", "date", "account_name"]


class ExpenseChargeSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True, default="")
    contact_name = serializers.CharField(source="contact.name", read_only=True, default="")
    remaining_amount = serializers.IntegerField(read_only=True)

    class Meta:
        model = ExpenseCharge
        fields = ["id", "source", "title", "category", "category_name", "recurring",
                  "investor", "contact", "contact_name", "year", "month", "amount",
                  "status", "paid_amount", "remaining_amount", "notes"]


class ExpenseChargeDetailSerializer(ExpenseChargeSerializer):
    installments = ExpenseChargePaymentSerializer(many=True, read_only=True)

    class Meta(ExpenseChargeSerializer.Meta):
        fields = ExpenseChargeSerializer.Meta.fields + ["installments"]


class InvestorSerializer(serializers.ModelSerializer):
    contact_name = serializers.CharField(source="contact.name", read_only=True)
    contact_phone = serializers.CharField(source="contact.phone", read_only=True)
    principal = serializers.IntegerField(read_only=True)

    class Meta:
        model = Investor
        fields = ["id", "contact", "contact_name", "contact_phone",
                  "annual_rate", "principal", "is_active"]


class InvestorMovementSerializer(serializers.ModelSerializer):
    signed_amount = serializers.IntegerField(read_only=True)
    account_name = serializers.CharField(source="account.name", read_only=True, default="")

    class Meta:
        model = InvestorMovement
        fields = ["id", "investor", "movement_type", "date", "amount",
                  "signed_amount", "account", "account_name", "note"]
