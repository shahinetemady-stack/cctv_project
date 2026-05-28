import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

# ─── اضافه کردن endpoint محصولات مشابه به catalog/views.py ───
views_path = os.path.join('apps', 'catalog', 'views.py')
with open(views_path, encoding='utf-8') as f:
    content = f.read()

similar_view = '''

class SimilarProductsView(APIView):
    """GET /api/catalog/products/<slug>/similar/ — محصولات مشابه برای کالای ناموجود"""
    permission_classes = [AllowAny]

    def get(self, request, slug):
        from django.db.models import Q
        try:
            product = Product.objects.get(slug=slug, is_active=True)
        except Product.DoesNotExist:
            return Response([])

        # بررسی موجودی
        total_stock = sum(v.stock_quantity for v in product.variants.filter(is_active=True))

        # همیشه محصولات مشابه برمی‌گردانیم (حتی اگر موجود باشد)
        filters = Q(is_active=True) & ~Q(id=product.id)

        # فیلتر بر اساس مشخصات مشترک
        conditions = []
        if product.sensor_name:
            conditions.append(Q(sensor_name=product.sensor_name))
        if product.voltage:
            conditions.append(Q(voltage=product.voltage))
        if product.category:
            conditions.append(Q(category=product.category))

        similar = Product.objects.none()

        # اول: همان سنسور و ولتاژ
        if product.sensor_name and product.voltage:
            similar = Product.objects.filter(
                filters & Q(sensor_name=product.sensor_name) & Q(voltage=product.voltage)
            ).prefetch_related('variants', 'images')[:3]

        # اگر کافی نبود: همان دسته‌بندی
        if similar.count() < 3 and product.category:
            exclude_ids = [p.id for p in similar] + [product.id]
            extra = Product.objects.filter(
                filters & Q(category=product.category)
            ).exclude(id__in=exclude_ids).prefetch_related('variants', 'images')[:3 - similar.count()]
            from itertools import chain
            similar = list(chain(similar, extra))

        result = []
        for p in similar[:3]:
            variants = p.variants.filter(is_active=True)
            stock = sum(v.stock_quantity for v in variants)
            first_image = p.images.first()
            result.append({
                'id': p.id,
                'name': p.name,
                'slug': p.slug,
                'category': p.category.name if p.category else '',
                'sensor_name': p.sensor_name or '',
                'voltage': p.voltage or '',
                'stock': stock,
                'is_available': stock > 0,
                'image': first_image.image.url if first_image else None,
                'price': variants.first().final_price if variants.exists() else 0,
            })

        return Response({
            'is_out_of_stock': total_stock == 0,
            'similar': result,
        })
'''

if 'SimilarProductsView' not in content:
    # اضافه کردن AllowAny به imports اگر نبود
    if 'AllowAny' not in content:
        content = content.replace(
            'from rest_framework.permissions import',
            'from rest_framework.permissions import AllowAny,'
        )
    content += similar_view
    with open(views_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("✓ SimilarProductsView اضافه شد")
else:
    print("✓ قبلاً موجود بود")

# ─── اضافه کردن URL ───────────────────────────────────────────
urls_path = os.path.join('apps', 'catalog', 'urls.py')
with open(urls_path, encoding='utf-8') as f:
    urls = f.read()

if 'similar' not in urls:
    urls = urls.replace(
        "path('products/<slug:slug>/',",
        "path('products/<slug:slug>/similar/', views.SimilarProductsView.as_view()),\n    path('products/<slug:slug>/',"
    )
    with open(urls_path, 'w', encoding='utf-8') as f:
        f.write(urls)
    print("✓ URL اضافه شد")

import subprocess, sys
r = subprocess.run([sys.executable, 'manage.py', 'check', '--verbosity=0'], capture_output=True, text=True)
print("✓ check موفق" if r.returncode == 0 else r.stderr[-300:])
