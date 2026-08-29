from django.urls import path
from . import views

app_name = "notifications"

urlpatterns = [
    path("sms-settings/", views.SmsSettingsView.as_view(), name="sms-settings"),
    path("sms-campaign/segments/", views.SmsCampaignSegmentsView.as_view(), name="sms-campaign-segments"),
    path("sms-campaign/send/", views.SmsCampaignSendView.as_view(), name="sms-campaign-send"),
]
