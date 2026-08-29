from django.contrib import admin

from .models import FAQ


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ("question", "is_active", "order", "created_at")
    list_editable = ("is_active", "order")
    search_fields = ("question", "answer", "keywords")
    list_filter = ("is_active",)
