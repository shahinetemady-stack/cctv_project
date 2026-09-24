"""
manage.py scrape_divar — جمع‌آوری لید از آگهی‌های دیوار

جستجوی کلیدواژه‌ای سراسری در دیوار → برای هر آگهی: عنوان + شهر + شماره تماس
(شماره تماس نیازمند توکن لاگین دیوار است — LeadSettings.divar_token).

اجرا:
  python manage.py scrape_divar                    # همه کلیدواژه‌ها، ۵ صفحه هرکدام
  python manage.py scrape_divar --pages 10
  python manage.py scrape_divar --keywords "نصب دوربین" "دزدگیر اماکن"
  python manage.py scrape_divar --no-contact       # فقط آگهی‌ها (بدون شماره — تست)

پیشنهاد کرون: روزی یک بار، مثلاً ۷ صبح.
"""
import logging
import time

import requests
from django.core.management.base import BaseCommand

from apps.leads.keywords import DEFAULT_KEYWORDS, category_for
from apps.leads.models import Lead, LeadSettings, normalize_phone

logger = logging.getLogger(__name__)

SEARCH_URL = "https://api.divar.ir/v8/postlist/w/search"
POST_URL = "https://api.divar.ir/v8/posts-v2/web/{token}"
CONTACT_URL = "https://api.divar.ir/v8/postcontact/web/contact_info_v2/{token}"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0 Safari/537.36",
    "Content-Type": "application/json",
}


def _search(keyword: str, page: int) -> list:
    """یک صفحه از نتایج جستجوی سراسری → لیست (token, title, hint)."""
    payload = {
        "city_ids": [],
        "source_view": "SEARCH_BANNER",
        "disable_recommendation": True,
        "map_state": {"visible": False},
        "search_data": {
            "form_data": {"data": {"query": {"str": {"value": keyword}}}},
            "server_payload": {
                "@type": "type.googleapis.com/widgets.SearchData.ServerPayload",
                "constraints": {},
                "sort": {"type": "sort_date"},
            },
        },
        "pagination_data": {
            "@type": "type.googleapis.com/post_list.PaginationData",
            "page": page,
            "layer_page": 1,
        },
    }
    r = requests.post(SEARCH_URL, json=payload, headers=HEADERS, timeout=20)
    r.raise_for_status()
    rows = []
    for w in r.json().get("list_widgets", []):
        if w.get("widget_type") != "POST_ROW":
            continue
        d = w.get("data", {})
        token = d.get("token") or d.get("action", {}).get("payload", {}).get("token")
        if token:
            rows.append({
                "token": token,
                "title": d.get("title", ""),
                "hint": d.get("bottom_description_text", ""),
            })
    return rows


def _post_detail(token: str) -> dict:
    """جزئیات آگهی → شهر و عنوان کامل."""
    r = requests.get(POST_URL.format(token=token), headers=HEADERS, timeout=20)
    if r.status_code != 200:
        return {}
    d = r.json()
    title = ""
    for s in d.get("sections", []):
        if s.get("section_name") == "TITLE":
            for w in s.get("widgets", []):
                t = w.get("data", {}).get("title")
                if t:
                    title = t
                    break
    return {
        "title": title,
        "city": (d.get("city") or {}).get("name", ""),
        "contact_uuid": (d.get("contact") or {}).get("contact_uuid", ""),
    }


def _contact_phone(token: str, contact_uuid: str, cookie: str) -> str:
    """شماره تماس آگهی — نیازمند کوکی لاگین دیوار (sAccessToken + sFrontToken)."""
    headers = {**HEADERS, "Cookie": cookie,
               "Origin": "https://divar.ir",
               "Referer": f"https://divar.ir/v/{token}"}
    r = requests.post(CONTACT_URL.format(token=token),
                      json={"contact_uuid": contact_uuid}, headers=headers, timeout=20)
    if r.status_code in (401, 403):
        raise PermissionError("توکن دیوار منقضی شده است — باید تازه شود")
    if r.status_code != 200:
        return ""
    data = r.json() or {}
    # فرمت‌های ممکن پاسخ
    for key in ("mobile", "phone", "phone_number"):
        if data.get(key):
            return normalize_phone(data[key])
    for w in data.get("widget_list", []) or []:
        d = w.get("data", {})
        phone = normalize_phone(d.get("value", "")) or \
            normalize_phone((d.get("action", {}).get("payload") or {}).get("phone_number", ""))
        if phone:
            return phone
    return ""


class Command(BaseCommand):
    help = "جمع‌آوری لید از آگهی‌های دیوار (کلیدواژه‌ای، سراسری)"

    def add_arguments(self, parser):
        parser.add_argument("--pages", type=int, default=5, help="صفحه به ازای هر کلیدواژه")
        parser.add_argument("--keywords", nargs="*", default=DEFAULT_KEYWORDS)
        parser.add_argument("--no-contact", action="store_true", help="بدون واکشی شماره تماس")
        parser.add_argument("--delay", type=float, default=1.5, help="تأخیر بین درخواست‌ها (ثانیه)")

    def handle(self, *args, **options):
        from apps.leads.models import ScraperRun
        run = ScraperRun.objects.create(source=Lead.Source.DIVAR)
        try:
            self._run(options, run)
        except Exception as e:
            run.finish(ScraperRun.Status.ERROR, message=str(e))
            raise

    def _run(self, options, run):
        from apps.leads.models import ScraperRun
        cookie = LeadSettings.get_instance().divar_token.strip()
        fetch_contact = not options["no_contact"]
        if fetch_contact and not cookie:
            self.stderr.write(
                "کوکی دیوار تنظیم نشده (ادمین جنگو ← تنظیمات لید) — "
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
                    source_url = f"https://divar.ir/v/{row['token']}"
                    if Lead.objects.filter(source_url=source_url).exists():
                        total_seen += 1
                        continue
                    detail = _post_detail(row["token"])
                    time.sleep(options["delay"])
                    phone = ""
                    if fetch_contact and detail.get("contact_uuid"):
                        try:
                            phone = _contact_phone(row["token"], detail["contact_uuid"], cookie)
                        except PermissionError as e:
                            self.stderr.write(str(e))
                            self.stderr.write("اجرا متوقف شد. کوکی تازه را در تنظیمات لید بگذار و دوباره اجرا کن.")
                            self.stdout.write(f"تا اینجا: {total_new} لید جدید")
                            run.finish(ScraperRun.Status.ERROR, total_new, total_seen,
                                       "توکن دیوار منقضی شده — از تب تنظیمات تازه‌اش کن")
                            return
                        except Exception as e:
                            logger.warning(f"[DIVAR] contact {row['token']}: {e}")
                        time.sleep(options["delay"])
                    if not phone:
                        # لید بدون شماره برای بازاریابی پیامکی ارزشی ندارد — رد می‌شود
                        continue
                    _, created = Lead.objects.get_or_create(
                        phone=phone,
                        defaults={
                            "name": "",
                            "city": detail.get("city", ""),
                            "source": Lead.Source.DIVAR,
                            "source_url": source_url,
                            "source_title": detail.get("title") or row["title"],
                            "keyword": keyword,
                            "category": category_for(keyword),
                        },
                    )
                    if created:
                        total_new += 1
                    else:
                        total_seen += 1
                # صفحه خالی یا کمتر از حد → احتمالاً ته نتایج
                if len(rows) < 5:
                    break

        self.stdout.write(self.style.SUCCESS(
            f"تمام شد — {total_new} لید جدید، {total_seen} تکراری/قبلی"
        ))
        run.finish(ScraperRun.Status.SUCCESS, total_new, total_seen)
