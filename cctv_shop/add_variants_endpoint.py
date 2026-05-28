"""
python add_variants_endpoint.py
اجرا در پوشه cctv_shop
اضافه کردن endpoint لیست variants برای کاردکس
"""
import os, sys

BASE = os.path.dirname(os.path.abspath(__file__))

# ─── 1. اضافه کردن VariantListView به views.py ───────────────
views_path = os.path.join('apps', 'catalog', 'views.py')
with open(views_path, encoding='utf-8') as f:
    views_content = f.read()

if 'VariantListView' in views_content:
    print("VariantListView قبلاً اضافه شده.")
else:
    new_view = '''

# ─── Variants (for Kardex) ───────────────────────────────────

class VariantListView(generics.ListAPIView):
    """
    GET /api/catalog/variants/
    لیست همه variant ها برای استفاده در صفحه کاردکس
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        from .models import ProductVariant
        qs = ProductVariant.objects.filter(is_active=True).select_related('product', 'product__category')
        data = []
        for v in qs:
            data.append({
                'id': v.id,
                'sku': v.sku,
                'name': v.product.name + (' - ' + v.name_suffix if v.name_suffix else ''),
                'product_name': v.product.name,
                'product_id': v.product.id,
                'category': v.product.category.name if v.product.category else '',
                'stock_quantity': v.stock_quantity,
            })
        return Response(data)
'''
    views_content += new_view
    with open(views_path, 'w', encoding='utf-8') as f:
        f.write(views_content)
    print("✓ VariantListView اضافه شد.")

# ─── 2. اضافه کردن URL ───────────────────────────────────────
urls_path = os.path.join('apps', 'catalog', 'urls.py')
with open(urls_path, encoding='utf-8') as f:
    urls_content = f.read()

if 'variants/' in urls_content:
    print("URL variants قبلاً اضافه شده.")
else:
    urls_content = urls_content.replace(
        'path("exchange-rate/", views.ExchangeRateView.as_view(), name="exchange-rate"),',
        'path("exchange-rate/", views.ExchangeRateView.as_view(), name="exchange-rate"),\n    path("variants/", views.VariantListView.as_view(), name="variant-list"),'
    )
    with open(urls_path, 'w', encoding='utf-8') as f:
        f.write(urls_content)
    print("✓ URL /api/catalog/variants/ اضافه شد.")

# ─── 3. تست ───────────────────────────────────────────────────
import subprocess
r = subprocess.run([sys.executable, 'manage.py', 'check', '--verbosity=0'],
                   capture_output=True, text=True)
if r.returncode == 0:
    print("✓ check موفق — سرور را restart کنید")
else:
    print("خطا:")
    print(r.stderr[-500:])
