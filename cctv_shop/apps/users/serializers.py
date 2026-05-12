"""
apps/users/serializers.py
"""
from django.contrib.auth import authenticate
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User, UserProfile


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
    return {"refresh": str(refresh), "access": str(refresh.access_token)}


class RegisterSerializer(serializers.ModelSerializer):
    password  = serializers.CharField(write_only=True, min_length=8)
    password2 = serializers.CharField(write_only=True, label="تکرار رمز عبور")
    email     = serializers.EmailField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = User
        fields = ["phone", "email", "password", "password2", "first_name", "last_name"]

    def validate_phone(self, value):
        value = value.strip()
        if not value.startswith('09') or len(value) != 11:
            raise serializers.ValidationError("شماره موبایل معتبر نیست (مثال: 09123456789)")
        if User.objects.filter(phone=value).exists():
            raise serializers.ValidationError("این شماره موبایل قبلاً ثبت شده است.")
        return value

    def validate_email(self, value):
        if value and User.objects.filter(email=value).exists():
            raise serializers.ValidationError("این ایمیل قبلاً ثبت شده است.")
        return value or None

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
        UserProfile.objects.create(user=user, user_type=UserProfile.UserType.PUBLIC)
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
                  "is_approved", "discount_percent", "credit_limit", "address"]
        read_only_fields = ["user_type", "is_approved", "credit_limit"]


class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)
    is_partner = serializers.BooleanField(read_only=True)

    class Meta:
        model = User
        fields = ["id", "phone", "email", "first_name", "last_name",
                  "is_partner", "date_joined", "profile"]
        read_only_fields = ["phone", "date_joined"]


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
        if data["new_password"] != data["new_password2"]:
            raise serializers.ValidationError({"new_password2": "رمزهای عبور مطابقت ندارند."})
        return data


class PartnerRegisterSerializer(serializers.Serializer):
    company_name = serializers.CharField(max_length=255)
    national_id  = serializers.CharField(max_length=20, required=False, allow_blank=True)
    address      = serializers.CharField(required=False, allow_blank=True)

    def save(self, user: User):
        data = self.validated_data
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.user_type    = UserProfile.UserType.PARTNER
        profile.company_name = data["company_name"]
        profile.national_id  = data.get("national_id", "")
        profile.address      = data.get("address", "")
        profile.is_approved  = False
        profile.save()
        return user


class AdminPartnerListSerializer(serializers.ModelSerializer):
    user_id   = serializers.IntegerField(source="user.id")
    phone     = serializers.CharField(source="user.phone")
    email     = serializers.EmailField(source="user.email")
    full_name = serializers.CharField(source="user.get_full_name")

    class Meta:
        model = UserProfile
        fields = ["user_id", "phone", "email", "full_name",
                  "company_name", "national_id", "is_approved",
                  "discount_percent", "credit_limit", "address", "notes", "created_at"]
        read_only_fields = ["user_id", "phone", "email", "full_name", "created_at"]


class AdminApprovePartnerSerializer(serializers.Serializer):
    is_approved  = serializers.BooleanField()
    credit_limit = serializers.IntegerField(min_value=0, required=False, default=0)
    notes        = serializers.CharField(required=False, allow_blank=True)