import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

views_path = os.path.join('apps', 'accounting', 'views.py')
with open(views_path, encoding='utf-8') as f:
    content = f.read()

# اصلاح CustomerSearchView — اضافه کردن نام کامل
old = '''    def get(self, request):
        from apps.users.models import User
        q = request.query_params.get('q', '')
        if len(q) < 2:
            return Response([])
        users = User.objects.filter(
            models.Q(phone__icontains=q) |
            models.Q(first_name__icontains=q) |
            models.Q(last_name__icontains=q)
        )[:10]
        return Response([{
            'id': u.id,
            'name': str(u),
            'phone': u.phone,
        } for u in users])'''

new = '''    def get(self, request):
        from apps.users.models import User
        from django.db.models import Q, Value
        from django.db.models.functions import Concat
        q = request.query_params.get('q', '')
        if len(q) < 2:
            return Response([])
        users = User.objects.filter(
            Q(phone__icontains=q) |
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q)
        )[:15]
        data = []
        for u in users:
            full_name = f"{u.first_name} {u.last_name}".strip() or str(u)
            data.append({
                'id': u.id,
                'name': full_name,
                'phone': getattr(u, 'phone', ''),
                'display': f"{full_name} | {getattr(u, 'phone', '')}",
            })
        return Response(data)'''

if old in content:
    content = content.replace(old, new)
    with open(views_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("✓ CustomerSearchView اصلاح شد")
else:
    print("✗ متن پیدا نشد")

# اضافه کردن endpoint قیمت variant
variant_price_view = '''

class VariantPriceView(APIView):
    """GET /api/accounting/variant-price/<variant_id>/ — قیمت فروش کالا"""
    permission_classes = [IsAdminUser]

    def get(self, request, variant_id):
        from apps.catalog.models import ProductVariant
        try:
            v = ProductVariant.objects.get(id=variant_id, is_active=True)
            # قیمت عمومی سایت
            public_price = v.final_price

            # قیمت همکار (اگر کاربر همکار است)
            partner_price = None
            if request.user.is_authenticated:
                try:
                    disc = float(request.user.profile.discount_percent or 0)
                    if disc > 0:
                        import math
                        partner_price = math.ceil(public_price * (1 - disc / 100))
                except Exception:
                    pass

            return Response({
                'variant_id': variant_id,
                'sku': v.sku,
                'public_price': public_price,
                'partner_price': partner_price,
                'suggested_price': partner_price or public_price,
            })
        except ProductVariant.DoesNotExist:
            return Response({'error': 'یافت نشد'}, status=404)
'''

if 'VariantPriceView' not in content:
    content += variant_price_view
    with open(views_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("✓ VariantPriceView اضافه شد")

# اضافه کردن URL
urls_path = os.path.join('apps', 'accounting', 'urls.py')
with open(urls_path, encoding='utf-8') as f:
    urls = f.read()

if 'variant-price' not in urls:
    urls = urls.replace(
        "path('customers/search/', views.CustomerSearchView.as_view()),",
        "path('customers/search/', views.CustomerSearchView.as_view()),\n    path('variant-price/<int:variant_id>/', views.VariantPriceView.as_view()),"
    )
    with open(urls_path, 'w', encoding='utf-8') as f:
        f.write(urls)
    print("✓ URL variant-price اضافه شد")

import subprocess, sys
r = subprocess.run([sys.executable, 'manage.py', 'check', '--verbosity=0'], capture_output=True, text=True)
if r.returncode == 0:
    print("✓ check موفق — سرور را restart کنید")
else:
    print(r.stderr[-300:])
