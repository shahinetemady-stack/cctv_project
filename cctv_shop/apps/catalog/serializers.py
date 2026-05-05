"""
apps/catalog/serializers.py
─────────────────────────────
DRF serializers for the catalog app.

CategorySerializer        — دسته‌بندی‌ها (nested children)
ProductListSerializer     — لیست محصولات (سبک، برای صفحه فهرست)
ProductDetailSerializer   — جزئیات محصول (کامل، با variant‌ها)
ProductVariantSerializer  — قیمت + موجودی لحظه‌ای
ExchangeRateSerializer    — نرخ ارز جاری
"""

from rest_framework import serializers
from .models import Category, ExchangeRateSetting, Product, ProductImage, ProductVariant


class CategorySerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()
    product_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ["id", "name", "slug", "icon", "image", "parent", "children",
                  "product_count", "sort_order", "is_active"]

    def get_children(self, obj):
        # فقط یک سطح فرزند برمی‌گردانیم
        children = obj.children.filter(is_active=True)
        return CategorySerializer(children, many=True, context=self.context).data

    def get_product_count(self, obj):
        return obj.products.filter(is_active=True).count()


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ["id", "image", "alt_text", "is_primary", "sort_order"]


class ProductVariantSerializer(serializers.ModelSerializer):
    final_price = serializers.IntegerField(read_only=True)
    available_stock = serializers.IntegerField(read_only=True)
    is_in_stock = serializers.BooleanField(read_only=True)
    is_low_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = ProductVariant
        fields = [
            "id", "sku", "name_suffix",
            "final_price", "available_stock",
            "is_in_stock", "is_low_stock",
            "is_active",
        ]
        # قیمت خرید و حاشیه سود برای عموم نمایش داده نمی‌شود


class ProductListSerializer(serializers.ModelSerializer):
    """سریالایزر سبک برای صفحه لیست محصولات."""
    category_name = serializers.CharField(source="category.name", read_only=True)
    main_image = ProductImageSerializer(read_only=True)
    min_price = serializers.SerializerMethodField()
    available_stock = serializers.IntegerField(read_only=True)

    class Meta:
        model = Product
        fields = [
            "id", "name", "slug", "brand", "model_number",
            "part_type", "chipset", "voltage", "lens_mount",
            "category_name", "main_image",
            "min_price", "available_stock",
            "is_active", "is_featured",
        ]

    def get_min_price(self, obj):
        variants = obj.variants.filter(is_active=True)
        if not variants.exists():
            return None
        return min(v.final_price for v in variants)


class ProductDetailSerializer(serializers.ModelSerializer):
    """سریالایزر کامل برای صفحه جزئیات محصول."""
    category = CategorySerializer(read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    variants = ProductVariantSerializer(many=True, read_only=True)
    compatible_with = serializers.SerializerMethodField()
    has_datasheet = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id", "name", "slug", "brand", "model_number",
            "description", "short_description",
            "part_type", "chipset", "voltage", "lens_mount",
            "resolution", "extra_specs",
            "category", "images", "variants",
            "compatible_with",
            "has_datasheet", "datasheet_pdf",
            "whatsapp_link", "bale_link",
            "is_active", "is_featured",
            "meta_title", "meta_description",
            "created_at", "updated_at",
        ]

    def get_compatible_with(self, obj):
        """لیست محصولات سازگار — فقط اطلاعات پایه."""
        compatible = obj.compatible_with.filter(is_active=True)
        return [
            {
                "id": p.id,
                "name": p.name,
                "slug": p.slug,
                "part_type": p.part_type,
            }
            for p in compatible
        ]

    def get_has_datasheet(self, obj):
        return bool(obj.datasheet_pdf)


class ExchangeRateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExchangeRateSetting
        fields = ["rate_usd_to_irt", "updated_at"]


# ─── Admin-only serializers ───────────────────────────────────────────────────

class ProductVariantAdminSerializer(serializers.ModelSerializer):
    """برای پنل ادمین — شامل قیمت خرید."""
    final_price = serializers.IntegerField(read_only=True)
    available_stock = serializers.IntegerField(read_only=True)

    class Meta:
        model = ProductVariant
        fields = "__all__"


class ExchangeRateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExchangeRateSetting
        fields = ["rate_usd_to_irt"]

    def update(self, instance, validated_data):
        instance.rate_usd_to_irt = validated_data["rate_usd_to_irt"]
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            instance.updated_by = request.user
        instance.save()
        return instance
