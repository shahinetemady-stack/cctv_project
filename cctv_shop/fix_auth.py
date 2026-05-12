"""
python fix_auth.py
۱. موبایل اجباری، ایمیل اختیاری در ثبت‌نام
۲. ورود با موبایل یا ایمیل
"""
import os, subprocess, sys

print("اصلاح سیستم احراز هویت ...")

# ─── 1. User model: phone اجباری، email اختیاری ──────────
users_path = os.path.join('apps','users','models.py')
with open(users_path, encoding='utf-8') as f:
    content = f.read()

old = '''    email = models.EmailField(unique=True, verbose_name="ایمیل")
    first_name = models.CharField(max_length=100, blank=True, verbose_name="نام")
    last_name = models.CharField(max_length=100, blank=True, verbose_name="نام خانوادگی")
    phone = models.CharField(
        max_length=15, blank=True, verbose_name="شماره موبایل",
        help_text="اختیاری",
    )'''

new = '''    email = models.EmailField(unique=True, null=True, blank=True, verbose_name="ایمیل")
    first_name = models.CharField(max_length=100, blank=True, verbose_name="نام")
    last_name = models.CharField(max_length=100, blank=True, verbose_name="نام خانوادگی")
    phone = models.CharField(
        max_length=15, unique=True, verbose_name="شماره موبایل",
        help_text="اجباری — با آن وارد شوید",
    )'''

content = content.replace(old, new)

# USERNAME_FIELD را به phone تغییر بده
old2 = '    USERNAME_FIELD = "email"'
new2 = '    USERNAME_FIELD = "phone"'
content = content.replace(old2, new2)

# UserManager: از phone استفاده کن
old3 = '''    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("ایمیل الزامی است.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)'''
new3 = '''    def _create_user(self, phone, password, **extra_fields):
        if not phone:
            raise ValueError("شماره موبایل الزامی است.")
        user = self.model(phone=phone, **extra_fields)'''
content = content.replace(old3, new3)

old4 = '''    def create_user(self, email, password=None, **extra_fields):'''
new4 = '''    def create_user(self, phone, password=None, **extra_fields):'''
content = content.replace(old4, new4)

old5 = '''        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):'''
new5 = '''        return self._create_user(phone, password, **extra_fields)

    def create_superuser(self, phone, password, **extra_fields):'''
content = content.replace(old5, new5)

old6 = '        return self._create_user(email, password, **extra_fields)\n\n\nclass User'
new6 = '        return self._create_user(phone, password, **extra_fields)\n\n\nclass User'
content = content.replace(old6, new6)

with open(users_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("  OK - users/models.py")

# ─── 2. serializers.py: phone اجباری، email اختیاری ──────
ser_path = os.path.join('apps','users','serializers.py')
with open(ser_path, encoding='utf-8') as f:
    content = f.read()

old = '''class RegisterSerializer(serializers.ModelSerializer):
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
        return user'''

new = '''class RegisterSerializer(serializers.ModelSerializer):
    """ثبت‌نام با شماره موبایل (اجباری) + رمز عبور. ایمیل اختیاری."""
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
        return user'''

content = content.replace(old, new)

# ورود با موبایل یا ایمیل
old2 = '''class LoginSerializer(serializers.Serializer):
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
        return data'''

new2 = '''class LoginSerializer(serializers.Serializer):
    """ورود با شماره موبایل یا ایمیل + رمز عبور."""
    username = serializers.CharField(label="موبایل یا ایمیل")
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        username = data["username"].strip()
        password = data["password"]
        # تشخیص موبایل یا ایمیل
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
        return data'''

content = content.replace(old2, new2)

# PartnerRegisterSerializer: کد ملی اختیاری
old3 = '''class PartnerRegisterSerializer(serializers.Serializer):
    """درخواست ارتقاء حساب به همکار. is_approved=False تا تأیید ادمین."""
    company_name = serializers.CharField(max_length=255)
    national_id  = serializers.CharField(max_length=20)
    address      = serializers.CharField()'''

new3 = '''class PartnerRegisterSerializer(serializers.Serializer):
    """درخواست ارتقاء حساب به همکار. is_approved=False تا تأیید ادمین."""
    company_name = serializers.CharField(max_length=255)
    national_id  = serializers.CharField(max_length=20, required=False, allow_blank=True)
    address      = serializers.CharField(required=False, allow_blank=True)'''

content = content.replace(old3, new3)

with open(ser_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("  OK - users/serializers.py")

# ─── 3. migration ──────────────────────────────────────────
migration = '''from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ("users", "0003_merge_20260505_1907"),
    ]
    operations = [
        migrations.AlterField(
            model_name="user",
            name="email",
            field=models.EmailField(blank=True, null=True, unique=True, verbose_name="ایمیل"),
        ),
        migrations.AlterField(
            model_name="user",
            name="phone",
            field=models.CharField(max_length=15, unique=True, verbose_name="شماره موبایل"),
        ),
    ]
'''

mig_path = os.path.join('apps','users','migrations','0004_phone_required.py')
with open(mig_path, 'w', encoding='utf-8') as f:
    f.write(migration)
print("  OK - migration")

# ─── 4. migrate ────────────────────────────────────────────
r = subprocess.run([sys.executable,'manage.py','migrate','--verbosity=0'],
                   capture_output=True, text=True)
if r.returncode == 0:
    print("  OK - migrate موفق")
else:
    for line in (r.stdout+r.stderr).strip().split('\n')[-6:]:
        if line.strip(): print(" ", line)

r2 = subprocess.run([sys.executable,'manage.py','check','--verbosity=0'],
                    capture_output=True, text=True)
print("  OK - check" if r2.returncode == 0 else "  خطا در check")

print("\nتمام! حالا بزنید: python manage.py runserver")
