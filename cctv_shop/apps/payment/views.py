"""
apps/payment/views.py — دو endpoint اصلی درگاه پرداخت + وضعیت + ادمین

POST /api/payment/bank/request/   → درخواست توکن + URL بانک
POST /api/payment/bank/verify/    → callback از بانک (بدون auth)
GET  /api/payment/status/<order>/ → وضعیت پرداخت
GET  /api/payment/transactions/   → تراکنش‌های من
GET  /api/payment/admin/transactions/ → همه تراکنش‌ها (ادمین)
"""

import logging
from urllib.parse import urlencode

from django.conf import settings
from django.http import HttpResponseRedirect
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.orders.models import Order
from .models import PaymentTransaction
from .serializers import PaymentTransactionSerializer
from .services import handle_callback, initiate_payment

logger = logging.getLogger(__name__)

FRONTEND_SUCCESS_URL = getattr(settings, "FRONTEND_SUCCESS_URL", "http://localhost:3000/payment/success")
FRONTEND_FAILURE_URL = getattr(settings, "FRONTEND_FAILURE_URL", "http://localhost:3000/payment/failure")


class PaymentRequestView(APIView):
    """
    POST /api/payment/bank/request/
    Body: { "order_number": "ORD-20240101-ABC123" }
    → { redirect_url, token, amount_rial, transaction_id }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        order_number = request.data.get("order_number", "").strip()
        if not order_number:
            return Response({"error": "order_number الزامی است."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            order = Order.objects.prefetch_related("items__variant").get(
                order_number=order_number, user=request.user
            )
        except Order.DoesNotExist:
            return Response({"error": "سفارش یافت نشد."}, status=status.HTTP_404_NOT_FOUND)

        result = initiate_payment(order, request)
        if not result["success"]:
            return Response({"error": result["error"]}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "redirect_url":   result["redirect_url"],
            "token":          result["token"],
            "amount_rial":    result["amount_rial"],
            "transaction_id": result["transaction_id"],
            "order_number":   order.order_number,
        })


class PaymentCallbackView(APIView):
    """
    POST /api/payment/bank/verify/
    به‌پرداخت ملت این endpoint را بعد از پرداخت کاربر POST می‌کند.
    بدون احراز هویت — IP بانک.
    نتیجه: redirect به فرانت‌اند.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        post_data = request.data if hasattr(request.data, "dict") else dict(request.data)
        result    = handle_callback(post_data)
        order     = result.get("order")
        order_num = order.order_number if order else post_data.get("SaleOrderId", "")

        if result["success"]:
            query = urlencode({"order": order_num, "ref": result.get("ref_id", "")})
            url = f"{FRONTEND_SUCCESS_URL}?{query}"
        else:
            query = urlencode({"order": order_num, "error": result.get("error", "خطا")})
            url = f"{FRONTEND_FAILURE_URL}?{query}"

        return HttpResponseRedirect(url)


class PaymentStatusView(APIView):
    """GET /api/payment/status/<order_number>/ — وضعیت پرداخت سفارش"""
    permission_classes = [IsAuthenticated]

    def get(self, request, order_number):
        try:
            order = Order.objects.get(order_number=order_number, user=request.user)
        except Order.DoesNotExist:
            return Response({"error": "سفارش یافت نشد."}, status=status.HTTP_404_NOT_FOUND)

        txn = order.payment_transactions.order_by("-created_at").first()
        return Response({
            "order_number":         order.order_number,
            "order_status":         order.status,
            "order_status_display": order.get_status_display(),
            "amount_rial":          order.effective_amount,
            "payment_link":         order.payment_link,
            "is_paid":              order.status == Order.Status.PAID,
            "latest_transaction":   PaymentTransactionSerializer(txn).data if txn else None,
        })


class TransactionListView(APIView):
    """GET /api/payment/transactions/"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        txns = (PaymentTransaction.objects
                .filter(user=request.user)
                .select_related("order")
                .order_by("-created_at")[:50])
        return Response(PaymentTransactionSerializer(txns, many=True).data)


class AdminTransactionListView(APIView):
    """GET /api/payment/admin/transactions/?status=failed&order=ORD-..."""
    permission_classes = [IsAdminUser]

    def get(self, request):
        qs = PaymentTransaction.objects.select_related("order", "user").order_by("-created_at")
        if s := request.query_params.get("status"):
            qs = qs.filter(status=s)
        if o := request.query_params.get("order"):
            qs = qs.filter(order__order_number__icontains=o)
        return Response(PaymentTransactionSerializer(qs[:200], many=True).data)
