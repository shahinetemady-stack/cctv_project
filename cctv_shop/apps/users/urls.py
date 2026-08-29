from django.urls import path
from . import views

app_name = "users"

urlpatterns = [
    # Auth
    path("auth/register/",        views.RegisterView.as_view(),      name="register"),
    path("auth/register/send-code/", views.RegisterSendCodeView.as_view(), name="register-send-code"),
    path("auth/login/",           views.LoginView.as_view(),         name="login"),
    path("auth/refresh/",         views.TokenRefreshView.as_view(),  name="token-refresh"),
    path("auth/forgot-password/", views.ForgotPasswordView.as_view(), name="forgot-password"),
    path("auth/reset-password/",  views.ResetPasswordView.as_view(),  name="reset-password"),
    path("auth/logout/",          views.LogoutView.as_view(),        name="logout"),
    # Profile
    path("me/",                   views.MeView.as_view(),            name="me"),
    path("me/change-password/",   views.ChangePasswordView.as_view(), name="change-password"),
    path("me/register-partner/",  views.RegisterPartnerView.as_view(), name="register-partner"),
    # Admin
    path("admin/partners/",       views.AdminPartnerListView.as_view(),   name="admin-partner-list"),
    path("admin/partners/<int:user_id>/approve/",
         views.AdminApprovePartnerView.as_view(), name="admin-approve-partner"),
    path("admin-badges/", views.AdminBadgesView.as_view(), name="admin-badges"),
    path("activity-logs/", views.ActivityLogListView.as_view(), name="activity-logs"),
]
