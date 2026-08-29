"""
apps/notifications/views.py
────────────────────────────
پنل ادمین پیامک:

GET/PUT /api/notifications/sms-settings/           → تنظیمات پنل sms.ir (کلید، قالب‌ها، کلیدهای روشن/خاموش)
GET     /api/notifications/sms-campaign/segments/  → تعداد گیرندگان هر گروه
POST    /api/notifications/sms-campaign/send/      → ارسال پیامک گروهی به یک گروه از مشتریان
"""

import logging

from django.contrib.auth import get_user_model
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import SmsSettings
from .serializers import SmsSettingsSerializer

logger = logging.getLogger(__name__)


class SmsSettingsView(APIView):
    """GET/PUT تنظیمات پیامک — فقط ادمین"""
    permission_classes = [IsAdminUser]

    def get(self, request):
        return Response(SmsSettingsSerializer(SmsSettings.get_instance()).data)

    def put(self, request):
        settings_obj = SmsSettings.get_instance()
        serializer = SmsSettingsSerializer(settings_obj, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)
        serializer.save()
        # کش داخلی sms.py را بی‌اعتبار کن تا تنظیمات جدید فوراً اعمال شود
        from . import sms
        sms._settings_cache["obj"] = None
        logger.info(f"[SMS] تنظیمات پیامک توسط {request.user.phone} به‌روزرسانی شد")
        return Response(serializer.data)


# ─── کمپین پیامکی ─────────────────────────────────────────────────────────────

SEGMENTS = {
    "all_users": "همه کاربران سایت",
    "public": "مشتریان عمومی",
    "partner": "همکاران تأییدشده",
    "silver": "همکاران سیلور",
    "gold": "همکاران گلد",
    "platinum": "همکاران پلاتینیوم",
    "contacts": "طرف‌حساب‌های دستی (بدون حساب سایت)",
}


def _segment_phones(segment):
    """لیست شماره موبایل‌های یک گروه"""
    User = get_user_model()
    users = User.objects.filter(is_active=True).exclude(phone="").exclude(phone__isnull=True)

    if segment == "all_users":
        return list(users.values_list("phone", flat=True))
    if segment == "public":
        return list(users.exclude(profile__user_type="partner").values_list("phone", flat=True))
    if segment == "partner":
        return list(users.filter(profile__user_type="partner", profile__is_approved=True)
                    .values_list("phone", flat=True))
    if segment in ("silver", "gold", "platinum"):
        return list(users.filter(profile__user_type="partner", profile__is_approved=True,
                                 profile__partner_tier=segment)
                    .values_list("phone", flat=True))
    if segment == "contacts":
        from apps.accounting.models import Contact
        return list(Contact.objects.filter(contact_type__in=["customer", "partner"])
                    .exclude(phone="").exclude(phone__isnull=True)
                    .values_list("phone", flat=True))
    return []


class SmsCampaignSegmentsView(APIView):
    """GET تعداد گیرندگان هر گروه"""
    permission_classes = [IsAdminUser]

    def get(self, request):
        return Response({
            "segments": [
                {"key": key, "label": label, "count": len(_segment_phones(key))}
                for key, label in SEGMENTS.items()
            ]
        })


class SmsCampaignSendView(APIView):
    """POST {segment, text} → ارسال پیامک گروهی"""
    permission_classes = [IsAdminUser]

    def post(self, request):
        segment = request.data.get("segment", "")
        text = str(request.data.get("text") or "").strip()
        if segment not in SEGMENTS:
            return Response({"error": "گروه هدف نامعتبر است"}, status=400)
        if not text:
            return Response({"error": "متن پیامک نمی‌تواند خالی باشد"}, status=400)

        phones = _segment_phones(segment)
        if not phones:
            return Response({"error": "هیچ گیرنده‌ای در این گروه یافت نشد"}, status=400)

        from .sms import send_bulk_sms
        from .services import _log
        sent, error = send_bulk_sms(phones, text)
        _log(
            channel="sms",
            recipient_type="user",
            recipient_address=f"کمپین:{segment}",
            subject=f"sms_campaign:{segment}",
            message=text,
            status="sent" if sent else "failed",
            error_message=error,
        )
        logger.info(f"[SMS] کمپین «{SEGMENTS[segment]}» توسط {request.user.phone}: "
                    f"{sent}/{len(phones)} ارسال شد")
        if not sent:
            return Response({"error": f"ارسال ناموفق بود — {error}"}, status=502)
        return Response({"ok": True, "sent": sent, "total": len(phones), "error": error})
