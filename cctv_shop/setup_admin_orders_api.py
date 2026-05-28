import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

# ─── اضافه کردن views ────────────────────────────────────────
views_path = os.path.join('apps', 'orders', 'views.py')
with open(views_path, encoding='utf-8') as f:
    views = f.read()

admin_views = '''

class AdminOrderListView(APIView):
    """GET /api/orders/admin/orders/ — لیست سفارشات برای ادمین"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not request.user.is_staff:
            return Response({'error': 'دسترسی ندارید'}, status=403)
        from .models import Order
        qs = Order.objects.select_related('user').order_by('-created_at')

        status = request.query_params.get('status')
        delivery = request.query_params.get('delivery_status')
        if status:
            qs = qs.filter(status=status)
        if delivery:
            qs = qs.filter(delivery_status=delivery)

        return Response([{
            'order_number': o.order_number,
            'user_name': o.user.get_full_name() or '',
            'user_phone': o.user.phone or '',
            'status': o.status,
            'total_amount': o.total_amount,
            'delivery_status': getattr(o, 'delivery_status', 'pending') or 'pending',
            'courier_company': getattr(o, 'courier_company', '') or '',
            'tracking_code': o.tracking_code or '',
            'shipping_address': o.shipping_address or '',
            'created_at': o.created_at.strftime('%Y-%m-%d %H:%M'),
        } for o in qs[:200]])


class AdminOrderUpdateView(APIView):
    """PATCH /api/orders/admin/<order_number>/update/ — آپدیت وضعیت سفارش"""
    permission_classes = [IsAuthenticated]

    def patch(self, request, order_number):
        if not request.user.is_staff:
            return Response({'error': 'دسترسی ندارید'}, status=403)
        from .models import Order
        from django.utils import timezone
        try:
            order = Order.objects.get(order_number=order_number)
        except Order.DoesNotExist:
            return Response({'error': 'سفارش یافت نشد'}, status=404)

        d = request.data
        allowed = ['status', 'delivery_status', 'courier_company', 'tracking_code']
        for field in allowed:
            if field in d:
                setattr(order, field, d[field])

        # تنظیم خودکار تاریخ ارسال
        if d.get('delivery_status') == 'shipped' and not getattr(order, 'shipped_at', None):
            order.shipped_at = timezone.now()
        if d.get('delivery_status') == 'delivered' and not getattr(order, 'delivered_at', None):
            order.delivered_at = timezone.now()

        order.save()
        return Response({'ok': True, 'order_number': order.order_number})
'''

if 'AdminOrderUpdateView' not in views:
    # اضافه کردن IsAuthenticated import
    if 'IsAuthenticated' not in views:
        views = views.replace(
            'from rest_framework.permissions import AllowAny',
            'from rest_framework.permissions import AllowAny, IsAuthenticated'
        )
    views += admin_views
    with open(views_path, 'w', encoding='utf-8') as f:
        f.write(views)
    print("✓ Admin views اضافه شد")

# ─── آپدیت URLs ───────────────────────────────────────────────
urls_path = os.path.join('apps', 'orders', 'urls.py')
with open(urls_path, encoding='utf-8') as f:
    urls = f.read()

if 'admin/orders/' not in urls:
    idx = urls.rfind(']')
    urls = urls[:idx] + \
        "    path('admin/orders/', views.AdminOrderListView.as_view()),\n" + \
        "    path('admin/<str:order_number>/update/', views.AdminOrderUpdateView.as_view()),\n" + \
        urls[idx:]
    with open(urls_path, 'w', encoding='utf-8') as f:
        f.write(urls)
    print("✓ Admin URLs اضافه شد")

import subprocess, sys
r = subprocess.run([sys.executable, 'manage.py', 'check', '--verbosity=0'],
                   capture_output=True, text=True)
print("✓ check موفق" if r.returncode == 0 else r.stderr[-300:])
print("\nسرور را restart کنید")
