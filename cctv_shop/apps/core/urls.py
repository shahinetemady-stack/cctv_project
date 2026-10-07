from django.urls import path
from . import views

urlpatterns = [
    path('settings/', views.SiteSettingsView.as_view()),
    path('settings/logo/', views.LogoUploadView.as_view()),
    path('pages/<str:key>/', views.StaticPageView.as_view()),
    path('services/', views.ServiceSubscriptionsView.as_view()),
    path('services/<int:pk>/', views.ServiceSubscriptionDetailView.as_view()),
    path('bot/price/', views.BotPriceLookupView.as_view()),
]
