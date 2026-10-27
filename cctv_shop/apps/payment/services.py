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


def _payable_amount(order):
    invoice = getattr(order, "sale_invoice", None)
    return int(invoice.remaining_amount) if invoice else int(order.effective_amount)


def initiate_payment(order: Order, request) -> dict:
    """ساخت/بازیابی یک تراکنش فعال برای مبلغ واقعی بدهی سفارش."""
    with db_transaction.atomic():
        order = Order.objects.select_for_update().select_related("user").get(pk=order.pk)
        if order.order_type != Order.OrderType.DIRECT_PURCHASE:
            return {"success": False, "error": "پرداخت آنلاین فقط برای خرید مستقیم است."}
        if order.status != Order.Status.AWAITING_PAYMENT:
            return {"success": False, "error": f"وضعیت سفارش '{order.get_status_display()}' قابل پرداخت نیست."}
        if order.is_payment_expired:
            return {"success": False, "error": "مهلت پرداخت این سفارش منقضی شده است."}
        if PaymentTransaction.objects.filter(order=order, status=PaymentTransaction.Status.SUCCESS).exists():
            return {"success": False, "error": "برای این سفارش قبلاً پرداخت موفق ثبت شده است."}

        amount_rial = _payable_amount(order)
        if amount_rial <= 0:
            return {"success": False, "error": "برای این سفارش مانده قابل پرداخت وجود ندارد."}
        existing = PaymentTransaction.objects.filter(
            order=order, amount=amount_rial, status=PaymentTransaction.Status.INITIATED,
        ).exclude(bank_token="").order_by("-created_at").first()
        if existing:
            return {
                "success": True,
                "redirect_url": get_payment_url(existing.bank_token),
                "token": existing.bank_token,
                "transaction_id": existing.id,
                "amount_rial": amount_rial,
            }

        now = timezone.localtime(timezone.now())
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
        invoice = getattr(order, "sale_invoice", None)
        reconciliation_pending = False
        if order.status != Order.Status.PAID and (not invoice or invoice.status != "paid"):
            try:
                process_payment_callback(order=order, ref_id=txn.sale_ref_id, success=True)
                txn.error_message = ""
            except Exception as exc:
                reconciliation_pending = True
                txn.error_message = f"تکمیل داخلی پس از callback تکراری ناموفق بود: {exc}"
                logger.critical(f"[PAYMENT] Self-heal failed for order {order.order_number}", exc_info=True)
            txn.save(update_fields=["error_message", "updated_at"])
        return {
            "success": True, "order": order, "ref_id": txn.sale_ref_id,
            "message": "قبلاً تأیید شده.", "reconciliation_pending": reconciliation_pending,
        }

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
    """verify، کنترل نسخهٔ بدهی، settle و پردازش داخلی قابل بازیابی."""
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

    order.refresh_from_db()
    duplicate_success = PaymentTransaction.objects.filter(
        order=order, status=PaymentTransaction.Status.SUCCESS,
    ).exclude(pk=txn.pk).exists()
    if (order.status != Order.Status.AWAITING_PAYMENT or duplicate_success
            or _payable_amount(order) != txn.amount):
        bp_reverse_request(txn.sale_order_id, sale_order_id, sale_ref_id)
        msg = "وضعیت یا مبلغ بدهی سفارش تغییر کرده است؛ تراکنش تکراری/ناسازگار برگشت داده شد."
        _finalize_failure(txn, msg)
        return {"success": False, "error": msg, "order": order}

    settle = bp_settle_request(txn.sale_order_id, sale_order_id, sale_ref_id)
    processing_error = ""
    if not settle["success"]:
        processing_error = f"تأیید بانک موفق ولی settle ناموفق بود: {settle.get('error', '')}"
        logger.critical(
            f"[PAYMENT] Settle FAILED (verify OK) — order={order.order_number} "
            f"ref={sale_ref_id} settle_rc={settle.get('res_code')}"
        )

    txn.status = PaymentTransaction.Status.SUCCESS
    txn.error_message = processing_error
    txn.save(update_fields=["status", "error_message", "updated_at"])

    try:
        with db_transaction.atomic():
            process_payment_callback(order=order, ref_id=sale_ref_id, success=True)
    except Exception as exc:
        processing_error = f"پرداخت بانکی موفق ولی تکمیل داخلی سفارش ناموفق بود: {exc}"
        txn.error_message = processing_error
        txn.save(update_fields=["error_message", "updated_at"])
        logger.critical(
            f"[PAYMENT] Post-process FAILED after successful payment — "
            f"order={order.order_number} ref={sale_ref_id}",
            exc_info=True,
        )

    logger.info(f"[PAYMENT] ✓ order={order.order_number} ref={sale_ref_id}")
    return {
        "success": True,
        "order": order,
        "ref_id": sale_ref_id,
        "message": "پرداخت موفق" if not processing_error else "پرداخت بانکی موفق؛ تکمیل داخلی نیازمند بررسی است",
        "reconciliation_pending": bool(processing_error),
    }


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
