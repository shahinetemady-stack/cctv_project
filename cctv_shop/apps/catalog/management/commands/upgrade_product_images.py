"""ارتقای رزولوشن تصاویر محصول به حداقل ۹۰۰px (حداقل ترب: ۶۰۰px — توصیه: ۹۰۰×۹۰۰).

تصاویر قدیمی (بیشترشان ۵۰۰×۵۰۰ وارداتی) با LANCZOS بزرگ‌نمایی و به WebP بازنویسی می‌شوند.
استفاده:
    python manage.py upgrade_product_images           # dry-run — فقط گزارش
    python manage.py upgrade_product_images --apply   # اعمال واقعی
"""
import io

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from PIL import Image

from apps.catalog.models import ProductImage

TARGET_SIDE = 900
QUALITY = 85


class Command(BaseCommand):
    help = "تصاویر محصول با ضلع بزرگ‌تر کوچک‌تر از ۹۰۰px را به ۹۰۰px ارتقا می‌دهد"

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="بدون این فلگ فقط گزارش می‌دهد")

    def handle(self, *args, **options):
        apply = options["apply"]
        todo = []
        for pi in ProductImage.objects.all().iterator():
            try:
                with Image.open(pi.image.path) as im:
                    w, h = im.size
            except Exception as exc:
                self.stderr.write(f"خطا در خواندن {pi.pk}: {exc}")
                continue
            if max(w, h) < TARGET_SIDE:
                todo.append((pi, w, h))

        self.stdout.write(f"{len(todo)} تصویر نیاز به ارتقا دارند (از {ProductImage.objects.count()})")
        if not apply:
            for pi, w, h in todo[:10]:
                self.stdout.write(f"  نمونه: {pi.pk} — {w}x{h} — {pi.image.name}")
            self.stdout.write("dry-run بود؛ با --apply اجرا کنید")
            return

        done = 0
        for pi, w, h in todo:
            try:
                old_path = pi.image.path
                with Image.open(old_path) as im:
                    if im.mode not in ("RGB", "RGBA"):
                        im = im.convert("RGBA" if "transparency" in im.info else "RGB")
                    ratio = TARGET_SIDE / max(w, h)
                    im = im.resize((round(im.width * ratio), round(im.height * ratio)), Image.LANCZOS)
                    buf = io.BytesIO()
                    im.save(buf, "WEBP", quality=QUALITY, method=4)
                base = pi.image.name.rsplit(".", 1)[0]
                new_name = f"{base}.webp"
                # ذخیره مستقیم در storage — image.save از upload_to استفاده می‌کند و مسیر را دوبرابر می‌کرد
                saved_name = pi.image.storage.save(new_name, ContentFile(buf.getvalue()))
                old_name = pi.image.name
                pi.image.name = saved_name
                pi.save(update_fields=["image"])
                # فایل قبلی را پاک کن
                if saved_name != old_name and pi.image.storage.exists(old_name):
                    pi.image.storage.delete(old_name)
                done += 1
            except Exception as exc:
                self.stderr.write(f"خطا در ارتقای {pi.pk}: {exc}")
        self.stdout.write(self.style.SUCCESS(f"{done} تصویر ارتقا یافت"))
