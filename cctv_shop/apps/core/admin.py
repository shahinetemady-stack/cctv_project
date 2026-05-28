from django.contrib import admin
from .models import SiteSettings, StaticPage


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        ("اطلاعات پایه", {"fields": ("site_name", "site_logo")}),
        ("تماس", {"fields": ("contact_phone", "contact_email", "contact_address", "working_hours")}),
        ("شبکه‌های اجتماعی", {"fields": (
            "whatsapp_number", "bale_username", "eitaa_username",
            "telegram_username", "instagram_username",
        )}),
        ("درباره ما", {"fields": ("about_us_text",)}),
        ("حساب‌های بانکی", {"fields": ("bank_accounts",)}),
    )

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(StaticPage)
class StaticPageAdmin(admin.ModelAdmin):
    list_display = ["key", "title", "updated_at"]
    fields = ["key", "title", "content"]
