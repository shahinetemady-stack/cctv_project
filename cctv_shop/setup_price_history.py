"""
python setup_price_history.py
مدل تاریخچه قیمت + نمودار ۳۰ روزه
"""
import os, sys, subprocess

# ─── 1. مدل ProductPriceHistory ───────────────────────────────
models_path = os.path.join('apps', 'catalog', 'models.py')
with open(models_path, encoding='utf-8') as f:
    content = f.read()

if 'ProductPriceHistory' not in content:
    content += '''

class ProductPriceHistory(models.Model):
    """تاریخچه قیمت محصول — روزانه ذخیره می‌شود"""
    variant    = models.ForeignKey('ProductVariant', on_delete=models.CASCADE,
                   related_name='price_history', verbose_name="variant")
    date       = models.DateField(verbose_name="تاریخ")
    price_irr  = models.PositiveIntegerField(verbose_name="قیمت (تومان)")
    price_cny  = models.DecimalField(max_digits=10, decimal_places=2,
                   default=0, verbose_name="قیمت (یوان)")

    class Meta:
        db_table = "catalog_price_history"
        verbose_name = "تاریخچه قیمت"
        unique_together = [("variant", "date")]
        ordering = ["-date"]

    def __str__(self):
        return f"{self.variant} | {self.date} | {self.price_irr:,}"
'''
    with open(models_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("✓ ProductPriceHistory اضافه شد")

# ─── 2. Migration ─────────────────────────────────────────────
r = subprocess.run([sys.executable, 'manage.py', 'makemigrations', 'catalog'],
                   capture_output=True, text=True)
print(r.stdout[-200:] if r.stdout else "")
if r.returncode != 0:
    print("خطا:", r.stderr[-300:])
else:
    r2 = subprocess.run([sys.executable, 'manage.py', 'migrate'],
                        capture_output=True, text=True)
    print(r2.stdout[-100:] if r2.stdout else "")

# ─── 3. View ──────────────────────────────────────────────────
views_path = os.path.join('apps', 'catalog', 'views.py')
with open(views_path, encoding='utf-8') as f:
    views = f.read()

price_history_view = '''

class ProductPriceHistoryView(APIView):
    """GET /api/catalog/products/<slug>/price-history/ — تاریخچه قیمت ۳۰ روزه"""
    permission_classes = [AllowAny]

    def get(self, request, slug):
        from datetime import date, timedelta
        from .models import ProductPriceHistory, Product
        try:
            product = Product.objects.get(slug=slug)
        except Product.DoesNotExist:
            return Response([], status=404)

        variant = product.variants.filter(is_active=True).first()
        if not variant:
            return Response([])

        # ذخیره قیمت امروز
        today = date.today()
        ProductPriceHistory.objects.get_or_create(
            variant=variant, date=today,
            defaults={'price_irr': variant.final_price, 'price_cny': variant.purchase_price_cny or 0}
        )

        # ۳۰ روز اخیر
        since = today - timedelta(days=30)
        history = ProductPriceHistory.objects.filter(
            variant=variant, date__gte=since
        ).order_by('date')

        return Response([{
            'date': str(h.date),
            'price': h.price_irr,
        } for h in history])
'''

if 'ProductPriceHistoryView' not in views:
    views += price_history_view
    with open(views_path, 'w', encoding='utf-8') as f:
        f.write(views)
    print("✓ ProductPriceHistoryView اضافه شد")

# ─── 4. URL ───────────────────────────────────────────────────
urls_path = os.path.join('apps', 'catalog', 'urls.py')
with open(urls_path, encoding='utf-8') as f:
    urls = f.read()

if 'price-history' not in urls:
    urls = urls.replace(
        'path("products/<str:slug>/similar/"',
        'path("products/<str:slug>/price-history/", views.ProductPriceHistoryView.as_view()),\n    path("products/<str:slug>/similar/"'
    )
    with open(urls_path, 'w', encoding='utf-8') as f:
        f.write(urls)
    print("✓ URL اضافه شد")

# ─── 5. Admin ─────────────────────────────────────────────────
admin_path = os.path.join('apps', 'catalog', 'admin.py')
with open(admin_path, encoding='utf-8') as f:
    admin = f.read()

if 'ProductPriceHistory' not in admin:
    admin += '''

from apps.catalog.models import ProductPriceHistory

@admin.register(ProductPriceHistory)
class ProductPriceHistoryAdmin(admin.ModelAdmin):
    list_display = ["variant", "date", "price_irr", "price_cny"]
    list_filter  = ["date"]
    date_hierarchy = "date"
'''
    with open(admin_path, 'w', encoding='utf-8') as f:
        f.write(admin)
    print("✓ Admin اضافه شد")

r3 = subprocess.run([sys.executable, 'manage.py', 'check', '--verbosity=0'],
                    capture_output=True, text=True)
print("✓ check موفق" if r3.returncode == 0 else r3.stderr[-200:])
