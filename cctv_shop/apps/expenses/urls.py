from django.urls import path

from . import views

app_name = "expenses"

urlpatterns = [
    path("categories/", views.CategoryListView.as_view()),
    path("categories/<int:pk>/", views.CategoryDetailView.as_view()),
    path("categories/<int:pk>/contacts/", views.CategoryContactsView.as_view()),
    path("recurring/", views.RecurringListView.as_view()),
    path("recurring/<int:pk>/", views.RecurringDetailView.as_view()),
    path("recurring/<int:pk>/kardex/", views.RecurringKardexView.as_view()),
    path("charges/", views.ChargeListView.as_view()),
    path("charges/open/", views.OpenChargesView.as_view()),
    path("charges/<int:pk>/", views.ChargeDetailView.as_view()),
    path("charges/<int:pk>/delete/", views.ChargeDeleteView.as_view()),
    path("charges/<int:pk>/pay/", views.ChargePayView.as_view()),
    path("investors/", views.InvestorListView.as_view()),
    path("investors/<int:pk>/", views.InvestorDetailView.as_view()),
    path("investors/<int:pk>/kardex/", views.InvestorKardexView.as_view()),
    path("investor-movements/", views.InvestorMovementListView.as_view()),
    path("accrue-month/", views.AccrueMonthView.as_view()),
]
