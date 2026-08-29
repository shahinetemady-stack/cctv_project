"""
apps/notifications/serializers.py
"""
from rest_framework import serializers

from .models import SmsSettings


class SmsSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SmsSettings
        fields = [
            "api_key", "line_number",
            "otp_template_id", "order_status_template_id",
            "payment_reminder_template_id", "tier_change_template_id",
            "partner_approved_template_id", "invoice_confirmed_template_id",
            "account_info_template_id",
            "order_status_enabled", "payment_reminder_enabled",
            "tier_change_enabled", "partner_approved_enabled",
            "invoice_confirmed_enabled", "account_info_enabled",
        ]
