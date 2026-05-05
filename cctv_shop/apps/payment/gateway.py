"""
apps/payment/gateway.py
────────────────────────
Behpardakht Mellat Payment Gateway — کلاینت SOAP درگاه به‌پرداخت ملت.

جریان:
  ① bpPayRequest  → token + redirect_url
  ③ bpVerifyRequest → تأیید پرداخت
  ④ bpSettleRequest → تسویه نهایی
"""
import logging
import re
from dataclasses import dataclass, field

import requests
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

BEHPARDAKHT_PAYMENT_URL = "https://bpm.shaparak.ir/pgwchannel/startpay.mellat"
BEHPARDAKHT_SERVICE_URL  = "https://bpm.shaparak.ir/pgwchannel/services/pgw"

RES_CODES = {
    "0":   "موفق",
    "11":  "شماره کارت نامعتبر",
    "12":  "موجودی ناکافی",
    "13":  "رمز اشتباه",
    "14":  "تعداد تلاش بیش از حد",
    "15":  "کارت نامعتبر",
    "16":  "سقف برداشت روزانه",
    "17":  "انصراف کاربر",
    "18":  "کارت منقضی شده",
    "21":  "پذیرنده نامعتبر",
    "23":  "خطای امنیتی",
    "24":  "اطلاعات پذیرنده اشتباه",
    "25":  "مبلغ نامعتبر",
    "31":  "پاسخ نامعتبر",
    "32":  "فرمت داده اشتباه",
    "33":  "حساب نامعتبر",
    "34":  "خطای سیستمی",
    "41":  "درخواست تکراری",
    "43":  "قبلاً Verify شده",
    "44":  "Verify یافت نشد",
    "45":  "قبلاً Settle شده",
    "51":  "تراکنش تکراری",
    "55":  "تراکنش نامعتبر",
    "415": "جلسه منقضی شده",
    "421": "IP نامعتبر",
}


@dataclass
class PayRequestResult:
    success: bool
    token: str = ""
    redirect_url: str = ""
    res_code: str = ""
    error: str = ""


@dataclass
class VerifyResult:
    success: bool
    res_code: str = ""
    sale_ref_id: str = ""
    error: str = ""


def _soap_call(action: str, body_xml: str, timeout: int = 15) -> str:
    envelope = f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                  xmlns:pgw="http://interfaces.core.sw.beh.com/">
  <soapenv:Header/>
  <soapenv:Body>{body_xml}</soapenv:Body>
</soapenv:Envelope>"""
    resp = requests.post(
        BEHPARDAKHT_SERVICE_URL,
        data=envelope.encode("utf-8"),
        headers={"Content-Type": "text/xml;charset=UTF-8", "SOAPAction": action},
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp.text


def _extract_return(xml: str) -> str:
    m = re.search(r"<return>(.*?)</return>", xml, re.DOTALL)
    return m.group(1).strip() if m else ""


class BehpardakhtGateway:

    def __init__(self):
        self.terminal_id  = getattr(settings, "BEHPARDAKHT_TERMINAL_ID", "")
        self.username     = getattr(settings, "BEHPARDAKHT_USERNAME", "")
        self.password     = getattr(settings, "BEHPARDAKHT_PASSWORD", "")
        self.callback_url = getattr(settings, "BEHPARDAKHT_CALLBACK_URL",
                                    "http://localhost:8000/api/payment/verify/")

    def _configured(self) -> bool:
        return bool(self.terminal_id and self.username and self.password)

    # ① درخواست پرداخت
    def pay_request(self, order_id: int, amount: int, order_desc: str = "") -> PayRequestResult:
        if not self._configured():
            return PayRequestResult(success=False, error="تنظیمات درگاه ناقص است.")

        now = timezone.localtime()
        body = f"""<pgw:bpPayRequest>
  <terminalId>{self.terminal_id}</terminalId>
  <userName>{self.username}</userName>
  <userPassword>{self.password}</userPassword>
  <orderId>{order_id}</orderId>
  <amount>{amount * 10}</amount>
  <localDate>{now.strftime("%Y%m%d")}</localDate>
  <localTime>{now.strftime("%H%M%S")}</localTime>
  <additionalData>{order_desc}</additionalData>
  <callBackUrl>{self.callback_url}</callBackUrl>
  <payerId>0</payerId>
</pgw:bpPayRequest>"""
        try:
            raw = _soap_call("bpPayRequest", body)
        except Exception as e:
            logger.error(f"[GW] bpPayRequest network error: {e}")
            return PayRequestResult(success=False, error=f"خطای اتصال: {e}")

        ret = _extract_return(raw)
        if ret.startswith("0,"):
            token = ret.split(",", 1)[1].strip()
            return PayRequestResult(
                success=True, token=token, res_code="0",
                redirect_url=f"{BEHPARDAKHT_PAYMENT_URL}?RefId={token}",
            )
        code = ret.strip()
        return PayRequestResult(success=False, res_code=code,
                                error=RES_CODES.get(code, f"کد: {code}"))

    # ③ تأیید
    def verify_request(self, order_id: int, sale_order_id: str, sale_ref_id: str) -> VerifyResult:
        if not self._configured():
            return VerifyResult(success=False, error="تنظیمات ناقص")
        body = f"""<pgw:bpVerifyRequest>
  <terminalId>{self.terminal_id}</terminalId>
  <userName>{self.username}</userName>
  <userPassword>{self.password}</userPassword>
  <orderId>{order_id}</orderId>
  <saleOrderId>{sale_order_id}</saleOrderId>
  <saleReferenceId>{sale_ref_id}</saleReferenceId>
</pgw:bpVerifyRequest>"""
        try:
            raw = _soap_call("bpVerifyRequest", body)
        except Exception as e:
            return VerifyResult(success=False, error=f"خطای اتصال: {e}")
        code = _extract_return(raw).strip()
        if code == "0":
            return VerifyResult(success=True, res_code="0", sale_ref_id=sale_ref_id)
        return VerifyResult(success=False, res_code=code, error=RES_CODES.get(code, f"کد: {code}"))

    # ④ تسویه
    def settle_request(self, order_id: int, sale_order_id: str, sale_ref_id: str) -> VerifyResult:
        if not self._configured():
            return VerifyResult(success=False, error="تنظیمات ناقص")
        body = f"""<pgw:bpSettleRequest>
  <terminalId>{self.terminal_id}</terminalId>
  <userName>{self.username}</userName>
  <userPassword>{self.password}</userPassword>
  <orderId>{order_id}</orderId>
  <saleOrderId>{sale_order_id}</saleOrderId>
  <saleReferenceId>{sale_ref_id}</saleReferenceId>
</pgw:bpSettleRequest>"""
        try:
            raw = _soap_call("bpSettleRequest", body)
        except Exception as e:
            return VerifyResult(success=False, error=f"خطای اتصال: {e}")
        code = _extract_return(raw).strip()
        if code == "0":
            return VerifyResult(success=True, res_code="0", sale_ref_id=sale_ref_id)
        return VerifyResult(success=False, res_code=code, error=RES_CODES.get(code, f"کد: {code}"))
