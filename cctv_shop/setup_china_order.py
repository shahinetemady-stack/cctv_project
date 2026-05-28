"""
python setup_china_order.py
سیستم درخواست سفارش مستقیم از چین
"""
import os, sys, subprocess

# ─── 1. اضافه کردن مدل به orders/models.py ───────────────────
models_path = os.path.join('apps', 'orders', 'models.py')
with open(models_path, encoding='utf-8') as f:
    content = f.read()

china_model = '''

class ChinaOrderRequest(models.Model):
    """درخواست سفارش مستقیم از چین"""

    class Status(models.TextChoices):
        PENDING   = "pending",   "در انتظار بررسی"
        REVIEWING = "reviewing", "در حال بررسی"
        APPROVED  = "approved",  "تأیید شده"
        REJECTED  = "rejected",  "رد شده"

    # اطلاعات درخواست‌دهنده
    name        = models.CharField(max_length=100, verbose_name="نام و نام خانوادگی")
    phone       = models.CharField(max_length=20, verbose_name="شماره تماس")
    email       = models.EmailField(blank=True, verbose_name="ایمیل")
    user        = models.ForeignKey(
        'users.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='china_requests', verbose_name="کاربر"
    )

    # اطلاعات کالا
    product_name = models.CharField(max_length=300, verbose_name="نام کالا")
    quantity     = models.PositiveIntegerField(verbose_name="تعداد")
    description  = models.TextField(blank=True, verbose_name="توضیحات")
    product_link = models.URLField(blank=True, verbose_name="لینک کالا (اختیاری)")

    # وضعیت
    status      = models.CharField(max_length=20, choices=Status.choices,
                    default=Status.PENDING, verbose_name="وضعیت")
    admin_note  = models.TextField(blank=True, verbose_name="یادداشت ادمین")
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "orders_china_request"
        verbose_name = "درخواست از چین"
        verbose_name_plural = "درخواست‌های از چین"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} | {self.product_name} × {self.quantity}"
'''

if 'ChinaOrderRequest' not in content:
    content += china_model
    with open(models_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("✓ مدل ChinaOrderRequest اضافه شد")
else:
    print("✓ قبلاً موجود بود")

# ─── 2. Migration ─────────────────────────────────────────────
r = subprocess.run([sys.executable, 'manage.py', 'makemigrations', 'orders'],
                   capture_output=True, text=True)
print(r.stdout[-200:] if r.stdout else "")
if r.returncode != 0:
    print("خطا:"); print(r.stderr[-400:])
else:
    r2 = subprocess.run([sys.executable, 'manage.py', 'migrate'],
                        capture_output=True, text=True)
    print(r2.stdout[-200:] if r2.stdout else "")

# ─── 3. Admin ─────────────────────────────────────────────────
orders_admin = os.path.join('apps', 'orders', 'admin.py')
with open(orders_admin, encoding='utf-8') as f:
    admin_content = f.read()

if 'ChinaOrderRequest' not in admin_content:
    admin_content += '''

from apps.orders.models import ChinaOrderRequest

@admin.register(ChinaOrderRequest)
class ChinaOrderRequestAdmin(admin.ModelAdmin):
    list_display  = ["name", "phone", "product_name", "quantity", "status", "created_at"]
    list_filter   = ["status", "created_at"]
    search_fields = ["name", "phone", "product_name"]
    list_editable = ["status"]
    readonly_fields = ["created_at", "updated_at", "user"]
    fieldsets = (
        ("اطلاعات درخواست‌دهنده", {"fields": ("name", "phone", "email", "user")}),
        ("اطلاعات کالا", {"fields": ("product_name", "quantity", "description", "product_link")}),
        ("وضعیت", {"fields": ("status", "admin_note")}),
        ("تاریخ‌ها", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )
'''
    with open(orders_admin, 'w', encoding='utf-8') as f:
        f.write(admin_content)
    print("✓ ChinaOrderRequestAdmin اضافه شد")

# ─── 4. View ──────────────────────────────────────────────────
# اضافه کردن به orders/views.py یا یک فایل جداگانه
views_path = os.path.join('apps', 'orders', 'views.py')
with open(views_path, encoding='utf-8') as f:
    views = f.read()

china_view = '''

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
            'created_at': r.created_at.strftime('%Y-%m-%d %H:%M'),
        } for r in reqs])
'''

if 'ChinaOrderRequestView' not in views:
    # اضافه کردن AllowAny import اگر نبود
    if 'AllowAny' not in views:
        views = views.replace(
            'from rest_framework.permissions import',
            'from rest_framework.permissions import AllowAny,'
        )
    if 'from rest_framework.views import APIView' not in views:
        views = 'from rest_framework.views import APIView\n' + views
    if 'from rest_framework.response import Response' not in views:
        views = 'from rest_framework.response import Response\n' + views
    views += china_view
    with open(views_path, 'w', encoding='utf-8') as f:
        f.write(views)
    print("✓ ChinaOrderRequestView اضافه شد")

# ─── 5. URL ───────────────────────────────────────────────────
urls_path = os.path.join('apps', 'orders', 'urls.py')
with open(urls_path, encoding='utf-8') as f:
    urls = f.read()

if 'china-request' not in urls:
    # پیدا کردن urlpatterns
    idx = urls.rfind(']')
    new_url = "    path('china-request/', views.ChinaOrderRequestView.as_view()),\n"
    urls = urls[:idx] + new_url + urls[idx:]
    with open(urls_path, 'w', encoding='utf-8') as f:
        f.write(urls)
    print("✓ URL اضافه شد")

r3 = subprocess.run([sys.executable, 'manage.py', 'check', '--verbosity=0'],
                    capture_output=True, text=True)
print("✓ check موفق" if r3.returncode == 0 else r3.stderr[-300:])
