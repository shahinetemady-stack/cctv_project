"""
python setup_education.py
ساخت اپ education با ویدیوها، مقالات و راهنماها
اجرا در پوشه cctv_shop
"""
import os, sys, subprocess

# ─── 1. ساخت اپ education ────────────────────────────────────
app_dir = os.path.join('apps', 'education')
if not os.path.exists(app_dir):
    os.makedirs(app_dir)
    # __init__.py
    open(os.path.join(app_dir, '__init__.py'), 'w').close()
    # apps.py
    with open(os.path.join(app_dir, 'apps.py'), 'w', encoding='utf-8') as f:
        f.write("""from django.apps import AppConfig
class EducationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.education'
    verbose_name = 'آموزش'
""")
    # migrations
    migrations_dir = os.path.join(app_dir, 'migrations')
    os.makedirs(migrations_dir, exist_ok=True)
    open(os.path.join(migrations_dir, '__init__.py'), 'w').close()
    print("✓ اپ education ساخته شد")

# ─── 2. models.py ────────────────────────────────────────────
with open(os.path.join(app_dir, 'models.py'), 'w', encoding='utf-8') as f:
    f.write("""from django.db import models
from django.utils import timezone


class ArticleCategory(models.Model):
    name  = models.CharField(max_length=100, verbose_name="نام دسته‌بندی")
    slug  = models.SlugField(max_length=120, unique=True, allow_unicode=True)
    order = models.PositiveSmallIntegerField(default=0, verbose_name="ترتیب")

    class Meta:
        db_table = "education_article_category"
        verbose_name = "دسته‌بندی مقاله"
        verbose_name_plural = "دسته‌بندی‌های مقاله"
        ordering = ["order", "name"]

    def __str__(self):
        return self.name


class Video(models.Model):
    class VideoType(models.TextChoices):
        MONTAJ          = "montaj",          "نصب و راه‌اندازی"
        TROUBLESHOOTING = "troubleshooting", "عیب‌یابی"
        PART_SELECTION  = "part_selection",  "انتخاب قطعه"
        GENERAL         = "general",         "عمومی"

    title            = models.CharField(max_length=300, verbose_name="عنوان")
    slug             = models.SlugField(max_length=320, unique=True, allow_unicode=True, verbose_name="نامک")
    description      = models.TextField(blank=True, verbose_name="توضیحات")
    video_url        = models.URLField(verbose_name="لینک ویدیو (آپارات/یوتیوب)")
    video_type       = models.CharField(max_length=20, choices=VideoType.choices,
                         default=VideoType.GENERAL, verbose_name="نوع ویدیو", db_index=True)
    related_products = models.ManyToManyField('catalog.Product', blank=True,
                         related_name='videos', verbose_name="محصولات مرتبط")
    duration         = models.PositiveSmallIntegerField(default=0, verbose_name="مدت (دقیقه)")
    thumbnail        = models.ImageField(upload_to='education/videos/', null=True, blank=True,
                         verbose_name="تصویر بندانگشتی")
    views_count      = models.PositiveIntegerField(default=0, verbose_name="بازدید")
    order            = models.PositiveSmallIntegerField(default=0, verbose_name="ترتیب")
    is_published     = models.BooleanField(default=True, verbose_name="منتشر شده")
    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "education_video"
        verbose_name = "ویدیو"
        verbose_name_plural = "ویدیوها"
        ordering = ["order", "-created_at"]

    def __str__(self):
        return self.title

    def get_embed_url(self):
        url = self.video_url
        if 'youtu.be' in url:
            vid = url.split('/')[-1].split('?')[0]
            return f"https://www.youtube.com/embed/{vid}"
        if 'youtube.com/watch' in url:
            import urllib.parse
            params = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
            vid = params.get('v', [''])[0]
            return f"https://www.youtube.com/embed/{vid}"
        if 'aparat.com' in url:
            return url.replace('/v/', '/embed/').rstrip('/') + '/true'
        return url


class Article(models.Model):
    title            = models.CharField(max_length=300, verbose_name="عنوان")
    slug             = models.SlugField(max_length=320, unique=True, allow_unicode=True, verbose_name="نامک")
    description      = models.TextField(blank=True, verbose_name="خلاصه")
    content          = models.TextField(blank=True, verbose_name="محتوا (HTML)")
    category         = models.ForeignKey(ArticleCategory, on_delete=models.SET_NULL,
                         null=True, blank=True, related_name='articles', verbose_name="دسته‌بندی")
    tags             = models.JSONField(default=list, blank=True, verbose_name="تگ‌ها")
    author           = models.CharField(max_length=100, blank=True, verbose_name="نویسنده")
    related_products = models.ManyToManyField('catalog.Product', blank=True,
                         related_name='articles', verbose_name="محصولات مرتبط")
    thumbnail        = models.ImageField(upload_to='education/articles/', null=True, blank=True,
                         verbose_name="تصویر شاخص")
    views_count      = models.PositiveIntegerField(default=0, verbose_name="بازدید")
    likes_count      = models.PositiveIntegerField(default=0, verbose_name="لایک")
    is_published     = models.BooleanField(default=True, verbose_name="منتشر شده")
    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "education_article"
        verbose_name = "مقاله"
        verbose_name_plural = "مقالات"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title
""")
print("✓ models.py ساخته شد")

# ─── 3. views.py ─────────────────────────────────────────────
with open(os.path.join(app_dir, 'views.py'), 'w', encoding='utf-8') as f:
    f.write("""from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAdminUser
from .models import Video, Article, ArticleCategory


class VideoListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        qs = Video.objects.filter(is_published=True)
        vtype = request.query_params.get('type')
        if vtype:
            qs = qs.filter(video_type=vtype)
        qs = qs.order_by('order', '-created_at')[:50]
        return Response([{
            'id': v.id, 'title': v.title, 'slug': v.slug,
            'description': v.description[:200],
            'video_type': v.video_type,
            'video_type_display': v.get_video_type_display(),
            'duration': v.duration,
            'views_count': v.views_count,
            'embed_url': v.get_embed_url(),
            'thumbnail': v.thumbnail.url if v.thumbnail else None,
        } for v in qs])


class VideoDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, slug):
        try:
            v = Video.objects.prefetch_related('related_products').get(
                slug=slug, is_published=True)
        except Video.DoesNotExist:
            return Response({'error': 'یافت نشد'}, status=404)
        return Response({
            'id': v.id, 'title': v.title, 'slug': v.slug,
            'description': v.description,
            'video_url': v.video_url,
            'embed_url': v.get_embed_url(),
            'video_type': v.video_type,
            'video_type_display': v.get_video_type_display(),
            'duration': v.duration,
            'views_count': v.views_count,
            'thumbnail': v.thumbnail.url if v.thumbnail else None,
            'related_products': [{'id': p.id, 'name': p.name, 'slug': p.slug}
                                  for p in v.related_products.filter(is_active=True)[:6]],
        })


class VideoViewCountView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, slug):
        Video.objects.filter(slug=slug).update(
            views_count=models.F('views_count') + 1)
        return Response({'ok': True})


class ArticleListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        qs = Article.objects.filter(is_published=True).select_related('category')
        cat = request.query_params.get('category')
        tag = request.query_params.get('tag')
        if cat:
            qs = qs.filter(category__slug=cat)
        if tag:
            qs = qs.filter(tags__contains=[tag])
        qs = qs.order_by('-created_at')[:50]
        return Response([{
            'id': a.id, 'title': a.title, 'slug': a.slug,
            'description': a.description[:200],
            'category': a.category.name if a.category else '',
            'category_slug': a.category.slug if a.category else '',
            'author': a.author,
            'tags': a.tags,
            'views_count': a.views_count,
            'likes_count': a.likes_count,
            'thumbnail': a.thumbnail.url if a.thumbnail else None,
            'created_at': a.created_at.strftime('%Y-%m-%d'),
        } for a in qs])


class ArticleDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, slug):
        try:
            a = Article.objects.prefetch_related('related_products', 'category').get(
                slug=slug, is_published=True)
        except Article.DoesNotExist:
            return Response({'error': 'یافت نشد'}, status=404)
        # افزایش بازدید
        Article.objects.filter(pk=a.pk).update(views_count=models.F('views_count') + 1)
        return Response({
            'id': a.id, 'title': a.title, 'slug': a.slug,
            'description': a.description,
            'content': a.content,
            'category': a.category.name if a.category else '',
            'category_slug': a.category.slug if a.category else '',
            'author': a.author,
            'tags': a.tags,
            'views_count': a.views_count,
            'likes_count': a.likes_count,
            'thumbnail': a.thumbnail.url if a.thumbnail else None,
            'created_at': a.created_at.strftime('%Y-%m-%d'),
            'related_products': [{'id': p.id, 'name': p.name, 'slug': p.slug}
                                  for p in a.related_products.filter(is_active=True)[:6]],
        })


class ArticleCategoryListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        cats = ArticleCategory.objects.all().order_by('order', 'name')
        return Response([{'id': c.id, 'name': c.name, 'slug': c.slug} for c in cats])


class PartSelectionGuideView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        guide = Article.objects.filter(
            tags__contains=['part-selection'], is_published=True
        ).first()
        videos = Video.objects.filter(
            video_type='part_selection', is_published=True
        )[:5]
        return Response({
            'guide': {
                'content': guide.content if guide else '',
                'title': guide.title if guide else 'راهنمای انتخاب قطعه',
            },
            'videos': [{'title': v.title, 'slug': v.slug, 'embed_url': v.get_embed_url(),
                         'duration': v.duration} for v in videos],
        })


from django.db import models
""")
print("✓ views.py ساخته شد")

# ─── 4. urls.py ──────────────────────────────────────────────
with open(os.path.join(app_dir, 'urls.py'), 'w', encoding='utf-8') as f:
    f.write("""from django.urls import path
from . import views

urlpatterns = [
    path('videos/', views.VideoListView.as_view()),
    path('videos/<str:slug>/', views.VideoDetailView.as_view()),
    path('videos/<str:slug>/view/', views.VideoViewCountView.as_view()),
    path('articles/', views.ArticleListView.as_view()),
    path('articles/<str:slug>/', views.ArticleDetailView.as_view()),
    path('categories/', views.ArticleCategoryListView.as_view()),
    path('guides/part-selection/', views.PartSelectionGuideView.as_view()),
]
""")
print("✓ urls.py ساخته شد")

# ─── 5. admin.py ─────────────────────────────────────────────
with open(os.path.join(app_dir, 'admin.py'), 'w', encoding='utf-8') as f:
    f.write("""from django.contrib import admin
from .models import Video, Article, ArticleCategory


@admin.register(ArticleCategory)
class ArticleCategoryAdmin(admin.ModelAdmin):
    list_display  = ['name', 'slug', 'order']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display   = ['title', 'video_type', 'duration', 'views_count', 'is_published', 'order']
    list_filter    = ['video_type', 'is_published']
    list_editable  = ['is_published', 'order']
    search_fields  = ['title', 'description']
    prepopulated_fields = {'slug': ('title',)}
    filter_horizontal = ['related_products']
    fieldsets = (
        ('اطلاعات اصلی', {'fields': ('title', 'slug', 'description', 'video_url', 'video_type')}),
        ('جزئیات', {'fields': ('duration', 'thumbnail', 'order', 'is_published')}),
        ('محصولات مرتبط', {'fields': ('related_products',)}),
    )


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display   = ['title', 'category', 'author', 'views_count', 'is_published', 'created_at']
    list_filter    = ['category', 'is_published']
    list_editable  = ['is_published']
    search_fields  = ['title', 'description', 'content']
    prepopulated_fields = {'slug': ('title',)}
    filter_horizontal = ['related_products']
    fieldsets = (
        ('اطلاعات اصلی', {'fields': ('title', 'slug', 'description', 'category', 'author')}),
        ('محتوا', {'fields': ('content', 'thumbnail')}),
        ('متادیتا', {'fields': ('tags', 'is_published', 'related_products')}),
    )
""")
print("✓ admin.py ساخته شد")

# ─── 6. اضافه کردن به settings ───────────────────────────────
settings_path = os.path.join('config', 'settings.py')
with open(settings_path, encoding='utf-8') as f:
    settings = f.read()

if 'apps.education' not in settings:
    settings = settings.replace(
        '"apps.accounting"',
        '"apps.accounting",\n    "apps.education"'
    )
    with open(settings_path, 'w', encoding='utf-8') as f:
        f.write(settings)
    print("✓ education به settings اضافه شد")

# ─── 7. اضافه کردن URL به config/urls.py ─────────────────────
urls_path = os.path.join('config', 'urls.py')
with open(urls_path, encoding='utf-8') as f:
    urls = f.read()

if 'education' not in urls:
    urls = urls.replace(
        "path('api/orders/',",
        "path('api/education/', include('apps.education.urls')),\n    path('api/orders/',"
    )
    with open(urls_path, 'w', encoding='utf-8') as f:
        f.write(urls)
    print("✓ URL education اضافه شد")

# ─── 8. Migration ─────────────────────────────────────────────
r = subprocess.run([sys.executable, 'manage.py', 'makemigrations', 'education'],
                   capture_output=True, text=True)
print(r.stdout[-200:] if r.stdout else "")
if r.returncode != 0:
    print("خطا:", r.stderr[-400:])
else:
    r2 = subprocess.run([sys.executable, 'manage.py', 'migrate'],
                        capture_output=True, text=True)
    print(r2.stdout[-200:] if r2.stdout else "")

r3 = subprocess.run([sys.executable, 'manage.py', 'check', '--verbosity=0'],
                    capture_output=True, text=True)
print("✓ check موفق" if r3.returncode == 0 else r3.stderr[-300:])
