"""
apps/leads/services.py — منطق کمپین پیامکی
"""
import logging

from django.utils import timezone

from apps.notifications.sms import send_bulk_sms
from .models import CampaignSend, Lead, LeadCampaign

logger = logging.getLogger(__name__)

# سقف هر اجرای کمپین — برای حجم بزرگتر کمپین را تکه‌تکه بساز
CAMPAIGN_MAX_TARGETS = 2000


def campaign_targets(campaign: LeadCampaign):
    """کوئری مخاطبان هدف کمپین بر اساس فیلترها."""
    qs = Lead.objects.all()
    if campaign.filter_status:
        qs = qs.filter(status=campaign.filter_status)
    if campaign.filter_city:
        qs = qs.filter(city=campaign.filter_city)
    if campaign.filter_source:
        qs = qs.filter(source=campaign.filter_source)
    if campaign.filter_category:
        qs = qs.filter(category=campaign.filter_category)
    if campaign.filter_keyword:
        qs = qs.filter(keyword=campaign.filter_keyword)
    return qs


def run_campaign(campaign: LeadCampaign) -> dict:
    """
    ارسال کمپین به مخاطبان هدف (سنکرون، دسته‌های ۲۰۰تایی از طریق send_bulk_sms).
    مخاطبی که در همین کمپین قبلاً ارسال موفق داشته دوباره نمی‌گیرد.
    """
    if campaign.status == LeadCampaign.Status.DONE:
        return {"success": False, "error": "این کمپین قبلاً کامل ارسال شده است."}

    targets = list(
        campaign_targets(campaign)
        .exclude(campaign_sends__campaign=campaign, campaign_sends__ok=True)
        [:CAMPAIGN_MAX_TARGETS]
    )
    if not targets:
        return {"success": False, "error": "مخاطبی مطابق فیلترها یافت نشد."}

    campaign.status = LeadCampaign.Status.SENDING
    campaign.started_at = campaign.started_at or timezone.now()
    campaign.total_targets = len(targets)
    campaign.save(update_fields=["status", "started_at", "total_targets", "updated_at"])

    sent, failed = 0, 0
    # دسته‌های ۱۰۰تایی — در صورت خطای یک دسته، بقیه ادامه می‌یابند و گزارش دقیق می‌ماند
    for i in range(0, len(targets), 100):
        chunk = targets[i:i + 100]
        ok_count, err = send_bulk_sms([t.phone for t in chunk], campaign.message)
        chunk_ok = ok_count >= len(chunk)
        now = timezone.now()
        for lead in chunk:
            CampaignSend.objects.update_or_create(
                campaign=campaign, lead=lead,
                defaults={"ok": chunk_ok, "error": "" if chunk_ok else err},
            )
            if chunk_ok:
                lead.sms_count += 1
                lead.last_sms_at = now
                if lead.status == Lead.Status.NEW:
                    lead.status = Lead.Status.CONTACTED
                lead.save(update_fields=["sms_count", "last_sms_at", "status", "updated_at"])
        if chunk_ok:
            sent += len(chunk)
        else:
            failed += len(chunk)
            logger.error(f"[LEADS] کمپین {campaign.id} — دسته {i // 100 + 1} ناموفق: {err}")

    campaign.sent_count += sent
    campaign.failed_count += failed
    campaign.status = LeadCampaign.Status.DONE if sent > 0 else LeadCampaign.Status.FAILED
    campaign.finished_at = timezone.now()
    campaign.save(update_fields=["sent_count", "failed_count", "status", "finished_at", "updated_at"])

    logger.info(f"[LEADS] کمپین {campaign.id}: {sent} موفق / {failed} ناموفق")
    return {"success": True, "sent": sent, "failed": failed}
