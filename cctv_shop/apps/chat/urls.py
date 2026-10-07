from django.urls import path

from . import views

urlpatterns = [
    path("mine/", views.MyChatView.as_view(), name="chat-mine"),
    path("mine/unread/", views.MyChatUnreadView.as_view(), name="chat-mine-unread"),
    path("mine/assign/", views.MyChatAssignView.as_view(), name="chat-mine-assign"),
    path("staff-list/", views.StaffListView.as_view(), name="chat-staff-list"),
    path("conversations/", views.ConversationListView.as_view(), name="chat-conversations"),
    path("conversations/start/", views.ConversationStartView.as_view(), name="chat-start"),
    path("user-search/", views.ChatUserSearchView.as_view(), name="chat-user-search"),
    path("conversations/<int:pk>/messages/", views.ConversationMessagesView.as_view(), name="chat-messages"),
    path("conversations/<int:pk>/close/", views.ConversationCloseView.as_view(), name="chat-close"),
]
