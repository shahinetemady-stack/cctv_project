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

from .models import UserProfile
from .permissions import IsVerifiedUser
from .serializers import (
    AdminApprovePartnerSerializer,
    AdminPartnerListSerializer,
    ChangePasswordSerializer,
    ClubSettingsSerializer,
    GuaranteeSerializer,
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

class TokenRefreshView(APIView):
    """
    POST /api/users/auth/refresh/ — { refresh } → توکن‌های جدید.
    rotation دستی: توکن قدیمی blacklist می‌شود و مهلت‌های پرسنل (۱۰ ساعت بیکاری)
    از get_tokens_for_user اعمال می‌شود — رفتار پیش‌فرض simplejwt مهلت سفارشی را
    هنگام rotation نگه نمی‌داشت.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        token_str = request.data.get("refresh")
        if not token_str:
            return Response({"error": "refresh token الزامی است."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            old = RefreshToken(token_str)  # امضا، انقضا و blacklist را چک می‌کند
        except TokenError:
            return Response({"error": "نشست منقضی شده است."}, status=status.HTTP_401_UNAUTHORIZED)
        from django.contrib.auth import get_user_model
        try:
            user = get_user_model().objects.get(id=old["user_id"], is_active=True)
        except Exception:
            return Response({"error": "کاربر یافت نشد یا غیرفعال است."}, status=status.HTTP_401_UNAUTHORIZED)
        tokens = get_tokens_for_user(user)
        try:
            old.blacklist()
        except Exception:
            pass
        return Response(tokens)


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
        if not any(c.isalpha() for c in password) or not any(c.isdigit() for c in password):
            return Response({'error': 'رمز عبور باید ترکیبی از حروف و عدد باشد (فقط عدد یا فقط حرف کافی نیست)'}, status=400)

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
        # مشخصات هویتی (موبایل، نام، شرکت، کد ملی، آدرس، ایمیل) = هویت حساب —
        # ویرایش مستقیم ممنوع؛ فقط با درخواست تغییر + تأیید مدیر اعمال می‌شود
        # (پرسنل بر اساس نام طرف سرچ می‌کنند و تغییر خودسرانه داده‌ها را خراب می‌کند)
        data = dict(request.data)
        for f in ("phone", "first_name", "last_name", "email",
                  "company_name", "national_id", "address"):
            data.pop(f, None)
        serializer = UserUpdateSerializer(
            request.user, data=data, partial=True, context={"request": request}
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

        # پیامک «درخواست ثبت شد» — best-effort؛ اگر قالب تنظیم نشده باشد ساکت رد می‌شود
        from apps.notifications.services import notify_partner_request_sms
        notify_partner_request_sms(user)

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
        elif request.query_params.get("approved", "").lower() == "true":
            # تازه‌تأییدشده‌ها — مرتب بر اساس زمان تأیید (آخرین به‌روزرسانی پروفایل)
            qs = qs.filter(is_approved=True).order_by("-updated_at")
        return Response(AdminPartnerListSerializer(qs, many=True, context={"request": request}).data)


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
            if data.get("partner_tier"):
                # تغییر دستی سطح → پاک شدن نشان «پلاتینیوم خودکار»
                profile.platinum_auto_granted = False
            profile.partner_tier = data.get("partner_tier") or profile.partner_tier
        else:
            # رد درخواست — برگشت به مشتری عمومی تا در لیست انتظار نماند
            profile.user_type = UserProfile.UserType.PUBLIC
            profile.partner_tier = ""
            profile.platinum_auto_granted = False
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
        return Response(AdminPartnerListSerializer(profile, context={"request": request}).data)


# ─── Admin — Partner Club Settings ────────────────────────────────────────────

class ClubSettingsView(APIView):
    """
    GET/PUT /api/users/club-settings/
    آستانه‌های ارتقای سطح باشگاه همکاران (تومان) + وضعیت ارزیابی خودکار.
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        from .services import get_club_settings, find_downgrade_risks, snoozed_risk_count
        st = get_club_settings()
        at_risk = find_downgrade_risks(limit=50)
        return Response({
            "silver_to_gold_amount": st.silver_to_gold_amount,
            "gold_to_platinum_amount": st.gold_to_platinum_amount,
            "period_months": st.period_months,
            "auto_evaluate_enabled": st.auto_evaluate_enabled,
            "overdue_warn_workdays": st.overdue_warn_workdays,
            "overdue_cash_only_days": st.overdue_cash_only_days,
            "tier_benefits_silver": st.tier_benefits_silver,
            "tier_benefits_gold": st.tier_benefits_gold,
            "tier_benefits_platinum": st.tier_benefits_platinum,
            "at_risk_count": len(at_risk),
            "at_risk": at_risk,
            "at_risk_snoozed_count": snoozed_risk_count(),
        })

    def put(self, request):
        from .models import PartnerClubSettings
        from .services import invalidate_club_settings_cache
        serializer = ClubSettingsSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        st = PartnerClubSettings.get_instance()
        for k, v in serializer.validated_data.items():
            setattr(st, k, v)
        st.save()
        invalidate_club_settings_cache()
        logger.info(f"[CLUB] تنظیمات باشگاه توسط {request.user.phone} به‌روز شد")
        return self.get(request)


class ClubAtRiskSnoozeView(APIView):
    """
    POST /api/users/club-settings/at-risk/snooze/
    پنهان کردن موقت هشدار تنزل برای لیستی از همکاران (پیش‌فرض ۳۰ روز).
    body: {"phones": ["09xxxx", ...], "days": 30}
    """
    permission_classes = [IsAdminUser]

    def post(self, request):
        from .services import snooze_downgrade_risk
        phones = request.data.get("phones") or []
        days = request.data.get("days") or 30
        if not isinstance(phones, list) or not phones:
            return Response({"error": "لیست موبایل‌ها خالی است."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            days = max(1, min(int(days), 180))
        except (TypeError, ValueError):
            days = 30
        n = snooze_downgrade_risk(phones, days=days)
        logger.info(f"[CLUB] هشدار تنزل {n} همکار توسط {request.user.phone} برای {days} روز پنهان شد")
        return Response({"ok": True, "snoozed": n, "days": days})


class ClubInfoView(APIView):
    """
    GET /api/users/club-info/
    اطلاعات عمومی باشگاه همکاران برای صفحه لندینگ — بدون نیاز به احراز هویت.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        from .services import get_club_settings
        st = get_club_settings()
        return Response({
            "silver_to_gold_amount": st.silver_to_gold_amount,
            "gold_to_platinum_amount": st.gold_to_platinum_amount,
            "period_months": st.period_months,
            "tiers": [
                {"key": "silver", "title": "همکار سیلور", "benefits": st.tier_benefits_silver},
                {"key": "gold", "title": "همکار گلد", "benefits": st.tier_benefits_gold},
                {"key": "platinum", "title": "همکار پلاتینیوم", "benefits": st.tier_benefits_platinum},
            ],
        })


class ClubEvaluateView(APIView):
    """
    POST /api/users/club-settings/evaluate/
    اجرای دستی ارزیابی سطوح — فقط ارتقا، با پیامک اطلاع‌رسانی.
    """
    permission_classes = [IsAdminUser]

    def post(self, request):
        from .services import evaluate_partner_tiers
        result = evaluate_partner_tiers()
        logger.info(f"[CLUB] ارزیابی دستی سطوح توسط {request.user.phone}: {result['upgraded']} ارتقا")
        return Response(result)


# ─── Admin — تضامین همکار (فروش اعتباری) ──────────────────────────────────────

class PartnerGuaranteeListCreateView(APIView):
    """
    GET/POST /api/users/admin/partners/<user_id>/guarantees/     → تضامین کاربر سایت
    GET/POST /api/users/admin/contacts/<contact_id>/guarantees/  → تضامین طرف حساب دستی
    (multipart، مدرک اختیاری)
    """
    permission_classes = [IsAdminUser]

    def _resolve(self, user_id, contact_id):
        from django.shortcuts import get_object_or_404
        if contact_id is not None:
            from apps.accounting.models import Contact
            return {"contact": get_object_or_404(Contact, pk=contact_id)}
        return {"profile": get_object_or_404(UserProfile, user__id=user_id)}

    def get(self, request, user_id=None, contact_id=None):
        subject = self._resolve(user_id, contact_id)
        qs = subject["profile"].guarantees.all() if "profile" in subject else subject["contact"].guarantees.all()
        return Response(GuaranteeSerializer(qs, many=True, context={"request": request}).data)

    def post(self, request, user_id=None, contact_id=None):
        subject = self._resolve(user_id, contact_id)
        serializer = GuaranteeSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        guarantee = serializer.save(created_by=request.user, **subject)
        who = subject["profile"].user.phone if "profile" in subject else subject["contact"].name
        logger.info(f"[GUARANTEE] ثبت تضمین {guarantee.get_guarantee_type_display()} برای {who} توسط {request.user.phone}")
        return Response(
            GuaranteeSerializer(guarantee, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class PartnerGuaranteeDeleteView(APIView):
    """DELETE /api/users/admin/partners/<user_id>/guarantees/<gid>/
              یا /api/users/admin/contacts/<contact_id>/guarantees/<gid>/"""
    permission_classes = [IsAdminUser]

    def delete(self, request, gid, user_id=None, contact_id=None):
        from .models import PartnerGuarantee
        flt = {"id": gid}
        if contact_id is not None:
            flt["contact_id"] = contact_id
        else:
            flt["profile__user__id"] = user_id
        try:
            g = PartnerGuarantee.objects.get(**flt)
        except PartnerGuarantee.DoesNotExist:
            return Response({"error": "تضمین یافت نشد."}, status=status.HTTP_404_NOT_FOUND)
        g.document.delete(save=False)
        g.delete()
        logger.info(f"[GUARANTEE] حذف تضمین #{gid} توسط {request.user.phone}")
        return Response({"detail": "تضمین حذف شد."})


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
        from .models import PhoneChangeRequest, ProfileChangeRequest
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
        # ارزیابی خودکار سطوح باشگاه همکاران — روزی یک بار (فقط ارتقا)
        try:
            from django.core.cache import cache
            from .services import get_club_settings, evaluate_partner_tiers
            today = timezone.now().date().isoformat()
            if get_club_settings().auto_evaluate_enabled and cache.get("club_eval_day") != today:
                cache.set("club_eval_day", today, timeout=60 * 60 * 48)
                evaluate_partner_tiers()
        except Exception:
            logger.exception("[CLUB] خطا در ارزیابی خودکار سطوح")
        # اعمال خودکار بستانکاری مشتریان (اضافه‌واریزی) به بدهی‌های باز — روزی یک بار
        try:
            from django.core.cache import cache
            today = timezone.now().date().isoformat()
            if cache.get("credit_apply_day") != today:
                cache.set("credit_apply_day", today, timeout=60 * 60 * 48)
                from apps.orders.services import apply_customer_credit
                for p in UserProfile.objects.filter(payment_credit_irr__gt=0).select_related("user"):
                    apply_customer_credit(p.user)
        except Exception:
            logger.exception("[CREDIT] خطا در اعمال خودکار بستانکاری")
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
                "phone_requests": PhoneChangeRequest.objects.filter(status="pending").count(),
            "profile_requests": ProfileChangeRequest.objects.filter(status="pending").count(),})

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

class PhoneChangeRequestView(APIView):
    """GET/POST /api/users/me/phone-change-request/ — درخواست تغییر موبایل مشتری."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        latest = request.user.phone_change_requests.first()
        return Response({"request": _phone_request_payload(latest) if latest else None})

    def post(self, request):
        from .models import PhoneChangeRequest

        new_phone = (request.data.get("new_phone") or "").strip()
        reason = (request.data.get("reason") or "").strip()
        if not new_phone.isdigit() or len(new_phone) != 11 or not new_phone.startswith("09"):
            return Response({"error": "شماره موبایل معتبر نیست (مثلاً 0912…)"}, status=400)
        if new_phone == request.user.phone:
            return Response({"error": "موبایل جدید با موبایل فعلی یکی است"}, status=400)
        if User.objects.filter(phone=new_phone).exists():
            return Response({"error": "این شماره قبلاً در سیستم ثبت شده"}, status=400)
        if request.user.phone_change_requests.filter(
                status=PhoneChangeRequest.Status.PENDING).exists():
            return Response({"error": "یک درخواست در انتظار تأیید دارید"}, status=400)
        req = PhoneChangeRequest.objects.create(
            user=request.user, new_phone=new_phone, reason=reason)
        return Response({"request": _phone_request_payload(req)}, status=201)


def _phone_request_payload(r):
    return {
        "id": r.id, "user_id": r.user_id,
        "user_name": r.user.get_full_name() or r.user.phone,
        "old_phone": r.user.phone, "new_phone": r.new_phone,
        "reason": r.reason, "status": r.status,
        "status_display": r.get_status_display(),
        "created_at": r.created_at.isoformat(),
    }


class AdminPhoneRequestsView(APIView):
    """GET /api/users/admin/phone-requests/?status=pending — لیست درخواست‌ها."""

    permission_classes = [IsAdminUser]

    def get(self, request):
        from .models import PhoneChangeRequest

        qs = PhoneChangeRequest.objects.select_related("user")
        st = request.query_params.get("status", "pending")
        if st and st != "all":
            qs = qs.filter(status=st)
        return Response([_phone_request_payload(r) for r in qs[:200]])


class AdminPhoneRequestActionView(APIView):
    """POST /api/users/admin/phone-requests/<pk>/approve|reject/"""

    permission_classes = [IsAdminUser]

    def post(self, request, pk, action):
        from .models import PhoneChangeRequest
        from django.utils import timezone

        if not _has_users_edit(request.user):
            return Response({"error": "دسترسی ندارید"}, status=403)
        try:
            req = PhoneChangeRequest.objects.select_related("user").get(pk=pk)
        except PhoneChangeRequest.DoesNotExist:
            return Response({"error": "یافت نشد"}, status=404)
        if req.status != PhoneChangeRequest.Status.PENDING:
            return Response({"error": "این درخواست قبلاً بررسی شده"}, status=400)

        if action == "approve":
            if User.objects.filter(phone=req.new_phone).exists():
                return Response({"error": "این شماره قبلاً در سیستم ثبت شده"}, status=400)
            req.user.phone = req.new_phone
            req.user.save(update_fields=["phone"])
            req.status = PhoneChangeRequest.Status.APPROVED
        elif action == "reject":
            req.status = PhoneChangeRequest.Status.REJECTED
        else:
            return Response({"error": "اکشن نامعتبر"}, status=400)
        req.reviewed_by = request.user
        req.reviewed_at = timezone.now()
        req.save(update_fields=["status", "reviewed_by", "reviewed_at"])
        return Response({"ok": True, "request": _phone_request_payload(req)})


class ProfileChangeRequestView(APIView):
    """GET/POST /api/users/me/profile-change-request/ — درخواست تغییر مشخصات مشتری."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = request.user.profile_change_requests.all()[:20]
        return Response({"requests": [_profile_request_payload(r) for r in qs]})

    def post(self, request):
        from .models import ProfileChangeRequest

        field = (request.data.get("field") or "").strip()
        new_value = (request.data.get("new_value") or "").strip()
        reason = (request.data.get("reason") or "").strip()
        if field not in ProfileChangeRequest.Field.values:
            return Response({"error": "فیلد نامعتبر است"}, status=400)
        if not new_value:
            return Response({"error": "مقدار جدید را وارد کنید"}, status=400)
        current = _profile_field_value(request.user, field)
        if new_value == (current or ""):
            return Response({"error": "مقدار جدید با مقدار فعلی یکی است"}, status=400)
        if request.user.profile_change_requests.filter(
                field=field, status=ProfileChangeRequest.Status.PENDING).exists():
            return Response({"error": "برای این مورد یک درخواست در انتظار تأیید دارید"}, status=400)
        req = ProfileChangeRequest.objects.create(
            user=request.user, field=field, new_value=new_value, reason=reason)
        return Response({"request": _profile_request_payload(req)}, status=201)


def _profile_field_value(user, field):
    if field in ("first_name", "last_name"):
        return getattr(user, field, "")
    profile = getattr(user, "profile", None)
    return getattr(profile, field, "") if profile else ""


def _profile_request_payload(r):
    return {
        "id": r.id, "user_id": r.user_id,
        "user_name": r.user.get_full_name() or r.user.phone,
        "user_phone": r.user.phone,
        "field": r.field, "field_display": r.get_field_display(),
        "old_value": _profile_field_value(r.user, r.field),
        "new_value": r.new_value,
        "reason": r.reason, "status": r.status,
        "status_display": r.get_status_display(),
        "created_at": r.created_at.isoformat(),
    }


class AdminProfileRequestsView(APIView):
    """GET /api/users/admin/profile-requests/?status=pending — لیست درخواست‌های تغییر مشخصات."""

    permission_classes = [IsAdminUser]

    def get(self, request):
        from .models import ProfileChangeRequest

        qs = ProfileChangeRequest.objects.select_related("user", "user__profile")
        st = request.query_params.get("status", "pending")
        if st and st != "all":
            qs = qs.filter(status=st)
        return Response([_profile_request_payload(r) for r in qs[:200]])


class AdminProfileRequestActionView(APIView):
    """POST /api/users/admin/profile-requests/<pk>/approve|reject/"""

    permission_classes = [IsAdminUser]

    def post(self, request, pk, action):
        from .models import ProfileChangeRequest, UserProfile
        from django.utils import timezone

        if not _has_users_edit(request.user):
            return Response({"error": "دسترسی ندارید"}, status=403)
        try:
            req = ProfileChangeRequest.objects.select_related("user", "user__profile").get(pk=pk)
        except ProfileChangeRequest.DoesNotExist:
            return Response({"error": "یافت نشد"}, status=404)
        if req.status != ProfileChangeRequest.Status.PENDING:
            return Response({"error": "این درخواست قبلاً بررسی شده"}, status=400)

        if action == "approve":
            if req.field in ("first_name", "last_name"):
                setattr(req.user, req.field, req.new_value)
                req.user.save(update_fields=[req.field])
            else:
                profile, _ = UserProfile.objects.get_or_create(user=req.user)
                setattr(profile, req.field, req.new_value)
                profile.save(update_fields=[req.field])
            req.status = ProfileChangeRequest.Status.APPROVED
        elif action == "reject":
            req.status = ProfileChangeRequest.Status.REJECTED
        else:
            return Response({"error": "اکشن نامعتبر"}, status=400)
        req.reviewed_by = request.user
        req.reviewed_at = timezone.now()
        req.save(update_fields=["status", "reviewed_by", "reviewed_at"])
        return Response({"ok": True, "request": _profile_request_payload(req)})


def _has_users_edit(user):
    if user.is_superuser:
        return True
    sp = getattr(user, "staff_profile", None)
    return bool(sp and sp.has_perm("users_edit"))


class AdminLinkAccountView(APIView):
    """PATCH /api/users/admin/users/<user_id>/link/ — لینک شریک به حساب اصلی.

    بدنه: {"parent_account_id": <id> | null} — null یعنی جدا کردن لینک.
    """

    permission_classes = [IsAdminUser]

    def patch(self, request, user_id):
        if not _has_users_edit(request.user):
            return Response({"error": "دسترسی ندارید"}, status=403)
        try:
            user = User.objects.get(pk=user_id)
            profile = user.profile
        except (User.DoesNotExist, User.profile.RelatedObjectDoesNotExist):
            return Response({"error": "کاربر یا پروفایل یافت نشد"}, status=404)
        parent_id = request.data.get("parent_account_id")
        if parent_id is None:
            profile.parent_account = None
        else:
            if int(parent_id) == user.id:
                return Response({"error": "کاربر نمی‌تواند حساب اصلی خودش باشد"}, status=400)
            parent = User.objects.filter(pk=parent_id).first()
            if not parent:
                return Response({"error": "حساب اصلی یافت نشد"}, status=404)
            if getattr(parent.profile, "parent_account_id", None):
                return Response({"error": "حساب اصلی خودش نمی‌تواند شریک باشد"}, status=400)
            profile.parent_account = parent
        profile.save(update_fields=["parent_account"])
        return Response({
            "ok": True,
            "parent_account_id": profile.parent_account_id,
            "parent_account_name": (profile.parent_account.get_full_name()
                                    or profile.parent_account.phone)
            if profile.parent_account_id else None,
        })
