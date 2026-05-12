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

GET  /api/users/admin/partners/               → لیست همکاران
POST /api/users/admin/partners/<id>/approve/  → تأیید / رد
"""

import logging
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
    { "email": "...", "password": "...", "password2": "...",
      "first_name": "...", "last_name": "..." }
    → 201: { access, refresh, user }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        user = serializer.save()
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
        if data.get("notes"):
            profile.notes = (
                (profile.notes + "\n" if profile.notes else "")
                + f"[ادمین {request.user.email}]: {data['notes']}"
            )
        profile.save()

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
