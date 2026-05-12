"""
apps/catalog/serializers.py
"""
from rest_framework import serializers
from .models import Category, ExchangeRateSetting, Product, ProductImage, ProductVariant


class CategorySerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()
    product_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ["id", "name", "slug", "category_type", "icon", "image",
                  "parent", "children", "product_count", "sort_order", "is_active"]

    def get_children(self, obj):
        children = obj.children.filter(is_active=True)
        return CategorySerializer(children, many=True, context=self.context).data

    def get_product_count(self, obj):
        return obj.products.filter(is_active=True).count()


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ["id", "image", "alt_text", "is_primary", "sort_order"]


class ProductVariantSerializer(serializers.ModelSerializer):
    final_price     = serializers.IntegerField(read_only=True)
    available_stock = serializers.IntegerField(read_only=True)
    is_in_stock     = serializers.BooleanField(read_only=True)
    is_low_stock    = serializers.BooleanField(read_only=True)

    class Meta:
        model  = ProductVariant
        fields = ["id", "sku", "name_suffix", "final_price",
                  "available_stock",
                  "is_in_stock", "is_low_stock", "is_active"]


class ProductListSerializer(serializers.ModelSerializer):
    category_name   = serializers.CharField(source="category.name", read_only=True)
    category_type   = serializers.CharField(source="category.category_type", read_only=True)
    main_image      = serializers.SerializerMethodField()
    min_price       = serializers.SerializerMethodField()
    available_stock = serializers.IntegerField(read_only=True)

    class Meta:
        model  = Product
        fields = [
            "id", "name", "slug", "brand", "model_number",
            "category_name", "category_type", "main_image",
            "min_price", "available_stock", "is_active", "is_featured",
            # ویژگی‌های برد
            "board_name", "board_system", "board_resolution",
            "sensor_name", "sensor_size",
            # ویژگی‌های لنز
            "lens_name", "lens_resolution", "lens_degree", "lens_type",
            # ویژگی‌های متعلقات
            "modem_model", "modem_type", "voltage",
            # ویژگی‌های بدنه
            "housing_material", "housing_type", "housing_size",
        ]

    def get_main_image(self, obj):
        img = obj.images.filter(is_primary=True).first() or obj.images.first()
        if img:
            return ProductImageSerializer(img, context=self.context).data
        return None

    def get_min_price(self, obj):
        variants = obj.variants.filter(is_active=True)
        if not variants.exists():
            return None
        return min(v.final_price for v in variants)


class ProductDetailSerializer(serializers.ModelSerializer):
    category       = CategorySerializer(read_only=True)
    images         = ProductImageSerializer(many=True, read_only=True)
    variants       = ProductVariantSerializer(many=True, read_only=True)
    compatible_with = serializers.SerializerMethodField()
    has_datasheet  = serializers.SerializerMethodField()
    specs          = serializers.SerializerMethodField()

    class Meta:
        model  = Product
        fields = [
            "id", "name", "slug", "brand", "model_number",
            "description", "short_description",
            "category", "images", "variants", "compatible_with",
            "has_datasheet", "datasheet_pdf",
            "whatsapp_link", "bale_link",
            "is_active", "is_featured",
            "meta_title", "meta_description",
            # ویژگی‌های برد
            "board_name", "board_system", "board_resolution",
            "sensor_name", "sensor_size", "ai_processor", "board_dimensions",
            # ویژگی‌های لنز
            "lens_name", "lens_resolution", "lens_degree", "lens_type", "focal_ratio",
            # ویژگی‌های متعلقات
            "modem_model", "modem_type", "pin_count", "voltage",
            "ampere_output", "sim_card", "output_ports", "modem_size",
            # ویژگی‌های بدنه
            "housing_material", "housing_type", "housing_size", "has_microphone",
            # فیلد محاسبه‌شده
            "specs",
            "created_at", "updated_at",
        ]

    def get_compatible_with(self, obj):
        return [
            {"id": p.id, "name": p.name, "slug": p.slug}
            for p in obj.compatible_with.filter(is_active=True)
        ]

    def get_has_datasheet(self, obj):
        return bool(obj.datasheet_pdf)

    def get_specs(self, obj):
        """
        فقط ویژگی‌های پر شده بر اساس نوع دسته برمی‌گرداند.
        فیلد خالی نمایش داده نمی‌شود.
        """
        cat_type = obj.category.category_type if obj.category_id else None
        specs = []

        def add(label, value):
            if value is not None and value != '' and value is not False:
                specs.append({"label": label, "value": value})

        if cat_type == "board":
            add("نام برد",        obj.board_name)
            add("سیستم",          obj.board_system)
            add("رزولوشن",        obj.board_resolution)
            add("نام سنسور",      obj.sensor_name)
            add("اندازه سنسور",   obj.sensor_size)
            add("AI پردازنده",    obj.ai_processor)
            add("ابعاد",          obj.board_dimensions)
            add("شرکت سازنده",    obj.brand)

        elif cat_type == "lens":
            add("نام لنز",        obj.lens_name)
            add("رزولوشن",        obj.lens_resolution)
            add("درجه لنز",       obj.lens_degree)
            add("نوع",            obj.lens_type)
            add("نسبت کانونی",    obj.focal_ratio)
            add("شرکت سازنده",    obj.brand)

        elif cat_type == "modem":
            add("مدل",            obj.modem_model)
            add("نوع",            obj.modem_type)
            add("تعداد پین",      obj.pin_count)
            add("ولتاژ کاری",     obj.voltage)
            add("آمپر خروجی",     obj.ampere_output)
            if obj.sim_card:
                add("قابلیت سیم کارت", "دارد")
            if obj.output_ports:
                add("تعداد پورت خروجی", str(obj.output_ports))
            add("سایز",           obj.modem_size)

        elif cat_type == "housing":
            add("جنس بدنه",       obj.housing_material)
            add("نوع بدنه",       obj.housing_type)
            add("سایز",           obj.housing_size)
            if obj.has_microphone:
                add("قابلیت میکروفون", "دارد")

        return specs


class ExchangeRateSerializer(serializers.ModelSerializer):
    class Meta:
        model  = ExchangeRateSetting
        fields = ["rate_cny_to_irt", "updated_at"]


class ProductVariantAdminSerializer(serializers.ModelSerializer):
    final_price     = serializers.IntegerField(read_only=True)
    available_stock = serializers.IntegerField(read_only=True)

    class Meta:
        model  = ProductVariant
        fields = "__all__"


class ExchangeRateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model  = ExchangeRateSetting
        fields = ["rate_cny_to_irt"]

    def update(self, instance, validated_data):
        instance.rate_cny_to_irt = validated_data["rate_cny_to_irt"]
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            instance.updated_by = request.user
        instance.save()
        return instance
