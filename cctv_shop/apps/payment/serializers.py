from rest_framework import serializers
from .models import PaymentTransaction


class PaymentTransactionSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    order_number   = serializers.CharField(source="order.order_number",  read_only=True)
    amount_toman   = serializers.SerializerMethodField()

    class Meta:
        model  = PaymentTransaction
        fields = [
            "id", "order_number", "amount_toman", "amount",
            "status", "status_display",
            "bank_token", "res_code", "sale_ref_id",
            "error_message", "created_at", "updated_at",
        ]

    def get_amount_toman(self, obj):
        return obj.amount // 10  # ریال → تومان
