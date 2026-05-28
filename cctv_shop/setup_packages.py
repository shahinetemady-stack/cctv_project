"""
python setup_packages.py
ساخت سیستم پکیج پیشنهادی
"""
import os, sys, subprocess

# ─── 1. اضافه کردن مدل Package به catalog/models.py ──────────
models_path = os.path.join('apps', 'catalog', 'models.py')
with open(models_path, encoding='utf-8') as f:
    content = f.read()

package_model = '''

class Package(models.Model):
    """پکیج پیشنهادی — ترکیب چند محصول با تخفیف"""

    name        = models.CharField(max_length=200, verbose_name="نام پکیج")
    slug        = models.SlugField(max_length=250, unique=True, allow_unicode=True, verbose_name="نامک")
    description = models.TextField(blank=True, verbose_name="توضیحات")
    image       = models.ImageField(upload_to='packages/', null=True, blank=True, verbose_name="تصویر")
    products    = models.ManyToManyField('Product', through='PackageItem', related_name='packages', verbose_name="محصولات")
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="تخفیف (%)")
    is_active   = models.BooleanField(default=True, verbose_name="فعال")
    is_featured = models.BooleanField(default=False, verbose_name="ویژه")
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "catalog_package"
        verbose_name = "پکیج"
        verbose_name_plural = "پکیج‌ها"
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    @property
    def original_price(self):
        """قیمت اصلی بدون تخفیف"""
        total = 0
        for item in self.package_items.select_related('variant').all():
            total += item.variant.final_price * item.quantity
        return total

    @property
    def final_price(self):
        """قیمت نهایی با تخفیف"""
        import math
        disc = float(self.discount_percent) / 100
        return math.ceil(self.original_price * (1 - disc))

    @property
    def savings(self):
        return self.original_price - self.final_price


class PackageItem(models.Model):
    """آیتم داخل پکیج"""
    package  = models.ForeignKey(Package, on_delete=models.CASCADE, related_name='package_items')
    product  = models.ForeignKey('Product', on_delete=models.CASCADE, verbose_name="محصول")
    variant  = models.ForeignKey('ProductVariant', on_delete=models.CASCADE, verbose_name="نوع محصول")
    quantity = models.PositiveSmallIntegerField(default=1, verbose_name="تعداد")

    class Meta:
        db_table = "catalog_package_item"
        verbose_name = "آیتم پکیج"
        verbose_name_plural = "آیتم‌های پکیج"

    def __str__(self):
        return f"{self.package.name} — {self.product.name} × {self.quantity}"
'''

if 'class Package' not in content:
    content += package_model
    with open(models_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("✓ مدل Package اضافه شد")
else:
    print("✓ قبلاً موجود بود")

# ─── 2. Migration ─────────────────────────────────────────────
r = subprocess.run([sys.executable, 'manage.py', 'makemigrations', 'catalog'],
                   capture_output=True, text=True)
print(r.stdout[-300:] if r.stdout else "")
if r.returncode != 0:
    print("خطا:"); print(r.stderr[-400:])
else:
    r2 = subprocess.run([sys.executable, 'manage.py', 'migrate'],
                        capture_output=True, text=True)
    print(r2.stdout[-200:] if r2.stdout else "")

# ─── 3. Admin ─────────────────────────────────────────────────
admin_path = os.path.join('apps', 'catalog', 'admin.py')
with open(admin_path, encoding='utf-8') as f:
    admin = f.read()

if 'PackageAdmin' not in admin:
    admin += '''

# ─── Package Admin ────────────────────────────────────────────
from apps.catalog.models import Package, PackageItem

class PackageItemInline(admin.TabularInline):
    model = PackageItem
    extra = 1
    fields = ['product', 'variant', 'quantity']
    autocomplete_fields = ['product']

@admin.register(Package)
class PackageAdmin(admin.ModelAdmin):
    list_display  = ['name', 'discount_percent', 'original_price_display',
                     'final_price_display', 'savings_display', 'is_active', 'is_featured']
    list_filter   = ['is_active', 'is_featured']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}
    inlines = [PackageItemInline]

    def original_price_display(self, obj):
        return f"{obj.original_price:,} ت"
    original_price_display.short_description = "قیمت اصلی"

    def final_price_display(self, obj):
        return f"{obj.final_price:,} ت"
    final_price_display.short_description = "قیمت با تخفیف"

    def savings_display(self, obj):
        return f"{obj.savings:,} ت"
    savings_display.short_description = "صرفه‌جویی"
'''
    with open(admin_path, 'w', encoding='utf-8') as f:
        f.write(admin)
    print("✓ PackageAdmin اضافه شد")

# ─── 4. Views ─────────────────────────────────────────────────
views_path = os.path.join('apps', 'catalog', 'views.py')
with open(views_path, encoding='utf-8') as f:
    views = f.read()

package_views = '''

class PackageListView(APIView):
    """GET /api/catalog/packages/ — لیست پکیج‌ها"""
    permission_classes = [AllowAny]

    def get(self, request):
        from .models import Package
        packages = Package.objects.filter(is_active=True).prefetch_related(
            'package_items__product__images',
            'package_items__variant',
        )
        featured_only = request.query_params.get('featured') == '1'
        if featured_only:
            packages = packages.filter(is_featured=True)

        result = []
        for pkg in packages:
            items = []
            for item in pkg.package_items.all():
                img = item.product.images.first()
                items.append({
                    'product_id': item.product_id,
                    'product_name': item.product.name,
                    'product_slug': item.product.slug,
                    'variant_id': item.variant_id,
                    'quantity': item.quantity,
                    'unit_price': item.variant.final_price,
                    'image': img.image.url if img else None,
                })
            result.append({
                'id': pkg.id,
                'name': pkg.name,
                'slug': pkg.slug,
                'description': pkg.description,
                'image': pkg.image.url if pkg.image else None,
                'discount_percent': float(pkg.discount_percent),
                'original_price': pkg.original_price,
                'final_price': pkg.final_price,
                'savings': pkg.savings,
                'is_featured': pkg.is_featured,
                'items': items,
            })
        return Response(result)


class PackageDetailView(APIView):
    """GET /api/catalog/packages/<slug>/ — جزئیات پکیج"""
    permission_classes = [AllowAny]

    def get(self, request, slug):
        from .models import Package
        try:
            pkg = Package.objects.prefetch_related(
                'package_items__product__images',
                'package_items__variant',
            ).get(slug=slug, is_active=True)
        except Package.DoesNotExist:
            return Response({'error': 'یافت نشد'}, status=404)

        items = []
        for item in pkg.package_items.all():
            img = item.product.images.first()
            items.append({
                'product_id': item.product_id,
                'product_name': item.product.name,
                'product_slug': item.product.slug,
                'variant_id': item.variant_id,
                'quantity': item.quantity,
                'unit_price': item.variant.final_price,
                'subtotal': item.variant.final_price * item.quantity,
                'image': img.image.url if img else None,
                'stock': item.variant.stock_quantity,
            })

        return Response({
            'id': pkg.id,
            'name': pkg.name,
            'slug': pkg.slug,
            'description': pkg.description,
            'image': pkg.image.url if pkg.image else None,
            'discount_percent': float(pkg.discount_percent),
            'original_price': pkg.original_price,
            'final_price': pkg.final_price,
            'savings': pkg.savings,
            'items': items,
        })
'''

if 'PackageListView' not in views:
    views += package_views
    with open(views_path, 'w', encoding='utf-8') as f:
        f.write(views)
    print("✓ Package views اضافه شد")

# ─── 5. URLs ──────────────────────────────────────────────────
urls_path = os.path.join('apps', 'catalog', 'urls.py')
with open(urls_path, encoding='utf-8') as f:
    urls = f.read()

if 'packages' not in urls:
    urls = urls.replace(
        '    path("variants/"',
        '    path("packages/", views.PackageListView.as_view(), name="package-list"),\n    path("packages/<slug:slug>/", views.PackageDetailView.as_view(), name="package-detail"),\n    path("variants/"'
    )
    with open(urls_path, 'w', encoding='utf-8') as f:
        f.write(urls)
    print("✓ Package URLs اضافه شد")

r3 = subprocess.run([sys.executable, 'manage.py', 'check', '--verbosity=0'],
                    capture_output=True, text=True)
print("✓ check موفق" if r3.returncode == 0 else r3.stderr[-300:])
print("\nحالا پکیج‌ها را در Django Admin تعریف کنید:")
print("http://127.0.0.1:8000/admin/catalog/package/")
