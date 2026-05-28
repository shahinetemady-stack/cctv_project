"""
python setup_rbac.py
سیستم مدیریت نقش و دسترسی
اجرا در پوشه cctv_shop
"""
import os, sys, subprocess

# ─── 1. اضافه کردن مدل‌های Role و Permission به users/models.py ──
models_path = os.path.join('apps', 'users', 'models.py')
with open(models_path, encoding='utf-8') as f:
    content = f.read()

rbac_models = '''

# ─── RBAC ────────────────────────────────────────────────────

PERMISSIONS = [
    # فروش
    ('sale_view',        'مشاهده فاکتورهای فروش'),
    ('sale_create',      'صدور فاکتور فروش'),
    ('sale_payment',     'ثبت پرداخت مشتری'),
    # کاردکس و انبار
    ('kardex_view',      'مشاهده کاردکس'),
    ('kardex_edit',      'ثبت ورود/خروج موجودی'),
    # خرید
    ('purchase_view',    'مشاهده فاکتورهای خرید'),
    ('purchase_create',  'ثبت فاکتور خرید'),
    # طرف حساب
    ('contacts_view',    'مشاهده طرف حساب‌ها'),
    ('contacts_edit',    'ویرایش طرف حساب‌ها'),
    # گزارشات مالی
    ('reports_view',     'مشاهده گزارشات مالی'),
    ('balance_view',     'مشاهده تراز و سود/زیان'),
    # مدیریت کاربران
    ('users_view',       'مشاهده کاربران'),
    ('users_edit',       'ویرایش کاربران و نقش‌ها'),
    # محصولات
    ('products_view',    'مشاهده محصولات'),
    ('products_edit',    'ویرایش محصولات'),
    # داشبورد
    ('dashboard_view',   'مشاهده داشبورد'),
]

PERMISSION_CHOICES = [(k, v) for k, v in PERMISSIONS]


class Role(models.Model):
    """نقش کاربری"""
    name        = models.CharField(max_length=50, unique=True, verbose_name="نام نقش")
    description = models.CharField(max_length=200, blank=True, verbose_name="توضیح")
    permissions = models.JSONField(default=list, verbose_name="دسترسی‌ها",
                    help_text="لیست کدهای دسترسی")
    is_active   = models.BooleanField(default=True, verbose_name="فعال")
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "users_role"
        verbose_name = "نقش"
        verbose_name_plural = "نقش‌ها"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def has_perm(self, perm_code):
        return perm_code in self.permissions

    def perm_count(self):
        return len(self.permissions)


class StaffProfile(models.Model):
    """پروفایل پرسنل — نقش و دسترسی"""
    user       = models.OneToOneField(User, on_delete=models.CASCADE,
                    related_name="staff_profile", verbose_name="کاربر")
    role       = models.ForeignKey(Role, on_delete=models.SET_NULL,
                    null=True, blank=True, related_name="staff_members",
                    verbose_name="نقش")
    employee_id = models.CharField(max_length=20, blank=True, verbose_name="کد پرسنلی")
    department  = models.CharField(max_length=100, blank=True, verbose_name="بخش")
    is_active   = models.BooleanField(default=True, verbose_name="فعال")
    note        = models.TextField(blank=True, verbose_name="توضیحات")
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "users_staff_profile"
        verbose_name = "پرسنل"
        verbose_name_plural = "پرسنل"

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.phone} — {self.role}"

    def has_perm(self, perm_code):
        """چک دسترسی — superuser همه چیز دارد"""
        if self.user.is_superuser:
            return True
        if not self.role or not self.role.is_active:
            return False
        return self.role.has_perm(perm_code)
'''

if 'class Role' not in content:
    content += rbac_models
    with open(models_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("✓ Role و StaffProfile اضافه شد")
else:
    print("✓ قبلاً موجود بود")

# ─── 2. migration ─────────────────────────────────────────────
r = subprocess.run([sys.executable, 'manage.py', 'makemigrations', 'users'],
                   capture_output=True, text=True)
print(r.stdout[-300:] if r.stdout else "")
if r.returncode != 0:
    print("خطا:"); print(r.stderr[-400:])
else:
    r2 = subprocess.run([sys.executable, 'manage.py', 'migrate'],
                        capture_output=True, text=True)
    print(r2.stdout[-200:] if r2.stdout else "")

# ─── 3. ساخت نقش‌های پیش‌فرض ─────────────────────────────────
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.users.models import Role

default_roles = [
    {
        'name': 'ادمین',
        'description': 'دسترسی کامل به همه بخش‌ها',
        'permissions': [p[0] for p in [
            ('sale_view',''), ('sale_create',''), ('sale_payment',''),
            ('kardex_view',''), ('kardex_edit',''),
            ('purchase_view',''), ('purchase_create',''),
            ('contacts_view',''), ('contacts_edit',''),
            ('reports_view',''), ('balance_view',''),
            ('users_view',''), ('users_edit',''),
            ('products_view',''), ('products_edit',''),
            ('dashboard_view',''),
        ]],
    },
    {
        'name': 'فروشنده',
        'description': 'فاکتور فروش و مشتریان',
        'permissions': ['sale_view', 'sale_create', 'sale_payment',
                        'contacts_view', 'products_view', 'dashboard_view'],
    },
    {
        'name': 'انباردار',
        'description': 'کاردکس و موجودی انبار',
        'permissions': ['kardex_view', 'kardex_edit',
                        'products_view', 'dashboard_view'],
    },
    {
        'name': 'حسابدار',
        'description': 'گزارشات مالی و تراز',
        'permissions': ['reports_view', 'balance_view',
                        'sale_view', 'purchase_view',
                        'contacts_view', 'dashboard_view'],
    },
    {
        'name': 'مدیر فروش',
        'description': 'فروش + خرید + گزارشات',
        'permissions': ['sale_view', 'sale_create', 'sale_payment',
                        'purchase_view', 'purchase_create',
                        'contacts_view', 'contacts_edit',
                        'reports_view', 'products_view', 'dashboard_view'],
    },
]

for role_data in default_roles:
    role, created = Role.objects.get_or_create(
        name=role_data['name'],
        defaults={
            'description': role_data['description'],
            'permissions': role_data['permissions'],
        }
    )
    if created:
        print(f"✓ نقش '{role.name}' ساخته شد")
    else:
        print(f"  نقش '{role.name}' قبلاً موجود بود")

# ─── 4. views و urls برای RBAC API ───────────────────────────
rbac_views = '''

# ─── RBAC Views ──────────────────────────────────────────────

class RoleListView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        from apps.users.models import Role, PERMISSIONS
        roles = Role.objects.all()
        return Response({
            'roles': [{
                'id': r.id,
                'name': r.name,
                'description': r.description,
                'permissions': r.permissions,
                'perm_count': r.perm_count(),
                'staff_count': r.staff_members.filter(is_active=True).count(),
                'is_active': r.is_active,
            } for r in roles],
            'all_permissions': [{'code': k, 'label': v} for k, v in PERMISSIONS],
        })

    def post(self, request):
        from apps.users.models import Role
        d = request.data
        r = Role.objects.create(
            name=d['name'],
            description=d.get('description', ''),
            permissions=d.get('permissions', []),
        )
        return Response({'id': r.id, 'name': r.name}, status=201)


class RoleDetailView(APIView):
    permission_classes = [IsAdminUser]

    def patch(self, request, pk):
        from apps.users.models import Role
        try:
            role = Role.objects.get(pk=pk)
        except Role.DoesNotExist:
            return Response({'error': 'یافت نشد'}, status=404)
        if 'name' in request.data:
            role.name = request.data['name']
        if 'description' in request.data:
            role.description = request.data['description']
        if 'permissions' in request.data:
            role.permissions = request.data['permissions']
        if 'is_active' in request.data:
            role.is_active = request.data['is_active']
        role.save()
        return Response({'id': role.id, 'name': role.name, 'permissions': role.permissions})

    def delete(self, request, pk):
        from apps.users.models import Role
        try:
            role = Role.objects.get(pk=pk)
            role.delete()
            return Response({'deleted': True})
        except Role.DoesNotExist:
            return Response({'error': 'یافت نشد'}, status=404)


class StaffListView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        from apps.users.models import StaffProfile, Role
        staff = StaffProfile.objects.select_related('user', 'role').filter(is_active=True)
        return Response([{
            'id': s.id,
            'user_id': s.user_id,
            'name': s.user.get_full_name() or s.user.phone,
            'phone': s.user.phone,
            'role_id': s.role_id,
            'role_name': s.role.name if s.role else '',
            'employee_id': s.employee_id,
            'department': s.department,
            'is_active': s.is_active,
        } for s in staff])

    def post(self, request):
        from apps.users.models import StaffProfile, User
        d = request.data
        try:
            user = User.objects.get(id=d['user_id'])
            staff, created = StaffProfile.objects.get_or_create(
                user=user,
                defaults={
                    'role_id': d.get('role_id') or None,
                    'employee_id': d.get('employee_id', ''),
                    'department': d.get('department', ''),
                }
            )
            if not created:
                if d.get('role_id'):
                    staff.role_id = d['role_id']
                staff.employee_id = d.get('employee_id', staff.employee_id)
                staff.department = d.get('department', staff.department)
                staff.is_active = True
                staff.save()
            # is_staff را فعال کن
            user.is_staff = True
            user.save(update_fields=['is_staff'])
            return Response({'id': staff.id, 'message': 'پرسنل ثبت شد'}, status=201)
        except User.DoesNotExist:
            return Response({'error': 'کاربر یافت نشد'}, status=404)
        except Exception as e:
            return Response({'error': str(e)}, status=400)


class StaffDetailView(APIView):
    permission_classes = [IsAdminUser]

    def patch(self, request, pk):
        from apps.users.models import StaffProfile
        try:
            staff = StaffProfile.objects.get(pk=pk)
        except StaffProfile.DoesNotExist:
            return Response({'error': 'یافت نشد'}, status=404)
        if 'role_id' in request.data:
            staff.role_id = request.data['role_id'] or None
        if 'employee_id' in request.data:
            staff.employee_id = request.data['employee_id']
        if 'department' in request.data:
            staff.department = request.data['department']
        if 'is_active' in request.data:
            staff.is_active = request.data['is_active']
        staff.save()
        return Response({'id': staff.id})


class MyPermissionsView(APIView):
    """دسترسی‌های کاربر جاری"""
    permission_classes = [IsAdminUser]

    def get(self, request):
        if request.user.is_superuser:
            from apps.users.models import PERMISSIONS
            return Response({
                'is_superuser': True,
                'permissions': [p[0] for p in PERMISSIONS],
            })
        try:
            staff = request.user.staff_profile
            return Response({
                'is_superuser': False,
                'role': staff.role.name if staff.role else '',
                'permissions': staff.role.permissions if staff.role else [],
            })
        except Exception:
            return Response({'permissions': [], 'role': ''})
'''

# اضافه کردن به accounting/views.py
acc_views_path = os.path.join('apps', 'accounting', 'views.py')
with open(acc_views_path, encoding='utf-8') as f:
    acc_views = f.read()

if 'RoleListView' not in acc_views:
    acc_views += rbac_views
    with open(acc_views_path, 'w', encoding='utf-8') as f:
        f.write(acc_views)
    print("✓ RBAC views اضافه شد")

# ─── 5. URLs ──────────────────────────────────────────────────
acc_urls_path = os.path.join('apps', 'accounting', 'urls.py')
with open(acc_urls_path, encoding='utf-8') as f:
    acc_urls = f.read()

new_urls = [
    ("roles/", "RoleListView"),
    ("roles/<int:pk>/", "RoleDetailView"),
    ("staff/", "StaffListView"),
    ("staff/<int:pk>/", "StaffDetailView"),
    ("my-permissions/", "MyPermissionsView"),
]

added = []
for path_str, view_name in new_urls:
    if path_str not in acc_urls:
        added.append(f"    path('{path_str}', views.{view_name}.as_view()),")

if added:
    acc_urls = acc_urls.rstrip()
    if acc_urls.endswith(']'):
        acc_urls = acc_urls[:-1] + ',\n' + '\n'.join(added) + '\n]'
    with open(acc_urls_path, 'w', encoding='utf-8') as f:
        f.write(acc_urls)
    print(f"✓ {len(added)} URL اضافه شد")

r3 = subprocess.run([sys.executable, 'manage.py', 'check', '--verbosity=0'],
                    capture_output=True, text=True)
if r3.returncode == 0:
    print("✓ check موفق — سرور را restart کنید")
else:
    print(r3.stderr[-400:])
