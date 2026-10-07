"""
extract_datasheets — متن دیتاشیت PDF همه محصولات فعال را استخراج و در
datasheets.json (کنار catalog.json) می‌نویسد: {slug: {name, text}}

مصرف‌کننده: apps/assistant — کانتکست فنی ربات هوشمند (به‌جای تزریق کل فایل،
فقط متن دیتاشیت محصولات مرتبط با سؤال به مدل داده می‌شود).
بعد از آپلود/تغییر دیتاشیت‌ها دوباره اجرا شود.
"""
import json
import re
import subprocess

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.catalog.models import Product

MAX_CHARS = 4000  # سقف متن هر محصول — پرامپت منفجر نشود


def clean_text(raw: str) -> str:
    # سطرهای خالی پشت‌سرهم و فضاهای اضافه — حجم متن کم و تمیز شود
    t = raw.replace("\x0c", "\n")
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


class Command(BaseCommand):
    help = "استخراج متن دیتاشیت‌های PDF محصولات به datasheets.json"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="فقط گزارش، بدون نوشتن فایل")

    def handle(self, *args, **opts):
        out = {}
        skipped = []
        qs = (Product.objects.filter(is_active=True)
              .exclude(datasheet_pdf__isnull=True).exclude(datasheet_pdf=""))
        for p in qs:
            try:
                raw = subprocess.run(
                    ["pdftotext", p.datasheet_pdf.path, "-"],
                    capture_output=True, timeout=60, check=True,
                ).stdout.decode("utf-8", errors="replace")
            except Exception as exc:
                skipped.append((p.slug, str(exc)[:80]))
                continue
            text = clean_text(raw)
            if len(text) < 50:  # PDF اسکن‌شده بدون لایه متنی
                skipped.append((p.slug, "متن استخراج نشد (احتمالاً اسکن تصویری)"))
                continue
            out[p.slug] = {"name": p.name, "text": text[:MAX_CHARS]}

        if not opts["dry_run"]:
            path = settings.BASE_DIR / "datasheets.json"
            path.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
            self.stdout.write(f"نوشته شد: {path}")

        self.stdout.write(f"✅ {len(out)} دیتاشیت استخراج شد")
        for slug, why in skipped:
            self.stdout.write(f"⚠️ رد شد: {slug} — {why}")
