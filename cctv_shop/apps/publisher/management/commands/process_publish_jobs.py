"""
apps/publisher/management/commands/process_publish_jobs.py
───────────────────────────────────────────────────────────
پردازش صف انتشار در پیام‌رسان‌ها — با کران اجرا می‌شود (مثلاً هر ۵ دقیقه):
  */5 * * * * cd <project> && venv/bin/python manage.py process_publish_jobs

هر لاگ «در انتظار» (یا «ناموفق» با کمتر از ۳ تلاش که موعد تلاش بعدی‌اش رسیده)
پردازش می‌شود. شکست‌ها با backoff نمایی (۶۰ثانیه × ۲^(تلاش-۱)) دوباره زمان‌بندی
می‌شوند و بعد از ۳ تلاش برای همیشه failed می‌مانند.
"""

from datetime import timedelta

import requests
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from apps.publisher.models import PublishJob, PublishLog
from apps.publisher.services import PublishError, get_service

MAX_ATTEMPTS = 3


def _due_filter(now):
    """شرط «موعد تلاش رسیده»: بدون زمان‌بندی یا زمان‌بندی گذشته."""
    return Q(next_attempt_at__isnull=True) | Q(next_attempt_at__lte=now)


def _recompute_job_status(job):
    """وضعیت کار را از روی لاگ‌هایش بازمحاسبه می‌کند."""
    statuses = list(job.logs.values_list("status", flat=True))
    if not statuses:
        return
    if all(s == PublishLog.Status.SUCCESS for s in statuses):
        new = PublishJob.Status.DONE
    elif all(s == PublishLog.Status.FAILED for s in statuses):
        new = PublishJob.Status.FAILED
    elif any(s in (PublishLog.Status.PENDING, PublishLog.Status.SENDING) for s in statuses):
        new = PublishJob.Status.PROCESSING
    elif any(s == PublishLog.Status.SUCCESS for s in statuses):
        new = PublishJob.Status.PARTIAL
    else:
        return
    if job.status != new:
        job.status = new
        job.save(update_fields=["status", "updated_at"])


class Command(BaseCommand):
    help = "پردازش صف انتشار محتوا در پیام‌رسان‌ها"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run", action="store_true",
            help="فقط گزارش بده؛ هیچ ارسال و تغییری انجام نشود",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        now = timezone.now()

        logs = (
            PublishLog.objects
            .filter(
                status=PublishLog.Status.PENDING,
            )
            .filter(_due_filter(now))
            .select_related("job__post", "platform", "platform__credential")
        )
        failed_retries = (
            PublishLog.objects
            .filter(
                status=PublishLog.Status.FAILED,
                attempt_count__lt=MAX_ATTEMPTS,
                next_attempt_at__lte=now,
            )
            .select_related("job__post", "platform", "platform__credential")
        )
        queue = list(logs) + list(failed_retries)

        if not queue:
            self.stdout.write("کاری برای انجام نیست.")
            return

        self.stdout.write(f"{len(queue)} لاگ در صف پردازش است{'(dry-run)' if dry_run else ''}.")
        touched_jobs = set()

        for log in queue:
            touched_jobs.add(log.job_id)
            label = f"لاگ {log.id} — {log.platform.name} — «{log.job.post.title}»"

            if dry_run:
                self.stdout.write(f"[dry-run] {label}: فقط نمایش داده شد")
                continue

            try:
                service = get_service(log.platform)
            except PublishError as e:
                log.status = PublishLog.Status.FAILED
                log.error_message = str(e)
                log.save(update_fields=["status", "error_message", "updated_at"])
                self.stdout.write(self.style.ERROR(f"{label}: خطا — {e}"))
                continue

            log.status = PublishLog.Status.SENDING
            log.attempt_count += 1
            log.save(update_fields=["status", "attempt_count", "updated_at"])

            try:
                result = service.publish(log.job.post)
            except (PublishError, requests.RequestException) as e:
                if log.attempt_count < MAX_ATTEMPTS:
                    # backoff نمایی: ۶۰ثانیه، ۱۲۰ثانیه، ...
                    log.status = PublishLog.Status.PENDING
                    log.next_attempt_at = now + timedelta(seconds=60 * 2 ** (log.attempt_count - 1))
                    log.error_message = str(e)
                    log.save(update_fields=[
                        "status", "next_attempt_at", "error_message", "updated_at",
                    ])
                    self.stdout.write(self.style.WARNING(f"{label}: شکست موقت — {e}"))
                else:
                    log.status = PublishLog.Status.FAILED
                    log.error_message = str(e)
                    log.save(update_fields=["status", "error_message", "updated_at"])
                    self.stdout.write(self.style.ERROR(f"{label}: شکست قطعی — {e}"))
                continue
            except Exception as e:
                # خطای پیش‌بینی‌نشده (فایل گمشده، رمزگشایی و…) — قطعی failed
                log.status = PublishLog.Status.FAILED
                log.error_message = f"خطای غیرمنتظره: {e}"
                log.save(update_fields=["status", "error_message", "updated_at"])
                self.stdout.write(self.style.ERROR(f"{label}: خطای غیرمنتظره — {e}"))
                continue

            log.status = PublishLog.Status.SUCCESS
            log.external_message_id = result.get("external_message_id") or ""
            log.response_data = result.get("raw") or {}
            log.error_message = ""
            log.next_attempt_at = None
            log.save(update_fields=[
                "status", "external_message_id", "response_data",
                "error_message", "next_attempt_at", "updated_at",
            ])
            self.stdout.write(self.style.SUCCESS(f"{label}: با موفقیت ارسال شد"))

        if not dry_run:
            for job in PublishJob.objects.filter(pk__in=touched_jobs).prefetch_related("logs"):
                _recompute_job_status(job)
