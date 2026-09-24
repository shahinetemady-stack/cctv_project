"""
apps/payment/behpardakht.py
────────────────────────────
کلاینت درگاه به‌پرداخت ملت (Behpardakht Mellat).

پروتکل: SOAP over HTTPS
وب‌سرویس: https://bpm.shaparak.ir/pgwchannel/services/pgw

جریان:
  ① bpPayRequest   → token (عدد بزرگ)
  ② redirect       → کاربر به صفحه بانک می‌رود
  ③ callback POST  → ResCode, Token, SaleOrderId, SaleReferenceId
  ④ bpVerifyRequest → تأیید نهایی (ضروری برای تسویه)
  ⑤ bpSettleRequest → نهایی‌سازی (در صورت نیاز)

کدهای ResCode مهم:
  0   → موفق
  -1  → خطای سیستمی
  17  → کاربر انصراف داد
  21  → قبلاً تأیید شده (تکراری — باید برگشتی داده شود)
  79  → مبلغ تراکنش با مبلغ ثبت‌شده مغایرت دارد

منبع: مستندات رسمی به‌پرداخت ملت — نسخه 1.4
"""

import logging
from typing import Optional
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

# ─── Constants ────────────────────────────────────────────────────────────────

WSDL_URL = "https://bpm.shaparak.ir/pgwchannel/services/pgw"
PAYMENT_PAGE_URL = "https://bpm.shaparak.ir/pgwchannel/startpay.mellat"
SOAP_TIMEOUT = 15  # ثانیه

# ─── SOAP Templates ───────────────────────────────────────────────────────────

_SOAP_ENVELOPE = """<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope
  xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
  xmlns:int="http://interfaces.core.sw.bps.com/">
  <soapenv:Header/>
  <soapenv:Body>
    <int:{method}>
      {params}
    </int:{method}>
  </soapenv:Body>
</soapenv:Envelope>"""

_SOAP_HEADERS = {
    "Content-Type": "text/xml;charset=UTF-8",
    "SOAPAction": "",
}


def _param(name: str, value) -> str:
    return f"<{name}>{escape(str(value))}</{name}>"


def _soap_call(method: str, params: dict) -> Optional[str]:
    """
    ارسال درخواست SOAP و برگرداندن محتوای تگ return.
    در صورت خطا None برمی‌گرداند.
    """
    params_xml = "\n".join(_param(k, v) for k, v in params.items())
    body = _SOAP_ENVELOPE.format(method=method, params=params_xml)

    try:
        resp = requests.post(
            WSDL_URL,
            data=body.encode("utf-8"),
            headers=_SOAP_HEADERS,
            timeout=SOAP_TIMEOUT,
            verify=True,
        )
        resp.raise_for_status()
        root = ET.fromstring(resp.text)
        # پیدا کردن تگ return (فرزند هر جایی در درخت)
        for elem in root.iter():
            if elem.tag.endswith("return"):
                return elem.text
        logger.error(f"[BANK] No <return> in response: {resp.text[:300]}")
        return None
    except requests.Timeout:
        logger.error(f"[BANK] SOAP timeout on {method}")
        return None
    except requests.RequestException as e:
        logger.error(f"[BANK] SOAP request failed ({method}): {e}")
        return None
    except ET.ParseError as e:
        logger.error(f"[BANK] XML parse error ({method}): {e}")
        return None


# ─── Gateway Methods ──────────────────────────────────────────────────────────

def bp_pay_request(
    amount_rial: int,
    order_id: int,
    local_date: str,
    local_time: str,
    additional_data: str = "",
    payer_id: str = "",
) -> dict:
    """
    مرحله ۱ — دریافت توکن پرداخت از بانک.

    amount_rial: مبلغ به ریال (قرارداد کل پروژه ریال است — هیچ تبدیلی اینجا انجام نمی‌شود)
    order_id   : شناسه عددی یکتای تراکنش — بانک فقط عدد (long) قبول می‌کند
    local_date : تاریخ میلادی سرور YYYYMMDD
    local_time : ساعت HHMMSS

    Returns:
      {"success": True,  "token": 1234567890, "amount_rial": 150000}
      {"success": False, "error": "توضیح خطا", "res_code": "-1"}
    """
    terminal_id = getattr(settings, "BEHPARDAKHT_TERMINAL_ID", "")
    username    = getattr(settings, "BEHPARDAKHT_USERNAME", "")
    password    = getattr(settings, "BEHPARDAKHT_PASSWORD", "")
    callback    = getattr(settings, "BEHPARDAKHT_CALLBACK_URL", "")

    if not all([terminal_id, username, password, callback]):
        logger.error("[BANK] Behpardakht credentials not configured.")
        return {"success": False, "error": "اعتبارنامه درگاه پیکربندی نشده است."}

    params = {
        "terminalId":     terminal_id,
        "userName":       username,
        "userPassword":   password,
        "orderId":        int(order_id),
        "amount":         int(amount_rial),
        "localDate":      local_date,
        "localTime":      local_time,
        "additionalData": additional_data or "",
        "callBackUrl":    callback,
        "payerId":        payer_id or "0",
    }

    logger.info(f"[BANK] bpPayRequest → order={order_id} amount={amount_rial}rial")
    result = _soap_call("bpPayRequest", params)

    if result is None:
        return {"success": False, "error": "خطا در ارتباط با بانک. لطفاً دوباره تلاش کنید."}

    parts = result.split(",")
    res_code = parts[0].strip()

    if res_code != "0":
        msg = _res_code_message(res_code)
        logger.warning(f"[BANK] bpPayRequest failed: resCode={res_code}")
        return {"success": False, "error": msg, "res_code": res_code}

    if len(parts) < 2 or not parts[1].strip():
        logger.error(f"[BANK] bpPayRequest: no token in response: {result}")
        return {"success": False, "error": "توکن معتبر از بانک دریافت نشد."}

    token = parts[1].strip()  # RefId — رشته هگز است، نه عدد
    logger.info(f"[BANK] Token received: {token} for order {order_id}")
    return {"success": True, "token": token, "amount_rial": int(amount_rial)}


def bp_verify_request(
    order_id: str,
    sale_order_id: str,
    sale_reference_id: str,
) -> dict:
    """
    مرحله ۴ — تأیید تراکنش پس از callback موفق.
    باید بلافاصله بعد از callback فراخوانی شود.

    Returns:
      {"success": True,  "res_code": "0"}
      {"success": False, "error": "...", "res_code": "-1"}
    """
    terminal_id = getattr(settings, "BEHPARDAKHT_TERMINAL_ID", "")
    username    = getattr(settings, "BEHPARDAKHT_USERNAME", "")
    password    = getattr(settings, "BEHPARDAKHT_PASSWORD", "")

    params = {
        "terminalId":      terminal_id,
        "userName":        username,
        "userPassword":    password,
        "orderId":         order_id,
        "saleOrderId":     sale_order_id,
        "saleReferenceId": sale_reference_id,
    }

    logger.info(f"[BANK] bpVerifyRequest → order={order_id} ref={sale_reference_id}")
    result = _soap_call("bpVerifyRequest", params)

    if result is None:
        return {"success": False, "error": "خطا در تأیید تراکنش با بانک.", "res_code": ""}

    res_code = str(result).strip()

    if res_code == "0":
        logger.info(f"[BANK] Verify OK: order={order_id}")
        return {"success": True, "res_code": res_code}

    # کد ۴۳ = قبلاً verify شده — یعنی پول مشتری یک بار گرفته شده و verify اول موفق بوده
    # (معمولاً یعنی callback اول بعد از verify کرش کرده). این را موفق حساب می‌کنیم تا
    # جریان settle/ثبت سفارش ادامه پیدا کند — reverse خودکار اینجا اشتباه است چون
    # پرداخت قانونی مشتری را برمی‌گرداند.
    if res_code == "43":
        logger.warning(f"[BANK] Already verified (43) — treating as success: order={order_id}")
        return {"success": True, "res_code": res_code}

    msg = _res_code_message(res_code)
    logger.warning(f"[BANK] Verify failed: resCode={res_code} order={order_id}")
    return {"success": False, "error": msg, "res_code": res_code}


def bp_settle_request(
    order_id: str,
    sale_order_id: str,
    sale_reference_id: str,
) -> dict:
    """
    مرحله ۵ — نهایی‌سازی (settle) تراکنش.
    باید ظرف ۳۰ دقیقه پس از verify فراخوانی شود.

    در اغلب موارد به‌پرداخت این مرحله را اتوماتیک انجام می‌دهد،
    اما توصیه می‌شود صراحتاً فراخوانی شود.
    """
    terminal_id = getattr(settings, "BEHPARDAKHT_TERMINAL_ID", "")
    username    = getattr(settings, "BEHPARDAKHT_USERNAME", "")
    password    = getattr(settings, "BEHPARDAKHT_PASSWORD", "")

    params = {
        "terminalId":      terminal_id,
        "userName":        username,
        "userPassword":    password,
        "orderId":         order_id,
        "saleOrderId":     sale_order_id,
        "saleReferenceId": sale_reference_id,
    }

    result = _soap_call("bpSettleRequest", params)
    res_code = str(result).strip() if result else ""

    if res_code in ("0", "45"):  # 45 = قبلاً settle شده
        logger.info(f"[BANK] Settle OK (rc={res_code}): order={order_id}")
        return {"success": True, "res_code": res_code}

    logger.warning(f"[BANK] Settle failed: resCode={res_code} order={order_id}")
    return {"success": False, "res_code": res_code,
            "error": _res_code_message(res_code)}


def bp_reverse_request(
    order_id: str,
    sale_order_id: str,
    sale_reference_id: str,
) -> dict:
    """برگشت تراکنش (در صورت verify تکراری یا خطا)."""
    terminal_id = getattr(settings, "BEHPARDAKHT_TERMINAL_ID", "")
    username    = getattr(settings, "BEHPARDAKHT_USERNAME", "")
    password    = getattr(settings, "BEHPARDAKHT_PASSWORD", "")

    params = {
        "terminalId":      terminal_id,
        "userName":        username,
        "userPassword":    password,
        "orderId":         order_id,
        "saleOrderId":     sale_order_id,
        "saleReferenceId": sale_reference_id,
    }

    result = _soap_call("bpReversalRequest", params)
    res_code = str(result).strip() if result else ""
    ok = res_code in ("0", "45")
    logger.info(f"[BANK] Reverse {'OK' if ok else 'FAIL'} (rc={res_code}): order={order_id}")
    return {"success": ok, "res_code": res_code}


# ─── Payment URL ──────────────────────────────────────────────────────────────

def get_payment_url(token: str) -> str:
    """URL کامل صفحه پرداخت بانک برای هدایت کاربر."""
    return f"{PAYMENT_PAGE_URL}?RefId={token}"


# ─── Helper — ResCode Messages ────────────────────────────────────────────────

_RES_CODE_MESSAGES = {
    "0":   "تراکنش موفق",
    "-1":  "خطای سیستمی بانک",
    "-2":  "اطلاعات ارسالی ناقص است",
    "-3":  "پذیرنده غیرفعال است",
    "-4":  "سرویس موقتاً غیرفعال است",
    "11":  "شماره کارت نامعتبر است",
    "12":  "موجودی کافی نیست",
    "13":  "رمز کارت اشتباه است",
    "14":  "تعداد دفعات ورود رمز غلط بیش از حد مجاز",
    "15":  "کارت نامعتبر است",
    "16":  "دفعات برداشت از حد مجاز گذشته",
    "17":  "کاربر از انجام تراکنش منصرف شد",
    "18":  "تاریخ انقضای کارت گذشته است",
    "19":  "مبلغ برداشت از حد مجاز کارت بیشتر است",
    "21":  "پذیرنده نامعتبر است",
    "23":  "خطای امنیتی رخ داده است",
    "24":  "اطلاعات کاربری پذیرنده نادرست است",
    "25":  "مبلغ نامعتبر است",
    "31":  "پاسخ نامعتبر",
    "32":  "فرمت اطلاعات وارد شده صحیح نمی‌باشد",
    "33":  "حساب نامعتبر است",
    "34":  "خطای سیستمی",
    "35":  "تاریخ نامعتبر است",
    "41":  "شماره درخواست تکراری است",
    "42":  "تراکنش Sale یافت نشد",
    "43":  "قبلاً درخواست Verify داده شده است",
    "44":  "درخواست Verify یافت نشد",
    "45":  "تراکنش Settle شده است",
    "46":  "تراکنش Settle نشده است",
    "47":  "تراکنش Settle نشده یافت نشد",
    "48":  "تراکنش Reverse شده است",
    "49":  "تراکنش Refund نشده است",
    "51":  "تراکنش تکراری است",
    "54":  "تراکنش مرجع موجود نیست",
    "55":  "تراکنش نامعتبر است",
    "61":  "خطا در واریز",
    "62":  "مسیر بازگشت نامعتبر است",
    "63":  "خطای امنیتی",
    "73":  "تاریخ پرداخت نامعتبر است",
    "79":  "مبلغ پرداخت با مبلغ تراکنش مغایرت دارد",
    "84":  "سرویس‌دهنده غیرفعال است",
    "86":  "پذیرنده غیرفعال است",
    "90":  "درخواست Settle تراکنش غیرمعتبر",
}


def _res_code_message(code: str) -> str:
    return _RES_CODE_MESSAGES.get(
        str(code),
        f"خطای ناشناخته بانک (کد: {code})",
    )
