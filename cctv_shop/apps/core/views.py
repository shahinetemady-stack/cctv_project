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


# ─── API ربات‌های پیام‌رسان (تلگرام/اینستاگرام) ─────────────────────────
# احراز با توکن مشترک (هدر X-Bot-Token) — مقدار در BOT_API_TOKEN در .env سرور
# و مینی‌پی‌سی نگه‌داری می‌شود. بدون کاربر لاگین‌شده کار می‌کند.

_FA2EN_DIGITS = str.maketrans('۰۱۲۳۴۵۶۷۸۹', '0123456789')


def _normalize_phone(raw):
    """هر فرمت موبایل ایران → 09xxxxxxxxx (خروجی None اگر نامعتبر)."""
    import re
    d = re.sub(r'\D', '', str(raw or '').translate(_FA2EN_DIGITS))
    if d.startswith('0098'):
        d = d[4:]
    elif d.startswith('98'):
        d = d[2:]
    if d and not d.startswith('0'):
        d = '0' + d
    return d if re.fullmatch(r'09\d{9}', d) else None


class BotPriceLookupView(APIView):
    """POST /api/core/bot/price/ — استعلام قیمت محصول برای مشتری بر اساس موبایل.
    بدنه: {slug یا product_id, phone (اختیاری)} — اگر موبایل ثبت‌نام‌کرده و همکار
    تأییدشده باشد، قیمت سطح خودش (سیلور/گلد/پلاتینیوم) برمی‌گردد، وگرنه قیمت عمومی."""
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        from decouple import config as env
        expected = env("BOT_API_TOKEN", default="")
        if not expected or request.headers.get("X-Bot-Token", "") != expected:
            return Response({"error": "دسترسی ندارید"}, status=401)

        from apps.catalog.models import Product
        from apps.catalog.pricing import formula_prices, user_price_key, TIER_LABELS
        from apps.users.models import User

        slug = (request.data.get('slug') or '').strip()
        pid = request.data.get('product_id')

        # فقط موبایل بدون محصول → فقط اطلاعات مشتری (تشخیص نوع مشتری توسط ربات)
        if not slug and not pid:
            phone_only = _normalize_phone(request.data.get('phone'))
            if not phone_only:
                return Response({"error": "slug یا product_id یا phone لازم است"}, status=400)
            from apps.users.models import User as _U
            u = _U.objects.filter(phone=phone_only).first()
            _, t = user_price_key(u)
            return Response({"customer": {
                "phone": phone_only, "registered": bool(u),
                "tier": t, "tier_label": TIER_LABELS.get(t) if t else "مشتری عمومی",
            }})

        qs = Product.objects.filter(is_active=True)
        product = qs.filter(pk=pid).first() if pid else qs.filter(slug=slug).first()
        if not product:
            return Response({"error": "محصول یافت نشد"}, status=404)

        site_base = env("SITE_BASE_URL", default="https://doorbinkar.com").rstrip('/')

        # کاربر بر اساس موبایل (اختیاری — ناشناس = مشتری عمومی)
        user = None
        phone = _normalize_phone(request.data.get('phone'))
        if phone:
            user = User.objects.filter(phone=phone).first()

        key, tier = user_price_key(user)  # ناشناس/عمومی → retail
        variants = list(product.variants.filter(is_active=True))
        if not variants:
            return Response({"error": "محصول واریانت فعال ندارد"}, status=404)
        cheapest = min(variants, key=lambda v: formula_prices(v)[key])
        prices = formula_prices(cheapest)

        payload = {
            "product": {
                "id": product.id,
                "name": product.name,
                "url": f"{site_base}/products/{product.slug}/",
                "in_stock": product.available_stock > 0,
            },
            "customer": {
                "phone": phone,
                "registered": bool(user),
                "tier": tier,
                "tier_label": TIER_LABELS.get(tier) if tier else "مشتری عمومی",
            },
            # ریال
            "price": prices[key],
            "retail_price": prices["retail"],
        }
        if tier == "platinum":
            payload["platinum_options"] = {
                "cash": prices["cash"], "credit": prices["credit"],
                "month1": prices["month1"], "month2": prices["month2"],
            }
        return Response(payload)


# ─── سرویس‌ها و اشتراک‌ها (دامنه/سرور/…) — perm: services_view ────────────
# اطلاعات حساب‌ها حساس است؛ سوپریوزر همیشه عبور می‌کند و پرسنل فقط با نقشی
# که کد services_view را دارد به این بخش دسترسی دارند.

from .models import ServiceSubscription


def _has_perm(user, code):
    if user.is_superuser:
        return True
    sp = getattr(user, 'staff_profile', None)
    return bool(sp and sp.is_active and sp.has_perm(code))


def _service_dict(s):
    return {
        'id': s.id,
        'name': s.name,
        'category': s.category,
        'category_display': s.get_category_display(),
        'provider': s.provider,
        'account': s.account,
        'expire_date': s.expire_date.isoformat(),
        'renew_cost': s.renew_cost,
        'warn_days': s.warn_days,
        'auto_renew': s.auto_renew,
        'note': s.note,
        'is_active': s.is_active,
        'days_left': s.days_left,
    }


def _service_payload(data):
    """اعتبارسنجی و استخراج فیلدها از بدنه درخواست. (payload, error)"""
    import datetime
    name = (data.get('name') or '').strip()
    if not name:
        return None, 'نام سرویس الزامی است'
    raw_date = (data.get('expire_date') or '').strip()
    try:
        expire_date = datetime.date.fromisoformat(raw_date)
    except ValueError:
        return None, 'تاریخ انقضا معتبر نیست (مثال: 2027-03-15)'
    category = data.get('category') or 'other'
    if category not in dict(ServiceSubscription.CATEGORIES):
        return None, 'دسته معتبر نیست'
    try:
        warn_days = max(1, min(365, int(data.get('warn_days') or 30)))
    except (TypeError, ValueError):
        return None, 'روزهای هشدار معتبر نیست'
    return {
        'name': name[:100],
        'category': category,
        'provider': (data.get('provider') or '').strip()[:100],
        'account': (data.get('account') or '').strip()[:150],
        'expire_date': expire_date,
        'renew_cost': (data.get('renew_cost') or '').strip()[:60],
        'warn_days': warn_days,
        'auto_renew': bool(data.get('auto_renew')),
        'note': (data.get('note') or '').strip(),
        'is_active': bool(data.get('is_active', True)),
    }, None


class ServiceSubscriptionsView(APIView):
    permission_classes = [IsAuthenticated]

    def _forbid(self, request):
        if not _has_perm(request.user, 'services_view'):
            return Response({'error': 'شما دسترسی لازم برای این عملیات را ندارید'}, status=403)

    def get(self, request):
        if (r := self._forbid(request)):
            return r
        items = ServiceSubscription.objects.all()
        return Response([_service_dict(s) for s in items])

    def post(self, request):
        if (r := self._forbid(request)):
            return r
        payload, err = _service_payload(request.data)
        if err:
            return Response({'error': err}, status=400)
        s = ServiceSubscription.objects.create(**payload)
        return Response(_service_dict(s), status=201)


class ServiceSubscriptionDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _forbid(self, request):
        if not _has_perm(request.user, 'services_view'):
            return Response({'error': 'شما دسترسی لازم برای این عملیات را ندارید'}, status=403)

    def patch(self, request, pk):
        if (r := self._forbid(request)):
            return r
        try:
            s = ServiceSubscription.objects.get(pk=pk)
        except ServiceSubscription.DoesNotExist:
            return Response({'error': 'یافت نشد'}, status=404)
        merged = {**_service_dict(s), **request.data}
        payload, err = _service_payload(merged)
        if err:
            return Response({'error': err}, status=400)
        for k, v in payload.items():
            setattr(s, k, v)
        s.save()
        return Response(_service_dict(s))

    def delete(self, request, pk):
        if (r := self._forbid(request)):
            return r
        deleted, _ = ServiceSubscription.objects.filter(pk=pk).delete()
        if not deleted:
            return Response({'error': 'یافت نشد'}, status=404)
        return Response({'ok': True})


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


def _offer_shipping_return():
    """فیلدهای اجباری جدید گوگل برای Offer — سیاست مرجوعی و جزئیات ارسال.
    بدون این دو فیلد سرچ کنسول روی Product snippets / Merchant listings
    اخطار زرد Missing field می‌دهد. مقادیر ثابت سیاست فروشگاه است."""
    return {
        "hasMerchantReturnPolicy": {
            "@type": "MerchantReturnPolicy",
            "applicableCountry": "IR",
            "returnPolicyCategory": "https://schema.org/MerchantReturnFiniteReturnWindow",
            "merchantReturnDays": 7,
            "returnMethod": "https://schema.org/ReturnByMail",
            "returnFees": "https://schema.org/FreeReturn",
        },
        "shippingDetails": {
            "@type": "OfferShippingDetails",
            "shippingRate": {
                "@type": "MonetaryAmount",
                "value": 0,
                "currency": "IRR",
            },
            "shippingDestination": {
                "@type": "DefinedRegion",
                "addressCountry": "IR",
            },
            "deliveryTime": {
                "@type": "ShippingDeliveryTime",
                "handlingTime": {
                    "@type": "QuantitativeValue",
                    "minValue": 0,
                    "maxValue": 1,
                    "unitCode": "DAY",
                },
                "transitTime": {
                    "@type": "QuantitativeValue",
                    "minValue": 1,
                    "maxValue": 3,
                    "unitCode": "DAY",
                },
            },
        },
    }


def _review_schema(obj):
    """aggregateRating + review از نظرهای تأییدشده دیتابیس.
    اگر نظر تأییدشده‌ای نباشد چیزی برنمی‌گردد — گوگل امتیاز ساختگی/پیش‌فرض را
    خلاف دستورالعمل می‌داند و بابتش جریمه دستی می‌دهد، پس فیلد فیک نمی‌سازیم."""
    from django.db.models import Avg
    reviews = list(obj.reviews.filter(is_approved=True).order_by("-created_at")[:10])
    if not reviews:
        return None, None
    avg = obj.reviews.filter(is_approved=True).aggregate(a=Avg("rating"))["a"]
    approved_count = obj.reviews.filter(is_approved=True).count()
    aggregate = {
        "@type": "AggregateRating",
        "ratingValue": round(float(avg), 1),
        "reviewCount": approved_count,
        "bestRating": 5,
        "worstRating": 1,
    }
    review_list = [{
        "@type": "Review",
        "author": {"@type": "Person", "name": r.author_name},
        "datePublished": r.created_at.date().isoformat(),
        "reviewBody": r.body or r.author_name,
        "reviewRating": {
            "@type": "Rating",
            "ratingValue": r.rating,
            "bestRating": 5,
            "worstRating": 1,
        },
    } for r in reviews]
    return aggregate, review_list


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
            ("نرخ فریم", obj.board_fps),
            ("رزولوشن لنز", obj.lens_resolution), ("فاصله کانونی", obj.lens_degree),
            ("کلاس نوری لنز", obj.focal_ratio), ("ضریب دیافراگم", obj.lens_aperture),
            ("سایز سنسور سازگار", obj.lens_image_size), ("نوع مانت / رزوه", obj.lens_mount),
            ("اقلام همراه", obj.lens_kit), ("فاصله پیچ هولدر", obj.lens_holder_pitch),
            ("زاویه دید افقی", obj.lens_fov),
            ("مدل", obj.modem_model), ("نوع", obj.modem_type),
            ("ولتاژ کاری", obj.voltage), ("آمپر خروجی", obj.ampere_output),
            ("جنس بدنه", obj.housing_material),
            ("سایز دوربین", obj.housing_size),
        ]
        ctx["specs"] = [(label, val) for label, val in spec_fields if val]
        if obj.has_microphone:
            ctx["specs"].append(("قابلیت میکروفون", "دارد"))
        if obj.sim_card:
            ctx["specs"].append(("قابلیت سیم‌کارت", "دارد"))
        # مشخصات سفارشی دسته — با لیبل فارسی فیلد؛ بولین True به «دارد» و False حذف می‌شود
        dyn = obj.dynamic_specs or {}
        if dyn and obj.category_id:
            cat = obj.category
            dyn_fields = []
            seen_keys = set()
            for c in ([cat.parent, cat] if cat.parent_id else [cat]):
                if c is None:
                    continue
                for f in c.spec_fields.filter(is_active=True):
                    if f.key not in seen_keys:
                        seen_keys.add(f.key)
                        dyn_fields.append(f)
            for f in dyn_fields:
                val = dyn.get(f.key)
                if isinstance(val, str) and val.strip().lower() in ("true", "false"):
                    val = val.strip().lower() == "true"
                if val not in (None, "", False):
                    ctx["specs"].append((f.label, "دارد" if val is True else val))
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
                **_offer_shipping_return(),
            }
        aggregate, review_list = _review_schema(obj)
        if aggregate:
            ld["aggregateRating"] = aggregate
            ld["review"] = review_list
        # مشخصات فنی به‌صورت PropertyValue استاندارد — خواندنی برای گوگل و موتورهای AI
        if ctx["specs"]:
            ld["additionalProperty"] = [
                {"@type": "PropertyValue", "name": label, "value": str(val)}
                for label, val in ctx["specs"]
            ]
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
                **_offer_shipping_return(),
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
