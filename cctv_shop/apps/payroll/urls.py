from django.urls import path

from . import views

app_name = "payroll"

urlpatterns = [
    path("staff/", views.StaffListView.as_view()),
    path("profiles/", views.PayrollProfileListView.as_view()),
    path("profiles/<int:pk>/", views.PayrollProfileDetailView.as_view()),
    path("leaves/", views.LeaveListView.as_view()),
    path("leaves/<int:pk>/", views.LeaveDetailView.as_view()),
    path("bonus-penalties/", views.BonusPenaltyListView.as_view()),
    path("bonus-penalties/<int:pk>/", views.BonusPenaltyDetailView.as_view()),
    path("payslips/", views.PayslipListView.as_view()),
    path("payslips/open/", views.OpenPayslipsView.as_view()),
    path("payslips/generate/", views.PayslipGenerateView.as_view()),
    path("payslips/<int:pk>/", views.PayslipDetailView.as_view()),
    path("payslips/<int:pk>/recalculate/", views.PayslipRecalculateView.as_view()),
    path("payslips/<int:pk>/confirm/", views.PayslipConfirmView.as_view()),
    path("payslips/<int:pk>/pay/", views.PayslipPayView.as_view()),
]
