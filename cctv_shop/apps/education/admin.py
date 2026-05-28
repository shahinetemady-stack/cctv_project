from django.contrib import admin
from .models import Video, Article, ArticleCategory


@admin.register(ArticleCategory)
class ArticleCategoryAdmin(admin.ModelAdmin):
    list_display  = ['name', 'slug', 'order']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display   = ['title', 'video_type', 'duration', 'views_count', 'is_published', 'order']
    list_filter    = ['video_type', 'is_published']
    list_editable  = ['is_published', 'order']
    search_fields  = ['title', 'description']
    prepopulated_fields = {'slug': ('title',)}
    filter_horizontal = ['related_products']
    fieldsets = (
        ('اطلاعات اصلی', {'fields': ('title', 'slug', 'description', 'video_url', 'video_type')}),
        ('جزئیات', {'fields': ('duration', 'thumbnail', 'order', 'is_published')}),
        ('محصولات مرتبط', {'fields': ('related_products',)}),
    )


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display   = ['title', 'category', 'author', 'views_count', 'is_published', 'created_at']
    list_filter    = ['category', 'is_published']
    list_editable  = ['is_published']
    search_fields  = ['title', 'description', 'content']
    prepopulated_fields = {'slug': ('title',)}
    filter_horizontal = ['related_products']
    fieldsets = (
        ('اطلاعات اصلی', {'fields': ('title', 'slug', 'description', 'category', 'author')}),
        ('محتوا', {'fields': ('content', 'thumbnail')}),
        ('متادیتا', {'fields': ('tags', 'is_published', 'related_products')}),
    )
