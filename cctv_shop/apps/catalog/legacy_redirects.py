"""
apps/catalog/legacy_redirects.py
────────────────────────────────
ریدایرکت ۳۰۱ از URLهای سایت قدیمی doorbinkar.com به URLهای جدید.

سایت قدیمی:
    /cat/<id>/<slug>        → دسته‌بندی
    /products/<id>/<slug>   → محصول

این مسیرها در config/urls.py سطح ریشه mount شده‌اند و nginx
باید درخواست‌های «/cat/<عدد>/...» و «/products/<عدد>/...» را
به گانیکورن پاس بدهد (deploy/nginx-legacy-redirects.conf).
"""

from django.http import Http404
from django.shortcuts import redirect

from .models import Category, Product


def legacy_category_redirect(request, legacy_id, rest=""):
    cat = Category.objects.filter(legacy_id=legacy_id, is_active=True).first()
    if cat is None:
        raise Http404("دسته‌بندی قدیمی پیدا نشد")
    return redirect(f"/categories/{cat.slug}", permanent=True)


def legacy_product_redirect(request, legacy_id, rest=""):
    product = Product.objects.filter(legacy_id=legacy_id, is_active=True).first()
    if product is None:
        raise Http404("محصول قدیمی پیدا نشد")
    return redirect(f"/products/{product.slug}", permanent=True)


def legacy_blog_redirect(request, legacy_id, rest=""):
    from apps.education.models import Article
    article = Article.objects.filter(legacy_id=legacy_id, is_published=True).first()
    if article is None:
        raise Http404("مقاله قدیمی پیدا نشد")
    return redirect(f"/blog/{article.slug}", permanent=True)
