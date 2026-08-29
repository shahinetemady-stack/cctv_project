from django.urls import path
from . import views

urlpatterns = [
    path('videos/', views.VideoListView.as_view()),
    path('videos/<str:slug>/', views.VideoDetailView.as_view()),
    path('videos/<str:slug>/view/', views.VideoViewCountView.as_view()),
    path('articles/', views.ArticleListView.as_view()),
    path('articles/<str:slug>/', views.ArticleDetailView.as_view()),
    path('categories/', views.ArticleCategoryListView.as_view()),
    path('guides/part-selection/', views.PartSelectionGuideView.as_view()),
    # مدیریت محتوی (ادمین)
    path('admin/articles/', views.AdminArticleListView.as_view()),
    path('admin/articles/<int:pk>/', views.AdminArticleDetailView.as_view()),
    path('admin/upload-image/', views.AdminArticleImageUploadView.as_view()),
    path('admin/article-categories/', views.AdminArticleCategoryListView.as_view()),
    path('admin/article-categories/<int:pk>/', views.AdminArticleCategoryDetailView.as_view()),
    path('admin/videos/', views.AdminVideoListView.as_view()),
    path('admin/videos/<int:pk>/', views.AdminVideoDetailView.as_view()),
]
