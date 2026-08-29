from django.urls import path

from .views import AssistantChatView, FAQListView, SmartSearchView

urlpatterns = [
    path("chat/", AssistantChatView.as_view(), name="assistant-chat"),
    path("smart-search/", SmartSearchView.as_view(), name="assistant-smart-search"),
    path("faqs/", FAQListView.as_view(), name="assistant-faqs"),
]
