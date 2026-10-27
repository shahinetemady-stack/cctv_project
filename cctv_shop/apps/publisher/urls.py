from django.urls import path

from . import views

urlpatterns = [
    path("platforms/", views.PlatformListView.as_view(), name="publisher-platforms"),
    path("credentials/", views.CredentialListView.as_view(), name="publisher-credentials"),
    path("credentials/save/", views.CredentialSaveView.as_view(), name="publisher-credentials-save"),
    path("settings/", views.PublisherSettingsView.as_view(), name="publisher-settings"),
    path("posts/", views.PostListCreateView.as_view(), name="publisher-posts"),
    path("posts/<int:pk>/approve/", views.PostApproveView.as_view(), name="publisher-post-approve"),
    path("posts/<int:pk>/reject/", views.PostRejectView.as_view(), name="publisher-post-reject"),
    path("posts/<int:pk>/build-media/", views.PostBuildMediaView.as_view(), name="publisher-post-build-media"),
    path("posts/<int:pk>/generate-hook/", views.PostGenerateHookView.as_view(), name="publisher-post-generate-hook"),
    path("posts/<int:pk>/style/", views.PostStyleView.as_view(), name="publisher-post-style"),
    path("ideas/", views.IdeaListCreateView.as_view(), name="publisher-ideas"),
    path("publish/", views.PublishCreateView.as_view(), name="publisher-publish"),
    path("jobs/", views.JobListView.as_view(), name="publisher-jobs"),
    path("jobs/<int:pk>/", views.JobDetailView.as_view(), name="publisher-job-detail"),
    path("logs/<int:pk>/retry/", views.LogRetryView.as_view(), name="publisher-log-retry"),
    path("music/", views.MusicTrackListCreateView.as_view(), name="publisher-music"),
    path("insights/", views.InsightListView.as_view(), name="publisher-insights"),
]
