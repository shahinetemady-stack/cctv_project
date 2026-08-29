"""
apps/users/views.py
────────────────────
Auth & user management — ایمیل + رمز عبور + JWT.

POST /api/users/auth/register/           → ثبت‌نام
POST /api/users/auth/login/              → ورود → access + refresh
POST /api/users/auth/refresh/            → تمدید access token
POST /api/users/auth/logout/             → blacklist refresh token

GET/PUT /api/users/me/                   → پروفایل من
POST    /api/users/me/change-password/   → تغییر رمز عبور
POST    /api/users/me/register-partner/  → درخواست عضویت همکار

POST /api/users/auth/forgot-password/    → ارسال کد یکبارمصرف پیامکی
POST /api/users/auth/reset-password/     → تأیید کد + تعیین رمز جدید (+ لاگین)
POST /api/users/auth/register/send-code/ → ارسال کد تأیید پیامکی برای ثبت‌نام

GET  /api/users/admin/partners/               → لیست همکاران
POST /api/users/admin/partners/<id>/approve/  → تأیید / رد
"""

import hashlib
import logging
import random
from datetime import timedelta
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView as BaseTokenRefreshView

from .models import UserProfile
from .permissions import IsVerifiedUser
from .serializers import (
    AdminApprovePartnerSerializer,
    AdminPartnerListSerializer,
    ChangePasswordSerializer,
    LoginSerializer,
    PartnerRegisterSerializer,
    RegisterSerializer,
    UserSerializer,
    UserUpdateSerializer,
    get_tokens_for_user,
)

logger = logging.getLogger(__name__)


# ─── Register ─────────────────────────────────────────────────────────────────

class RegisterView(APIView):
    """
    POST /api/users/auth/register/
    { "phone": "...", "code": "...", "email": "...", "password": "...",
      "password2": "...", "first_name": "...", "last_name": "..." }
    → 201: { access, refresh, user }
    پیش‌نیاز: تأیید شماره با کد پیامکی — auth/register/send-code/
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        phone = _normalize_phone(request.data.get("phone"))
        code = _normalize_phone(request.data.get("code"))
        otp, err = _check_otp(phone, code)
        if err is not None:
            return err
        user = serializer.save()
        otp.delete()
        tokens = get_tokens_for_user(user)
        logger.info(f"[AUTH] New user: {user.email}")
        return Response(
            {**tokens, "user": UserSerializer(user, context={"request": request}).data},
            status=status.HTTP_201_CREATED,
        )


# ─── Login ────────────────────────────────────────────────────────────────────

class LoginView(APIView):
    """
    POST /api/users/auth/login/
    { "email": "...", "password": "..." }
    → 200: { access, refresh, user }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        user = serializer.validated_data["user"]
        tokens = get_tokens_for_user(user)
        logger.info(f"[AUTH] Login: {user.email} | is_partner={user.is_partner}")
        return Response(
            {**tokens, "user": UserSerializer(user, context={"request": request}).data},
            status=status.HTTP_200_OK,
        )


# ─── Token Refresh ────────────────────────────────────────────────────────────

class TokenRefreshView(BaseTokenRefreshView):
    """POST /api/users/auth/refresh/ — simplejwt استاندارد"""
    pass


# ─── بازیابی رمز عبور با پیامک (OTP) ─────────────────────────────────────────
# هم برای کاربران عادی (فراموشی رمز) و هم برای حساب‌های فروشگاهی (کاربر سایه
# بدون رمز) کار می‌کند — مشتری حضوری با کد پیامکی حسابش را خودش فعال می‌کند.

OTP_TTL_SECONDS = 120        # اعتبار کد
OTP_RESEND_SECONDS = 60      # حداقل فاصله بین دو ارسال
OTP_MAX_ATTEMPTS = 5         # حداکثر تلاش برای هر کد


def _normalize_phone(raw):
    p = str(raw or '').strip()
    p = p.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789"))
    return p


def _hash_code(phone, code):
    return hashlib.sha256(f"{phone}:{code}".encode()).hexdigest()


def _create_and_send_otp(phone):
    """ساخت و ارسال کد OTP → None در صورت موفقیت، وگرنه Response خطا"""
    from .models import OtpCode
    from apps.notifications.sms import send_otp_sms, sms_configured

    existing = OtpCode.objects.filter(phone=phone).first()
    if existing and (timezone.now() - existing.created_at).total_seconds() < OTP_RESEND_SECONDS:
        return Response({'error': 'کد تأیید قبلاً ارسال شده است؛ کمی صبر کنید و دوباره تلاش کنید'}, status=429)
    if not sms_configured():
        logger.error("[AUTH] درخواست OTP ولی سرویس پیامک پیکربندی نشده است")
        return Response({'error': 'سرویس پیامک موقتاً در دسترس نیست؛ بعداً تلاش کنید'}, status=503)
    code = f"{random.SystemRandom().randint(0, 99999):05d}"
    OtpCode.objects.filter(phone=phone).delete()
    OtpCode.objects.create(
        phone=phone,
        code_hash=_hash_code(phone, code),
        expires_at=timezone.now() + timedelta(seconds=OTP_TTL_SECONDS),
    )
    if not send_otp_sms(phone, code):
        OtpCode.objects.filter(phone=phone).delete()
        return Response({'error': 'ارسال پیامک ناموفق بود؛ دوباره تلاش کنید'}, status=502)
    logger.info(f"[AUTH] OTP برای {phone} ارسال شد")
    return None


def _check_otp(phone, code):
    """بررسی کد پیامکی → (otp, None) یا (None, Response خطا)"""
    from .models import OtpCode

    if not code:
        return None, Response({'code': 'کد تأیید پیامکی الزامی است'}, status=400)
    otp = OtpCode.objects.filter(phone=phone).first()
    if otp is None or otp.expires_at < timezone.now():
        return None, Response({'code': 'کد منقضی شده است؛ دوباره درخواست دهید'}, status=400)
    if otp.attempts >= OTP_MAX_ATTEMPTS:
        otp.delete()
        return None, Response({'code': 'تعداد تلاش‌ها بیش از حد — دوباره درخواست کد دهید'}, status=429)
    if _hash_code(phone, code) != otp.code_hash:
        otp.attempts += 1
        otp.save(update_fields=['attempts'])
        return None, Response({'code': 'کد تأیید اشتباه است'}, status=400)
    return otp, None


class RegisterSendCodeView(APIView):
    """POST /api/users/auth/register/send-code/  {phone} → ارسال کد تأیید ثبت‌نام"""
    permission_classes = [AllowAny]

    def post(self, request):
        from django.contrib.auth import get_user_model

        phone = _normalize_phone(request.data.get('phone'))
        if not (phone.startswith('09') and len(phone) == 11 and phone.isdigit()):
            return Response({'error': 'شماره موبایل معتبر نیست (مثال: 09123456789)'}, status=400)

        User = get_user_model()
        existing = User.objects.filter(phone=phone, is_active=True).first()
        if existing is not None:
            profile = getattr(existing, 'profile', None)
            if profile and profile.linked_contact_id and not existing.has_usable_password():
                return Response({
                    'error': 'حساب این شماره از قبل توسط فروشگاه ساخته شده و فاکتورهایتان در همان حساب است؛ کافی است رمز خود را تعیین کنید و وارد شوید',
                    'reason': 'account_claimable',
                }, status=400)
            return Response({
                'error': 'این شماره موبایل قبلاً ثبت شده است؛ از صفحه ورود وارد شوید',
                'reason': 'account_exists',
            }, status=400)

        err = _create_and_send_otp(phone)
        if err is not None:
            return err
        return Response({'ok': True, 'message': 'کد تأیید برایتان پیامک شد'})


class ForgotPasswordView(APIView):
    """POST /api/users/auth/forgot-password/  {phone} → ارسال کد پیامکی"""
    permission_classes = [AllowAny]

    def post(self, request):
        from django.contrib.auth import get_user_model

        phone = _normalize_phone(request.data.get('phone'))
        if not (phone.startswith('09') and len(phone) == 11 and phone.isdigit()):
            return Response({'error': 'شماره موبایل معتبر نیست (مثال: 09123456789)'}, status=400)

        User = get_user_model()
        user = User.objects.filter(phone=phone, is_active=True).first()
        # پاسخ یکسان چه کاربر باشد چه نباشد — شماره‌ها قابل شمارش نشوند
        if user is not None:
            err = _create_and_send_otp(phone)
            if err is not None:
                return err
        return Response({'ok': True, 'message': 'اگر این شماره ثبت شده باشد، کد تأیید برایتان پیامک می‌شود'})


class ResetPasswordView(APIView):
    """POST /api/users/auth/reset-password/  {phone, code, password} → رمز جدید + توکن‌ها"""
    permission_classes = [AllowAny]

    def post(self, request):
        from django.contrib.auth import get_user_model
        from .models import OtpCode

        phone = _normalize_phone(request.data.get('phone'))
        code = str(request.data.get('code') or '').strip()
        code = _normalize_phone(code)  # ارقام فارسی → لاتین
        password = str(request.data.get('password') or '')
        if len(password) < 8:
            return Response({'error': 'رمز عبور باید حداقل ۸ کاراکتر باشد'}, status=400)

        otp = OtpCode.objects.filter(phone=phone).first()
        if otp is None or otp.expires_at < timezone.now():
            return Response({'error': 'کد منقضی شده است؛ دوباره درخواست دهید'}, status=400)
        if otp.attempts >= OTP_MAX_ATTEMPTS:
            otp.delete()
            return Response({'error': 'تعداد تلاش‌ها بیش از حد — دوباره درخواست کد دهید'}, status=429)
        if _hash_code(phone, code) != otp.code_hash:
            otp.attempts += 1
            otp.save(update_fields=['attempts'])
            return Response({'error': 'کد تأیید اشتباه است'}, status=400)

        User = get_user_model()
        user = User.objects.filter(phone=phone, is_active=True).first()
        if user is None:
            return Response({'error': 'کاربری با این شماره یافت نشد'}, status=400)
        user.set_password(password)
        user.save(update_fields=['password'])
        otp.delete()
        logger.info(f"[AUTH] رمز عبور {phone} از طریق OTP بازنشانی شد")
        tokens = get_tokens_for_user(user)
        return Response({**tokens, 'user': UserSerializer(user, context={'request': request}).data})


# ─── Logout ───────────────────────────────────────────────────────────────────

class LogoutView(APIView):
    """
    POST /api/users/auth/logout/
    { "refresh": "eyJ..." }
    → refresh token را blacklist می‌کند.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        token_str = request.data.get("refresh")
        if not token_str:
            return Response(
                {"error": "refresh token الزامی است."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            RefreshToken(token_str).blacklist()
            logger.info(f"[AUTH] Logout: {request.user.email}")
            return Response({"detail": "با موفقیت خارج شدید."})
        except TokenError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# ─── Me ───────────────────────────────────────────────────────────────────────

class MeView(APIView):
    """GET/PUT /api/users/me/"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user, context={"request": request}).data)

    def put(self, request):
        serializer = UserUpdateSerializer(
            request.user, data=request.data, partial=True, context={"request": request}
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        serializer.save()
        return Response(UserSerializer(request.user, context={"request": request}).data)


class ChangePasswordView(APIView):
    """POST /api/users/me/change-password/"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        if not user.check_password(serializer.validated_data["old_password"]):
            return Response(
                {"error": "رمز عبور فعلی اشتباه است."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.set_password(serializer.validated_data["new_password"])
        user.save()
        logger.info(f"[AUTH] Password changed: {user.email}")
        return Response({"detail": "رمز عبور با موفقیت تغییر یافت."})


# ─── Partner Registration ─────────────────────────────────────────────────────

class RegisterPartnerView(APIView):
    """
    POST /api/users/me/register-partner/
    کاربر لاگین‌شده درخواست عضویت همکار می‌دهد → is_approved=False.
    ادمین در پنل تأیید می‌کند.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        try:
            profile = user.profile
            if profile.user_type == UserProfile.UserType.PARTNER:
                msg = ("شما قبلاً به عنوان همکار تأیید شده‌اید."
                       if profile.is_approved
                       else "درخواست همکاری شما در انتظار بررسی است.")
                return Response({"detail": msg}, status=status.HTTP_200_OK)
        except UserProfile.DoesNotExist:
            pass

        serializer = PartnerRegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        serializer.save(user=user)

        logger.info(f"[AUTH] Partner request: {user.phone}")
        return Response(
            {"detail": "درخواست همکاری ثبت شد. بعد از بررسی ادمین اطلاع داده می‌شود."},
            status=status.HTTP_201_CREATED,
        )


# ─── Admin — Partner Management ───────────────────────────────────────────────

class AdminPartnerListView(APIView):
    """GET /api/users/admin/partners/?pending=true"""
    permission_classes = [IsAdminUser]

    def get(self, request):
        qs = (
            UserProfile.objects
            .filter(user_type=UserProfile.UserType.PARTNER)
            .select_related("user")
            .order_by("-created_at")
        )
        if request.query_params.get("pending", "").lower() == "true":
            qs = qs.filter(is_approved=False)
        return Response(AdminPartnerListSerializer(qs, many=True).data)


class AdminApprovePartnerView(APIView):
    """
    POST /api/users/admin/partners/<user_id>/approve/
    { "is_approved": true, "credit_limit": 5000000, "notes": "تأیید شد" }
    """
    permission_classes = [IsAdminUser]

    def post(self, request, user_id):
        try:
            profile = UserProfile.objects.select_related("user").get(
                user__id=user_id,
                user_type=UserProfile.UserType.PARTNER,
            )
        except UserProfile.DoesNotExist:
            return Response({"error": "همکار یافت نشد."}, status=status.HTTP_404_NOT_FOUND)

        serializer = AdminApprovePartnerSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        profile.is_approved  = data["is_approved"]
        profile.credit_limit = data.get("credit_limit", profile.credit_limit)
        if data["is_approved"]:
            profile.partner_tier = data.get("partner_tier") or profile.partner_tier
        else:
            # رد درخواست — برگشت به مشتری عمومی تا در لیست انتظار نماند
            profile.user_type = UserProfile.UserType.PUBLIC
            profile.partner_tier = ""
        if data.get("notes"):
            profile.notes = (
                (profile.notes + "\n" if profile.notes else "")
                + f"[ادمین {request.user.email}]: {data['notes']}"
            )
        profile.save()

        # پیامک اطلاع‌رسانی به همکار — best-effort
        if data["is_approved"]:
            from apps.notifications.services import notify_partner_approved_sms
            notify_partner_approved_sms(profile.user)

        # ایمیل اطلاع‌رسانی به همکار
        try:
            from django.core.mail import send_mail
            from django.conf import settings
            subject = "تأیید درخواست همکاری" if data["is_approved"] else "وضعیت درخواست همکاری"
            body = (
                "تبریک! درخواست همکاری شما تأیید شد."
                if data["is_approved"]
                else "متأسفانه درخواست همکاری شما تأیید نشد. با پشتیبانی تماس بگیرید."
            )
            send_mail(subject, body,
                      settings.EMAIL_HOST_USER or "noreply@cctvshop.ir",
                      [profile.user.email], fail_silently=True)
        except Exception:
            pass

        action = "تأیید" if data["is_approved"] else "رد"
        logger.info(f"[ADMIN] Partner {action}: user_id={user_id} by {request.user.email}")
        return Response(AdminPartnerListSerializer(profile).data)


class AdminBadgesView(APIView):
    """
    GET /api/users/admin-badges/
    شمارنده بج‌های منوی ادمین — سفارش‌های در انتظار بررسی + درخواست‌های همکاری در انتظار تأیید.
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        from apps.orders.models import Order
        from apps.orders.services import due_settlements_queryset, send_due_settlement_reminders
        from apps.accounting.models import SaleInvoice, PaymentReceipt
        from django.utils import timezone
        due_qs = SaleInvoice.objects.filter(
            settlement='credit', due_date__lte=timezone.now().date(),
        ).exclude(status='cancelled')
        sales_due = sum(1 for i in due_qs if i.remaining_amount > 0)
        # هشدارهای سررسید تسویه سفارش‌های سایت — روزی یک بار، تنبل هنگام باز شدن پنل
        try:
            send_due_settlement_reminders()
        except Exception:
            pass
        return Response({
            "orders_pending": Order.objects.filter(status=Order.Status.PENDING).count(),
            "partners_pending": UserProfile.objects.filter(
                user_type=UserProfile.UserType.PARTNER, is_approved=False,
            ).count(),
            "sales_due": sales_due,
            "orders_due": due_settlements_queryset().count(),
            "receipts_pending": PaymentReceipt.objects.filter(
                status=PaymentReceipt.Status.PENDING,
            ).count(),
        })

class ActivityLogListView(APIView):
    """
    GET /api/users/activity-logs/?user_id=&action=&date=&page=
    لاگ فعالیت‌ها — فیلتر کاربر/رویداد/تاریخ، صفحه‌بندی ۵۰تایی.
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        from .models import ActivityLog
        qs = ActivityLog.objects.select_related('user')
        p = request.query_params
        if p.get('user_id'):
            qs = qs.filter(user_id=p['user_id'])
        if p.get('action'):
            qs = qs.filter(action=p['action'])
        if p.get('date'):
            qs = qs.filter(created_at__date=p['date'])
        page = max(int(p.get('page', 1) or 1), 1)
        per = 50
        total = qs.count()
        rows = qs[(page - 1) * per: page * per]
        return Response({
            'total': total, 'page': page, 'pages': max((total + per - 1) // per, 1),
            'results': [{
                'id': a.id,
                'user': (a.user.get_full_name() or a.user.phone) if a.user else '—',
                'user_id': a.user_id,
                'action': a.action,
                'action_display': a.get_action_display(),
                'method': a.method,
                'path': a.path,
                'status': a.status,
                'created_at': a.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            } for a in rows],
        })
