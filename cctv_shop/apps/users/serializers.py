"""
apps/users/serializers.py
──────────────────────────
Serializers for email+password auth and user management.

RegisterSerializer         → ثبت‌نام عمومی
LoginSerializer            → ورود (email + password)
UserSerializer             → پروفایل کاربر
UserUpdateSerializer       → ویرایش پروفایل
PartnerRegisterSerializer  → درخواست عضویت همکار
AdminPartnerListSerializer → لیست همکاران (ادمین)
AdminApproveSerializer     → تأیید / رد همکار (ادمین)
"""

from django.contrib.auth import authenticate
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User, UserProfile


# ─── JWT helper ───────────────────────────────────────────────────────────────

def get_tokens_for_user(user: User) -> dict:
    """JWT با کلیم‌های سفارشی: email, user_type, is_partner"""
    refresh = RefreshToken.for_user(user)
    refresh["email"] = user.email
    refresh["is_staff"] = user.is_staff
    try:
        refresh["user_type"] = user.profile.user_type
        refresh["is_partner"] = user.is_partner
        refresh["is_approved"] = user.profile.is_approved
    except UserProfile.DoesNotExist:
        refresh["user_type"] = "public"
        refresh["is_partner"] = False
        refresh["is_approved"] = False
    return {"refresh": str(refresh), "access": str(refresh.access_token)}


# ─── Auth ─────────────────────────────────────────────────────────────────────

class RegisterSerializer(serializers.ModelSerializer):
    """ثبت‌نام مشتری عمومی با ایمیل + رمز عبور."""
    password = serializers.CharField(write_only=True, min_length=8)
    password2 = serializers.CharField(write_only=True, label="تکرار رمز عبور")

    class Meta:
        model = User
        fields = ["email", "password", "password2", "first_name", "last_name", "phone"]

    def validate(self, data):
        if data["password"] != data["password2"]:
            raise serializers.ValidationError({"password2": "رمزهای عبور مطابقت ندارند."})
        return data

    def create(self, validated_data):
        validated_data.pop("password2")
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        # ساخت پروفایل پیش‌فرض
        UserProfile.objects.create(user=user, user_type=UserProfile.UserType.PUBLIC)
        return user


class LoginSerializer(serializers.Serializer):
    """ورود با ایمیل + رمز عبور."""
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = authenticate(username=data["email"], password=data["password"])
        if not user:
            raise serializers.ValidationError("ایمیل یا رمز عبور اشتباه است.")
        if not user.is_active:
            raise serializers.ValidationError("حساب کاربری غیرفعال است.")
        data["user"] = user
        return data


# ─── Profile ──────────────────────────────────────────────────────────────────

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ["user_type", "company_name", "national_id",
                  "is_approved", "credit_limit", "address"]
        read_only_fields = ["user_type", "is_approved", "credit_limit"]


class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)
    is_partner = serializers.BooleanField(read_only=True)

    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name", "phone",
                  "is_partner", "date_joined", "profile"]
        read_only_fields = ["email", "date_joined"]


class UserUpdateSerializer(serializers.ModelSerializer):
    """ویرایش اطلاعات پایه (ایمیل قابل تغییر نیست)."""
    company_name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    national_id  = serializers.CharField(write_only=True, required=False, allow_blank=True)
    address      = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ["first_name", "last_name", "phone", "company_name", "national_id", "address"]

    def update(self, instance, validated_data):
        company_name = validated_data.pop("company_name", None)
        national_id  = validated_data.pop("national_id", None)
        address      = validated_data.pop("address", None)
        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        instance.save()
        profile, _ = UserProfile.objects.get_or_create(user=instance)
        if company_name is not None:
            profile.company_name = company_name
        if national_id is not None:
            profile.national_id = national_id
        if address is not None:
            profile.address = address
        profile.save()
        return instance


class ChangePasswordSerializer(serializers.Serializer):
    """تغییر رمز عبور توسط کاربر لاگین‌شده."""
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)
    new_password2 = serializers.CharField(write_only=True, label="تکرار رمز جدید")

    def validate(self, data):
        if data["new_password"] != data["new_password2"]:
            raise serializers.ValidationError({"new_password2": "رمزهای عبور مطابقت ندارند."})
        return data


# ─── Partner ──────────────────────────────────────────────────────────────────

class PartnerRegisterSerializer(serializers.Serializer):
    """درخواست ارتقاء حساب به همکار. is_approved=False تا تأیید ادمین."""
    company_name = serializers.CharField(max_length=255)
    national_id  = serializers.CharField(max_length=20)
    address      = serializers.CharField()

    def save(self, user: User):
        data = self.validated_data
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.user_type    = UserProfile.UserType.PARTNER
        profile.company_name = data["company_name"]
        profile.national_id  = data["national_id"]
        profile.address      = data["address"]
        profile.is_approved  = False
        profile.save()
        return user


# ─── Admin ────────────────────────────────────────────────────────────────────

class AdminPartnerListSerializer(serializers.ModelSerializer):
    user_id    = serializers.IntegerField(source="user.id")
    email      = serializers.EmailField(source="user.email")
    full_name  = serializers.CharField(source="user.get_full_name")
    phone      = serializers.CharField(source="user.phone")

    class Meta:
        model = UserProfile
        fields = ["user_id", "email", "full_name", "phone",
                  "company_name", "national_id", "is_approved",
                  "credit_limit", "address", "notes", "created_at"]
        read_only_fields = ["user_id", "email", "full_name", "phone", "created_at"]


class AdminApprovePartnerSerializer(serializers.Serializer):
    is_approved  = serializers.BooleanField()
    credit_limit = serializers.IntegerField(min_value=0, required=False, default=0)
    notes        = serializers.CharField(required=False, allow_blank=True)
