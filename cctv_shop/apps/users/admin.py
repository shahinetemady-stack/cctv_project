from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, UserProfile, Role, StaffProfile, PartnerClubSettings, PartnerGuarantee


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    fk_name = "user"
    can_delete = False
    fields = ["user_type", "company_name", "national_id", "social_url", "document",
              "is_approved", "partner_tier", "discount_percent", "credit_limit", "address", "notes"]


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    inlines = [UserProfileInline]
    list_display  = ["phone", "get_full_name", "is_active", "is_staff", "date_joined"]
    list_filter   = ["is_active", "is_staff"]
    search_fields = ["phone", "email", "first_name", "last_name"]
    ordering      = ["-date_joined"]

    fieldsets = (
        (None, {"fields": ("phone", "email", "password")}),
        ("اطلاعات شخصی", {"fields": ("first_name", "last_name")}),
        ("دسترسی‌ها", {"fields": ("is_active", "is_staff", "is_superuser")}),
        ("تاریخ‌ها", {"fields": ("date_joined", "last_login"), "classes": ("collapse",)}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("phone", "password1", "password2", "first_name", "last_name"),
        }),
    )


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display  = ["name", "description", "perm_count", "is_active"]
    list_filter   = ["is_active"]
    search_fields = ["name"]

    def perm_count(self, obj):
        return len(obj.permissions)
    perm_count.short_description = "تعداد دسترسی"


@admin.register(StaffProfile)
class StaffProfileAdmin(admin.ModelAdmin):
    list_display  = ["user", "role", "employee_id", "department", "is_active"]
    list_filter   = ["role", "is_active"]
    search_fields = ["user__phone", "user__first_name", "employee_id"]


@admin.register(PartnerClubSettings)
class PartnerClubSettingsAdmin(admin.ModelAdmin):
    list_display = ["__str__", "silver_to_gold_amount", "gold_to_platinum_amount",
                    "period_months", "auto_evaluate_enabled", "updated_at"]

    def has_add_permission(self, request):
        return False  # سینگلتون — فقط ویرایش

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(PartnerGuarantee)
class PartnerGuaranteeAdmin(admin.ModelAdmin):
    list_display  = ["profile", "guarantee_type", "amount_rials", "created_by", "created_at"]
    list_filter   = ["guarantee_type"]
    search_fields = ["profile__user__phone", "profile__user__first_name", "profile__user__last_name"]
