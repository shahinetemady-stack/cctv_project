"""
manage.py scrape_sheypoor — جمع‌آوری لید از آگهی‌های شیپور

جستجوی کلیدواژه‌ای سراسری در API عمومی شیپور (v10) → برای هر آگهی شماره تماس
از endpoint نمایش شماره (نیازمند کوکی لاگین شیپور — LeadSettings.sheypoor_token).

اجرا:
  python manage.py scrape_sheypoor                    # همه کلیدواژه‌ها، ۵ صفحه هرکدام
  python manage.py scrape_sheypoor --pages 10
  python manage.py scrape_sheypoor --keywords "نصب دوربین" "هایک ویژن"
  python manage.py scrape_sheypoor --no-contact       # فقط جستجو (تست)
"""
import logging
import re
import time

import requests
from django.core.management.base import BaseCommand

from apps.leads.keywords import DEFAULT_KEYWORDS, category_for
from apps.leads.models import Lead, LeadSettings, normalize_phone

logger = logging.getLogger(__name__)

BASE = "https://www.sheypoor.com/api/v10.0.0"
SEARCH_URL = f"{BASE}/search"
NUMBER_URL = f"{BASE}/listings/{{listing_id}}/number"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0 Safari/537.36",
    "Accept": "application/json",
}

PAGE_SIZE = 20


def _search(keyword: str, page: int) -> list:
    """یک صفحه از نتایج جستجوی سراسری → لیست (id, title, location, url)."""
    r = requests.get(SEARCH_URL, params={
        "q": keyword, "size": PAGE_SIZE, "start": (page - 1) * PAGE_SIZE,
    }, headers=HEADERS, timeout=20)
    r.raise_for_status()
    rows = []
    for item in r.json().get("data", []):
        a = item.get("attributes", {})
        if not a.get("title"):
            continue
        rows.append({
            "id": item.get("id"),
            "title": a.get("title", ""),
            "location": a.get("location", ""),
            "url": a.get("url", ""),
        })
    return rows


class RateLimited(Exception):
    """شیپور محدودیت سرعت اعمال کرد (۴۰۰ «پذیرفته نیست» یا کپچا)."""


def _phone_once(listing_id: str, cookie: str) -> str:
    r = requests.get(NUMBER_URL.format(listing_id=listing_id),
                     headers={**HEADERS, "Cookie": cookie,
                              "Referer": f"https://www.sheypoor.com/v/x-{listing_id}.html"},
                     timeout=20)
    if r.status_code in (401, 403):
        raise PermissionError("توکن شیپور منقضی شده است — باید تازه شود")
    if r.status_code == 429 or "errors" in r.text[:80] or "پذیرفته نیست" in r.text:
        raise RateLimited()
    if r.status_code != 200:
        return ""
    data = r.json() or {}
    payload = data.get("data") or {}
    # فرمت واقعی: data.attributes.phoneNumber — ولی چند فرمت دیگر را هم پوشش می‌دهیم
    for source in (payload.get("attributes") or {}, payload):
        if not isinstance(source, dict):
            continue
        for key in ("phoneNumber", "phone", "number", "mobile", "telephone"):
            if source.get(key):
                return normalize_phone(source[key])
    if isinstance(payload, str):
        return normalize_phone(payload)
    # فرمت ناشناخته → کل پاسخ را برای الگوی موبایل ایران بگرد
    m = re.search(r"(?:\+98|0)?9\d{9}", r.text.replace(" ", "").replace("-", ""))
    return normalize_phone(m.group(0)) if m else ""


def _phone(listing_id: str, cookie: str) -> str:
    """شماره تماس آگهی — شیپور برای نمایش شماره سهمیه دارد؛ روی ۴۲۹/کپچا فقط یک retry."""
    for attempt in range(2):
        try:
            return _phone_once(listing_id, cookie)
        except RateLimited:
            if attempt == 0:
                logger.warning("[SHEYPOOR] rate limit — 90s صبر و یک تلاش مجدد")
                time.sleep(90)
    raise RateLimited()


def _city(location: str) -> str:
    """location شیپور مثل «تهران، نازی آباد» یا «تهران، تهران، نازی آباد» → بخش اول."""
    return (location or "").split("،")[0].strip()


class Command(BaseCommand):
    help = "جمع‌آوری لید از آگهی‌های شیپور (کلیدواژه‌ای، سراسری)"

    def add_arguments(self, parser):
        parser.add_argument("--pages", type=int, default=5, help="صفحه به ازای هر کلیدواژه")
        parser.add_argument("--keywords", nargs="*", default=DEFAULT_KEYWORDS)
        parser.add_argument("--no-contact", action="store_true", help="بدون واکشی شماره تماس")
        parser.add_argument("--delay", type=float, default=6.0,
                            help="تأخیر بین واکشی شماره‌ها (ثانیه) — شیپور حساس است، کمتر از ۴ توصیه نمی‌شود")

    def handle(self, *args, **options):
        from apps.leads.models import ScraperRun
        run = ScraperRun.objects.create(source=Lead.Source.SHEYPOOR)
        try:
            self._run(options, run)
        except Exception as e:
            run.finish(ScraperRun.Status.ERROR, message=str(e))
            raise

    def _run(self, options, run):
        from apps.leads.models import ScraperRun
        cookie = LeadSettings.get_instance().sheypoor_token.strip()
        fetch_contact = not options["no_contact"]
        if fetch_contact and not cookie:
            self.stderr.write(
                "کوکی شیپور تنظیم نشده (ادمین جنگو ← تنظیمات لید) — "
                "بدون آن فقط جستجو تست می‌شود. برای شماره، کوکی را بگذار یا --no-contact بزن."
            )
            fetch_contact = False

        total_new, total_seen = 0, 0
        for keyword in options["keywords"]:
            for page in range(1, options["pages"] + 1):
                try:
                    rows = _search(keyword, page)
                except Exception as e:
                    self.stderr.write(f"[{keyword}] صفحه {page} خطا: {e}")
                    break
                if not rows:
                    break
                self.stdout.write(f"[{keyword}] صفحه {page}: {len(rows)} آگهی")
                time.sleep(options["delay"])

                for row in rows:
                    if not row["id"]:
                        continue
                    if Lead.objects.filter(source_url=row["url"]).exists():
                        total_seen += 1
                        continue
                    phone = ""
                    if fetch_contact:
                        try:
                            phone = _phone(row["id"], cookie)
                        except PermissionError as e:
                            self.stderr.write(str(e))
                            self.stderr.write("اجرا متوقف شد. کوکی تازه را در تنظیمات لید بگذار و دوباره اجرا کن.")
                            self.stdout.write(f"تا اینجا: {total_new} لید جدید")
                            run.finish(ScraperRun.Status.ERROR, total_new, total_seen,
                                       "توکن شیپور منقضی شده — از تب تنظیمات تازه‌اش کن")
                            return
                        except RateLimited:
                            self.stderr.write(
                                "سهمیه نمایش شماره شیپور برای این اکانت فعلاً تمام شده (کپچا). "
                                "فردا دوباره اجرا کن — آگهی‌های ناموفق دوباره تلاش می‌شوند."
                            )
                            self.stdout.write(f"تا اینجا: {total_new} لید جدید")
                            run.finish(ScraperRun.Status.ERROR, total_new, total_seen,
                                       "سهمیه روزانه نمایش شماره شیپور تمام شد — فردا خودکار ادامه می‌یابد")
                            return
                        except Exception as e:
                            logger.warning(f"[SHEYPOOR] number {row['id']}: {e}")
                        time.sleep(options["delay"])
                    if not phone:
                        # لید بدون شماره برای بازاریابی پیامکی ارزشی ندارد — رد می‌شود
                        continue
                    _, created = Lead.objects.get_or_create(
                        phone=phone,
                        defaults={
                            "name": "",
                            "city": _city(row["location"]),
                            "source": Lead.Source.SHEYPOOR,
                            "source_url": row["url"],
                            "source_title": row["title"],
                            "keyword": keyword,
                            "category": category_for(keyword),
                        },
                    )
                    if created:
                        total_new += 1
                    else:
                        total_seen += 1
                if len(rows) < PAGE_SIZE:
                    break

        self.stdout.write(self.style.SUCCESS(
            f"تمام شد — {total_new} لید جدید، {total_seen} تکراری/قبلی"
        ))
        run.finish(ScraperRun.Status.SUCCESS, total_new, total_seen)
