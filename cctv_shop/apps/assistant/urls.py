from django.urls import path

from .views import AccountingChatView, AssistantChatView, AssistantSettingsView, FAQListView, SmartSearchView

urlpatterns = [
    path("chat/", AssistantChatView.as_view(), name="assistant-chat"),
    path("accounting-chat/", AccountingChatView.as_view(), name="assistant-accounting-chat"),
    path("smart-search/", SmartSearchView.as_view(), name="assistant-smart-search"),
    path("faqs/", FAQListView.as_view(), name="assistant-faqs"),
    path("settings/", AssistantSettingsView.as_view(), name="assistant-settings"),
]
