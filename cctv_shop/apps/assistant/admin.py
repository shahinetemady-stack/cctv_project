from django.contrib import admin

from .models import FAQ, AssistantSettings, LearnedQA


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ("question", "is_active", "order", "created_at")
    list_editable = ("is_active", "order")
    search_fields = ("question", "answer", "keywords")
    list_filter = ("is_active",)


@admin.register(AssistantSettings)
class AssistantSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        ("موتور اصلی", {"fields": ("provider",)}),
        ("Google Gemini", {"fields": ("gemini_enabled", "gemini_api_key", "gemini_model", "gemini_proxy")}),
        ("ModelScope — Qwen3 ابری (رایگان)", {"fields": ("ms_api_key", "ms_model")}),
        ("z.ai — GLM (رایگان)", {"fields": ("zai_api_key", "zai_model")}),
        ("DeepSeek", {"fields": ("ds_api_key", "ds_model")}),
        ("یادگیری", {"fields": ("learn_from_gemini",)}),
    )

    def has_add_permission(self, request):
        return not AssistantSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(LearnedQA)
class LearnedQAAdmin(admin.ModelAdmin):
    list_display = ("question", "engine", "created_at")
    search_fields = ("question", "answer")
    list_filter = ("engine",)
    readonly_fields = ("question", "answer", "engine", "created_at")
