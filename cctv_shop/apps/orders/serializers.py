"""
apps/orders/serializers.py
────────────────────────────
"""
from rest_framework import serializers
from apps.catalog.serializers import ProductVariantSerializer
from .models import Cart, CartItem, InquiryCart, InquiryCartItem, Order, OrderItem, StockReservation


class _VariantInfoMixin(serializers.Serializer):
    """نام، SKU و عکس محصول برای نمایش آیتم سبد — variant_detail این‌ها را ندارد."""
    variant_name  = serializers.CharField(source="variant.product.name", read_only=True)
    variant_sku   = serializers.CharField(source="variant.sku", read_only=True)
    variant_image = serializers.SerializerMethodField()
    available_stock = serializers.SerializerMethodField()
    stock_short     = serializers.SerializerMethodField()

    def get_variant_image(self, obj):
        if not obj.variant_id:
            return None
        img = (
            obj.variant.product.images.filter(is_primary=True).first()
            or obj.variant.product.images.first()
        )
        if img and img.image:
            request = self.context.get("request")
            return request.build_absolute_uri(img.image.url) if request else img.image.url
        return None

    def get_available_stock(self, obj):
        # موجودی نمایشی به مشتری = فقط انبارهای با تیک «نمایش به مشتری»
        return obj.variant.sellable_stock if obj.variant_id else None

    def get_stock_short(self, obj):
        if not obj.variant_id:
            return False
        return obj.quantity > obj.variant.sellable_stock


class CartItemSerializer(_VariantInfoMixin, serializers.ModelSerializer):
    variant_detail = ProductVariantSerializer(source="variant", read_only=True)
    unit_price = serializers.IntegerField(read_only=True)
    subtotal = serializers.IntegerField(read_only=True)
    settlement_display = serializers.CharField(source="get_settlement_type_display", read_only=True)
    is_package = serializers.SerializerMethodField()
    package_name = serializers.CharField(source="package.name", read_only=True)
    package_slug = serializers.CharField(source="package.slug", read_only=True)
    package_image = serializers.SerializerMethodField()
    package_min_quantity = serializers.IntegerField(source="package.min_quantity", read_only=True)

    class Meta:
        model = CartItem
        fields = ["id", "variant", "variant_detail", "variant_name", "variant_sku",
                  "variant_image", "quantity", "settlement_type", "settlement_display",
                  "unit_price", "subtotal", "available_stock", "stock_short",
                  "is_package", "package", "package_name", "package_slug",
                  "package_image", "package_min_quantity"]

    def get_is_package(self, obj):
        return obj.package_id is not None

    def get_package_image(self, obj):
        if not obj.package_id or not obj.package.image:
            return None
        request = self.context.get("request")
        return request.build_absolute_uri(obj.package.image.url) if request else obj.package.image.url

    def validate(self, data):
        variant = data.get("variant") or self.instance.variant
        quantity = data.get("quantity", 1)
        if variant.sellable_stock < quantity:
            raise serializers.ValidationError(
                f"درخواست شما بیشتر از موجودی است — حداکثر موجودی قابل فروش این کالا {variant.sellable_stock} عدد است."
            )
        return data


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_price = serializers.IntegerField(read_only=True)
    item_count = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ["id", "items", "total_price", "item_count", "created_at"]

    def get_item_count(self, obj):
        return obj.items.count()


class InquiryCartItemSerializer(_VariantInfoMixin, serializers.ModelSerializer):
    variant_detail = ProductVariantSerializer(source="variant", read_only=True)
    settlement_display = serializers.CharField(source="get_settlement_type_display", read_only=True)

    class Meta:
        model = InquiryCartItem
        fields = ["id", "variant", "variant_detail", "variant_name", "variant_sku",
                  "variant_image", "quantity", "settlement_type", "settlement_display",
                  "available_stock", "stock_short"]


class InquiryCartSerializer(serializers.ModelSerializer):
    items = InquiryCartItemSerializer(many=True, read_only=True)
    item_count = serializers.SerializerMethodField()

    class Meta:
        model = InquiryCart
        fields = ["id", "items", "item_count", "notes", "created_at"]

    def get_item_count(self, obj):
        return obj.items.count()


class OrderItemSerializer(serializers.ModelSerializer):
    variant_name = serializers.CharField(source="variant.product.name", read_only=True)
    variant_sku = serializers.CharField(source="variant.sku", read_only=True)
    subtotal = serializers.IntegerField(read_only=True)
    settlement_display = serializers.CharField(source="get_settlement_type_display", read_only=True)
    is_settlement_due = serializers.BooleanField(read_only=True)

    class Meta:
        model = OrderItem
        fields = [
            "id", "variant", "variant_name", "variant_sku",
            "quantity", "unit_price", "confirmed_unit_price",
            "subtotal", "reserved_until",
            "settlement_type", "settlement_display", "settlement_due_date",
            "is_settlement_due",
        ]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    order_type_display = serializers.CharField(source="get_order_type_display", read_only=True)
    effective_amount = serializers.IntegerField(read_only=True)
    is_payment_expired = serializers.BooleanField(read_only=True)
    settlement_display = serializers.CharField(source="get_settlement_type_display", read_only=True)
    is_settlement_due = serializers.BooleanField(read_only=True)
    settlement_lines = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id", "order_number", "order_type", "order_type_display",
            "status", "status_display",
            "total_amount", "confirmed_amount", "effective_amount",
            "payment_link", "payment_deadline", "is_payment_expired",
            "payment_ref_id", "paid_at",
            "settlement_type", "settlement_display", "settlement_due_date",
            "is_settlement_due", "settlement_lines",
            "sarraf_account_number", "sarraf_account_holder",
            "shipping_address", "shipping_method", "freight_company",
            "tracking_code", "paid_amount", "payment_method",
            "customer_notes",
            "items", "created_at", "updated_at",
        ]
        read_only_fields = [
            "order_number", "status", "total_amount", "confirmed_amount",
            "payment_link", "payment_deadline", "payment_ref_id", "paid_at",
            "shipping_method", "freight_company", "tracking_code",
            "paid_amount", "payment_method",
        ]

    def get_settlement_lines(self, obj):
        """ردیف‌های تسویه فاکتور فروش متصل به سفارش — اگر فاکتور ندارد، لیست خالی."""
        invoice = getattr(obj, "sale_invoice", None)
        if invoice is None:
            return []
        return [{
            "id": line.id,
            "settlement_type": line.settlement_type,
            "settlement_display": line.get_settlement_type_display(),
            "amount": line.amount,
            "paid_amount": line.paid_amount,
            "remaining_amount": line.remaining_amount,
            "due_date": line.due_date.isoformat() if line.due_date else None,
            "is_overdue": line.is_overdue,
            "days_overdue": line.days_overdue,
        } for line in invoice.settlement_lines.all()]


class OrderAdminSerializer(OrderSerializer):
    """سریالایزر پنل ادمین — شامل یادداشت ادمین."""
    class Meta(OrderSerializer.Meta):
        fields = OrderSerializer.Meta.fields + ["admin_notes", "admin_confirm_deadline"]


class ConfirmInquirySerializer(serializers.Serializer):
    """ورودی ادمین برای تأیید سفارش استعلامی."""
    confirmed_amount = serializers.IntegerField(min_value=1)
    sarraf_account_number = serializers.CharField(required=False, allow_blank=True, default="")
    sarraf_account_holder = serializers.CharField(required=False, allow_blank=True, default="")


# ─── Receipts (فیش واریزی) ─────────────────────────────────────────────────────

class PaymentReceiptSerializer(serializers.ModelSerializer):
    """سریالایزر فیش واریزی — مدل در accounting است، اما API سفارشی اینجا نگه داشته می‌شود."""
    order_number = serializers.CharField(source="order.order_number", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    image_url = serializers.SerializerMethodField()
    customer_name = serializers.CharField(source="customer.get_full_name", read_only=True)
    customer_phone = serializers.CharField(source="customer.phone", read_only=True)
    uploaded_by_name = serializers.SerializerMethodField()

    class Meta:
        from apps.accounting.models import PaymentReceipt
        model = PaymentReceipt
        fields = [
            "id", "order_number", "status", "status_display", "reject_reason",
            "image", "image_url", "amount", "paid_at", "tracking_code",
            "customer_name", "customer_phone", "uploaded_by_name",
            "reviewed_at", "created_at",
        ]
        read_only_fields = fields

    def get_image_url(self, obj):
        if not obj.image:
            return None
        request = self.context.get("request")
        return request.build_absolute_uri(obj.image.url) if request else obj.image.url

    def get_uploaded_by_name(self, obj):
        if not obj.uploaded_by:
            return ""
        return obj.uploaded_by.get_full_name() or obj.uploaded_by.phone or ""
