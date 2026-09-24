"""
apps/payment/services.py — payment orchestration layer
"""
import logging
from django.db import transaction as db_transaction
from django.utils import timezone

from apps.orders.models import Order
from apps.orders.services import process_payment_callback
from .behpardakht import (
    bp_pay_request, bp_verify_request, bp_settle_request, bp_reverse_request,
    get_payment_url,
)
from .models import PaymentTransaction

logger = logging.getLogger(__name__)


def initiate_payment(order: Order, request) -> dict:
    """
    مرحله ۱: درخواست توکن از بانک.

    فقط برای DIRECT_PURCHASE + AWAITING_PAYMENT + مهلت نگذشته.

    Returns:
      {"success": True,  "redirect_url": "...", "token": 123, "amount_rial": 1500000}
      {"success": False, "error": "..."}
    """
    if order.order_type != Order.OrderType.DIRECT_PURCHASE:
        return {"success": False, "error": "پرداخت آنلاین فقط برای خرید مستقیم است."}
    if order.status != Order.Status.AWAITING_PAYMENT:
        return {"success": False, "error": f"وضعیت سفارش '{order.get_status_display()}' قابل پرداخت نیست."}
    if order.is_payment_expired:
        return {"success": False, "error": "مهلت پرداخت این سفارش منقضی شده است."}

    now = timezone.localtime(timezone.now())
    amount_rial = order.effective_amount

    # تراکنش اول ساخته می‌شود تا id عددی یکتای آن به بانک به‌عنوان orderId برود
    # (به‌پرداخت فقط orderId عددی قبول می‌کند و همان را در SaleOrderId برمی‌گرداند)
    txn = PaymentTransaction.objects.create(
        order=order,
        user=order.user,
        amount=amount_rial,
        status=PaymentTransaction.Status.INITIATED,
        sale_order_id="",
        raw_request={"order_number": order.order_number, "amount_rial": amount_rial},
    )
    txn.sale_order_id = str(txn.id)
    txn.save(update_fields=["sale_order_id", "updated_at"])

    bank_result = bp_pay_request(
        amount_rial=amount_rial,
        order_id=txn.id,
        local_date=now.strftime("%Y%m%d"),
        local_time=now.strftime("%H%M%S"),
        additional_data=f"order:{order.order_number}",
    )

    if not bank_result["success"]:
        txn.status = PaymentTransaction.Status.FAILED
        txn.error_message = bank_result.get("error", "")
        txn.save(update_fields=["status", "error_message", "updated_at"])
        logger.error(f"[PAYMENT] Token failed: order={order.order_number} err={bank_result.get('error')}")
        return {"success": False, "error": bank_result["error"]}

    txn.bank_token = bank_result["token"]
    txn.save(update_fields=["bank_token", "updated_at"])

    redirect_url = get_payment_url(bank_result["token"])
    order.payment_link = redirect_url
    order.save(update_fields=["payment_link", "updated_at"])

    logger.info(f"[PAYMENT] Initiated: order={order.order_number} token={bank_result['token']}")
    return {
        "success": True,
        "redirect_url": redirect_url,
        "token": bank_result["token"],
        "transaction_id": txn.id,
        "amount_rial": amount_rial,
    }


def handle_callback(post_data: dict) -> dict:
    """
    مرحله ۲: پردازش callback POST از بانک.

    فیلدهایی که به‌پرداخت POST می‌کند:
      RefId (توکن bpPayRequest)، ResCode، SaleOrderId (همان orderId عددی ما)،
      SaleReferenceId، FinalAmount، CardHolderPan

    Returns:
      {"success": True,  "order": <Order>, "ref_id": "...", "message": "..."}
      {"success": False, "error": "...",   "order": <Order>|None}
    """
    res_code      = str(post_data.get("ResCode", "")).strip()
    token_str     = str(post_data.get("RefId") or post_data.get("Token") or "").strip()
    sale_order_id = str(post_data.get("SaleOrderId", "")).strip()
    sale_ref_id   = str(post_data.get("SaleReferenceId", "")).strip()
    final_amount  = str(post_data.get("FinalAmount", "")).strip()

    logger.info(f"[PAYMENT] Callback: ResCode={res_code} RefId={token_str} SaleOrderId={sale_order_id}")

    txn = _find_transaction(token_str, sale_order_id)
    if txn is None:
        logger.error(f"[PAYMENT] Transaction not found: token={token_str} saleOrderId={sale_order_id}")
        return {"success": False, "error": "تراکنش یافت نشد.", "order": None}

    txn.raw_callback = dict(post_data)
    txn.res_code = res_code
    txn.save(update_fields=["raw_callback", "res_code", "updated_at"])
    order = txn.order

    if res_code != "0":
        from .behpardakht import _res_code_message
        msg = _res_code_message(res_code)
        _finalize_failure(txn, msg)
        return {"success": False, "error": msg, "order": order}

    if txn.status == PaymentTransaction.Status.SUCCESS:
        logger.warning(f"[PAYMENT] Duplicate callback for txn {txn.id}")
        # خودترمیمی: اگر تراکنش موفق ولی سفارش PAID نشده (کرش قبلی)، پردازش داخلی را تکمیل کن
        if order.status != Order.Status.PAID:
            try:
                process_payment_callback(order=order, ref_id=txn.sale_ref_id, success=True)
            except Exception:
                logger.critical(f"[PAYMENT] Self-heal failed for order {order.order_number}", exc_info=True)
        return {"success": True, "order": order, "ref_id": txn.sale_ref_id, "message": "قبلاً تأیید شده."}

    # کنترل مبلغ — مغایرت یعنی دستکاری؛ تراکنش برگشت می‌خورد
    if final_amount and final_amount.lstrip("-").isdigit() and int(final_amount) != txn.amount:
        logger.critical(
            f"[PAYMENT] Amount mismatch: txn={txn.id} expected={txn.amount} got={final_amount} — reversing"
        )
        bp_reverse_request(txn.sale_order_id, txn.sale_order_id, sale_ref_id)
        msg = "مبلغ پرداخت‌شده با مبلغ سفارش مغایرت دارد؛ تراکنش برگشت داده شد."
        _finalize_failure(txn, msg)
        return {"success": False, "error": msg, "order": order}

    return _finalize_success(txn, sale_order_id, sale_ref_id)


def _finalize_success(txn, sale_order_id, sale_ref_id) -> dict:
    """
    verify → settle → ثبت موفقیت → پردازش داخلی (کسر موجودی، PAID).

    قاعده مهم: بعد از verify موفق پول مشتری گرفته شده — از آن نقطه به بعد
    هیچ خطای داخلی نباید باعث ۵۰۰ شدن callback شود؛ تراکنش SUCCESS ثبت می‌شود
    و خطای پردازش داخلی فقط critical لاگ می‌شود تا دستی پیگیری شود.
    (بدون atomic سراسری: تماس‌های HTTP بانک نباید داخل تراکنش DB باشند.)
    """
    order = txn.order

    verify = bp_verify_request(
        order_id=txn.sale_order_id,
        sale_order_id=sale_order_id,
        sale_reference_id=sale_ref_id,
    )
    txn.raw_verify = verify
    txn.sale_ref_id = sale_ref_id
    txn.save(update_fields=["raw_verify", "sale_ref_id", "updated_at"])

    if not verify["success"]:
        _finalize_failure(txn, verify["error"])
        return {"success": False, "error": f"تأیید ناموفق: {verify['error']}", "order": order}

    # Settle — حتی اگر شکست بخورد سفارش را PAID می‌کنیم (پول گرفته شده)
    settle = bp_settle_request(txn.sale_order_id, sale_order_id, sale_ref_id)
    if not settle["success"]:
        logger.critical(
            f"[PAYMENT] Settle FAILED (verify OK) — order={order.order_number} "
            f"ref={sale_ref_id} settle_rc={settle.get('res_code')}"
        )

    # پول گرفته شده — موفقیت تراکنش را اول ثبت کن تا callback تکراری دوباره verify نزند
    txn.status = PaymentTransaction.Status.SUCCESS
    txn.save(update_fields=["status", "updated_at"])

    try:
        with db_transaction.atomic():
            process_payment_callback(order=order, ref_id=sale_ref_id, success=True)
    except ValueError as e:
        # سفارش قبلاً از وضعیت «در انتظار پرداخت» خارج شده — قابل چشم‌پوشی
        if "مناسب" not in str(e):
            logger.critical(
                f"[PAYMENT] Post-process ValueError after successful payment — "
                f"order={order.order_number} ref={sale_ref_id}: {e}"
            )
    except Exception:
        logger.critical(
            f"[PAYMENT] Post-process FAILED after successful payment — "
            f"order={order.order_number} ref={sale_ref_id} — پیگیری دستی لازم است",
            exc_info=True,
        )

    logger.info(f"[PAYMENT] ✓ order={order.order_number} ref={sale_ref_id}")
    return {"success": True, "order": order, "ref_id": sale_ref_id, "message": "پرداخت موفق"}


def _finalize_failure(txn, error_msg: str) -> None:
    txn.status = PaymentTransaction.Status.FAILED
    txn.error_message = error_msg
    txn.save(update_fields=["status", "error_message", "updated_at"])
    logger.warning(f"[PAYMENT] Failed: order={txn.order.order_number} reason={error_msg}")


def _find_transaction(token_str: str, sale_order_id: str):
    # بدون فیلتر وضعیت — callback تکراری هم باید تراکنش را پیدا کند
    if token_str:
        txn = (PaymentTransaction.objects
               .filter(bank_token=token_str)
               .select_related("order__user")
               .order_by("-created_at").first())
        if txn:
            return txn
    if sale_order_id:
        return (PaymentTransaction.objects
                .filter(sale_order_id=sale_order_id)
                .select_related("order__user").order_by("-created_at").first())
    return None
