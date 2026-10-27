"""
apps/catalog/serializers.py
"""
from rest_framework import serializers
from .models import Category, CategorySpecField, DatasheetPage, ExchangeRateSetting, Product, ProductImage, ProductVariant


class CategorySpecFieldSerializer(serializers.ModelSerializer):
    """ویژگی‌های تعریف‌شده برای دسته — برای ساخت فیلترهای پویا در فرانت"""

    class Meta:
        model = CategorySpecField
        fields = ["key", "label", "field_type", "choices", "sort_order", "is_filterable"]


class CategorySerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()
    product_count = serializers.SerializerMethodField()
    spec_fields = serializers.SerializerMethodField()
    brands = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ["id", "name", "slug", "category_type", "icon", "image",
                  "description", "meta_title", "meta_description",
                  "parent", "children", "product_count", "spec_fields", "brands",
                  "sort_order", "is_active"]

    def get_children(self, obj):
        children = obj.children.filter(is_active=True)
        return CategorySerializer(children, many=True, context=self.context).data

    def get_product_count(self, obj):
        return obj.get_active_product_count()

    def get_spec_fields(self, obj):
        qs = obj.spec_fields.filter(is_active=True).order_by("sort_order", "id")
        return CategorySpecFieldSerializer(qs, many=True).data

    def get_brands(self, obj):
        # برندهای تعریف‌شده برای دسته (مدیریت برندها در ادمین) + برندهای در حال استفاده
        cat_ids = [obj.id, *obj.children.values_list("id", flat=True)]
        used = (Product.objects.filter(category_id__in=cat_ids, is_active=True)
                .exclude(brand__isnull=True).exclude(brand="")
                .values_list("brand", flat=True).distinct())
        defined = obj.brands.values_list("name", flat=True)
        return sorted(set(used) | set(defined))


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ["id", "image", "alt_text", "is_primary", "sort_order"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')
        if request and data.get('image'):
            data['image'] = request.build_absolute_uri(data['image'])
        return data


class DatasheetPageSerializer(serializers.ModelSerializer):
    class Meta:
        model = DatasheetPage
        fields = ["id", "image", "page"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')
        if request and data.get('image'):
            data['image'] = request.build_absolute_uri(data['image'])
        return data


class ProductVariantSerializer(serializers.ModelSerializer):
    # موجودی نمایشی به مشتری = فقط انبارهای با تیک «نمایش به مشتری» (sellable_stock)
    final_price     = serializers.IntegerField(read_only=True)
    discount_percent = serializers.FloatField(read_only=True)
    available_stock = serializers.IntegerField(source="sellable_stock", read_only=True)
    is_in_stock     = serializers.SerializerMethodField()
    is_low_stock    = serializers.SerializerMethodField()
    pricing         = serializers.SerializerMethodField()

    class Meta:
        model  = ProductVariant
        fields = ["id", "sku", "name_suffix", "final_price", "discount_percent",
                  "available_stock",
                  "is_in_stock", "is_low_stock", "is_active", "pricing"]

    def get_is_in_stock(self, obj):
        return obj.sellable_stock > 0

    def get_is_low_stock(self, obj):
        from django.conf import settings
        return 0 < obj.sellable_stock <= getattr(settings, "LOW_STOCK_THRESHOLD", 5)

    def get_pricing(self, obj):
        """قیمت فرمول بر اساس سطح همکاری کاربر درخواست‌دهنده."""
        from .pricing import variant_pricing_payload
        request = self.context.get("request")
        return variant_pricing_payload(obj, request.user if request else None)


class ProductListSerializer(serializers.ModelSerializer):
    category_name   = serializers.CharField(source="category", read_only=True)  # «والد / زیردسته» از __str__ دسته
    category_type   = serializers.CharField(source="category.category_type", read_only=True)
    main_image      = serializers.SerializerMethodField()
    secondary_image = serializers.SerializerMethodField()
    min_price       = serializers.SerializerMethodField()
    min_price_original = serializers.SerializerMethodField()
    discount_percent   = serializers.SerializerMethodField()
    # موجودی نمایشی به مشتری = فقط انبارهای با تیک «نمایش به مشتری»
    available_stock = serializers.IntegerField(source="sellable_stock", read_only=True)
    # وضعیت نمایشی — «به‌زودی» خودکار وقتی فروشگاه خالی ولی کالا در راه هوایی است
    availability = serializers.CharField(source="effective_availability", read_only=True)
    # فقط برای پرسنل — موجودی واقعی کل + تفکیک انبار (برای صفحه مدیریت محصولات)
    total_stock = serializers.SerializerMethodField()
    stocks = serializers.SerializerMethodField()

    class Meta:
        model  = Product
        fields = [
            "id", "name", "slug", "brand", "model_number",
            "category_id", "category_name", "category_type", "main_image",
            "secondary_image",
            "min_price", "min_price_original", "discount_percent",
            "available_stock", "total_stock", "stocks", "is_active", "is_featured", "availability",
            # ویژگی‌های برد
            "board_name", "board_system", "board_resolution",
            "sensor_name", "sensor_size",
            # ویژگی‌های لنز
            "lens_name", "lens_resolution", "lens_degree", "focal_ratio",
            "lens_aperture", "lens_image_size", "lens_mount", "lens_kit", "lens_holder_pitch", "lens_fov",
            # ویژگی‌های متعلقات
            "modem_model", "modem_type", "voltage",
            # ویژگی‌های بدنه
            "housing_material", "housing_size",
        ]

    def _is_staff(self):
        request = self.context.get("request")
        return bool(request and request.user.is_authenticated and request.user.is_staff)

    def get_total_stock(self, obj):
        """موجودی واقعی کل (همه انبارها) — فقط برای پرسنل، وگرنه None."""
        if not self._is_staff():
            return None
        return sum(v.stock_quantity for v in obj.variants.all())

    def get_stocks(self, obj):
        """موجودی به تفکیک انبار (جمع واریانت‌ها در هر انبار) — فقط برای پرسنل."""
        if not self._is_staff():
            return None
        agg = {}
        for v in obj.variants.all():
            for ws in v.warehouse_stocks.all():
                if not ws.warehouse.is_active or ws.quantity <= 0:
                    continue
                e = agg.setdefault(ws.warehouse.name, {"quantity": 0, "is_public": ws.warehouse.is_public})
                e["quantity"] += ws.quantity
        return [{"warehouse": name, **d} for name, d in sorted(agg.items())]

    def get_main_image(self, obj):
        img = obj.images.filter(is_primary=True).first() or obj.images.first()
        if img:
            return ProductImageSerializer(img, context=self.context).data
        return None

    def get_secondary_image(self, obj):
        """تصویر دوم محصول (غیر از تصویر اصلی) — برای افکت چرخش هاور در کارت محصول."""
        primary = obj.images.filter(is_primary=True).first() or obj.images.first()
        qs = obj.images.exclude(pk=primary.pk) if primary else obj.images.none()
        img = qs.first()
        if img:
            return ProductImageSerializer(img, context=self.context).data
        return None

    def get_min_price(self, obj):
        """کمترین قیمت فرمول با کلید متناسب با سطح همکاری کاربر (با اعمال تخفیف)."""
        variants = obj.variants.filter(is_active=True)
        if not variants.exists():
            return None
        from .pricing import formula_prices, user_price_key
        request = self.context.get("request")
        key, _ = user_price_key(request.user if request else None)
        return min(formula_prices(v)[key] for v in variants)

    def get_discount_percent(self, obj):
        """بیشترین درصد تخفیف بین واریانت‌های فعال — ۰ یعنی بدون تخفیف."""
        variants = obj.variants.filter(is_active=True)
        if not variants.exists():
            return 0
        return float(max((v.discount_percent or 0) for v in variants))

    def get_min_price_original(self, obj):
        """کمترین قیمت فرمول قبل از تخفیف — فقط وقتی محصول تخفیف دارد (برای نمایش خط‌خورده)."""
        variants = obj.variants.filter(is_active=True)
        if not variants.exists() or not any((v.discount_percent or 0) > 0 for v in variants):
            return None
        from .pricing import base_prices, user_price_key
        request = self.context.get("request")
        key, _ = user_price_key(request.user if request else None)
        return min(base_prices(v)[key] for v in variants)


class ProductDetailSerializer(serializers.ModelSerializer):
    category       = CategorySerializer(read_only=True)
    images         = ProductImageSerializer(many=True, read_only=True)
    datasheet_pages = DatasheetPageSerializer(many=True, read_only=True)
    variants       = ProductVariantSerializer(many=True, read_only=True)
    compatible_with = serializers.SerializerMethodField()
    has_datasheet  = serializers.SerializerMethodField()
    specs          = serializers.SerializerMethodField()
    rating         = serializers.SerializerMethodField()
    # وضعیت نمایشی — «به‌زودی» خودکار وقتی فروشگاه خالی ولی کالا در راه هوایی است
    availability = serializers.CharField(source="effective_availability", read_only=True)

    class Meta:
        model  = Product
        fields = [
            "id", "name", "slug", "brand", "model_number",
            "description", "short_description",
            "category", "images", "variants", "compatible_with",
            "has_datasheet", "datasheet_pdf", "datasheet_pages",
            "whatsapp_link", "bale_link",
            "is_active", "is_featured", "availability",
            "meta_title", "meta_description", "keywords", "geo_tags",
            # ویژگی‌های برد
            "board_name", "board_system", "board_resolution",
            "sensor_name", "sensor_size", "ai_processor", "board_dimensions", "board_fps",
            "board_tech_notes",
            # ویژگی‌های لنز
            "lens_resolution", "lens_degree", "focal_ratio",
            "lens_aperture", "lens_image_size", "lens_mount", "lens_kit", "lens_holder_pitch", "lens_fov",
            # ویژگی‌های متعلقات
            "modem_model", "modem_type", "pin_count", "voltage",
            "ampere_output", "sim_card", "output_ports", "modem_size",
            # ویژگی‌های بدنه
            "housing_material", "housing_size", "has_microphone",
            # فیلد محاسبه‌شده
            "specs", "rating",
            "created_at", "updated_at",
        ]

    def get_rating(self, obj):
        """خلاصه امتیاز از نظرهای تأییدشده — برای aggregateRating در اسکیمای SPA."""
        from django.db.models import Avg, Count
        agg = obj.reviews.filter(is_approved=True).aggregate(a=Avg("rating"), c=Count("id"))
        if not agg["c"]:
            return None
        return {"average": round(float(agg["a"]), 1), "count": agg["c"]}

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
            add("پردازنده",       obj.ai_processor)
            add("ابعاد",          obj.board_dimensions)
            add("نرخ فریم",       obj.board_fps)
            add("شرکت سازنده",    obj.brand)
            if obj.has_microphone:
                add("میکروفون داخلی", "دارد")
            add("اطلاعات فنی بیشتر", obj.board_tech_notes)

        elif cat_type == "lens":
            add("رزولوشن",        obj.lens_resolution)
            add("فاصله کانونی",   obj.lens_degree)
            add("کلاس نوری لنز",  obj.focal_ratio)
            add("ضریب دیافراگم",  obj.lens_aperture)
            add("سایز سنسور سازگار", obj.lens_image_size)
            add("نوع مانت / رزوه", obj.lens_mount)
            add("اقلام همراه",    obj.lens_kit)
            add("فاصله پیچ هولدر", obj.lens_holder_pitch)
            add("زاویه دید افقی (FOV)", obj.lens_fov)
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

        elif cat_type == "accessory":
            add("مدل",            obj.modem_model)
            add("نوع",            obj.modem_type)
            add("ولتاژ کاری",     obj.voltage)
            add("سایز",           obj.modem_size)

        elif cat_type == "housing":
            add("جنس بدنه",       obj.housing_material)
            add("سایز",           obj.housing_size)
            if obj.has_microphone:
                add("قابلیت میکروفون", "دارد")

        # ویژگی‌های سفارشی داینامیک دسته (تعریف‌شده توسط ادمین)
        # ویژگی‌های دسته اصلی به زیردسته‌هایش هم می‌رسد (والد اول، بعد خود دسته)
        if obj.category_id and obj.dynamic_specs:
            cat = obj.category
            cats = [cat.parent, cat] if cat.parent_id else [cat]
            seen = set()
            for c in cats:
                for f in c.spec_fields.filter(is_active=True):
                    if f.key in seen:
                        continue
                    seen.add(f.key)
                    val = obj.dynamic_specs.get(f.key)
                    if isinstance(val, str) and val.strip().lower() in ("true", "false"):
                        val = val.strip().lower() == "true"
                    if val not in (None, "", False):
                        specs.append({"label": f.label, "value": "دارد" if val is True else val})

        return specs


class ExchangeRateSerializer(serializers.ModelSerializer):
    class Meta:
        model  = ExchangeRateSetting
        fields = ["rate_cny_to_irt"]


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
