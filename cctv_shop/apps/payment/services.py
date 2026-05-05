"""
apps/payment/services.py — payment orchestration layer
"""
import logging
from django.db import transaction as db_transaction
from django.utils import timezone

from apps.orders.models import Order
from apps.orders.services import process_payment_callback
from .behpardakht import bp_pay_request, bp_verify_request, bp_settle_request, get_payment_url
from .models import PaymentTransaction

logger = logging.getLogger(__name__)


def initiate_payment(order: Order, request) -> dict:
    """
    مرحله ۱: درخواست توکن از بانک.

    فقط برای DIRECT_PURCHASE + AWAITING_PAYMENT + مهلت نگذشته.

    Returns:
      {"success": True,  "redirect_url": "...", "token": 123, "amount_toman": 150000}
      {"success": False, "error": "..."}
    """
    if order.order_type != Order.OrderType.DIRECT_PURCHASE:
        return {"success": False, "error": "پرداخت آنلاین فقط برای خرید مستقیم است."}
    if order.status != Order.Status.AWAITING_PAYMENT:
        return {"success": False, "error": f"وضعیت سفارش '{order.get_status_display()}' قابل پرداخت نیست."}
    if order.is_payment_expired:
        return {"success": False, "error": "مهلت پرداخت این سفارش منقضی شده است."}

    now = timezone.localtime(timezone.now())
    amount_toman = order.effective_amount

    bank_result = bp_pay_request(
        amount_toman=amount_toman,
        order_id=order.order_number,
        local_date=now.strftime("%Y%m%d"),
        local_time=now.strftime("%H%M%S"),
        additional_data=f"order:{order.order_number}",
        payer_email=order.user.email,
    )

    txn = PaymentTransaction.objects.create(
        order=order,
        user=order.user,
        amount=amount_toman * 10,
        status=(PaymentTransaction.Status.INITIATED
                if bank_result["success"] else PaymentTransaction.Status.FAILED),
        bank_token=bank_result.get("token"),
        sale_order_id=order.order_number,
        error_message="" if bank_result["success"] else bank_result.get("error", ""),
        raw_request={"order_number": order.order_number, "amount_toman": amount_toman},
    )

    if not bank_result["success"]:
        logger.error(f"[PAYMENT] Token failed: order={order.order_number} err={bank_result.get('error')}")
        return {"success": False, "error": bank_result["error"]}

    redirect_url = get_payment_url(bank_result["token"])
    order.payment_link = redirect_url
    order.save(update_fields=["payment_link", "updated_at"])

    logger.info(f"[PAYMENT] Initiated: order={order.order_number} token={bank_result['token']}")
    return {
        "success": True,
        "redirect_url": redirect_url,
        "token": bank_result["token"],
        "transaction_id": txn.id,
        "amount_toman": amount_toman,
    }


def handle_callback(post_data: dict) -> dict:
    """
    مرحله ۲: پردازش callback POST از بانک.

    فیلدهای به‌پرداخت: ResCode, Token, SaleOrderId, SaleReferenceId

    Returns:
      {"success": True,  "order": <Order>, "ref_id": "...", "message": "..."}
      {"success": False, "error": "...",   "order": <Order>|None}
    """
    res_code      = str(post_data.get("ResCode", "")).strip()
    token_str     = str(post_data.get("Token", "")).strip()
    sale_order_id = str(post_data.get("SaleOrderId", "")).strip()
    sale_ref_id   = str(post_data.get("SaleReferenceId", "")).strip()

    logger.info(f"[PAYMENT] Callback: ResCode={res_code} Token={token_str} Order={sale_order_id}")

    txn = _find_transaction(token_str, sale_order_id)
    if txn is None:
        logger.error(f"[PAYMENT] Transaction not found: token={token_str} order={sale_order_id}")
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
        return {"success": True, "order": order, "ref_id": txn.sale_ref_id, "message": "قبلاً تأیید شده."}

    return _finalize_success(txn, sale_order_id, sale_ref_id)


@db_transaction.atomic
def _finalize_success(txn, sale_order_id, sale_ref_id) -> dict:
    """verify → settle → کسر موجودی → PAID (همه یا هیچ)."""
    order = txn.order

    verify = bp_verify_request(
        order_id=order.order_number,
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
    settle = bp_settle_request(order.order_number, sale_order_id, sale_ref_id)
    if not settle["success"]:
        logger.critical(
            f"[PAYMENT] Settle FAILED (verify OK) — order={order.order_number} "
            f"ref={sale_ref_id} settle_rc={settle.get('res_code')}"
        )

    try:
        process_payment_callback(order=order, ref_id=sale_ref_id, success=True)
    except ValueError as e:
        if "مناسب" not in str(e):
            raise

    txn.status = PaymentTransaction.Status.SUCCESS
    txn.save(update_fields=["status", "updated_at"])

    logger.info(f"[PAYMENT] ✓ order={order.order_number} ref={sale_ref_id}")
    return {"success": True, "order": order, "ref_id": sale_ref_id, "message": "پرداخت موفق"}


def _finalize_failure(txn, error_msg: str) -> None:
    txn.status = PaymentTransaction.Status.FAILED
    txn.error_message = error_msg
    txn.save(update_fields=["status", "error_message", "updated_at"])
    logger.warning(f"[PAYMENT] Failed: order={txn.order.order_number} reason={error_msg}")


def _find_transaction(token_str: str, sale_order_id: str):
    if token_str and token_str.lstrip("-").isdigit():
        txn = (PaymentTransaction.objects
               .filter(bank_token=int(token_str), status=PaymentTransaction.Status.INITIATED)
               .select_related("order__user").first())
        if txn:
            return txn
    if sale_order_id:
        return (PaymentTransaction.objects
                .filter(sale_order_id=sale_order_id, status=PaymentTransaction.Status.INITIATED)
                .select_related("order__user").order_by("-created_at").first())
    return None
