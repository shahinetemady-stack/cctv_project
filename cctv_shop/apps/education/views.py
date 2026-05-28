from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAdminUser
from .models import Video, Article, ArticleCategory


class VideoListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        qs = Video.objects.filter(is_published=True)
        vtype = request.query_params.get('type')
        if vtype:
            qs = qs.filter(video_type=vtype)
        qs = qs.order_by('order', '-created_at')[:50]
        return Response([{
            'id': v.id, 'title': v.title, 'slug': v.slug,
            'description': v.description[:200],
            'video_type': v.video_type,
            'video_type_display': v.get_video_type_display(),
            'duration': v.duration,
            'views_count': v.views_count,
            'embed_url': v.get_embed_url(),
            'thumbnail': v.thumbnail.url if v.thumbnail else None,
        } for v in qs])


class VideoDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, slug):
        try:
            v = Video.objects.prefetch_related('related_products').get(
                slug=slug, is_published=True)
        except Video.DoesNotExist:
            return Response({'error': 'یافت نشد'}, status=404)
        return Response({
            'id': v.id, 'title': v.title, 'slug': v.slug,
            'description': v.description,
            'video_url': v.video_url,
            'embed_url': v.get_embed_url(),
            'video_type': v.video_type,
            'video_type_display': v.get_video_type_display(),
            'duration': v.duration,
            'views_count': v.views_count,
            'thumbnail': v.thumbnail.url if v.thumbnail else None,
            'related_products': [{'id': p.id, 'name': p.name, 'slug': p.slug}
                                  for p in v.related_products.filter(is_active=True)[:6]],
        })


class VideoViewCountView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, slug):
        Video.objects.filter(slug=slug).update(
            views_count=models.F('views_count') + 1)
        return Response({'ok': True})


class ArticleListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        qs = Article.objects.filter(is_published=True).select_related('category')
        cat = request.query_params.get('category')
        tag = request.query_params.get('tag')
        if cat:
            qs = qs.filter(category__slug=cat)
        if tag:
            qs = qs.filter(tags__contains=[tag])
        qs = qs.order_by('-created_at')[:50]
        return Response([{
            'id': a.id, 'title': a.title, 'slug': a.slug,
            'description': a.description[:200],
            'category': a.category.name if a.category else '',
            'category_slug': a.category.slug if a.category else '',
            'author': a.author,
            'tags': a.tags,
            'views_count': a.views_count,
            'likes_count': a.likes_count,
            'thumbnail': a.thumbnail.url if a.thumbnail else None,
            'created_at': a.created_at.strftime('%Y-%m-%d'),
        } for a in qs])


class ArticleDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, slug):
        try:
            a = Article.objects.prefetch_related('related_products', 'category').get(
                slug=slug, is_published=True)
        except Article.DoesNotExist:
            return Response({'error': 'یافت نشد'}, status=404)
        # افزایش بازدید
        Article.objects.filter(pk=a.pk).update(views_count=models.F('views_count') + 1)
        return Response({
            'id': a.id, 'title': a.title, 'slug': a.slug,
            'description': a.description,
            'content': a.content,
            'category': a.category.name if a.category else '',
            'category_slug': a.category.slug if a.category else '',
            'author': a.author,
            'tags': a.tags,
            'views_count': a.views_count,
            'likes_count': a.likes_count,
            'thumbnail': a.thumbnail.url if a.thumbnail else None,
            'created_at': a.created_at.strftime('%Y-%m-%d'),
            'related_products': [{'id': p.id, 'name': p.name, 'slug': p.slug}
                                  for p in a.related_products.filter(is_active=True)[:6]],
        })


class ArticleCategoryListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        cats = ArticleCategory.objects.all().order_by('order', 'name')
        return Response([{'id': c.id, 'name': c.name, 'slug': c.slug} for c in cats])


class PartSelectionGuideView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        guide = Article.objects.filter(
            tags__contains=['part-selection'], is_published=True
        ).first()
        videos = Video.objects.filter(
            video_type='part_selection', is_published=True
        )[:5]
        return Response({
            'guide': {
                'content': guide.content if guide else '',
                'title': guide.title if guide else 'راهنمای انتخاب قطعه',
            },
            'videos': [{'title': v.title, 'slug': v.slug, 'embed_url': v.get_embed_url(),
                         'duration': v.duration} for v in videos],
        })


from django.db import models
