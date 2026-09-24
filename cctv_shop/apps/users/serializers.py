"""
apps/users/serializers.py
"""
from datetime import timedelta
from django.contrib.auth import authenticate
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User, UserProfile


def validate_password_strength(password):
    """رمز باید حداقل ۸ کاراکتر و شامل حروف و عدد باشد (عدد خالی یا حرف خالی ممنوع)."""
    if not any(c.isalpha() for c in password) or not any(c.isdigit() for c in password):
        raise serializers.ValidationError("رمز عبور باید ترکیبی از حروف و عدد باشد (فقط عدد یا فقط حرف کافی نیست).")


def get_tokens_for_user(user: User) -> dict:
    refresh = RefreshToken.for_user(user)
    refresh["phone"] = str(user.phone or "")
    refresh["email"] = str(user.email or "")
    refresh["is_staff"] = bool(user.is_staff)
    try:
        refresh["user_type"] = str(user.profile.user_type)
        refresh["is_partner"] = bool(user.is_partner)
        refresh["is_approved"] = bool(user.profile.is_approved)
    except Exception:
        refresh["user_type"] = "public"
        refresh["is_partner"] = False
        refresh["is_approved"] = False

    access = refresh.access_token
    # پرسنل/ادمین: انقضای بیکاری — توکن دسترسی ۳۰ دقیقه‌ای (تازه‌سازی بی‌صدا در پنل)
    # و refresh ده‌ساعته؛ چون با rotation هر تازه‌سازی refresh جدید می‌گیرد،
    # ۱۰ ساعت از «آخرین فعالیت» شمرده می‌شود، نه از لاگین. مشتریان: ۱ روز / ۳۰ روز.
    if user.is_staff or user.is_superuser:
        refresh.set_exp(lifetime=STAFF_REFRESH_LIFETIME)
        access.set_exp(lifetime=STAFF_ACCESS_LIFETIME)
    return {"refresh": str(refresh), "access": str(access)}


STAFF_ACCESS_LIFETIME = timedelta(minutes=30)
STAFF_REFRESH_LIFETIME = timedelta(hours=10)


class RegisterSerializer(serializers.ModelSerializer):
    password  = serializers.CharField(write_only=True, min_length=8)
    password2 = serializers.CharField(write_only=True, label="تکرار رمز عبور")
    email     = serializers.EmailField(required=False, allow_blank=True, allow_null=True)
    first_name = serializers.CharField(required=True, allow_blank=False)
    last_name  = serializers.CharField(required=True, allow_blank=False)
    company_name = serializers.CharField(required=False, allow_blank=True, write_only=True)

    class Meta:
        model = User
        fields = ["phone", "email", "password", "password2", "first_name", "last_name", "company_name"]
        # UniqueValidator پیش‌فرض غیرفعال — تکراری بودن در validate_phone با پیام دقیق‌تر چک می‌شود
        extra_kwargs = {"phone": {"validators": []}}

    def validate_phone(self, value):
        value = value.strip()
        if any(ch in value for ch in "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩"):
            raise serializers.ValidationError("شماره موبایل را با اعداد انگلیسی وارد کنید.")
        if not value.startswith('09') or len(value) != 11:
            raise serializers.ValidationError("شماره موبایل معتبر نیست (مثال: 09123456789)")
        existing = User.objects.filter(phone=value).first()
        if existing:
            profile = getattr(existing, 'profile', None)
            if profile and profile.linked_contact_id and not existing.has_usable_password():
                raise serializers.ValidationError(
                    "حساب این شماره از قبل توسط فروشگاه ساخته شده است؛ برای فعال‌سازی و دریافت رمز عبور با فروشگاه تماس بگیرید.")
            raise serializers.ValidationError("این شماره موبایل قبلاً ثبت شده است.")
        return value

    def validate_email(self, value):
        if value and User.objects.filter(email=value).exists():
            raise serializers.ValidationError("این ایمیل قبلاً ثبت شده است.")
        return value or None

    def validate(self, data):
        validate_password_strength(data["password"])
        if data["password"] != data["password2"]:
            raise serializers.ValidationError({"password2": "رمزهای عبور مطابقت ندارند."})
        return data

    def create(self, validated_data):
        validated_data.pop("password2")
        password = validated_data.pop("password")
        company_name = validated_data.pop("company_name", "")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        UserProfile.objects.create(user=user, user_type=UserProfile.UserType.PUBLIC, company_name=company_name)
        return user


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(label="موبایل یا ایمیل")
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        username = data["username"].strip()
        password = data["password"]
        try:
            if username.startswith('09') and len(username) == 11:
                user_obj = User.objects.get(phone=username)
            else:
                user_obj = User.objects.get(email=username)
            user = authenticate(username=user_obj.phone, password=password)
        except User.DoesNotExist:
            user = None
        if not user:
            raise serializers.ValidationError("اطلاعات ورود اشتباه است.")
        if not user.is_active:
            raise serializers.ValidationError("حساب کاربری غیرفعال است.")
        data["user"] = user
        return data


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ["user_type", "company_name", "national_id",
                  "is_approved", "partner_tier", "discount_percent", "credit_limit", "address"]
        read_only_fields = ["user_type", "is_approved", "credit_limit"]


class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)
    is_partner = serializers.BooleanField(read_only=True)
    staff_role = serializers.SerializerMethodField()
    parent_account = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "phone", "email", "first_name", "last_name",
                  "is_partner", "is_staff", "is_superuser", "date_joined", "profile", "staff_role",
            "parent_account",]
        read_only_fields = ["phone", "date_joined", "is_staff", "is_superuser"]

    def get_parent_account(self, obj):
        try:
            profile = obj.profile
        except Exception:
            return None
        if profile and profile.parent_account_id:
            p = profile.parent_account
            return {"id": p.id, "name": p.get_full_name() or p.phone}
        return None

    def get_staff_role(self, obj):
        if not obj.is_staff:
            return None
        try:
            sp = obj.staff_profile
            return {
                "role_name": sp.role.name if sp.role else "",
                "permissions": sp.role.permissions if sp.role else [],
            }
        except Exception:
            if obj.is_superuser:
                return {"role_name": "ادمین", "permissions": ["all"]}
            return None


class UserUpdateSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    national_id  = serializers.CharField(write_only=True, required=False, allow_blank=True)
    address      = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "company_name", "national_id", "address"]

    def update(self, instance, validated_data):
        company_name = validated_data.pop("company_name", None)
        national_id  = validated_data.pop("national_id", None)
        address      = validated_data.pop("address", None)
        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        instance.save()
        profile, _ = UserProfile.objects.get_or_create(user=instance)
        if company_name is not None: profile.company_name = company_name
        if national_id is not None:  profile.national_id = national_id
        if address is not None:       profile.address = address
        profile.save()
        return instance


class ChangePasswordSerializer(serializers.Serializer):
    old_password  = serializers.CharField(write_only=True)
    new_password  = serializers.CharField(write_only=True, min_length=8)
    new_password2 = serializers.CharField(write_only=True, label="تکرار رمز جدید")

    def validate(self, data):
        validate_password_strength(data["new_password"])
        if data["new_password"] != data["new_password2"]:
            raise serializers.ValidationError({"new_password2": "رمزهای عبور مطابقت ندارند."})
        return data


class PartnerRegisterSerializer(serializers.Serializer):
    """درخواست همکاری — پشتیبانی از نصاب‌های مستقل.

    نام فروشگاه/شرکت/برند شخصی اجباری است (نصاب مستقل نام برند شخصی‌اش را می‌نویسد)؛
    «تصویر کارت ویزیت یا عکس صفحه ادمین پیج» برای بررسی درخواست اجباری است.
    آدرس برای ارسال بار اجباری است.
    """
    company_name = serializers.CharField(max_length=255, required=True, allow_blank=False)
    national_id  = serializers.CharField(max_length=20, required=False, allow_blank=True)
    address      = serializers.CharField(required=True, allow_blank=False)
    social_url   = serializers.CharField(max_length=255, required=False, allow_blank=True)
    document     = serializers.ImageField(required=True)

    def save(self, user: User):
        data = self.validated_data
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.user_type    = UserProfile.UserType.PARTNER
        profile.company_name = data.get("company_name", "")
        profile.national_id  = data.get("national_id", "")
        profile.address      = data["address"]
        profile.social_url   = data.get("social_url", "")
        if data.get("document"):
            profile.document = data["document"]
        profile.is_approved  = False
        profile.save()
        return user


class AdminPartnerListSerializer(serializers.ModelSerializer):
    user_id   = serializers.IntegerField(source="user.id")
    phone     = serializers.CharField(source="user.phone")
    email     = serializers.EmailField(source="user.email")
    full_name = serializers.CharField(source="user.get_full_name")
    document_url = serializers.SerializerMethodField()
    signup_source = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        fields = ["user_id", "phone", "email", "full_name",
                  "company_name", "national_id", "social_url", "document_url",
                  "is_approved", "partner_tier", "signup_source",
                  "discount_percent", "credit_limit", "address", "notes", "created_at", "updated_at"]
        read_only_fields = ["user_id", "phone", "email", "full_name", "created_at", "updated_at"]

    def get_signup_source(self, obj):
        # کاربر سایه (ساخته‌شده از پنل برای لینک فاکتور) پسورد قابل‌استفاده ندارد
        return "self" if obj.user.has_usable_password() else "admin"

    def get_document_url(self, obj):
        if not obj.document:
            return None
        url = obj.document.url
        request = self.context.get("request")
        return request.build_absolute_uri(url) if request else url


class AdminApprovePartnerSerializer(serializers.Serializer):
    is_approved  = serializers.BooleanField()
    credit_limit = serializers.IntegerField(min_value=0, required=False, default=0)
    notes        = serializers.CharField(required=False, allow_blank=True)
    partner_tier = serializers.ChoiceField(
        choices=["silver", "gold", "platinum"], required=False, allow_blank=True,
    )


class ClubSettingsSerializer(serializers.Serializer):
    silver_to_gold_amount = serializers.IntegerField(min_value=0)
    gold_to_platinum_amount = serializers.IntegerField(min_value=0)
    period_months = serializers.IntegerField(min_value=1, max_value=36)
    auto_evaluate_enabled = serializers.BooleanField(required=False, default=True)
    overdue_warn_workdays = serializers.IntegerField(min_value=1, max_value=30, required=False, default=3)
    overdue_cash_only_days = serializers.IntegerField(min_value=1, max_value=60, required=False, default=7)
    tier_benefits_silver = serializers.CharField(required=False, allow_blank=True)
    tier_benefits_gold = serializers.CharField(required=False, allow_blank=True)
    tier_benefits_platinum = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        if data["gold_to_platinum_amount"] < data["silver_to_gold_amount"]:
            raise serializers.ValidationError({
                "gold_to_platinum_amount": "آستانه پلاتینیوم نمی‌تواند کمتر از آستانه گلد باشد."
            })
        return data


class GuaranteeSerializer(serializers.ModelSerializer):
    """تضمین همکار برای فروش اعتباری — ثبت/مشاهده توسط ادمین."""
    guarantee_type_display = serializers.CharField(source="get_guarantee_type_display", read_only=True)
    document_url = serializers.SerializerMethodField()

    class Meta:
        from .models import PartnerGuarantee
        model = PartnerGuarantee
        fields = ["id", "guarantee_type", "guarantee_type_display",
                  "amount_rials", "description", "document", "document_url", "created_at"]
        read_only_fields = ["id", "created_at"]

    def get_document_url(self, obj):
        if not obj.document:
            return None
        url = obj.document.url
        request = self.context.get("request")
        return request.build_absolute_uri(url) if request else url