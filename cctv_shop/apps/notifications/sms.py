"""
ارسال پیامک از طریق پنل sms.ir

تنظیمات از مدل SmsSettings (دیتابیس، قابل ویرایش در پنل ادمین) خوانده می‌شود؛
اگر فیلدی در دیتابیس خالی باشد، به متغیرهای .env برمی‌گردد:
  SMS_IR_API_KEY      کلید API از پنل sms.ir
  SMS_IR_TEMPLATE_ID  شناسه قالب Verify برای کد تأیید (پارامتر %CODE%)
"""
import logging
import time

import requests
from decouple import config

logger = logging.getLogger(__name__)

VERIFY_URL = "https://api.sms.ir/v1/send/verify"
BULK_URL = "https://api.sms.ir/v1/send/bulk"

# کش کوتاه‌مدت تنظیمات تا هر پیامک یک کوئری دیتابیس نزند
_settings_cache = {"obj": None, "at": 0.0}
_CACHE_TTL = 60


def get_sms_settings():
    """تنظیمات پیامک از دیتابیس (با کش ۶۰ ثانیه‌ای)"""
    now = time.monotonic()
    if _settings_cache["obj"] is None or now - _settings_cache["at"] > _CACHE_TTL:
        from .models import SmsSettings
        _settings_cache["obj"] = SmsSettings.get_instance()
        _settings_cache["at"] = now
    return _settings_cache["obj"]


def get_api_key():
    key = get_sms_settings().api_key.strip()
    return key or config("SMS_IR_API_KEY", default="")


def get_template_id(kind="otp"):
    """kind: otp | order_status | payment_reminder | tier_change | near_tier | partner_approved | partner_request | invoice_confirmed"""
    value = (getattr(get_sms_settings(), f"{kind}_template_id", "") or "").strip()
    if not value and kind == "otp":
        value = config("SMS_IR_TEMPLATE_ID", default="")
    return value


def get_line_number():
    return (get_sms_settings().line_number or "").strip()


def sms_configured():
    return bool(get_api_key() and get_template_id("otp"))


def _post(url, payload):
    """POST به sms.ir → (ok, message, raw_data)"""
    api_key = get_api_key()
    if not api_key:
        return False, "کلید API پیامک تنظیم نشده است", {}
    try:
        r = requests.post(
            url,
            json=payload,
            headers={"X-API-KEY": api_key, "Content-Type": "application/json", "Accept": "application/json"},
            timeout=20,
        )
        data = r.json() if r.content else {}
        if r.status_code == 200 and data.get("status") == 1:
            return True, "", data
        return False, f"HTTP {r.status_code} — {data.get('message')}", data
    except Exception as e:
        logger.exception(f"[SMS] استثنا در ارتباط با sms.ir: {e}")
        return False, str(e), {}


def send_verify(phone, template_id, params):
    """
    ارسال با سرویس Verify (سریع، قالب‌های از پیش تأییدشده).
    params: دیکشنری {نام پارامتر: مقدار} — مثل {"CODE": "12345"}
    → True/False
    """
    if not template_id:
        logger.error(f"[SMS] شناسه قالب تنظیم نشده — ارسال به {phone} لغو شد")
        return False
    ok, msg, data = _post(VERIFY_URL, {
        "mobile": phone,
        "templateId": int(template_id),
        "parameters": [{"name": k, "value": str(v)} for k, v in params.items()],
    })
    if ok:
        logger.info(f"[SMS] Verify (template={template_id}) برای {phone} ارسال شد "
                    f"(messageId={data.get('data', {}).get('messageId')})")
    else:
        logger.error(f"[SMS] خطا در ارسال Verify به {phone}: {msg}")
    return ok


def send_otp_sms(phone, code):
    """ارسال کد یکبارمصرف. True/False برمی‌گرداند."""
    return send_verify(phone, get_template_id("otp"), {"CODE": code})


def send_bulk_sms(phones, text):
    """
    ارسال متن آزاد گروهی (کمپین) با خط اختصاصی.
    phones: لیست شماره‌ها — به صورت داخلی در دسته‌های ۲۰۰تایی ارسال می‌شود.
    → (تعداد موفق، پیام خطا یا '')
    """
    line = get_line_number()
    if not line:
        return 0, "شماره خط ارسال در تنظیمات پیامک وارد نشده است"
    phones = [p for p in dict.fromkeys(phones) if p]
    sent = 0
    last_error = ""
    for i in range(0, len(phones), 200):
        chunk = phones[i:i + 200]
        ok, msg, _ = _post(BULK_URL, {
            "lineNumber": line,
            "messageText": text,
            "mobiles": chunk,
        })
        if ok:
            sent += len(chunk)
        else:
            last_error = msg
            logger.error(f"[SMS] خطا در ارسال گروهی (دسته {i // 200 + 1}): {msg}")
    return sent, last_error
