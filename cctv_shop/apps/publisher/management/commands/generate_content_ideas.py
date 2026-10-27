"""
کامند تولید ایدهٔ محتوای اینستاگرام با LLM — برای هر ایده یک ContentIdea و یک
پیش‌نویس ChannelPost (approval_status=draft) ساخته می‌شود؛ پیش‌نویس‌ها در پنل
تأیید/رد و زمان‌بندی می‌شوند.

مثال:
    python manage.py generate_content_ideas --count 5 --type reel
    python manage.py generate_content_ideas --dry-run --count 2
"""

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Exists, OuterRef

from apps.catalog.models import Product, ProductImage
from apps.education.models import Article

from ...contentgen import generate_ideas
from ...models import ChannelPost, ContentIdea, ContentInsight
from ...trendsources import customer_question_signals, google_trends_signals, rejected_signals


def _source_products(limit: int = 10):
    """محصولات فعال — ویژه و دارای تصویر اصلی در اولویت."""
    primary = ProductImage.objects.filter(product=OuterRef("pk"), is_primary=True)
    return list(
        Product.objects.filter(is_active=True)
        .select_related("category")
        .annotate(has_primary=Exists(primary))
        .order_by("-is_featured", "-has_primary", "-created_at")[:limit]
    )


def _source_articles(limit: int = 5):
    return list(Article.objects.filter(is_published=True).order_by("-created_at")[:limit])


def _top_insights(limit: int = 3):
    """سه پست برتر بر اساس ریچ برای تزریق به پرامپت — بدون داده، لیست خالی."""
    return [
        {"title": ins.post.title, "views": ins.views, "saved": ins.saved}
        for ins in ContentInsight.objects.select_related("post").order_by("-reach")[:limit]
    ]


def _match_product(name: str | None):
    if not name:
        return None
    return Product.objects.filter(is_active=True, name__icontains=name).first()


class Command(BaseCommand):
    help = "تولید ایدهٔ محتوای اینستاگرام با LLM و ساخت پیش‌نویس پست"

    def add_arguments(self, parser):
        parser.add_argument("--count", type=int, default=5, help="تعداد ایده (پیش‌فرض ۵)")
        parser.add_argument("--type", choices=["reel", "post", "story"], default="reel",
                            help="نوع محتوای پیش‌نویس (پیش‌فرض reel)")
        parser.add_argument("--dry-run", action="store_true",
                            help="فقط چاپ ایده‌ها — هیچ رکوردی ساخته نمی‌شود")

    def handle(self, *args, **options):
        count = max(1, options["count"])
        content_type = options["type"]
        dry_run = options["dry_run"]

        products = _source_products()
        articles = _source_articles()
        top_posts = _top_insights()
        trends = google_trends_signals()
        questions = customer_question_signals()
        rejected = rejected_signals()
        self.stdout.write(
            f"منابع: {len(products)} محصول، {len(articles)} مقاله"
            + (f"، {len(top_posts)} پست برتر از اینسایت" if top_posts else "")
            + (f"، {len(trends)} ترند گوگل" if trends else "")
            + (f"، {len(questions)} سؤال مشتری" if questions else "")
            + (f"، {len(rejected)} نمونهٔ ردشده" if rejected else "")
        )

        try:
            ideas = generate_ideas(products, articles, count, content_type, top_posts=top_posts,
                                   trends=trends, questions=questions, rejected=rejected)
        except Exception as exc:
            raise CommandError(f"تولید ایده با LLM ناموفق بود: {exc}")
        if not ideas:
            raise CommandError("مدل هیچ ایدهٔ معتبری برنگرداند")

        if dry_run:
            for i, idea in enumerate(ideas, 1):
                product = _match_product(idea["product_name"])
                self.stdout.write(f"\n── ایدهٔ {i}: {idea['title']} [{idea['category']}]"
                                  + (f" → محصول: {product.name}" if product else ""))
                if idea.get("why"):
                    self.stdout.write(f"منبع ایده: {idea['why']}")
                self.stdout.write(idea["caption"])
                self.stdout.write(" ".join(f"#{h}" for h in idea["hashtags"]))
            self.stdout.write(self.style.WARNING("\n(dry-run) هیچ رکوردی ساخته نشد."))
            return

        created = 0
        for idea in ideas:
            product = _match_product(idea["product_name"])
            content_idea = ContentIdea.objects.create(
                title=idea["title"],
                description=idea["caption"][:500],
                source=ContentIdea.Source.AUTO,
                category=idea["category"],
                product=product,
                signal=idea.get("why") or "",
                status=ContentIdea.Status.USED,
            )
            ChannelPost.objects.create(
                title=idea["title"],
                body=idea["caption"] or idea["title"],
                content_type=content_type,
                approval_status=ChannelPost.ApprovalStatus.DRAFT,
                idea=content_idea,
                hashtags=" ".join(f"#{h}" for h in idea["hashtags"]),
            )
            created += 1
            self.stdout.write(f"ایدهٔ «{idea['title']}» + پیش‌نویس پست ساخته شد"
                              + (f" (محصول: {product.name})" if product else ""))
        self.stdout.write(self.style.SUCCESS(f"{created} ایده و پیش‌نویس پست ساخته شد."))
