import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

# اضافه کردن is_staff به UserSerializer
ser_path = os.path.join('apps', 'users', 'serializers.py')
with open(ser_path, encoding='utf-8') as f:
    content = f.read()

old = '''class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)
    is_partner = serializers.BooleanField(read_only=True)

    class Meta:
        model = User
        fields = ["id", "phone", "email", "first_name", "last_name",
                  "is_partner", "date_joined", "profile"]
        read_only_fields = ["phone", "date_joined"]'''

new = '''class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)
    is_partner = serializers.BooleanField(read_only=True)
    staff_role = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "phone", "email", "first_name", "last_name",
                  "is_partner", "is_staff", "date_joined", "profile", "staff_role"]
        read_only_fields = ["phone", "date_joined", "is_staff"]

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
            return None'''

if old in content:
    content = content.replace(old, new)
    with open(ser_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("✓ UserSerializer اصلاح شد")
else:
    print("✗ متن پیدا نشد")

import subprocess, sys
r = subprocess.run([sys.executable, 'manage.py', 'check', '--verbosity=0'], capture_output=True, text=True)
print("✓ check موفق" if r.returncode == 0 else r.stderr[-200:])
print("\nحالا logout کنید و دوباره login کنید تا is_staff در store ذخیره شود")
