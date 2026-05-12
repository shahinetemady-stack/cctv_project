"""
apps/catalog/views.py
──────────────────────
Public API endpoints for the catalog.

GET  /api/catalog/categories/          لیست دسته‌بندی‌ها
GET  /api/catalog/products/            لیست محصولات (با فیلتر)
GET  /api/catalog/products/<slug>/     جزئیات محصول
GET  /api/catalog/products/search/     جستجوی هوشمند
GET  /api/catalog/exchange-rate/       نرخ ارز جاری
PUT  /api/catalog/exchange-rate/       بروزرسانی نرخ (فقط ادمین)
POST /api/catalog/products/bulk-upload/ آپلود اکسل (فقط ادمین)
"""

import logging
from django.db.models import Prefetch
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.views import APIView

from .filters import ProductFilter
from .models import Category, ExchangeRateSetting, Product, ProductImage, ProductVariant
from .serializers import (
    CategorySerializer,
    ExchangeRateSerializer,
    ExchangeRateUpdateSerializer,
    ProductDetailSerializer,
    ProductListSerializer,
)

logger = logging.getLogger(__name__)


# ─── Categories ───────────────────────────────────────────────────────────────

class CategoryListView(generics.ListAPIView):
    """
    GET /api/catalog/categories/
    فقط دسته‌های ریشه (parent=None) با فرزندانشان.
    """
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return (
            Category.objects.filter(is_active=True, parent__isnull=True)
            .prefetch_related("children")
            .order_by("sort_order", "name")
        )


# ─── Products ─────────────────────────────────────────────────────────────────

class ProductListView(generics.ListAPIView):
    """
    GET /api/catalog/products/
    پارامترهای فیلتر: part_type, chipset, voltage, lens_mount,
                       category, in_stock, is_featured, search
    مرتب‌سازی: ?ordering=name / -name / created_at / -created_at
    """
    serializer_class = ProductListSerializer
    permission_classes = [AllowAny]
    filterset_class = ProductFilter
    search_fields = ["name", "brand", "model_number", "chipset"]
    ordering_fields = ["name", "created_at", "is_featured"]
    ordering = ["-is_featured", "-created_at"]

    def list(self, request, *args, **kwargs):
        import math
        response = super().list(request, *args, **kwargs)
        if request.user.is_authenticated:
            try:
                discount = float(request.user.profile.discount_percent or 0)
                if discount > 0:
                    for product in response.data.get("results", response.data if isinstance(response.data, list) else []):
                        mp = product.get("min_price")
                        if mp:
                            product["partner_min_price"] = math.ceil(float(mp) * (1 - discount/100))
                            product["partner_discount_percent"] = discount
            except Exception:
                pass
        return response

    def get_queryset(self):
        qs = (
            Product.objects.filter(is_active=True)
            .select_related("category")
            .prefetch_related(
                Prefetch("images", queryset=ProductImage.objects.filter(is_primary=True)),
                Prefetch("variants", queryset=ProductVariant.objects.filter(is_active=True)),
            )
        )
        p = self.request.query_params

        # فیلترهای اختصاصی برد
        if p.get("sensor_name"):   qs = qs.filter(sensor_name__icontains=p["sensor_name"])
        if p.get("board_system"):  qs = qs.filter(board_system__icontains=p["board_system"])
        if p.get("board_resolution"): qs = qs.filter(board_resolution__icontains=p["board_resolution"])
        if p.get("sensor_size"):   qs = qs.filter(sensor_size__icontains=p["sensor_size"])

        # فیلترهای اختصاصی لنز
        if p.get("lens_degree"):   qs = qs.filter(lens_degree__icontains=p["lens_degree"])
        if p.get("lens_type"):     qs = qs.filter(lens_type__icontains=p["lens_type"])
        if p.get("focal_ratio"):   qs = qs.filter(focal_ratio__icontains=p["focal_ratio"])

        # فیلترهای اختصاصی متعلقات
        if p.get("modem_type"):    qs = qs.filter(modem_type__icontains=p["modem_type"])
        if p.get("voltage"):       qs = qs.filter(voltage__icontains=p["voltage"])
        if p.get("sim_card") == "true": qs = qs.filter(sim_card=True)

        # فیلترهای اختصاصی بدنه
        if p.get("housing_material"): qs = qs.filter(housing_material__icontains=p["housing_material"])
        if p.get("housing_type"):  qs = qs.filter(housing_type__icontains=p["housing_type"])
        if p.get("has_microphone") == "true": qs = qs.filter(has_microphone=True)

        return qs


class ProductDetailView(generics.RetrieveAPIView):
    """
    GET /api/catalog/products/<slug>/
    """
    serializer_class = ProductDetailSerializer
    permission_classes = [AllowAny]
    lookup_field = "slug"

    def get_queryset(self):
        return (
            Product.objects.filter(is_active=True)
            .select_related("category")
            .prefetch_related(
                "images",
                "variants",
                "compatible_with",
            )
        )

    def retrieve(self, request, *args, **kwargs):
        import math
        response = super().retrieve(request, *args, **kwargs)
        if request.user.is_authenticated:
            try:
                discount = float(request.user.profile.discount_percent or 0)
                if discount > 0:
                    for v in response.data.get("variants", []):
                        base = v.get("final_price", 0)
                        v["partner_price"] = math.ceil(base * (1 - discount/100))
                        v["partner_discount_percent"] = discount
            except Exception:
                pass
        return response


# ─── Smart Search ──────────────────────────────────────────────────────────────

class ProductSearchView(APIView):
    """
    GET /api/catalog/products/search/?q=<query>

    جستجوی هوشمند با اصلاح غلط‌های رایج فارسی:
    - اشتباهات رایج حروف (ک/ک، ی/ی، و/و ...)
    - جستجو در نام، برند، مدل، چیپست
    """
    permission_classes = [AllowAny]

    # نگاشت غلط‌های رایج فارسی (ساده‌ترین رویکرد بدون نیاز به کتابخانه خارجی)
    PERSIAN_CORRECTIONS = {
        "ك": "ک",   # عربی → فارسی
        "ي": "ی",   # عربی → فارسی
        "ة": "ه",
        "ؤ": "و",
        "إ": "ا",
        "أ": "ا",
        "آ": "ا",   # گاهی کاربران آ را بدون همزه می‌نویسند
    }

    def _normalize(self, text: str) -> str:
        """اصلاح حروف عربی/فارسی."""
        for wrong, correct in self.PERSIAN_CORRECTIONS.items():
            text = text.replace(wrong, correct)
        return text.strip()

    def get(self, request):
        query = request.query_params.get("q", "").strip()
        if len(query) < 2:
            return Response({"results": [], "query": query, "corrected": False})

        normalized = self._normalize(query)
        corrected = normalized != query

        from django.db.models import Q
        products = (
            Product.objects.filter(is_active=True)
            .filter(
                Q(name__icontains=normalized)
                | Q(brand__icontains=normalized)
                | Q(model_number__icontains=normalized)
                | Q(chipset__icontains=normalized)
                | Q(short_description__icontains=normalized)
            )
            .select_related("category")
            .prefetch_related(
                Prefetch("images", queryset=ProductImage.objects.filter(is_primary=True)),
                Prefetch("variants", queryset=ProductVariant.objects.filter(is_active=True)),
            )[:20]
        )

        serializer = ProductListSerializer(products, many=True, context={"request": request})
        return Response({
            "results": serializer.data,
            "count": len(serializer.data),
            "query": query,
            "normalized_query": normalized,
            "corrected": corrected,
        })


# ─── Exchange Rate ─────────────────────────────────────────────────────────────

class ExchangeRateView(APIView):
    """
    GET  /api/catalog/exchange-rate/   → نرخ ارز جاری (عموم)
    PUT  /api/catalog/exchange-rate/   → بروزرسانی (فقط ادمین)
    """

    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsAdminUser()]

    def get(self, request):
        instance = ExchangeRateSetting.get_instance()
        serializer = ExchangeRateSerializer(instance)
        return Response(serializer.data)

    def put(self, request):
        instance = ExchangeRateSetting.get_instance()
        serializer = ExchangeRateUpdateSerializer(
            instance, data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        logger.info(f"Exchange rate updated to {instance.rate_cny_to_irt} by {request.user}")
        return Response(ExchangeRateSerializer(instance).data)


# ─── Bulk Upload (Excel) ──────────────────────────────────────────────────────

@api_view(["POST"])
@permission_classes([IsAdminUser])
def bulk_upload_products(request):
    """
    POST /api/catalog/products/bulk-upload/
    Content-Type: multipart/form-data
    فیلد: file (xlsx)

    فرمت اکسل موردانتظار:
    sku | product_name | category_slug | chipset | voltage |
    lens_mount | part_type | purchase_price_usd | shipping_cost |
    profit_margin | stock_quantity
    """
    import openpyxl
    from decimal import Decimal, InvalidOperation

    file = request.FILES.get("file")
    if not file:
        return Response({"error": "فایل اکسل ارسال نشد."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        wb = openpyxl.load_workbook(file, read_only=True, data_only=True)
        ws = wb.active
    except Exception as e:
        return Response({"error": f"خطا در خواندن فایل: {e}"}, status=status.HTTP_400_BAD_REQUEST)

    results = {"created": 0, "updated": 0, "errors": []}
    headers = None

    for row_idx, row in enumerate(ws.iter_rows(values_only=True), start=1):
        if row_idx == 1:
            headers = [str(h).strip().lower() if h else "" for h in row]
            continue

        row_data = dict(zip(headers, row))
        sku = str(row_data.get("sku", "")).strip()
        if not sku:
            continue

        try:
            # دسته‌بندی
            cat_slug = str(row_data.get("category_slug", "")).strip()
            try:
                category = Category.objects.get(slug=cat_slug)
            except Category.DoesNotExist:
                results["errors"].append(f"ردیف {row_idx}: دسته '{cat_slug}' یافت نشد")
                continue

            # Product
            product_name = str(row_data.get("product_name", "")).strip()
            product, _ = Product.objects.get_or_create(
                name=product_name,
                defaults={
                    "category": category,
                    "part_type": row_data.get("part_type", "other"),
                    "chipset": str(row_data.get("chipset", "") or ""),
                    "voltage": str(row_data.get("voltage", "") or ""),
                    "lens_mount": row_data.get("lens_mount", "none"),
                },
            )

            # ProductVariant
            purchase_usd = Decimal(str(row_data.get("purchase_price_usd", 0) or 0))
            variant, created = ProductVariant.objects.update_or_create(
                sku=sku,
                defaults={
                    "product": product,
                    "purchase_price_usd": purchase_usd,
                    "shipping_cost": int(row_data.get("shipping_cost", 0) or 0),
                    "profit_margin": int(row_data.get("profit_margin", 0) or 0),
                    "stock_quantity": int(row_data.get("stock_quantity", 0) or 0),
                },
            )
            if created:
                results["created"] += 1
            else:
                results["updated"] += 1

        except (ValueError, InvalidOperation) as e:
            results["errors"].append(f"ردیف {row_idx} (SKU: {sku}): {e}")

    return Response(results, status=status.HTTP_200_OK)
