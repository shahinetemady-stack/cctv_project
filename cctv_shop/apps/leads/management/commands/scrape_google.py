"""
manage.py scrape_google — جمع‌آوری لید از گوگل مپ (از طریق SerpAPI)

برای هر کلیدواژه × شهر، نتایج گوگل مپ (نام کسب‌وکار + شماره + آدرس) جمع می‌شود.
نیازمند کلید SerpAPI در LeadSettings.serpapi_key (serpapi.com — پلن رایگان ماهی ۱۰۰ جستجو).

اجرا:
  python manage.py scrape_google                             # همه کلیدواژه‌ها × شهرهای پیش‌فرض
  python manage.py scrape_google --cities تهران مشهد
  python manage.py scrape_google --keywords "نصب دوربین مداربسته"

توجه: هر ترکیب کلیدواژه×شهر = ۱ جستجو از سهمیه SerpAPI (هر کدام ~۲۰ نتیجه).
"""
import logging
import time

import requests
from django.core.management.base import BaseCommand

from apps.leads.keywords import DEFAULT_KEYWORDS, GOOGLE_CITIES, category_for
from apps.leads.models import Lead, LeadSettings, normalize_phone

logger = logging.getLogger(__name__)

SERP_URL = "https://serpapi.com/search.json"

# نوع کسب‌وکار گوگل مپ → دسته لید (گوگل نوع واقعی کسب‌وکار را می‌دهد)
_TYPE_CATEGORY = {
    "نصب": Lead.Category.INSTALLER,
    "نصاب": Lead.Category.INSTALLER,
    "اجرا": Lead.Category.INSTALLER,
    "فروشگاه": Lead.Category.SELLER,
    "فروش": Lead.Category.SELLER,
    "شرکت": Lead.Category.COMPANY,
}


def _category(place_type: str, keyword: str) -> str:
    for key, cat in _TYPE_CATEGORY.items():
        if key in (place_type or ""):
            return cat
    return category_for(keyword)


def _search(api_key: str, keyword: str, city: str) -> list:
    """نتایج گوگل مپ → لیست (name, phone, type, address)."""
    r = requests.get(SERP_URL, params={
        "engine": "google_maps",
        "q": f"{keyword} {city}",
        "type": "search",
        "hl": "fa",
        "gl": "ir",
        "api_key": api_key,
    }, timeout=30)
    if r.status_code in (401, 403):
        raise PermissionError("کلید SerpAPI نامعتبر یا سهمیه تمام شده است")
    r.raise_for_status()
    data = r.json()
    if data.get("error"):
        raise RuntimeError(data["error"])
    rows = []
    for place in data.get("local_results", []):
        rows.append({
            "name": place.get("title", ""),
            "phone": normalize_phone(place.get("phone", "")),
            "type": place.get("type", ""),
            "address": place.get("address", ""),
            "gps": place.get("gps_coordinates", {}),
            "place_id": place.get("place_id", ""),
        })
    return rows


class Command(BaseCommand):
    help = "جمع‌آوری لید از گوگل مپ با SerpAPI (کلیدواژه × شهر)"

    def add_arguments(self, parser):
        parser.add_argument("--keywords", nargs="*", default=DEFAULT_KEYWORDS)
        parser.add_argument("--cities", nargs="*", default=GOOGLE_CITIES)
        parser.add_argument("--delay", type=float, default=1.0, help="تأخیر بین جستجوها (ثانیه)")

    def handle(self, *args, **options):
        from apps.leads.models import ScraperRun
        run = ScraperRun.objects.create(source=Lead.Source.GOOGLE)
        try:
            self._run(options, run)
        except Exception as e:
            run.finish(ScraperRun.Status.ERROR, message=str(e))
            raise

    def _run(self, options, run):
        from apps.leads.models import ScraperRun
        api_key = LeadSettings.get_instance().serpapi_key.strip()
        if not api_key:
            self.stderr.write(
                "کلید SerpAPI تنظیم نشده (ادمین جنگو ← تنظیمات لید). "
                "از serpapi.com کلید رایگان بساز و بگذار."
            )
            run.finish(ScraperRun.Status.ERROR, message="کلید SerpAPI تنظیم نشده")
            return

        keywords, cities = options["keywords"], options["cities"]
        total_queries = len(keywords) * len(cities)
        self.stdout.write(f"{len(keywords)} کلیدواژه × {len(cities)} شهر = {total_queries} جستجو از سهمیه SerpAPI")

        total_new, total_seen, total_nophone = 0, 0, 0
        for keyword in keywords:
            for city in cities:
                try:
                    rows = _search(api_key, keyword, city)
                except PermissionError as e:
                    self.stderr.write(str(e))
                    self.stdout.write(f"تا اینجا: {total_new} لید جدید")
                    run.finish(ScraperRun.Status.ERROR, total_new, total_seen + total_nophone,
                               "کلید SerpAPI نامعتبر یا سهمیه ماهانه تمام شده")
                    return
                except Exception as e:
                    self.stderr.write(f"[{keyword} @ {city}] خطا: {e}")
                    time.sleep(options["delay"])
                    continue
                time.sleep(options["delay"])

                for row in rows:
                    if not row["phone"]:
                        total_nophone += 1
                        continue
                    source_url = (f"https://www.google.com/maps/search/?api=1&query={keyword} {city}"
                                  + (f"&query_place_id={row['place_id']}" if row["place_id"] else ""))
                    _, created = Lead.objects.get_or_create(
                        phone=row["phone"],
                        defaults={
                            "name": row["name"],
                            "city": city,
                            "source": Lead.Source.GOOGLE,
                            "source_url": source_url,
                            "source_title": f"{row['name']} — {row['address']}".strip(" —"),
                            "keyword": keyword,
                            "category": _category(row["type"], keyword),
                        },
                    )
                    if created:
                        total_new += 1
                    else:
                        total_seen += 1
                self.stdout.write(f"[{keyword} @ {city}] {len(rows)} نتیجه")

        self.stdout.write(self.style.SUCCESS(
            f"تمام شد — {total_new} لید جدید، {total_seen} تکراری، {total_nophone} بدون شماره موبایل (رد شد)"
        ))
        run.finish(ScraperRun.Status.SUCCESS, total_new, total_seen + total_nophone)
