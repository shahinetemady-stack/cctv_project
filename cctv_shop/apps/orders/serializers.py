"""
apps/orders/serializers.py
────────────────────────────
"""
from rest_framework import serializers
from apps.catalog.serializers import ProductVariantSerializer
from .models import Cart, CartItem, InquiryCart, InquiryCartItem, Order, OrderItem, StockReservation


class CartItemSerializer(serializers.ModelSerializer):
    variant_detail = ProductVariantSerializer(source="variant", read_only=True)
    subtotal = serializers.IntegerField(read_only=True)

    class Meta:
        model = CartItem
        fields = ["id", "variant", "variant_detail", "quantity", "subtotal"]

    def validate(self, data):
        variant = data.get("variant") or self.instance.variant
        quantity = data.get("quantity", 1)
        if variant.available_stock < quantity:
            raise serializers.ValidationError(
                f"موجودی کافی نیست. موجودی فعلی: {variant.available_stock}"
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


class InquiryCartItemSerializer(serializers.ModelSerializer):
    variant_detail = ProductVariantSerializer(source="variant", read_only=True)

    class Meta:
        model = InquiryCartItem
        fields = ["id", "variant", "variant_detail", "quantity"]


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

    class Meta:
        model = OrderItem
        fields = [
            "id", "variant", "variant_name", "variant_sku",
            "quantity", "unit_price", "confirmed_unit_price",
            "subtotal", "reserved_until",
        ]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    order_type_display = serializers.CharField(source="get_order_type_display", read_only=True)
    effective_amount = serializers.IntegerField(read_only=True)
    is_payment_expired = serializers.BooleanField(read_only=True)

    class Meta:
        model = Order
        fields = [
            "id", "order_number", "order_type", "order_type_display",
            "status", "status_display",
            "total_amount", "confirmed_amount", "effective_amount",
            "payment_link", "payment_deadline", "is_payment_expired",
            "payment_ref_id", "paid_at",
            "shipping_address", "customer_notes",
            "items", "created_at", "updated_at",
        ]
        read_only_fields = [
            "order_number", "status", "total_amount", "confirmed_amount",
            "payment_link", "payment_deadline", "payment_ref_id", "paid_at",
        ]


class OrderAdminSerializer(OrderSerializer):
    """سریالایزر پنل ادمین — شامل یادداشت ادمین."""
    class Meta(OrderSerializer.Meta):
        fields = OrderSerializer.Meta.fields + ["admin_notes", "admin_confirm_deadline"]


class ConfirmInquirySerializer(serializers.Serializer):
    """ورودی ادمین برای تأیید سفارش استعلامی."""
    confirmed_amount = serializers.IntegerField(min_value=1)
