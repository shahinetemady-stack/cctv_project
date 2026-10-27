"""
config/sitemaps.py
──────────────────
سایت‌مپ داینامیک: /sitemap.xml
دامنه از SITE_URL در settings خوانده می‌شود (env: SITE_URL).
"""

from django.conf import settings
from django.contrib.sitemaps import Sitemap

from apps.catalog.models import Category, Package, Product
from apps.education.models import Article, Video


class ProductSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return Product.objects.filter(is_active=True)

    def location(self, obj):
        return f"/products/{obj.slug}/"

    def lastmod(self, obj):
        return obj.updated_at


class CategorySitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.6

    def items(self):
        return Category.objects.filter(is_active=True)

    def location(self, obj):
        return f"/categories/{obj.slug}/"

    def lastmod(self, obj):
        return obj.updated_at


class PackageSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.6

    def items(self):
        return Package.objects.filter(is_active=True)

    def location(self, obj):
        return f"/packages/{obj.slug}/"

    def lastmod(self, obj):
        return obj.updated_at


class ArticleSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.5

    def items(self):
        return Article.objects.filter(is_published=True)

    def location(self, obj):
        return f"/blog/{obj.slug}/"

    def lastmod(self, obj):
        return obj.updated_at


class VideoSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.5

    def items(self):
        return Video.objects.filter(is_published=True)

    def location(self, obj):
        return f"/videos/{obj.slug}/"

    def lastmod(self, obj):
        return obj.updated_at


class StaticViewSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.4

    pages = [
        ("/", 1.0),
        ("/products/", 0.7),
        ("/packages/", 0.6),
        ("/blog/", 0.5),
        ("/videos/", 0.4),
        ("/china-order/faq/", 0.4),
        ("/terms/", 0.2),
        ("/privacy/", 0.2),
    ]

    def items(self):
        return self.pages

    def location(self, item):
        return item[0]

    def priority(self, item):
        return item[1]


sitemaps = {
    "products": ProductSitemap,
    "categories": CategorySitemap,
    "packages": PackageSitemap,
    "articles": ArticleSitemap,
    "videos": VideoSitemap,
    "static": StaticViewSitemap,
}
