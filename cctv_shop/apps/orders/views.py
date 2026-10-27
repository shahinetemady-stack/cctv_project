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
from django.db import transaction
from django.utils import timezone
from apps.core.utils import iso_local as _iso_local
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.permissions import IsPartner, IsVerifiedUser
from apps.users.models import accessible_user_ids, effective_user

from .models import Cart, CartItem, InquiryCart, InquiryCartItem, Order
from .serializers import (
    CartSerializer, CartItemSerializer,
    InquiryCartSerializer, InquiryCartItemSerializer,
    OrderSerializer, OrderAdminSerializer, ConfirmInquirySerializer,
    PaymentReceiptSerializer,
)
from .services import (
    create_direct_order, create_inquiry_order,
    confirm_inquiry_order, cancel_order,
)

logger = logging.getLogger(__name__)


def _overdue_warning(user):
    """هشدار تسویه‌های سررسیدگذشته کاربر + سطح محدودیت فعلی."""
    try:
        from apps.users.services import partner_restriction
        restriction = partner_restriction(user)
        count = user.overdue_count()
        if count > 0:
            return {
                "count": count,
                "total": user.overdue_total(),
                "level": restriction["level"] if restriction else "warning",
            }
    except Exception as e:
        logger.warning(f"[ORDER] overdue check failed for user {user.pk}: {e}")
    return None


def _restriction_block_response(user, *, inquiry=False):
    """
    اگر کاربر در مرحله «مسدود» است → 403 برای هر نوع سفارش.
    اگر در مرحله «فقط نقدی» است → برای سفارش استعلامی، اقلام غیرنقدی رد می‌شوند.
    وگرنه None.
    """
    try:
        from apps.users.services import partner_restriction
        restriction = partner_restriction(user)
    except Exception as e:
        logger.warning(f"[ORDER] restriction check failed for user {user.pk}: {e}")
        return None
    if not restriction:
        return None
    if restriction["level"] == "blocked":
        return Response(
            {"error": "به دلیل معوقات تسویه‌نشده، امکان ثبت سفارش جدید موقتاً برای شما غیرفعال است. لطفاً ابتدا تسویه کنید یا با فروشگاه تماس بگیرید."},
            status=status.HTTP_403_FORBIDDEN,
        )
    if inquiry and restriction["level"] == "cash_only":
        cart = InquiryCart.objects.filter(user=user).first()
        if cart and cart.items.exclude(settlement_type="cash").exists():
            return Response(
                {"error": "به دلیل معوقات تسویه‌نشده، فعلاً فقط خرید نقدی برای شما فعال است؛ اقلام با تسویه اعتباری را از سبد حذف کنید."},
                status=status.HTTP_403_FORBIDDEN,
            )
    return None


# ─── Cart ─────────────────────────────────────────────────────────────────────

class CartView(APIView):
    """GET: دریافت سبد | POST: افزودن آیتم"""
    permission_classes = [IsAuthenticated]

    def _get_cart(self, request):
        cart, _ = Cart.objects.get_or_create(user=effective_user(request.user))
        return cart

    def get(self, request):
        cart = self._get_cart(request)
        return Response(CartSerializer(cart, context={"request": request}).data)

    def post(self, request):
        """افزودن یا بروزرسانی آیتم در سبد — variant_id (کالا) یا package_id (پکیج)."""
        cart = self._get_cart(request)
        variant_id = request.data.get("variant_id")
        package_id = request.data.get("package_id")
        quantity = int(request.data.get("quantity", 1))
        settlement = request.data.get("settlement_type") or "cash"

        # ── آیتم پکیج — قیمت ثابت بسته، تسویه نقدی، حداقل تعداد رعایت می‌شود ──
        if package_id:
            from apps.catalog.models import Package
            try:
                pkg = Package.objects.get(pk=package_id, is_active=True)
            except (Package.DoesNotExist, TypeError, ValueError):
                return Response({"error": "پکیج یافت نشد."}, status=status.HTTP_404_NOT_FOUND)
            if quantity < pkg.min_quantity:
                return Response(
                    {"error": f"حداقل تعداد سفارش این پکیج {pkg.min_quantity} بسته است."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            # سقف تعداد پکیج = کمترین موجودی قابل فروش (انبارهای عمومی) اقلام داخل آن
            max_pkg = min(
                (pi.variant.sellable_stock // pi.quantity for pi in pkg.package_items.select_related("variant")),
                default=0,
            )
            if quantity > max_pkg:
                return Response(
                    {"error": f"درخواست شما بیشتر از موجودی است — حداکثر موجودی قابل فروش این پکیج {max_pkg} بسته است."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            item, created = CartItem.objects.get_or_create(
                cart=cart, package=pkg, variant=None,
                defaults={"quantity": quantity},
            )
            if not created:
                item.quantity = quantity
                item.save()
            return Response(CartSerializer(cart, context={"request": request}).data)

        try:
            from apps.catalog.models import ProductVariant
            variant = ProductVariant.objects.get(pk=variant_id, is_active=True)
        except (ProductVariant.DoesNotExist, TypeError):
            return Response({"error": "محصول یافت نشد."}, status=status.HTTP_404_NOT_FOUND)

        from apps.catalog.pricing import allowed_settlements
        if settlement not in allowed_settlements(request.user, variant):
            return Response({"error": "این نوع تسویه برای شما مجاز نیست."},
                            status=status.HTTP_400_BAD_REQUEST)

        # سقف تعداد = موجودی قابل فروش (فقط انبارهای با تیک «نمایش به مشتری»، منهای رزروشده)
        available = variant.sellable_stock
        if quantity > available:
            return Response(
                {"error": f"درخواست شما بیشتر از موجودی است — حداکثر موجودی قابل فروش این کالا {available} عدد است."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        item, created = CartItem.objects.get_or_create(
            cart=cart, variant=variant, settlement_type=settlement,
            defaults={"quantity": quantity},
        )
        if not created:
            item.quantity = quantity
            item.save()

        return Response(CartSerializer(cart, context={"request": request}).data)

    def delete(self, request):
        """حذف آیتم از سبد — اگر تسویه مشخص شود فقط همان نوع."""
        cart = self._get_cart(request)
        package_id = request.data.get("package_id")
        if package_id:
            CartItem.objects.filter(cart=cart, package_id=package_id).delete()
            return Response(CartSerializer(cart, context={"request": request}).data)
        variant_id = request.data.get("variant_id")
        qs = CartItem.objects.filter(cart=cart, variant_id=variant_id)
        if request.data.get("settlement_type"):
            qs = qs.filter(settlement_type=request.data["settlement_type"])
        qs.delete()
        return Response(CartSerializer(cart, context={"request": request}).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def cart_checkout(request):
    """
    POST /api/orders/cart/checkout/
    تبدیل سبد به سفارش + رزرو موجودی + لینک پرداخت
    """
    shipping_method = request.data.get("shipping_method") or "courier"
    if shipping_method not in ("courier", "freight"):
        return Response(
            {"error": "روش ارسال انتخاب‌شده غیرفعال است؛ لطفاً پیک یا باربری را انتخاب کنید."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        cart = Cart.objects.get(user=effective_user(request.user))
    except Cart.DoesNotExist:
        return Response({"error": "سبد خرید خالی است."}, status=status.HTTP_400_BAD_REQUEST)

    blocked = _restriction_block_response(request.user)
    if blocked is not None:
        return blocked

    shipping_address = request.data.get("shipping_address", "")
    freight_company = request.data.get("freight_company", "")

    try:
        orders = create_direct_order(effective_user(request.user), cart)
        for o in orders:
            o.shipping_address = shipping_address
            o.shipping_method = shipping_method
            o.freight_company = freight_company
            o.save(update_fields=["shipping_address", "shipping_method", "freight_company"])
        # payment_link توسط POST /api/orders/bank/request/ پر می‌شود
        orders_data = OrderSerializer(orders, many=True).data
        data = dict(orders_data[0])
        data["orders"] = orders_data
        data["split"] = len(orders) > 1
        data["overdue_warning"] = _overdue_warning(request.user)
        return Response(data, status=status.HTTP_201_CREATED)
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
        cart, _ = InquiryCart.objects.get_or_create(user=effective_user(request.user))
        return cart

    def get(self, request):
        cart = self._get_cart(request)
        return Response(InquiryCartSerializer(cart, context={"request": request}).data)

    def post(self, request):
        cart = self._get_cart(request)
        variant_id = request.data.get("variant_id")
        quantity = int(request.data.get("quantity", 1))
        settlement = request.data.get("settlement_type") or "cash"

        try:
            from apps.catalog.models import ProductVariant
            variant = ProductVariant.objects.get(pk=variant_id, is_active=True)
        except (ProductVariant.DoesNotExist, TypeError):
            return Response({"error": "محصول یافت نشد."}, status=status.HTTP_404_NOT_FOUND)

        from apps.catalog.pricing import allowed_settlements
        if settlement not in allowed_settlements(request.user, variant):
            return Response({"error": "این نوع تسویه برای شما مجاز نیست."},
                            status=status.HTTP_400_BAD_REQUEST)

        # سقف تعداد = موجودی قابل فروش (فقط انبارهای با تیک «نمایش به مشتری»، منهای رزروشده)
        available = variant.sellable_stock
        if quantity > available:
            return Response(
                {"error": f"درخواست شما بیشتر از موجودی است — حداکثر موجودی قابل فروش این کالا {available} عدد است."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        item, created = InquiryCartItem.objects.get_or_create(
            cart=cart, variant=variant, settlement_type=settlement,
            defaults={"quantity": quantity},
        )
        if not created:
            item.quantity = quantity
            item.save()

        return Response(InquiryCartSerializer(cart, context={"request": request}).data)

    def delete(self, request):
        cart = self._get_cart(request)
        variant_id = request.data.get("variant_id")
        qs = InquiryCartItem.objects.filter(cart=cart, variant_id=variant_id)
        if request.data.get("settlement_type"):
            qs = qs.filter(settlement_type=request.data["settlement_type"])
        qs.delete()
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
        cart = InquiryCart.objects.get(user=effective_user(request.user))
    except InquiryCart.DoesNotExist:
        return Response({"error": "سبد استعلام خالی است."}, status=status.HTTP_400_BAD_REQUEST)

    blocked = _restriction_block_response(request.user, inquiry=True)
    if blocked is not None:
        return blocked

    notes = request.data.get("notes", "")
    cart.notes = notes
    cart.save()

    try:
        orders = create_inquiry_order(effective_user(request.user), cart)
        orders_data = OrderSerializer(orders, many=True).data
        data = dict(orders_data[0])
        data["orders"] = orders_data
        data["split"] = len(orders) > 1
        data["overdue_warning"] = _overdue_warning(request.user)
        return Response(data, status=status.HTTP_201_CREATED)
    except ValueError as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# ─── Orders (user) ────────────────────────────────────────────────────────────

class OrderListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        orders = (
            Order.objects.filter(user__in=accessible_user_ids(request.user))
            .prefetch_related("items__variant__product")
            .order_by("-created_at")
        )
        return Response(OrderSerializer(orders, many=True).data)


class OrderDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, request, order_number):
        return (
            Order.objects.prefetch_related("items__variant__product")
            .filter(order_number=order_number, user__in=accessible_user_ids(request.user))
            .first()
        )

    def get(self, request, order_number):
        order = self.get_object(request, order_number)
        if not order:
            return Response({"error": "سفارش یافت نشد."}, status=status.HTTP_404_NOT_FOUND)
        return Response(OrderSerializer(order).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def cancel_order_view(request, order_number):
    try:
        order = Order.objects.get(order_number=order_number, user__in=accessible_user_ids(request.user))
    except Order.DoesNotExist:
        return Response({"error": "سفارش یافت نشد."}, status=status.HTTP_404_NOT_FOUND)

    try:
        order = cancel_order(order, reason="user_request")
        return Response(OrderSerializer(order).data)
    except ValueError as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# ─── Admin order endpoints ─────────────────────────────────────────────────────

@api_view(["POST"])
@permission_classes([IsAdminUser])
def admin_confirm_inquiry(request, order_number):
    """
    POST /api/orders/admin/<order_number>/confirm/
    body: { "confirmed_amount": 1500000, "settlement_type"؟, "settlement_due_date"؟,
            "sarraf_account_number"؟, "sarraf_account_holder"؟ }
    تأیید سفارش در انتظار — هم استعلامی هم خرید مستقیم.
    اگر قلم نقدی داشته باشد، اطلاعات حساب صراف اجباری است.
    """
    from apps.accounting.views import _has_perm
    if not _has_perm(request.user, "orders_view"):
        return Response(
            {"error": "شما دسترسی لازم برای این عملیات را ندارید"}, status=403
        )

    try:
        order = Order.objects.get(order_number=order_number)
    except Order.DoesNotExist:
        return Response({"error": "سفارش یافت نشد."}, status=status.HTTP_404_NOT_FOUND)

    serializer = ConfirmInquirySerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    sarraf_number = serializer.validated_data.get("sarraf_account_number", "").strip()
    sarraf_holder = serializer.validated_data.get("sarraf_account_holder", "").strip()

    # برای سفارش‌های دارای قلم نقدی، اطلاعات حساب صراف اجباری است
    if order.items.filter(settlement_type="cash").exists():
        if not sarraf_number or not sarraf_holder:
            return Response(
                {"error": "برای اقلام نقدی، شماره حساب و نام صاحب حساب صراف الزامی است."},
                status=status.HTTP_400_BAD_REQUEST,
            )

    # نحوه تسویه و موعد آن (اختیاری) — فرمت تاریخ: YYYY-MM-DD
    settlement_type = request.data.get("settlement_type") or None
    due_raw = request.data.get("settlement_due_date") or None
    due_date = None
    if due_raw:
        from datetime import date as _date
        try:
            due_date = _date.fromisoformat(str(due_raw))
        except ValueError:
            return Response({"error": "فرمت موعد تسویه نامعتبر است (YYYY-MM-DD)"},
                            status=status.HTTP_400_BAD_REQUEST)

    try:
        order = confirm_inquiry_order(
            order=order,
            admin_user=request.user,
            confirmed_amount=serializer.validated_data["confirmed_amount"],
            settlement_type=settlement_type,
            settlement_due_date=due_date,
            sarraf_account_number=sarraf_number,
            sarraf_account_holder=sarraf_holder,
            staff=request.user,
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
            'created_at': _iso_local(r.created_at),
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
            'shipped_at': _iso_local(order.shipped_at) if getattr(order, 'shipped_at', None) else None,
            'delivered_at': _iso_local(order.delivered_at) if getattr(order, 'delivered_at', None) else None,
            'created_at': _iso_local(order.created_at),
            'steps': steps,
            'items_count': order.items.count(),
            'total': order.effective_amount,
        })


class AdminOrderListView(APIView):
    """GET /api/orders/admin/orders/ — لیست سفارشات برای ادمین"""
    permission_classes = [IsAdminUser]

    def get(self, request):
        from apps.accounting.views import _has_perm
        if not _has_perm(request.user, "orders_view"):
            return Response({"error": "شما دسترسی لازم برای این عملیات را ندارید"}, status=403)
        from .models import Order
        qs = Order.objects.select_related('user', 'user__profile', 'created_by', 'updated_by', 'sale_invoice').order_by('-created_at')

        status = request.query_params.get('status')
        delivery = request.query_params.get('delivery_status')
        if status:
            qs = qs.filter(status=status)
        else:
            # پیش‌فرض: پیش‌فاکتورهای ردشده فقط با ?status=rejected (تب مخصوص) دیده می‌شوند
            qs = qs.exclude(status=Order.Status.REJECTED)
        if delivery:
            qs = qs.filter(delivery_status=delivery)

        return Response([{
            'order_number': o.order_number,
            'order_type': o.order_type,
            'user_name': o.user.get_full_name() or '',
            'user_phone': o.user.phone or '',
            'customer_is_partner': o.user.is_partner,
            'status': o.status,
            'total_amount': o.total_amount,
            'confirmed_amount': o.confirmed_amount,
            'effective_amount': o.effective_amount,
            'settlement_type': o.settlement_type,
            'settlement_display': o.get_settlement_type_display(),
            'settlement_due_date': o.settlement_due_date.isoformat() if o.settlement_due_date else None,
            'is_settlement_due': o.is_settlement_due,
            'sarraf_account_number': o.sarraf_account_number or '',
            'sarraf_account_holder': o.sarraf_account_holder or '',
            'items_count': o.items.count(),
            'customer_notes': o.customer_notes or '',
            'admin_notes': o.admin_notes or '',
            'delivery_status': getattr(o, 'delivery_status', 'pending') or 'pending',
            'courier_company': getattr(o, 'courier_company', '') or '',
            'tracking_code': o.tracking_code or '',
            'shipping_method': o.shipping_method or '',
            'shipping_method_display': o.get_shipping_method_display() if o.shipping_method else '',
            'shipping_address': o.shipping_address or '',
            'paid_amount': o.sale_invoice.paid_amount if hasattr(o, 'sale_invoice') else (o.paid_amount or 0),
            'paid_at': _iso_local(o.paid_at) if o.paid_at else '',
            'created_at': _iso_local(o.created_at),
            'updated_at': _iso_local(o.updated_at),
            'created_by': (o.created_by.get_full_name() or o.created_by.phone) if o.created_by else '',
            'updated_by': o.updated_by.get_full_name() or o.updated_by.phone if o.updated_by else '',
            'status_updated_at': _iso_local(o.status_updated_at) if o.status_updated_at else '',
            'reject_reason': o.reject_reason or '',
            'rejected_at': _iso_local(o.rejected_at) if o.rejected_at else '',
        } for o in qs[:200]])


class AdminOrderDetailView(APIView):
    """GET /api/orders/admin/<order_number>/detail/ — جزئیات سفارش با اقلام"""
    permission_classes = [IsAdminUser]

    def get(self, request, order_number):
        from apps.accounting.views import _has_perm
        if not _has_perm(request.user, "orders_view"):
            return Response({"error": "شما دسترسی لازم برای این عملیات را ندارید"}, status=403)
        from .models import Order
        try:
            order = Order.objects.select_related('user', 'created_by', 'updated_by', 'sale_invoice').prefetch_related('items__variant__product').get(
                order_number=order_number
            )
        except Order.DoesNotExist:
            return Response({'error': 'سفارش یافت نشد'}, status=404)

        items = [{
            'id': it.id,
            'variant_id': it.variant_id,
            'product_name': it.variant.product.name,
            'sku': it.variant.sku,
            'quantity': it.quantity,
            'available_stock': it.variant.available_stock,
            'stocks': it.variant.stock_by_warehouse(),
            'unit_price': it.unit_price,
            'confirmed_unit_price': it.confirmed_unit_price,
            'subtotal': it.subtotal,
            'settlement_type': it.settlement_type,
            'settlement_display': it.get_settlement_type_display(),
            'settlement_due_date': it.settlement_due_date.isoformat() if it.settlement_due_date else None,
            'is_settlement_due': it.is_settlement_due,
        } for it in order.items.all()]

        return Response({
            'order_number': order.order_number,
            'order_type': order.order_type,
            'order_type_display': order.get_order_type_display(),
            'status': order.status,
            'status_display': order.get_status_display(),
            'user_name': order.user.get_full_name() or '',
            'user_phone': order.user.phone or '',
            'total_amount': order.total_amount,
            'confirmed_amount': order.confirmed_amount,
            'effective_amount': order.effective_amount,
            'settlement_type': order.settlement_type,
            'settlement_display': order.get_settlement_type_display(),
            'settlement_due_date': order.settlement_due_date.isoformat() if order.settlement_due_date else None,
            'is_settlement_due': order.is_settlement_due,
            'sarraf_account_number': order.sarraf_account_number or '',
            'sarraf_account_holder': order.sarraf_account_holder or '',
            'paid_amount': order.sale_invoice.paid_amount if hasattr(order, 'sale_invoice') else order.paid_amount,
            'payment_method': order.payment_method,
            'customer_notes': order.customer_notes or '',
            'admin_notes': order.admin_notes or '',
            'delivery_status': order.delivery_status or 'pending',
            'courier_company': order.courier_company or '',
            'shipping_method': order.shipping_method or '',
            'shipping_method_display': order.get_shipping_method_display() if order.shipping_method else '',
            'shipping_address': order.shipping_address or '',
            'tracking_code': order.tracking_code or '',
            'items': items,
            'reject_reason': order.reject_reason or '',
            'rejected_at': _iso_local(order.rejected_at) if order.rejected_at else '',
            'created_at': _iso_local(order.created_at),
            'created_by': (order.created_by.get_full_name() or order.created_by.phone) if order.created_by else '',
            'updated_by': (order.updated_by.get_full_name() or order.updated_by.phone) if order.updated_by else '',
            'receipts': PaymentReceiptSerializer(
                order.payment_receipts.all(), many=True, context={'request': request}
            ).data,
        })


class AdminOrderItemUpdateView(APIView):
    """
    PATCH /api/orders/admin/<order_number>/items/<item_id>/
    اصلاح یک قلم سفارش — تعداد واقعی قابل ارسال، نحوه تسویه، موعد تسویه.
    quantity=0 یعنی حذف قلم (اگر آخرین قلم باشد رد می‌شود). مبلغ کل سفارش بازمحاسبه می‌شود.
    """
    permission_classes = [IsAdminUser]

    @transaction.atomic
    def patch(self, request, order_number, item_id):
        from apps.accounting.views import _has_perm
        if not _has_perm(request.user, "orders_view"):
            return Response({"error": "شما دسترسی لازم برای این عملیات را ندارید"}, status=403)
        from .models import Order, OrderItem, Settlement, StockShortage
        try:
            order = Order.objects.select_for_update().get(order_number=order_number)
            item = order.items.get(pk=item_id)
        except (Order.DoesNotExist, OrderItem.DoesNotExist):
            return Response({'error': 'سفارش یا قلم یافت نشد'}, status=404)
        if order.status != Order.Status.PENDING or getattr(order, "sale_invoice", None):
            return Response({'error': 'اقلام سفارش فقط پیش از تأیید و صدور فاکتور قابل ویرایش است'}, status=400)

        d = request.data

        def _record_shortage(old_qty, new_qty):
            """ثبت مازاد تقاضا وقتی ادمین تعداد را کم می‌کند یا قلم را حذف می‌کند — فقط برای سفارش‌های در انتظار بررسی."""
            if order.status != Order.Status.PENDING or new_qty >= old_qty:
                return
            StockShortage.objects.create(
                order=order,
                variant=item.variant,
                requested_qty=old_qty,
                approved_qty=new_qty,
                shortage_qty=old_qty - new_qty,
                reason=d.get("reason", "stock"),
                created_by=request.user,
            )

        # تعداد — صفر یعنی حذف قلم
        if 'quantity' in d:
            try:
                qty = int(d['quantity'])
            except (TypeError, ValueError):
                return Response({'error': 'تعداد نامعتبر است'}, status=400)
            if qty <= 0:
                if order.items.count() <= 1:
                    return Response({'error': 'نمی‌توان آخرین قلم سفارش را حذف کرد — سفارش را لغو کنید'}, status=400)
                _record_shortage(item.quantity, 0)
                item.delete()
                order.updated_by = request.user
                self._recalc(order)
                return Response({'ok': True, 'deleted': True, 'total_amount': order.total_amount})
            _record_shortage(item.quantity, qty)
            item.quantity = qty

        # نحوه تسویه — با تغییر آن قیمت واحد هم از فرمول به‌روز می‌شود
        if 'settlement_type' in d:
            st = d['settlement_type']
            if st not in Settlement.values:
                return Response({'error': 'نوع تسویه نامعتبر است'}, status=400)
            item.settlement_type = st
            from apps.catalog.pricing import price_for_settlement
            item.unit_price = price_for_settlement(item.variant, order.user, st)
            # موعد خودکار از نوع تسویه — تقویم دستی از فرانت حذف شده؛ مگر اینکه صراحتاً تاریخ ارسال شود
            if 'settlement_due_date' not in d:
                from .models import settlement_due_for
                item.settlement_due_date = settlement_due_for(st)

        # موعد تسویه — رشته YYYY-MM-DD یا null
        if 'settlement_due_date' in d:
            raw = d['settlement_due_date']
            if not raw:
                item.settlement_due_date = None
            else:
                from datetime import date as _date
                try:
                    item.settlement_due_date = _date.fromisoformat(str(raw))
                except ValueError:
                    return Response({'error': 'فرمت موعد تسویه نامعتبر است (YYYY-MM-DD)'}, status=400)

        item.save()
        order.updated_by = request.user
        self._recalc(order)
        return Response({'ok': True, 'total_amount': order.total_amount})

    @staticmethod
    def _recalc(order):
        order.total_amount = sum(i.subtotal for i in order.items.all())
        order.save(update_fields=['total_amount', 'updated_by', 'updated_at'])


class AdminOrderUpdateView(APIView):
    """PATCH /api/orders/admin/<order_number>/update/ — آپدیت وضعیت سفارش"""
    permission_classes = [IsAdminUser]

    @transaction.atomic
    def patch(self, request, order_number):
        from apps.accounting.views import _has_perm
        if not _has_perm(request.user, "orders_view"):
            return Response({"error": "شما دسترسی لازم برای این عملیات را ندارید"}, status=403)
        from .models import Order
        from django.utils import timezone
        try:
            order = Order.objects.select_for_update().get(order_number=order_number)
        except Order.DoesNotExist:
            return Response({'error': 'سفارش یافت نشد'}, status=404)

        d = request.data
        if d.get('status') == Order.Status.CANCELLED and order.status != Order.Status.CANCELLED:
            try:
                order = cancel_order(order, reason="admin_update")
            except ValueError as exc:
                return Response({'error': str(exc)}, status=400)
            return Response({'ok': True, 'order_number': order.order_number})
        if d.get('status') in (Order.Status.PAID, Order.Status.REFUNDED, Order.Status.REJECTED) \
                and d['status'] != order.status:
            return Response({'error': 'تغییر وضعیت مالی سفارش فقط از مسیر پرداخت/سند مربوط انجام می‌شود'}, status=400)
        if d.get('status') in (Order.Status.PENDING, Order.Status.CONFIRMED, Order.Status.AWAITING_PAYMENT) \
                and d['status'] != order.status:
            return Response({'error': 'بازگرداندن وضعیت سفارش از فرم ویرایش مجاز نیست'}, status=400)

        invoice = getattr(order, 'sale_invoice', None)
        if 'confirmed_amount' in d and int(d['confirmed_amount'] or 0) != int(order.confirmed_amount or 0):
            return Response({'error': 'مبلغ تأییدشده فقط از مسیر تأیید سفارش تغییر می‌کند'}, status=400)
        if 'paid_amount' in d and int(d['paid_amount'] or 0) != int(order.paid_amount or 0):
            return Response({'error': 'مبلغ پرداخت‌شده فقط از اسناد دریافت محاسبه می‌شود'}, status=400)
        if 'payment_method' in d and d['payment_method'] != order.payment_method:
            return Response({'error': 'روش پرداخت فقط از اسناد دریافت تعیین می‌شود'}, status=400)
        if ('settlement_type' in d and d['settlement_type'] != order.settlement_type) \
                and (invoice or order.status != Order.Status.PENDING):
            return Response({'error': 'نحوه تسویه پس از تأیید/صدور فاکتور قابل تغییر نیست'}, status=400)

        old_status = order.status
        allowed = ['status', 'delivery_status', 'courier_company', 'tracking_code',
                   'settlement_type', 'admin_notes', 'shipping_method', 'freight_company']
        for field in allowed:
            if field in d:
                setattr(order, field, d[field])

        if 'settlement_due_date' in d:
            raw = d['settlement_due_date']
            new_due = None
            if raw:
                from datetime import date as _date
                try:
                    new_due = _date.fromisoformat(str(raw))
                except ValueError:
                    return Response({'error': 'فرمت موعد تسویه نامعتبر است (YYYY-MM-DD)'}, status=400)
            if new_due != order.settlement_due_date and (invoice or order.status != Order.Status.PENDING):
                return Response({'error': 'موعد تسویه پس از تأیید/صدور فاکتور قابل تغییر نیست'}, status=400)
            order.settlement_due_date = new_due

        if d.get('settlement_type') == 'credit' and 'settlement_due_date' not in d:
            from .models import settlement_due_for
            order.settlement_due_date = settlement_due_for('credit')

        if d.get('delivery_status') == 'shipped' and not getattr(order, 'shipped_at', None):
            order.shipped_at = timezone.now()
        if d.get('delivery_status') == 'delivered' and not getattr(order, 'delivered_at', None):
            order.delivered_at = timezone.now()

        order.updated_by = request.user
        order.status_updated_at = timezone.now()
        order.save()

        if 'status' in d and order.status != old_status:
            from apps.notifications.services import notify_order_status_sms
            notify_order_status_sms(order)

        return Response({'ok': True, 'order_number': order.order_number})


class AdminOrderRejectView(APIView):
    """POST /api/orders/admin/<order_number>/reject/ — رد پیش‌فاکتور (فقط از وضعیت در انتظار بررسی)"""
    permission_classes = [IsAdminUser]

    @transaction.atomic
    def post(self, request, order_number):
        from apps.accounting.views import _has_perm
        if not _has_perm(request.user, "orders_view"):
            return Response(
                {"error": "شما دسترسی لازم برای این عملیات را ندارید"}, status=403
            )
        reason = (request.data.get("reason") or "").strip()
        if not reason:
            return Response({"error": "دلیل رد الزامی است."},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            order = Order.objects.get(order_number=order_number)
        except Order.DoesNotExist:
            return Response({"error": "سفارش یافت نشد."}, status=status.HTTP_404_NOT_FOUND)
        if order.status != Order.Status.PENDING:
            return Response({"error": "فقط پیش‌فاکتورهای در انتظار بررسی قابل رد هستند."},
                            status=status.HTTP_400_BAD_REQUEST)

        # آزاد کردن رزروها در صورت وجود (سفارش در انتظار بررسی معمولاً رزرو ندارد)
        for reservation in order.reservations.filter(is_released=False):
            reservation.release(reason="admin_reject")

        order.status = Order.Status.REJECTED
        order.reject_reason = reason
        order.rejected_at = timezone.now()
        order.updated_by = request.user
        order.save(update_fields=["status", "reject_reason", "rejected_at", "updated_by", "updated_at"])

        # اطلاع‌رسانی به مشتری — best-effort، خرابی آن جریان اصلی را نشکند
        try:
            from apps.notifications.services import notify_order_rejected
            notify_order_rejected(order, reason)
        except Exception as e:
            logger.warning(f"[ORDER] notify rejected failed for {order.order_number}: {e}")

        logger.info(f"[ORDER] Rejected: {order.order_number} | by: {request.user} | reason: {reason}")
        return Response({
            "order_number": order.order_number,
            "status": order.status,
            "reject_reason": order.reject_reason,
            "rejected_at": order.rejected_at.strftime("%Y-%m-%d %H:%M"),
        })


class AdminOrderDeleteView(APIView):
    """DELETE /api/orders/admin/<order_number>/ — حذف کامل پیش‌فاکتور ردشده (فقط سوپریوزر)"""
    permission_classes = [IsAdminUser]

    def delete(self, request, order_number):
        if not request.user.is_superuser:
            return Response({"error": "فقط مدیر ارشد می‌تواند پیش‌فاکتور را حذف کند."},
                            status=status.HTTP_403_FORBIDDEN)
        try:
            order = Order.objects.get(order_number=order_number)
        except Order.DoesNotExist:
            return Response({"error": "سفارش یافت نشد."}, status=status.HTTP_404_NOT_FOUND)
        if order.status != Order.Status.REJECTED:
            return Response({"error": "فقط پیش‌فاکتورهای ردشده قابل حذف هستند."},
                            status=status.HTTP_400_BAD_REQUEST)
        logger.warning(f"[ORDER] پیش‌فاکتور {order.order_number} توسط {request.user} حذف شد")
        order.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminRejectReportView(APIView):
    """
    GET /api/orders/admin/reject-report/?from=YYYY-MM-DD&to=YYYY-MM-DD
    گزارش پیش‌فاکتورهای ردشده در بازه زمانی (بر اساس تاریخ رد) — پیش‌فرض: ۳۰ روز گذشته.
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        from apps.accounting.views import _has_perm
        if not _has_perm(request.user, "reject_report_view"):
            return Response(
                {"error": "شما دسترسی لازم برای این عملیات را ندارید"}, status=403
            )

        from datetime import date as _date, timedelta
        today = timezone.localdate()
        try:
            date_from = _date.fromisoformat(str(request.query_params["from"])) \
                if request.query_params.get("from") else today - timedelta(days=30)
            date_to = _date.fromisoformat(str(request.query_params["to"])) \
                if request.query_params.get("to") else today
        except ValueError:
            return Response({"error": "فرمت تاریخ نامعتبر است (YYYY-MM-DD)."},
                            status=status.HTTP_400_BAD_REQUEST)

        qs = (
            Order.objects
            .filter(
                status=Order.Status.REJECTED,
                rejected_at__date__gte=date_from,
                rejected_at__date__lte=date_to,
            )
            .select_related("user")
            .order_by("-rejected_at")
        )
        items = [{
            "order_number": o.order_number,
            "customer_name": o.user.get_full_name() or "",
            "customer_phone": o.user.phone or "",
            "reason": o.reject_reason or "",
            "rejected_at": o.rejected_at.strftime("%Y-%m-%d %H:%M") if o.rejected_at else "",
        } for o in qs]
        return Response({
            "from": date_from.isoformat(),
            "to": date_to.isoformat(),
            "total": len(items),
            "items": items,
        })


# ─── Receipts (فیش واریزی) ─────────────────────────────────────────────────────

def _parse_receipt_payload(request):
    """اعتبارسنجی فیلدهای فیش واریزی — خروجی: (data, error_response)."""
    image = request.FILES.get("image")
    if not image:
        return None, Response({"error": "تصویر فیش واریزی الزامی است."},
                              status=status.HTTP_400_BAD_REQUEST)
    try:
        amount = int(request.data.get("amount", 0))
    except (TypeError, ValueError):
        amount = 0
    if amount <= 0:
        return None, Response({"error": "مبلغ فیش باید عدد مثبت باشد."},
                              status=status.HTTP_400_BAD_REQUEST)
    from datetime import date as _date
    try:
        paid_at = _date.fromisoformat(str(request.data.get("paid_at", "")))
    except (TypeError, ValueError):
        return None, Response({"error": "تاریخ واریز نامعتبر است (YYYY-MM-DD)."},
                              status=status.HTTP_400_BAD_REQUEST)
    return {
        "image": image,
        "amount": amount,
        "paid_at": paid_at,
        "tracking_code": request.data.get("tracking_code", "") or "",
    }, None


class OrderReceiptCreateView(APIView):
    """POST /api/orders/<order_number>/receipts/ — آپلود فیش واریزی توسط مشتری"""
    permission_classes = [IsAuthenticated]

    def post(self, request, order_number):
        try:
            order = Order.objects.get(order_number=order_number, user__in=accessible_user_ids(request.user))
        except Order.DoesNotExist:
            return Response({"error": "سفارش یافت نشد."}, status=status.HTTP_404_NOT_FOUND)

        # فیش واریزی فقط برای سفارش‌های تمام‌نقدی — سفارش‌های اعتباری سررسید دارند
        if order.items.exclude(settlement_type="cash").exists():
            return Response({"error": "ثبت فیش واریزی فقط برای سفارش‌های نقدی است."},
                            status=status.HTTP_400_BAD_REQUEST)
        # فیش فقط بعد از تأیید سفارش و ارسال شماره حساب صراف — نه در وضعیت در انتظار بررسی
        if order.status != Order.Status.AWAITING_PAYMENT:
            return Response({"error": "ثبت فیش فقط بعد از تأیید سفارش و ارسال شماره حساب ممکن است."},
                            status=status.HTTP_400_BAD_REQUEST)

        data, err = _parse_receipt_payload(request)
        if err:
            return err

        from apps.accounting.models import PaymentReceipt
        receipt = PaymentReceipt.objects.create(
            order=order,
            customer=order.user,
            uploaded_by=request.user,
            status=PaymentReceipt.Status.PENDING,
            **data,
        )
        return Response(
            PaymentReceiptSerializer(receipt, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class MyReceiptsView(APIView):
    """GET /api/orders/my-receipts/ — فیش‌های واریزی کاربر جاری"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.accounting.models import PaymentReceipt
        receipts = (
            PaymentReceipt.objects.filter(customer__in=accessible_user_ids(request.user))
            .select_related("order", "customer", "uploaded_by")
        )
        return Response(
            PaymentReceiptSerializer(receipts, many=True, context={"request": request}).data
        )


class AdminReceiptListCreateView(APIView):
    """
    GET  /api/orders/admin/receipts/?status=pending|approved|rejected — همه فیش‌ها
    POST /api/orders/admin/receipts/ — آپلود فیش از طرف مشتری توسط ادمین (body: order_number + فیلدهای فیش)
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        from apps.accounting.views import _has_perm
        if not _has_perm(request.user, "sale_payment"):
            return Response(
                {"error": "شما دسترسی لازم برای این عملیات را ندارید"}, status=403
            )
        from apps.accounting.models import PaymentReceipt
        qs = PaymentReceipt.objects.select_related("order", "customer", "uploaded_by")
        status_filter = request.query_params.get("status")
        if status_filter in PaymentReceipt.Status.values:
            qs = qs.filter(status=status_filter)
        return Response(
            PaymentReceiptSerializer(qs, many=True, context={"request": request}).data
        )

    def post(self, request):
        from apps.accounting.views import _has_perm
        if not _has_perm(request.user, "sale_payment"):
            return Response(
                {"error": "شما دسترسی لازم برای این عملیات را ندارید"}, status=403
            )
        order_number = request.data.get("order_number")
        if not order_number:
            return Response({"error": "شماره سفارش الزامی است."},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            order = Order.objects.get(order_number=order_number)
        except Order.DoesNotExist:
            return Response({"error": "سفارش یافت نشد."}, status=status.HTTP_404_NOT_FOUND)
        if order.status != Order.Status.AWAITING_PAYMENT:
            return Response({"error": "فیش فقط برای سفارش در انتظار پرداخت قابل ثبت است"}, status=400)
        if order.items.exclude(settlement_type="cash").exists():
            return Response({"error": "ثبت فیش واریزی فقط برای سفارش‌های نقدی است"}, status=400)

        data, err = _parse_receipt_payload(request)
        if err:
            return err

        from apps.accounting.models import PaymentReceipt
        receipt = PaymentReceipt.objects.create(
            order=order,
            customer=order.user,
            uploaded_by=request.user,
            status=PaymentReceipt.Status.PENDING,
            **data,
        )
        return Response(
            PaymentReceiptSerializer(receipt, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class AdminReceiptApproveView(APIView):
    """
    POST /api/orders/admin/receipts/<pk>/approve/
    تأیید فیش — تخصیص FIFO مبلغ فیش به فاکتورهای باز مشتری (به ترتیب موعد مؤثر،
    از طریق apps.accounting.services.settle_customer_fifo که فاکتور/سفارش
    تسویه‌شده را هم می‌بندد و مازاد را به بستانکاری نقدی می‌برد).
    """
    permission_classes = [IsAdminUser]

    @transaction.atomic
    def post(self, request, pk):
        from apps.accounting.views import _has_perm
        if not _has_perm(request.user, "sale_payment"):
            return Response({"error": "شما دسترسی لازم برای این عملیات را ندارید"}, status=403)
        from apps.accounting.models import PaymentReceipt
        try:
            receipt = PaymentReceipt.objects.select_for_update().select_related("order", "customer").get(pk=pk)
        except PaymentReceipt.DoesNotExist:
            return Response({"error": "فیش یافت نشد."}, status=status.HTTP_404_NOT_FOUND)
        if receipt.status != PaymentReceipt.Status.PENDING:
            return Response({"error": "این فیش قبلاً بررسی شده است."},
                            status=status.HTTP_400_BAD_REQUEST)
        if receipt.order.status != Order.Status.AWAITING_PAYMENT:
            return Response({"error": "وضعیت سفارش برای تأیید فیش معتبر نیست"}, status=400)
        if receipt.order.items.exclude(settlement_type="cash").exists():
            return Response({"error": "تأیید فیش فقط برای سفارش نقدی مجاز است"}, status=400)

        # فیش تأییدشده یعنی پرداخت انجام شده — سفارش‌های تأیید خودکار هنوز فاکتور
        # ندارند (فاکتور فقط بعد از پرداخت ساخته می‌شود)؛ اینجا ساخته می‌شود تا
        # تخصیص FIFO به همان فاکتور بخورد، نه اینکه مبلغ برود به بستانکاری.
        from apps.orders.services import _create_sale_invoice_for_order
        order_invoice = getattr(receipt.order, "sale_invoice", None)
        if order_invoice is None:
            order_invoice = _create_sale_invoice_for_order(receipt.order, created_by=request.user)

        # اول بستانکاری قبلی مشتری (اضافه‌واریزی‌ها) به بدهی‌های باز تخصیص می‌یابد
        from apps.orders.services import apply_customer_credit
        apply_customer_credit(receipt.customer, actor=request.user)

        # تخصیص FIFO مبلغ فیش به فاکتورهای باز مشتری (به ترتیب موعد مؤثر) —
        # هم فاکتورهای سفارش سایت و هم فاکتورهای دستی. مازاد → بستانکاری نقدی (داخل سرویس)
        from apps.accounting.services import settle_customer_fifo
        result = settle_customer_fifo(
            receipt.customer, receipt.amount,
            date=receipt.paid_at, actor=request.user,
            method="transfer", reference=receipt.tracking_code,
            note=f"فیش واریزی #{receipt.id} — صراف: {receipt.order.sarraf_account_holder}",
            receipt=receipt,
        )

        # فیش به SalePayment فاکتورِ همین سفارش (یا اولین تخصیص) لینک می‌شود
        payments_by_invoice = {a["invoice_id"]: a["payment_id"] for a in result["allocated"]}
        receipt.sale_payment_id = (
            payments_by_invoice.get(order_invoice.id) if order_invoice else None
        ) or (result["allocated"][0]["payment_id"] if result["allocated"] else None)
        receipt.status = PaymentReceipt.Status.APPROVED
        receipt.reviewed_by = request.user
        receipt.reviewed_at = timezone.now()
        receipt.save(update_fields=[
            "sale_payment", "status", "reviewed_by", "reviewed_at",
        ])

        # اطلاع‌رسانی به مشتری — best-effort، خرابی آن جریان اصلی را نشکند
        try:
            from apps.notifications.services import notify_receipt_approved
            notify_receipt_approved(receipt)
        except Exception as e:
            logger.warning(f"[RECEIPT] notify approved failed for receipt {receipt.id}: {e}")

        return Response(
            PaymentReceiptSerializer(receipt, context={"request": request}).data
        )


class AdminReceiptRejectView(APIView):
    """POST /api/orders/admin/receipts/<pk>/reject/ — رد فیش با دلیل"""
    permission_classes = [IsAdminUser]

    def post(self, request, pk):
        from apps.accounting.views import _has_perm
        if not _has_perm(request.user, "sale_payment"):
            return Response({"error": "شما دسترسی لازم برای این عملیات را ندارید"}, status=403)
        reason = (request.data.get("reason") or "").strip()
        if not reason:
            return Response({"error": "دلیل رد فیش الزامی است."},
                            status=status.HTTP_400_BAD_REQUEST)

        from apps.accounting.models import PaymentReceipt
        try:
            receipt = PaymentReceipt.objects.select_related("order", "customer").get(pk=pk)
        except PaymentReceipt.DoesNotExist:
            return Response({"error": "فیش یافت نشد."}, status=status.HTTP_404_NOT_FOUND)
        if receipt.status != PaymentReceipt.Status.PENDING:
            return Response({"error": "این فیش قبلاً بررسی شده است."},
                            status=status.HTTP_400_BAD_REQUEST)

        receipt.status = PaymentReceipt.Status.REJECTED
        receipt.reject_reason = reason
        receipt.reviewed_by = request.user
        receipt.reviewed_at = timezone.now()
        receipt.save(update_fields=["status", "reject_reason", "reviewed_by", "reviewed_at"])

        try:
            from apps.notifications.services import notify_receipt_rejected
            notify_receipt_rejected(receipt, reason)
        except Exception as e:
            logger.warning(f"[RECEIPT] notify rejected failed for receipt {receipt.id}: {e}")

        return Response(
            PaymentReceiptSerializer(receipt, context={"request": request}).data
        )


class AdminShortageReportView(APIView):
    """
    GET /api/orders/admin/shortage-report/?from=YYYY-MM-DD&to=YYYY-MM-DD
    گزارش مازاد تقاضا (StockShortage) گروه‌بندی‌شده بر اساس واریانت — پیش‌فرض: ۳۰ روز گذشته.
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        from apps.accounting.views import _has_perm
        if not _has_perm(request.user, "shortage_view"):
            return Response(
                {"error": "شما دسترسی لازم برای این عملیات را ندارید"}, status=403
            )

        from datetime import date as _date, timedelta
        from django.db.models import Sum, Count
        from .models import StockShortage

        today = timezone.localdate()
        try:
            date_from = _date.fromisoformat(str(request.query_params["from"])) \
                if request.query_params.get("from") else today - timedelta(days=30)
            date_to = _date.fromisoformat(str(request.query_params["to"])) \
                if request.query_params.get("to") else today
        except ValueError:
            return Response({"error": "فرمت تاریخ نامعتبر است (YYYY-MM-DD)."},
                            status=status.HTTP_400_BAD_REQUEST)

        rows = (
            StockShortage.objects
            .filter(created_at__date__gte=date_from, created_at__date__lte=date_to)
            .values("variant_id", "variant__sku", "variant__product__name")
            .annotate(
                total_shortage=Sum("shortage_qty"),
                total_requested=Sum("requested_qty"),
                orders_count=Count("order", distinct=True),
            )
            .order_by("-total_shortage")
        )
        return Response({
            "from": date_from.isoformat(),
            "to": date_to.isoformat(),
            "items": [{
                "variant_id": r["variant_id"],
                "sku": r["variant__sku"],
                "product_name": r["variant__product__name"],
                "total_shortage": r["total_shortage"] or 0,
                "total_requested": r["total_requested"] or 0,
                "orders_count": r["orders_count"],
            } for r in rows],
        })


class MyOverdueView(APIView):
    """GET /api/orders/my-overdue/ — وضعیت معوقات کاربر جاری (برای هشدار قبل از ثبت سفارش)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.users.services import partner_restriction
        restriction = partner_restriction(request.user)
        return Response({
            "count": request.user.overdue_count(),
            "total": request.user.overdue_total(),
            "level": restriction["level"] if restriction else None,
            "days_overdue": restriction["days_overdue"] if restriction else 0,
        })
