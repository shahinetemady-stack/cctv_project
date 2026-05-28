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
]
