from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.shortcuts import render
from django.conf import settings
from .models import SiteSettings, StaticPage
import django


def home_view(request):
    """صفحه اصلی (landing page) — نمایش صفحه خوش‌آمدگویی.

    این view به جای 404 بودن ریشه سایت، یک صفحه خوش‌آمدگویی
    به همراه لینک‌های مفید به API و پنل ادمین نمایش می‌دهد.
    """
    return render(request, "home.html", {
        "django_version": django.VERSION,
        "debug": settings.DEBUG,
    })


class SiteSettingsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        s = SiteSettings.get_instance()
        return Response({
            'site_name': s.site_name,
            'contact_phone': s.contact_phone,
            'contact_email': s.contact_email,
            'contact_address': s.contact_address,
            'working_hours': s.working_hours,
            'china_phone': s.china_phone,
            'china_address': s.china_address,
            'wechat_qr': request.build_absolute_uri(s.wechat_qr.url) if s.wechat_qr else None,
            'whatsapp_number': s.whatsapp_number,
            'bale_username': s.bale_username,
            'eitaa_username': s.eitaa_username,
            'telegram_username': s.telegram_username,
            'instagram_username': s.instagram_username,
            'about_us_text': s.about_us_text,
            'bank_accounts': s.bank_accounts,
            'site_logo': request.build_absolute_uri(s.site_logo.url) if s.site_logo else None,
            'enamad_id': s.enamad_id,
            'enamad_code': s.enamad_code,
        })


class StaticPageView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, key):
        try:
            page = StaticPage.objects.get(key=key)
            images = [
                request.build_absolute_uri(getattr(page, f'image{i}').url)
                for i in range(1, 5)
                if getattr(page, f'image{i}')
            ]
            return Response({'title': page.title, 'content': page.content, 'images': images})
        except StaticPage.DoesNotExist:
            return Response({'title': '', 'content': '', 'images': []})


class LogoUploadView(APIView):
    """POST /api/core/settings/logo/ — آپلود لوگو"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not request.user.is_staff:
            return Response({'error': 'دسترسی ندارید'}, status=403)
        logo = request.FILES.get('logo')
        if not logo:
            return Response({'error': 'فایل ارسال نشده'}, status=400)
        s = SiteSettings.get_instance()
        s.site_logo = logo
        s.save()
        logo_url = request.build_absolute_uri(s.site_logo.url) if s.site_logo else None
        return Response({'logo_url': logo_url})


# ─── OG برای کرولرهای پیش‌نمایش لینک + رندر داینامیک برای موتورهای جستجو ────
# nginx بر اساس User-Agent، ربات‌ها را با هدر X-Bot-Kind اینجا پروکسی می‌کند:
#   social → متای اشتراک‌گذاری (واتساپ، تلگرام، بله…) با ریدایرکت JS برای انسان
#   search → HTML کامل قابل‌خواندن (Googlebot، GPTBot، ClaudeBot و…) — همان
#            «رندر داینامیک» رسمی گوگل برای SPA؛ محتوا معادل چیزی است که
#            کاربر بعد از اجرای JS می‌بیند، پس cloaking محسوب نمی‌شود.
# کاربران عادی (بدون هدر) عملاً به اینجا نمی‌رسند و همان SPA را می‌گیرند.

def _resolve_seo_object(kind, slug):
    """شیء و متادیتای هر نوع صفحه را برمی‌گرداند. (obj, title, desc, image)"""
    from apps.catalog.models import Product, Category, Package
    from apps.education.models import Article, Video

    if kind == "products":
        obj = Product.objects.filter(slug=slug, is_active=True).first()
        if obj:
            title = obj.meta_title or obj.name
            desc = obj.meta_description or obj.short_description or obj.description[:160]
            img = obj.main_image
            return obj, title, desc, (img.image if img else None)
    elif kind == "categories":
        obj = Category.objects.filter(slug=slug, is_active=True).first()
        if obj:
            title = obj.meta_title or obj.name
            desc = obj.meta_description or obj.description[:160]
            return obj, title, desc, obj.image
    elif kind == "packages":
        obj = Package.objects.filter(slug=slug, is_active=True).first()
        if obj:
            title = obj.meta_title or obj.name
            desc = obj.meta_description or obj.description[:160]
            return obj, title, desc, obj.image
    elif kind == "blog":
        obj = Article.objects.filter(slug=slug, is_published=True).first()
        if obj:
            return obj, obj.title, (obj.description[:160] if obj.description else ""), obj.thumbnail
    elif kind == "videos":
        obj = Video.objects.filter(slug=slug, is_published=True).first()
        if obj:
            return obj, obj.title, (obj.description[:160] if obj.description else ""), obj.thumbnail
    return None, None, None, None


def social_meta_view(request, kind, slug):
    from django.http import Http404
    from django.shortcuts import redirect

    obj, title, desc, image = _resolve_seo_object(kind, slug)
    if not obj:
        # اسلاگ قدیمی (ایندکس گوگل/لینک‌های خارجی) → ۳۰۱ به مسیر جدید تا
        # اعتبار دامنه حفظ شود؛ بدون این چک خزنده‌ها ۴۰۴ می‌گرفتند.
        from apps.catalog.models import SlugRedirect
        red = SlugRedirect.objects.filter(
            old_slug=slug, new_path__startswith=f"/{kind}/"
        ).first()
        if red:
            path = red.new_path if red.new_path.endswith("/") else red.new_path + "/"
            return redirect(path, permanent=True)
        raise Http404

    site = SiteSettings.get_instance()
    page_url = request.build_absolute_uri(f"/{kind}/{obj.slug}/")
    context = {
        "title": title,
        # H1 باید نام کامل و کوتاه‌شده‌نیافته باشد (meta_title ممکن است با … کوتاه شده باشد)
        "h1": getattr(obj, "name", None) or getattr(obj, "title", None) or title,
        "description": desc,
        "page_url": page_url,
        "image_url": request.build_absolute_uri(image.url) if image else None,
        "site_name": site.site_name or "دوربینکار",
    }
    if kind == "products":
        context.update(_torob_product_meta(obj, request))

    if request.META.get("HTTP_X_BOT_KIND") == "search":
        context.update(_search_page_context(obj, kind, request))
        return render(request, "seo_page.html", context)
    return render(request, "social_meta.html", context)


def _torob_product_meta(product, request):
    """متاهای موردنیاز ترب (torob.com) برای صفحه محصول.

    خزنده ترب JS اجرا نمی‌کند و شناسه/نام/قیمت/موجودی را از متای HTML خام
    می‌خواند. قیمت همان حداقل قیمت خرده (retail = قیمت مهمان) است که در
    صفحه محصول نمایش داده می‌شود؛ تومان و بدون جداکننده.
    """
    from apps.catalog.pricing import base_prices, formula_prices

    ctx = {
        "torob_name": product.name,
        "torob_availability": (
            "instock" if product.available_stock > 0 and product.availability == "auto"
            else "outofstock"
        ),
    }
    variants = list(product.variants.filter(is_active=True))
    if variants:
        cheapest = min(variants, key=lambda v: formula_prices(v)["retail"])
        retail = formula_prices(cheapest)["retail"]       # ریال — قیمت خرده نمایشی
        ctx["torob_price"] = retail // 10                 # تومان
        disc = float(getattr(cheapest, "discount_percent", 0) or 0)
        old = base_prices(cheapest)["retail"] if disc > 0 else retail
        ctx["torob_old_price"] = old // 10                # تومان
    img = product.main_image
    if img:
        ctx["torob_image"] = request.build_absolute_uri(img.image.url)
    return ctx


def _search_page_context(obj, kind, request):
    """کنتکست کامل صفحه برای خزنده‌های جستجو/AI: بدنه، مشخصات، قیمت، JSON-LD، لینک‌های داخلی."""
    import json
    from apps.education.models import Article

    ctx = {"kind": kind, "obj": obj, "json_ld": None, "min_price": None,
           "specs": [], "category_products": [], "package_items": [],
           "related_products": [], "latest_articles": []}
    ld = None

    if kind == "products":
        variants = [v for v in obj.variants.filter(is_active=True)]
        prices = [v.final_price for v in variants]
        if prices:
            ctx["min_price"] = min(prices)          # ریال
            ctx["min_price_toman"] = f"{min(prices) // 10:,}"
        # مشخصات فنی — فیلدهای پرشده مدل + مشخصات سفارشی دسته
        spec_fields = [
            ("برند", obj.brand), ("شماره مدل", obj.model_number),
            ("سیستم", obj.board_system), ("رزولوشن", obj.board_resolution),
            ("سنسور", obj.sensor_name), ("اندازه سنسور", obj.sensor_size),
            ("پردازنده", obj.ai_processor), ("ابعاد برد", obj.board_dimensions),
            ("رزولوشن لنز", obj.lens_resolution), ("فاصله کانونی", obj.lens_degree),
            ("نوع لنز", obj.lens_type), ("نوع کاربرد", obj.focal_ratio),
            ("مدل", obj.modem_model), ("نوع", obj.modem_type),
            ("ولتاژ کاری", obj.voltage), ("آمپر خروجی", obj.ampere_output),
            ("جنس بدنه", obj.housing_material), ("نوع بدنه", obj.housing_type),
            ("سایز دوربین", obj.housing_size),
        ]
        ctx["specs"] = [(label, val) for label, val in spec_fields if val]
        if obj.has_microphone:
            ctx["specs"].append(("قابلیت میکروفون", "دارد"))
        if obj.sim_card:
            ctx["specs"].append(("قابلیت سیم‌کارت", "دارد"))
        for key, val in (obj.dynamic_specs or {}).items():
            if val not in (None, "", False):
                ctx["specs"].append((key, val))
        ctx["related_products"] = obj.compatible_with.filter(is_active=True)[:8]
        ld = {
            "@context": "https://schema.org", "@type": "Product",
            "name": obj.name,
            "description": obj.short_description or obj.description[:300],
            "category": obj.category.name if obj.category_id else None,
            "brand": {"@type": "Brand", "name": obj.brand} if obj.brand else None,
        }
        img = obj.main_image
        if img:
            ld["image"] = request.build_absolute_uri(img.image.url)
        if prices:
            ld["offers"] = {
                "@type": "Offer",
                "priceCurrency": "IRR",
                "price": min(prices),
                "availability": ("https://schema.org/InStock" if obj.available_stock > 0
                                 else "https://schema.org/OutOfStock"),
                "url": ctx.get("page_url") or request.build_absolute_uri(f"/products/{obj.slug}/"),
            }
        ld = {k: v for k, v in ld.items() if v is not None}

    elif kind == "categories":
        ctx["category_products"] = obj.products.filter(is_active=True)[:30]
        ld = {
            "@context": "https://schema.org", "@type": "CollectionPage",
            "name": obj.name, "description": obj.description[:300],
        }

    elif kind == "packages":
        ctx["package_items"] = [
            {"product": it.product, "quantity": it.quantity}
            for it in obj.package_items.select_related("product").all()
        ]
        ctx["min_price"] = obj.final_price
        ctx["min_price_toman"] = f"{obj.final_price // 10:,}"
        ld = {
            "@context": "https://schema.org", "@type": "Product",
            "name": obj.name, "description": obj.description[:300],
            "offers": {
                "@type": "Offer", "priceCurrency": "IRR",
                "price": obj.final_price, "availability": "https://schema.org/InStock",
            },
        }

    elif kind == "blog":
        ctx["related_products"] = obj.related_products.filter(is_active=True)[:8]
        ctx["latest_articles"] = (Article.objects.filter(is_published=True)
                                  .exclude(pk=obj.pk))[:6]
        ld = {
            "@context": "https://schema.org", "@type": "Article",
            "headline": obj.title, "description": obj.description[:300],
            "inLanguage": "fa-IR",
            "datePublished": obj.created_at.isoformat(),
            "dateModified": obj.updated_at.isoformat(),
        }
        if obj.author:
            ld["author"] = {"@type": "Person", "name": obj.author}
        if obj.thumbnail:
            ld["image"] = request.build_absolute_uri(obj.thumbnail.url)

    elif kind == "videos":
        ctx["related_products"] = obj.related_products.filter(is_active=True)[:8]
        ld = {
            "@context": "https://schema.org", "@type": "VideoObject",
            "name": obj.title, "description": obj.description[:300],
            "embedUrl": obj.get_embed_url(), "inLanguage": "fa-IR",
        }
        if obj.thumbnail:
            ld["thumbnailUrl"] = request.build_absolute_uri(obj.thumbnail.url)

    if ld:
        # جلوگیری از شکستن </script> داخل JSON
        ctx["json_ld"] = json.dumps(ld, ensure_ascii=False).replace("<", "\\u003c")
    return ctx


def llms_txt_view(request):
    """GET /llms.txt — راهنمای خزنده‌های AI: فهرست به‌روز صفحات، دسته‌ها، مقالات و محصولات."""
    from apps.catalog.models import Product, Category, Package
    from apps.education.models import Article, Video

    base = request.build_absolute_uri("/").rstrip("/")
    site = SiteSettings.get_instance()
    return render(request, "llms.txt", {
        "base": base,
        "site_name": site.site_name or "دوربینکار",
        "categories": Category.objects.filter(is_active=True),
        "packages": Package.objects.filter(is_active=True),
        "articles": Article.objects.filter(is_published=True),
        "videos": Video.objects.filter(is_published=True),
        "products": Product.objects.filter(is_active=True).select_related("category"),
    }, content_type="text/plain; charset=utf-8")
