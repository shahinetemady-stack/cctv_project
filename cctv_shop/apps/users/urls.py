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
    path("me/phone-change-request/", views.PhoneChangeRequestView.as_view(), name="phone-change-request"),
    path("me/profile-change-request/", views.ProfileChangeRequestView.as_view(), name="profile-change-request"),
    path("admin/phone-requests/", views.AdminPhoneRequestsView.as_view(), name="admin-phone-requests"),
    path("admin/phone-requests/<int:pk>/<str:action>/", views.AdminPhoneRequestActionView.as_view(), name="admin-phone-request-action"),
    path("admin/profile-requests/", views.AdminProfileRequestsView.as_view(), name="admin-profile-requests"),
    path("admin/profile-requests/<int:pk>/<str:action>/", views.AdminProfileRequestActionView.as_view(), name="admin-profile-request-action"),
    path("admin/users/<int:user_id>/link/", views.AdminLinkAccountView.as_view(), name="admin-link-account"),
    path("me/register-partner/",  views.RegisterPartnerView.as_view(), name="register-partner"),
    # Admin
    path("admin/partners/",       views.AdminPartnerListView.as_view(),   name="admin-partner-list"),
    path("admin/partners/<int:user_id>/approve/",
         views.AdminApprovePartnerView.as_view(), name="admin-approve-partner"),
    path("club-settings/", views.ClubSettingsView.as_view(), name="club-settings"),
    path("club-info/", views.ClubInfoView.as_view(), name="club-info"),
    path("club-settings/evaluate/", views.ClubEvaluateView.as_view(), name="club-evaluate"),
    path("club-settings/at-risk/snooze/", views.ClubAtRiskSnoozeView.as_view(), name="club-at-risk-snooze"),
    path("admin/partners/<int:user_id>/guarantees/",
         views.PartnerGuaranteeListCreateView.as_view(), name="partner-guarantees"),
    path("admin/partners/<int:user_id>/guarantees/<int:gid>/",
         views.PartnerGuaranteeDeleteView.as_view(), name="partner-guarantee-delete"),
    path("admin/contacts/<int:contact_id>/guarantees/",
         views.PartnerGuaranteeListCreateView.as_view(), name="contact-guarantees"),
    path("admin/contacts/<int:contact_id>/guarantees/<int:gid>/",
         views.PartnerGuaranteeDeleteView.as_view(), name="contact-guarantee-delete"),
    path("admin-badges/", views.AdminBadgesView.as_view(), name="admin-badges"),
    path("activity-logs/", views.ActivityLogListView.as_view(), name="activity-logs"),
]
