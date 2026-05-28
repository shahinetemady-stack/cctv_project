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
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
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


class ChinaOrderRequestView(APIView):
    """POST /api/orders/china-request/ — ثبت درخواست سفارش از چین"""
    permission_classes = [AllowAny]

    def post(self, request):
        from .models import ChinaOrderRequest
        d = request.data
        name = d.get('name', '').strip()
        phone = d.get('phone', '').strip()
        product_name = d.get('product_name', '').strip()
        quantity = d.get('quantity', 1)

        if not name:
            return Response({'error': 'نام الزامی است'}, status=400)
        if not phone:
            return Response({'error': 'شماره تماس الزامی است'}, status=400)
        if not product_name:
            return Response({'error': 'نام کالا الزامی است'}, status=400)

        req = ChinaOrderRequest.objects.create(
            name=name,
            phone=phone,
            email=d.get('email', ''),
            product_name=product_name,
            quantity=int(quantity),
            description=d.get('description', ''),
            product_link=d.get('product_link', ''),
            user=request.user if request.user.is_authenticated else None,
        )

        # ارسال نوتیفیکیشن به ادمین
        try:
            from apps.notifications.models import Notification
            from django.contrib.auth import get_user_model
            User = get_user_model()
            admins = User.objects.filter(is_staff=True, is_active=True)
            for admin in admins:
                Notification.objects.create(
                    user=admin,
                    title=f"درخواست جدید از چین: {product_name}",
                    message=f"{name} | {phone} | تعداد: {quantity}",
                    notification_type="system",
                )
        except Exception:
            pass

        return Response({
            'id': req.id,
            'message': 'درخواست شما با موفقیت ثبت شد. کارشناسان ما در اسرع وقت با شما تماس خواهند گرفت.',
        }, status=201)

    def get(self, request):
        """لیست درخواست‌ها برای ادمین"""
        if not request.user.is_staff:
            return Response({'error': 'دسترسی ندارید'}, status=403)
        from .models import ChinaOrderRequest
        reqs = ChinaOrderRequest.objects.all().order_by('-created_at')[:50]
        return Response([{
            'id': r.id,
            'name': r.name,
            'phone': r.phone,
            'product_name': r.product_name,
            'quantity': r.quantity,
            'status': r.status,
            'status_display': r.get_status_display(),
            'created_at': r.created_at.strftime('%Y-%m-%d %H:%M'),
        } for r in reqs])


class OrderTrackingView(APIView):
    """GET /api/orders/<order_number>/track/ — رهگیری سفارش"""
    permission_classes = [AllowAny]

    def get(self, request, order_number):
        from .models import Order
        try:
            order = Order.objects.get(order_number=order_number)
        except Order.DoesNotExist:
            return Response({'error': 'سفارش یافت نشد'}, status=404)

        # بررسی دسترسی — فقط صاحب سفارش یا ادمین
        if not request.user.is_staff:
            if not request.user.is_authenticated or request.user.id != order.user_id:
                # فقط اطلاعات عمومی
                if not order.tracking_code:
                    return Response({'error': 'اطلاعات رهگیری موجود نیست'}, status=404)

        # وضعیت‌های مرحله به مرحله
        steps = [
            {'key': 'pending',    'label': 'ثبت سفارش',        'icon': '📋'},
            {'key': 'confirmed',  'label': 'تأیید سفارش',       'icon': '✅'},
            {'key': 'shipped',    'label': 'ارسال شده',          'icon': '📦'},
            {'key': 'in_transit', 'label': 'در مسیر',           'icon': '🚚'},
            {'key': 'delivered',  'label': 'تحویل داده شده',    'icon': '🎉'},
        ]

        delivery_status = getattr(order, 'delivery_status', 'pending')
        step_keys = [s['key'] for s in steps]
        current_idx = step_keys.index(delivery_status) if delivery_status in step_keys else 0

        for i, step in enumerate(steps):
            step['done'] = i <= current_idx
            step['current'] = i == current_idx

        return Response({
            'order_number': order.order_number,
            'status': order.status,
            'status_display': order.get_status_display(),
            'delivery_status': delivery_status,
            'tracking_code': getattr(order, 'tracking_code', '') or order.tracking_code,
            'courier_company': getattr(order, 'courier_company', ''),
            'courier_display': dict([
                ('post', 'پست'), ('tipax', 'تیپاکس'),
                ('chapar', 'چاپار'), ('snap', 'اسنپ‌باکس'), ('other', 'سایر')
            ]).get(getattr(order, 'courier_company', ''), ''),
            'shipped_at': order.shipped_at.strftime('%Y-%m-%d %H:%M') if getattr(order, 'shipped_at', None) else None,
            'delivered_at': order.delivered_at.strftime('%Y-%m-%d %H:%M') if getattr(order, 'delivered_at', None) else None,
            'created_at': order.created_at.strftime('%Y-%m-%d %H:%M'),
            'steps': steps,
            'items_count': order.items.count(),
            'total': order.effective_amount,
        })


class AdminOrderListView(APIView):
    """GET /api/orders/admin/orders/ — لیست سفارشات برای ادمین"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not request.user.is_staff:
            return Response({'error': 'دسترسی ندارید'}, status=403)
        from .models import Order
        qs = Order.objects.select_related('user').order_by('-created_at')

        status = request.query_params.get('status')
        delivery = request.query_params.get('delivery_status')
        if status:
            qs = qs.filter(status=status)
        if delivery:
            qs = qs.filter(delivery_status=delivery)

        return Response([{
            'order_number': o.order_number,
            'user_name': o.user.get_full_name() or '',
            'user_phone': o.user.phone or '',
            'status': o.status,
            'total_amount': o.total_amount,
            'delivery_status': getattr(o, 'delivery_status', 'pending') or 'pending',
            'courier_company': getattr(o, 'courier_company', '') or '',
            'tracking_code': o.tracking_code or '',
            'shipping_address': o.shipping_address or '',
            'created_at': o.created_at.strftime('%Y-%m-%d %H:%M'),
            'updated_by': o.updated_by.get_full_name() or o.updated_by.phone if o.updated_by else '',
            'status_updated_at': o.status_updated_at.strftime('%Y-%m-%d %H:%M') if o.status_updated_at else '',
        } for o in qs[:200]])


class AdminOrderUpdateView(APIView):
    """PATCH /api/orders/admin/<order_number>/update/ — آپدیت وضعیت سفارش"""
    permission_classes = [IsAuthenticated]

    def patch(self, request, order_number):
        if not request.user.is_staff:
            return Response({'error': 'دسترسی ندارید'}, status=403)
        from .models import Order
        from django.utils import timezone
        try:
            order = Order.objects.get(order_number=order_number)
        except Order.DoesNotExist:
            return Response({'error': 'سفارش یافت نشد'}, status=404)

        d = request.data
        allowed = ['status', 'delivery_status', 'courier_company', 'tracking_code']
        for field in allowed:
            if field in d:
                setattr(order, field, d[field])

        # تنظیم خودکار تاریخ ارسال
        if d.get('delivery_status') == 'shipped' and not getattr(order, 'shipped_at', None):
            order.shipped_at = timezone.now()
        if d.get('delivery_status') == 'delivered' and not getattr(order, 'delivered_at', None):
            order.delivered_at = timezone.now()

        order.updated_by = request.user
        order.status_updated_at = timezone.now()
        order.save()
        return Response({'ok': True, 'order_number': order.order_number})
