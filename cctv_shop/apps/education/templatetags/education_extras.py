from django import template
from django.utils import timezone
from django.utils.html import format_html, format_html_join

register = template.Library()


@register.simple_tag
def due_articles_banner():
    """بنر هشدار مقاله‌های پیش‌نویسی که زمان انتشارشان رسیده است."""
    from apps.education.models import Article
    now = timezone.now()
    due = list(
        Article.objects.filter(is_published=False, publish_at__lte=now)
        .order_by("publish_at")
        .values_list("id", "title", "publish_at")
    )
    if not due:
        return ""
    items = format_html_join(
        "\n",
        "<li style=\"margin:2px 0;\"><a href=\"/admin/education/article/{}/change/\" style=\"font-weight:bold;\">{}</a>"
        " <span style=\"color:#666;\">(موعد: {})</span></li>",
        ((pk, title, timezone.localtime(pa).strftime("%Y-%m-%d %H:%M")) for pk, title, pa in due),
    )
    return format_html(
        "<div style=\"background:#fff3cd;border:1px solid #e0a800;border-radius:6px;"
        "padding:10px 14px;margin:10px 0;direction:rtl;text-align:right;\">"
        "<strong>🔔 {} مقاله به موعد انتشار رسیده‌اند — تیک «منتشر شده» را بزنید:</strong>"
        "<ul style=\"margin:6px 0 0;padding:0 18px;\">{}</ul></div>",
        len(due), items,
    )
