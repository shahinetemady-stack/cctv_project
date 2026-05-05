"""
apps/orders/views.py
─────────────────────
API endpoints for order management.

Cart (مشتری عمومی):
  GET/POST  /api/orders/cart/
  POST      /api/orders/cart/checkout/

InquiryCart (مشتری همکار):
  GET/POST  /api/orders/inquiry-cart/
  POST      /api/orders/inquiry-cart/submit/

Orders:
  GET       /api/orders/                  لیست سفارش‌های من
  GET       /api/orders/<order_number>/   جزئیات
  POST      /api/orders/<order_number>/cancel/

Admin:
  GET       /api/orders/admin/orders/            همه سفارش‌ها
  POST      /api/orders/admin/<order>/confirm/   تأیید استعلام

پرداخت → apps/payments (جدا)
"""

import logging
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.permissions import IsPartner, IsVerifiedUser

from .models import Cart, CartItem, InquiryCart, InquiryCartItem, Order
from .serializers import (
    CartSerializer, CartItemSerializer,
    InquiryCartSerializer, InquiryCartItemSerializer,
    OrderSerializer, OrderAdminSerializer, ConfirmInquirySerializer,
)
from .services import (
    create_direct_order, create_inquiry_order,
    confirm_inquiry_order, cancel_order,
)

logger = logging.getLogger(__name__)


# ─── Cart ─────────────────────────────────────────────────────────────────────

class CartView(APIView):
    """GET: دریافت سبد | POST: افزودن آیتم"""
    permission_classes = [IsAuthenticated]

    def _get_cart(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        return cart

    def get(self, request):
        cart = self._get_cart(request)
        return Response(CartSerializer(cart, context={"request": request}).data)

    def post(self, request):
        """افزودن یا بروزرسانی آیتم در سبد."""
        cart = self._get_cart(request)
        variant_id = request.data.get("variant_id")
        quantity = int(request.data.get("quantity", 1))

        try:
            from apps.catalog.models import ProductVariant
            variant = ProductVariant.objects.get(pk=variant_id, is_active=True)
        except (ProductVariant.DoesNotExist, TypeError):
            return Response({"error": "محصول یافت نشد."}, status=status.HTTP_404_NOT_FOUND)

        if variant.available_stock < quantity:
            return Response(
                {"error": f"موجودی کافی نیست. موجودی: {variant.available_stock}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        item, created = CartItem.objects.get_or_create(
            cart=cart, variant=variant,
            defaults={"quantity": quantity},
        )
        if not created:
            item.quantity = quantity
            item.save()

        return Response(CartSerializer(cart, context={"request": request}).data)

    def delete(self, request):
        """حذف آیتم از سبد."""
        cart = self._get_cart(request)
        variant_id = request.data.get("variant_id")
        CartItem.objects.filter(cart=cart, variant_id=variant_id).delete()
        return Response(CartSerializer(cart, context={"request": request}).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def cart_checkout(request):
    """
    POST /api/orders/cart/checkout/
    تبدیل سبد به سفارش + رزرو موجودی + لینک پرداخت
    """
    try:
        cart = Cart.objects.get(user=request.user)
    except Cart.DoesNotExist:
        return Response({"error": "سبد خرید خالی است."}, status=status.HTTP_400_BAD_REQUEST)

    shipping_address = request.data.get("shipping_address", "")

    try:
        order = create_direct_order(request.user, cart)
        order.shipping_address = shipping_address
        order.save(update_fields=["shipping_address"])
        # payment_link توسط POST /api/orders/bank/request/ پر می‌شود
        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)
    except ValueError as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# ─── InquiryCart ──────────────────────────────────────────────────────────────

class InquiryCartView(APIView):
    """
    سبد استعلام — فقط مشتریان همکار تأیید شده.
    permission_classes = [IsPartner] کار _check_partner را می‌کند.
    """
    permission_classes = [IsPartner]

    def _get_cart(self, request):
        cart, _ = InquiryCart.objects.get_or_create(user=request.user)
        return cart

    def get(self, request):
        cart = self._get_cart(request)
        return Response(InquiryCartSerializer(cart, context={"request": request}).data)

    def post(self, request):
        cart = self._get_cart(request)
        variant_id = request.data.get("variant_id")
        quantity = int(request.data.get("quantity", 1))

        try:
            from apps.catalog.models import ProductVariant
            variant = ProductVariant.objects.get(pk=variant_id, is_active=True)
        except (ProductVariant.DoesNotExist, TypeError):
            return Response({"error": "محصول یافت نشد."}, status=status.HTTP_404_NOT_FOUND)

        item, created = InquiryCartItem.objects.get_or_create(
            cart=cart, variant=variant,
            defaults={"quantity": quantity},
        )
        if not created:
            item.quantity = quantity
            item.save()

        return Response(InquiryCartSerializer(cart, context={"request": request}).data)

    def delete(self, request):
        cart = self._get_cart(request)
        variant_id = request.data.get("variant_id")
        InquiryCartItem.objects.filter(cart=cart, variant_id=variant_id).delete()
        return Response(InquiryCartSerializer(cart, context={"request": request}).data)


@api_view(["POST"])
@permission_classes([IsPartner])
def inquiry_cart_submit(request):
    """
    POST /api/orders/inquiry-cart/submit/
    ثبت سفارش استعلامی + ارسال پیامک به ادمین و کاربر
    (فقط مشتریان همکار تأیید شده — توسط IsPartner permission کنترل می‌شود)
    """

    try:
        cart = InquiryCart.objects.get(user=request.user)
    except InquiryCart.DoesNotExist:
        return Response({"error": "سبد استعلام خالی است."}, status=status.HTTP_400_BAD_REQUEST)

    notes = request.data.get("notes", "")
    cart.notes = notes
    cart.save()

    try:
        order = create_inquiry_order(request.user, cart)
        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)
    except ValueError as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# ─── Orders (user) ────────────────────────────────────────────────────────────

class OrderListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        orders = (
            Order.objects.filter(user=request.user)
            .prefetch_related("items__variant__product")
            .order_by("-created_at")
        )
        return Response(OrderSerializer(orders, many=True).data)


class OrderDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, request, order_number):
        try:
            return Order.objects.prefetch_related("items__variant__product").get(
                order_number=order_number, user=request.user
            )
        except Order.DoesNotExist:
            return None

    def get(self, request, order_number):
        order = self.get_object(request, order_number)
        if not order:
            return Response({"error": "سفارش یافت نشد."}, status=status.HTTP_404_NOT_FOUND)
        return Response(OrderSerializer(order).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def cancel_order_view(request, order_number):
    try:
        order = Order.objects.get(order_number=order_number, user=request.user)
    except Order.DoesNotExist:
        return Response({"error": "سفارش یافت نشد."}, status=status.HTTP_404_NOT_FOUND)

    try:
        order = cancel_order(order, reason="user_request")
        return Response(OrderSerializer(order).data)
    except ValueError as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# ─── Admin order endpoints ─────────────────────────────────────────────────────

class AdminOrderListView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        order_type = request.query_params.get("type")
        status_filter = request.query_params.get("status")

        qs = Order.objects.prefetch_related("items__variant__product").order_by("-created_at")
        if order_type:
            qs = qs.filter(order_type=order_type)
        if status_filter:
            qs = qs.filter(status=status_filter)

        return Response(OrderAdminSerializer(qs, many=True).data)


@api_view(["POST"])
@permission_classes([IsAdminUser])
def admin_confirm_inquiry(request, order_number):
    """
    POST /api/orders/admin/<order_number>/confirm/
    body: { "confirmed_amount": 1500000 }
    """
    try:
        order = Order.objects.get(
            order_number=order_number,
            order_type=Order.OrderType.INQUIRY,
        )
    except Order.DoesNotExist:
        return Response({"error": "سفارش یافت نشد."}, status=status.HTTP_404_NOT_FOUND)

    serializer = ConfirmInquirySerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    try:
        order = confirm_inquiry_order(
            order=order,
            admin_user=request.user,
            confirmed_amount=serializer.validated_data["confirmed_amount"],
        )
        return Response(OrderAdminSerializer(order).data)
    except ValueError as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

# پرداخت به payment_views.py منتقل شده است.
# /api/orders/payment/request/  ← PaymentRequestView
# /api/orders/payment/verify/   ← PaymentVerifyView (callback بانک)
