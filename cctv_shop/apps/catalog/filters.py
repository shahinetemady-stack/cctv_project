import django_filters
from django.db.models import Q
from .models import Category, Product


class ProductFilter(django_filters.FilterSet):
    category = django_filters.ModelChoiceFilter(
        queryset=Category.objects.filter(is_active=True),
        label="دسته‌بندی",
        method="filter_category",
    )
    category_slug = django_filters.CharFilter(
        method="filter_category_slug",
        label="اسلاگ دسته",
    )
    category_type = django_filters.CharFilter(
        field_name="category__category_type",
        label="نوع دسته",
    )
    brand = django_filters.CharFilter(
        field_name="brand", lookup_expr="icontains", label="شرکت سازنده",
    )
    in_stock = django_filters.BooleanFilter(
        method="filter_in_stock", label="فقط موجود",
    )
    is_featured = django_filters.BooleanFilter(
        field_name="is_featured", label="فقط ویژه",
    )
    discounted = django_filters.BooleanFilter(
        method="filter_discounted", label="فقط تخفیف‌دار",
    )
    search = django_filters.CharFilter(
        method="filter_search", label="جستجو",
    )

    class Meta:
        model = Product
        fields = []

    def filter_category(self, queryset, name, value):
        if not value:
            return queryset
        ids = list(value.children.filter(is_active=True).values_list("id", flat=True))
        ids.append(value.id)
        return queryset.filter(category_id__in=ids)

    def filter_category_slug(self, queryset, name, value):
        if not value:
            return queryset
        try:
            cat = Category.objects.get(slug=value, is_active=True)
        except Category.DoesNotExist:
            return queryset.none()
        ids = list(cat.children.filter(is_active=True).values_list("id", flat=True))
        ids.append(cat.id)
        return queryset.filter(category_id__in=ids)

    def filter_discounted(self, queryset, name, value):
        if value is None:
            return queryset
        qs = queryset.filter(variants__is_active=True, variants__discount_percent__gt=0).distinct()
        if value:
            return qs
        return queryset.exclude(pk__in=qs.values("pk"))

    @staticmethod
    def _sellable_variants_q():
        """
        شرط «موجودی قابل فروش» برای واریانت — فقط انبارهای با تیک «نمایش به مشتری»
        منهای رزروشده. واریانت بدون رکورد انبار (داده قدیمی) از موجودی کل خودش سنجیده می‌شود.
        """
        from django.db.models import Exists, OuterRef, Subquery, Sum, IntegerField, Q, F
        from django.db.models.functions import Coalesce
        from apps.inventory.models import WarehouseStock
        from .models import ProductVariant

        public_stock = Coalesce(Subquery(
            WarehouseStock.objects.filter(
                variant_id=OuterRef("pk"),
                warehouse__is_public=True, warehouse__is_active=True,
            ).values("variant_id").annotate(t=Sum("quantity")).values("t"),
            output_field=IntegerField(),
        ), 0)
        has_warehouse = Exists(
            WarehouseStock.objects.filter(variant_id=OuterRef("pk"), warehouse__is_active=True)
        )
        return Q(
            variants__in=ProductVariant.objects.filter(is_active=True)
            .annotate(_public=public_stock, _has_wh=has_warehouse)
            .filter(
                Q(_has_wh=False, stock_quantity__gt=F("reserved_qty"))
                | Q(_has_wh=True, _public__gt=F("reserved_qty"))
            )
        )

    def filter_in_stock(self, queryset, name, value):
        if value is None:
            return queryset
        cond = self._sellable_variants_q()
        if value:
            return queryset.filter(cond).distinct()
        return queryset.exclude(cond).distinct()

    def filter_search(self, queryset, name, value):
        if not value:
            return queryset
        # نرمال‌سازی ارقام فارسی/عربی به لاتین تا «۸۰۰» هم مثل «800» جستجو شود
        value = value.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789"))
        value = value.replace("ك", "ک").replace("ي", "ی")
        return queryset.filter(
            Q(name__icontains=value)
            | Q(brand__icontains=value)
            | Q(model_number__icontains=value)
            | Q(board_name__icontains=value)
            | Q(sensor_name__icontains=value)
            | Q(lens_name__icontains=value)
            | Q(short_description__icontains=value)
        )
