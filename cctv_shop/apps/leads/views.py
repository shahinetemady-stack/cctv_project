"""
apps/leads/views.py — API مدیریت مخاطبان و کمپین‌ها (فقط ادمین)

GET    /api/leads/                    لیست + فیلتر (q, city, source, status, keyword, page)
POST   /api/leads/                    افزودن دستی
PATCH  /api/leads/<id>/               ویرایش (name, city, status, notes)
DELETE /api/leads/<id>/               حذف
POST   /api/leads/import/             ایمپورت متنی (هر خط: موبایل [نام])
GET    /api/leads/export/             خروجی CSV
GET    /api/leads/meta/               شهرها/منابع/وضعیت‌ها + آمار
GET    /api/leads/campaigns/          لیست کمپین‌ها
POST   /api/leads/campaigns/          ساخت کمپین
POST   /api/leads/campaigns/<id>/send/  ارسال کمپین
"""
import csv
import logging

from django.http import HttpResponse
from rest_framework import status
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Lead, LeadCampaign, normalize_phone
from .serializers import LeadCampaignSerializer, LeadSerializer
from .services import campaign_targets, run_campaign

logger = logging.getLogger(__name__)

PAGE_SIZE = 50


# ─── RBAC helpers ────────────────────────────────────────────

def _has_perm(user, code):
    if user.is_superuser:
        return True
    sp = getattr(user, 'staff_profile', None)
    return bool(sp and sp.is_active and sp.has_perm(code))


def _has_any_perm(user, *codes):
    return any(_has_perm(user, c) for c in codes)


def _forbidden(msg='شما دسترسی لازم برای این عملیات را ندارید'):
    return Response({'error': msg}, status=403)


class LeadListView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        if not _has_perm(request.user, 'leads_view'):
            return _forbidden()
        qs = Lead.objects.all()
        if q := request.query_params.get("q"):
            qs = qs.filter(phone__icontains=q) | qs.filter(name__icontains=q) | qs.filter(source_title__icontains=q)
        for param in ("city", "source", "status", "keyword", "category"):
            if v := request.query_params.get(param):
                qs = qs.filter(**{param: v})
        qs = qs.order_by("-created_at")

        total = qs.count()
        try:
            page = max(1, int(request.query_params.get("page", 1)))
        except ValueError:
            page = 1
        items = qs[(page - 1) * PAGE_SIZE: page * PAGE_SIZE]
        return Response({
            "count": total,
            "page": page,
            "results": LeadSerializer(items, many=True).data,
        })

    def post(self, request):
        if not _has_perm(request.user, 'leads_view'):
            return _forbidden()
        phone = normalize_phone(request.data.get("phone", ""))
        if not phone:
            return Response({"error": "شماره موبایل نامعتبر است."}, status=status.HTTP_400_BAD_REQUEST)
        if Lead.objects.filter(phone=phone).exists():
            return Response({"error": "این شماره قبلاً ثبت شده است."}, status=status.HTTP_409_CONFLICT)
        lead = Lead.objects.create(
            phone=phone,
            name=(request.data.get("name") or "").strip(),
            city=(request.data.get("city") or "").strip(),
            notes=(request.data.get("notes") or "").strip(),
            source=Lead.Source.MANUAL,
        )
        return Response(LeadSerializer(lead).data, status=status.HTTP_201_CREATED)


class LeadDetailView(APIView):
    permission_classes = [IsAdminUser]

    def patch(self, request, pk):
        if not _has_perm(request.user, 'leads_view'):
            return _forbidden()
        try:
            lead = Lead.objects.get(pk=pk)
        except Lead.DoesNotExist:
            return Response({"error": "یافت نشد."}, status=status.HTTP_404_NOT_FOUND)
        for f in ("name", "city", "status", "notes", "category"):
            if f in request.data:
                setattr(lead, f, str(request.data[f]).strip())
        lead.save()
        return Response(LeadSerializer(lead).data)

    def delete(self, request, pk):
        if not _has_perm(request.user, 'leads_view'):
            return _forbidden()
        Lead.objects.filter(pk=pk).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class LeadImportView(APIView):
    """POST /api/leads/import/ — body: {"text": "0912... نام\n...", "city": "تهران"}"""
    permission_classes = [IsAdminUser]

    def post(self, request):
        if not _has_perm(request.user, 'leads_view'):
            return _forbidden()
        text = request.data.get("text", "")
        default_city = (request.data.get("city") or "").strip()
        created, duplicate, invalid = 0, 0, 0
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.replace("،", ",").split(",", 1)
            phone = normalize_phone(parts[0])
            if not phone:
                # شاید کل خط فقط یک شماره باشد با فاصله/تب
                phone = normalize_phone(line)
            if not phone:
                invalid += 1
                continue
            name = parts[1].strip() if len(parts) > 1 else ""
            if Lead.objects.filter(phone=phone).exists():
                duplicate += 1
                continue
            Lead.objects.create(phone=phone, name=name, city=default_city, source=Lead.Source.MANUAL)
            created += 1
        return Response({"created": created, "duplicate": duplicate, "invalid": invalid})


class LeadExportView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        if not _has_perm(request.user, 'leads_view'):
            return _forbidden()
        qs = Lead.objects.all().order_by("-created_at")
        for param in ("city", "source", "status", "keyword", "category"):
            if v := request.query_params.get(param):
                qs = qs.filter(**{param: v})
        resp = HttpResponse(content_type="text/csv; charset=utf-8-sig")
        resp["Content-Disposition"] = 'attachment; filename="leads.csv"'
        w = csv.writer(resp)
        w.writerow(["موبایل", "نام", "شهر", "منبع", "دسته‌بندی", "کلیدواژه", "وضعیت", "تعداد پیامک", "تاریخ ثبت"])
        for l in qs[:10000]:
            w.writerow([l.phone, l.name, l.city, l.get_source_display(), l.get_category_display(), l.keyword,
                        l.get_status_display(), l.sms_count, l.created_at.strftime("%Y-%m-%d")])
        return resp


class LeadMetaView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        if not _has_perm(request.user, 'leads_view'):
            return _forbidden()
        from django.db.models import Count
        by_status = {r["status"]: r["c"] for r in Lead.objects.values("status").annotate(c=Count("id"))}
        by_category = {r["category"]: r["c"] for r in Lead.objects.values("category").annotate(c=Count("id"))}
        return Response({
            "total": Lead.objects.count(),
            "by_status": by_status,
            "by_category": by_category,
            "cities": list(Lead.objects.exclude(city="").values_list("city", flat=True).distinct().order_by("city")),
            "keywords": list(Lead.objects.exclude(keyword="").values_list("keyword", flat=True).distinct().order_by("keyword")),
            "sources": Lead.Source.choices,
            "statuses": Lead.Status.choices,
            "categories": Lead.Category.choices,
        })


class LeadSettingsView(APIView):
    """
    GET /api/leads/settings/ — وضعیت توکن‌ها (فقط ماسک، هرگز مقدار کامل برنمی‌گردد) + آخرین اجرای هر اسکرپر
    PUT /api/leads/settings/ — ذخیره توکن جدید (فیلد خالی یعنی بدون تغییر)
    """
    permission_classes = [IsAdminUser]

    @staticmethod
    def _mask(value: str) -> str:
        value = (value or "").strip()
        return f"…{value[-6:]}" if value else ""

    @staticmethod
    def _run_payload(run):
        if not run:
            return None
        return {
            "status": run.status,
            "new_count": run.new_count,
            "seen_count": run.seen_count,
            "message": run.message,
            "started_at": run.started_at,
            "finished_at": run.finished_at,
        }

    def get(self, request):
        if not _has_perm(request.user, 'leads_view'):
            return _forbidden()
        from .models import LeadSettings, ScraperRun
        s = LeadSettings.get_instance()
        return Response({
            "divar_token_set": bool(s.divar_token.strip()),
            "divar_token_mask": self._mask(s.divar_token),
            "sheypoor_token_set": bool(s.sheypoor_token.strip()),
            "sheypoor_token_mask": self._mask(s.sheypoor_token),
            "serpapi_key_set": bool(s.serpapi_key.strip()),
            "serpapi_key_mask": self._mask(s.serpapi_key),
            "last_runs": {
                src: self._run_payload(ScraperRun.latest_for(src))
                for src in ("divar", "sheypoor", "google")
            },
        })

    def put(self, request):
        if not _has_perm(request.user, 'leads_view'):
            return _forbidden()
        from .models import LeadSettings
        s = LeadSettings.get_instance()
        updated = []
        for field in ("divar_token", "sheypoor_token", "serpapi_key"):
            value = (request.data.get(field) or "").strip()
            if value:
                setattr(s, field, value)
                updated.append(field)
        if updated:
            s.save()
        return self.get(request)


# آرگومان‌های اجرا از پنل — گوگل محدود به ۴ شهر اصلی تا سهمیه ماهانه SerpAPI حفظ شود
SCRAPER_RUN_ARGS = {
    "divar":    ["scrape_divar"],
    "sheypoor": ["scrape_sheypoor", "--pages", "3", "--delay", "8"],
    "google":   ["scrape_google", "--cities", "تهران", "مشهد", "اصفهان", "شیراز"],
}


class ScraperRunView(APIView):
    """POST /api/leads/run/<source>/ — اجرای دستی اسکرپر در بک‌گراند (فقط ادمین)."""
    permission_classes = [IsAdminUser]

    def post(self, request, source):
        if not _has_perm(request.user, 'leads_view'):
            return _forbidden()
        from datetime import timedelta

        from django.conf import settings
        from django.utils import timezone

        from .models import ScraperRun

        if source not in SCRAPER_RUN_ARGS:
            return Response({"error": "منبع نامعتبر است."}, status=status.HTTP_400_BAD_REQUEST)

        # جلوگیری از اجرای همزمان — اجرای «در حال اجرا»ی قدیمی‌تر از ۳ ساعت مرده تلقی می‌شود
        stale_before = timezone.now() - timedelta(hours=3)
        ScraperRun.objects.filter(
            source=source, status=ScraperRun.Status.RUNNING, started_at__lt=stale_before
        ).update(status=ScraperRun.Status.ERROR, message="اجرا ناتمام ماند (متوقف/کرش)")
        if ScraperRun.objects.filter(source=source, status=ScraperRun.Status.RUNNING).exists():
            return Response({"error": "یک اجرا برای این منبع در حال انجام است — صبر کن تمام شود."},
                            status=status.HTTP_409_CONFLICT)

        import subprocess
        import sys
        log_path = f"/tmp/scrape_{source}_panel.log"
        log = open(log_path, "ab")
        subprocess.Popen(
            [sys.executable, "-u", "manage.py", *SCRAPER_RUN_ARGS[source]],
            cwd=settings.BASE_DIR, stdout=log, stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        return Response({"success": True, "message": "اجرای اسکرپر شروع شد — نتیجه را همین‌جا دنبال کن."})


class CampaignListView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        if not _has_perm(request.user, 'leads_view'):
            return _forbidden()
        qs = LeadCampaign.objects.order_by("-created_at")[:100]
        return Response(LeadCampaignSerializer(qs, many=True).data)

    def post(self, request):
        if not _has_perm(request.user, 'leads_view'):
            return _forbidden()
        campaign = LeadCampaign.objects.create(
            name=(request.data.get("name") or "").strip() or "کمپین بدون‌نام",
            message=(request.data.get("message") or "").strip(),
            filter_city=(request.data.get("filter_city") or "").strip(),
            filter_source=(request.data.get("filter_source") or "").strip(),
            filter_category=(request.data.get("filter_category") or "").strip(),
            filter_status=(request.data.get("filter_status") or Lead.Status.NEW).strip(),
            filter_keyword=(request.data.get("filter_keyword") or "").strip(),
        )
        if not campaign.message:
            campaign.delete()
            return Response({"error": "متن پیامک الزامی است."}, status=status.HTTP_400_BAD_REQUEST)
        data = LeadCampaignSerializer(campaign).data
        data["target_preview"] = campaign_targets(campaign).count()
        return Response(data, status=status.HTTP_201_CREATED)


class CampaignSendView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, pk):
        if not _has_perm(request.user, 'leads_view'):
            return _forbidden()
        try:
            campaign = LeadCampaign.objects.get(pk=pk)
        except LeadCampaign.DoesNotExist:
            return Response({"error": "کمپین یافت نشد."}, status=status.HTTP_404_NOT_FOUND)
        result = run_campaign(campaign)
        if not result["success"]:
            return Response({"error": result["error"]}, status=status.HTTP_400_BAD_REQUEST)
        return Response(result)
