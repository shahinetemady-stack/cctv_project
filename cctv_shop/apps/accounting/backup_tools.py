"""
apps/accounting/backup_tools.py — v3
─────────────────────────────────
v3 changes:
  • LZMA compression option (30-50% کوچک‌تر از deflate)
  • VACUUM SQLite قبل از بک‌اپ
  • گزینه include_media برای ساعتی/روزانه (پیش‌فرض ساعتی=بدون media)
  • alert بعد از browse تا کاربر بداند مسیر هنوز save نشده
  • JSON API endpoints برای استفاده از React frontend
"""
import os
import json
import shutil
import logging
import zipfile
import sqlite3
from datetime import datetime
from time import time as time_now

from django.db import models
from django.conf import settings
from django.views import View
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator
from django.middleware.csrf import get_token
from django.utils import timezone

# DRF برای JSON APIs
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from rest_framework.parsers import MultiPartParser, FormParser

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# Models
# ═══════════════════════════════════════════════════════════════

class BackupSetting(models.Model):
    """تنظیمات بک‌اپ — singleton"""

    backup_path = models.CharField(max_length=500, blank=True,
        verbose_name="مسیر ذخیره بک‌اپ")

    is_auto_enabled = models.BooleanField(default=False,
        verbose_name="بک‌اپ خودکار ساعتی")
    interval_hours = models.PositiveIntegerField(default=1,
        verbose_name="بازه (ساعت)")
    daily_backup_enabled = models.BooleanField(default=True,
        verbose_name="بک‌اپ روزانه")
    daily_backup_time = models.CharField(max_length=5, default="23:30")
    daily_keep_count = models.PositiveIntegerField(default=30)

    safety_backup_enabled = models.BooleanField(default=True,
        verbose_name="بک‌اپ خودکار قبل از خطر")

    # ── کاهش حجم (v3) ──
    use_lzma_compression = models.BooleanField(default=True,
        verbose_name="فشرده‌سازی LZMA",
        help_text="30-50٪ کوچک‌تر، ولی کمی کندتر")
    vacuum_sqlite_before_backup = models.BooleanField(default=True,
        verbose_name="بهینه‌سازی SQLite قبل از بک‌اپ",
        help_text="فضای خالی DB را پاک می‌کند")
    include_media_in_hourly = models.BooleanField(default=False,
        verbose_name="بک‌اپ ساعتی شامل media (عکس‌ها)",
        help_text="معمولاً false — چون media حجم زیاد دارد")
    include_media_in_daily = models.BooleanField(default=True,
        verbose_name="بک‌اپ روزانه شامل media")

    email_enabled = models.BooleanField(default=False)
    email_to = models.CharField(max_length=200, blank=True)

    telegram_enabled = models.BooleanField(default=False)
    telegram_token = models.CharField(max_length=200, blank=True)
    telegram_chat_id = models.CharField(max_length=100, blank=True)

    bale_enabled = models.BooleanField(default=False)
    bale_token = models.CharField(max_length=200, blank=True)
    bale_chat_id = models.CharField(max_length=100, blank=True)

    # رمز فایل‌های ارسالی — فایل بدون رمز هرگز ارسال نمی‌شود
    send_encryption_password = models.CharField(max_length=200, blank=True,
        verbose_name="رمز رمزنگاری فایل ارسالی",
        help_text="AES-256 — برای باز کردن با WinRAR/7-Zip لازم است")

    keep_count = models.PositiveIntegerField(default=10)

    last_backup_at = models.DateTimeField(null=True, blank=True)
    last_daily_backup_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "accounting_backup_setting"
        verbose_name = "تنظیمات بک‌اپ"
        verbose_name_plural = "تنظیمات بک‌اپ"

    def __str__(self):
        return f"تنظیمات بک‌اپ"

    @classmethod
    def get_instance(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class BackupLog(models.Model):
    class Status(models.TextChoices):
        SUCCESS = "success", "موفق"
        PARTIAL = "partial", "نسبتاً موفق"
        FAILED = "failed", "ناموفق"

    class Trigger(models.TextChoices):
        MANUAL = "manual", "دستی"
        AUTO = "auto", "خودکار ساعتی"
        DAILY = "daily", "خودکار روزانه"
        SAFETY = "safety", "ایمنی"
        COMMAND = "command", "Command Line"

    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=Status.choices)
    trigger = models.CharField(max_length=10, choices=Trigger.choices)
    is_daily = models.BooleanField(default=False)
    file_path = models.CharField(max_length=500, blank=True)
    file_size_bytes = models.PositiveBigIntegerField(default=0)
    duration_seconds = models.FloatField(default=0)
    sent_email = models.BooleanField(default=False)
    sent_telegram = models.BooleanField(default=False)
    sent_bale = models.BooleanField(default=False)
    error = models.TextField(blank=True)
    note = models.TextField(blank=True)
    triggered_by_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "accounting_backup_log"
        verbose_name = "لاگ بک‌اپ"
        verbose_name_plural = "لاگ بک‌اپ‌ها"
        ordering = ["-created_at"]

    @property
    def file_size_mb(self):
        return round(self.file_size_bytes / 1024 / 1024, 2) if self.file_size_bytes else 0


# ═══════════════════════════════════════════════════════════════
# Service Functions
# ═══════════════════════════════════════════════════════════════

def _vacuum_sqlite():
    """فشرده‌سازی فایل SQLite — حذف فضای خالی"""
    db_engine = settings.DATABASES['default']['ENGINE']
    if 'sqlite' not in db_engine:
        return False
    db_path = str(settings.DATABASES['default']['NAME'])
    if not os.path.exists(db_path):
        return False
    try:
        # connection جدا تا با Django در تضاد نباشد
        conn = sqlite3.connect(db_path)
        conn.execute("VACUUM")
        conn.close()
        return True
    except Exception as e:
        logger.warning(f"[VACUUM] خطا: {e}")
        return False


def _create_backup_file(output_dir, name_prefix="cctv_backup",
                        include_media=True, use_lzma=True, vacuum=True):
    """ساخت ZIP بک‌اپ با گزینه‌های فشرده‌سازی"""
    os.makedirs(output_dir, exist_ok=True)

    if vacuum:
        _vacuum_sqlite()

    timestamp = timezone.localtime().strftime("%Y%m%d_%H%M%S")
    backup_name = f"{name_prefix}_{timestamp}.zip"
    backup_path = os.path.join(output_dir, backup_name)

    db_engine = settings.DATABASES['default']['ENGINE']
    files_added = 0

    # LZMA → فشرده‌سازی بهتر | DEFLATED → استاندارد
    if use_lzma:
        try:
            compression = zipfile.ZIP_LZMA
            extra_kwargs = {}
        except Exception:
            compression = zipfile.ZIP_DEFLATED
            extra_kwargs = {'compresslevel': 9}
    else:
        compression = zipfile.ZIP_DEFLATED
        extra_kwargs = {'compresslevel': 9}

    with zipfile.ZipFile(backup_path, 'w', compression, allowZip64=True, **extra_kwargs) as zf:
        # Database
        if 'sqlite' in db_engine:
            db_path = str(settings.DATABASES['default']['NAME'])
            if os.path.exists(db_path):
                zf.write(db_path, 'db.sqlite3')
                files_added += 1

        # Media (اختیاری)
        media_skipped = False
        if include_media:
            media_root = str(settings.MEDIA_ROOT)
            if os.path.exists(media_root):
                for root, dirs, files in os.walk(media_root):
                    for fname in files:
                        # رد کردن فایل‌های موقت
                        if fname.startswith('.') or fname.endswith('.tmp'):
                            continue
                        full = os.path.join(root, fname)
                        rel = os.path.relpath(full, media_root)
                        arcname = os.path.join('media', rel).replace('\\', '/')
                        try:
                            zf.write(full, arcname)
                            files_added += 1
                        except Exception as exc:
                            logger.warning(f"[BACKUP] skipped {full}: {exc}")
        else:
            media_skipped = True

        manifest = {
            'timestamp': timestamp,
            'database_engine': db_engine,
            'files_added': files_added,
            'compression': 'lzma' if use_lzma else 'deflate-9',
            'media_included': not media_skipped,
            'created_at': timezone.localtime().isoformat(),
        }
        zf.writestr('manifest.json', json.dumps(manifest, indent=2, ensure_ascii=False))

    return backup_path


def _send_to_telegram(token, chat_id, file_path, caption=""):
    import requests
    file_size = os.path.getsize(file_path)
    if file_size > 50 * 1024 * 1024:
        raise ValueError(f"فایل {file_size / 1024 / 1024:.1f}MB > 50MB.")
    url = f"https://api.telegram.org/bot{token}/sendDocument"
    with open(file_path, 'rb') as f:
        r = requests.post(url, data={'chat_id': chat_id, 'caption': caption[:1024]},
            files={'document': (os.path.basename(file_path), f)}, timeout=120)
    if r.status_code != 200:
        raise RuntimeError(f"Telegram خطا: {r.text[:500]}")


def _send_to_bale(token, chat_id, file_path, caption=""):
    """ارسال از طریق بات بله — API سازگار با تلگرام"""
    import requests
    file_size = os.path.getsize(file_path)
    if file_size > 50 * 1024 * 1024:
        raise ValueError(f"فایل {file_size / 1024 / 1024:.1f}MB > 50MB.")
    url = f"https://tapi.bale.ai/bot{token}/sendDocument"
    with open(file_path, 'rb') as f:
        r = requests.post(url, data={'chat_id': chat_id, 'caption': caption[:1024]},
            files={'document': (os.path.basename(file_path), f)}, timeout=120)
    if r.status_code != 200 or not r.json().get('ok', False):
        raise RuntimeError(f"بله خطا: {r.text[:500]}")


def _create_send_file(output_dir, password, name_prefix="cctv_send"):
    """نسخه سبک فقط-دیتابیس با رمزنگاری AES-256 — مخصوص ارسال خارج از سرور.
    بدون رمز، فایل ارسالی ساخته نمی‌شود (داده مشتری هرگز بدون رمز نمی‌رود)."""
    if not password:
        raise ValueError("رمز رمزنگاری فایل ارسالی در تنظیمات بک‌اپ وارد نشده")
    import pyzipper
    db_engine = settings.DATABASES['default']['ENGINE']
    db_path = str(settings.DATABASES['default']['NAME'])
    if 'sqlite' not in db_engine or not os.path.exists(db_path):
        raise RuntimeError("دیتابیس SQLite برای ارسال پیدا نشد")
    os.makedirs(output_dir, exist_ok=True)
    timestamp = timezone.localtime().strftime("%Y%m%d_%H%M%S")
    send_path = os.path.join(output_dir, f"{name_prefix}_{timestamp}.zip")
    with pyzipper.AESZipFile(send_path, 'w', compression=pyzipper.ZIP_LZMA) as zf:
        zf.setpassword(password.encode('utf-8'))
        zf.setencryption(pyzipper.WZ_AES, nbits=256)
        zf.write(db_path, 'db.sqlite3')
        zf.writestr('manifest.json', json.dumps({
            'timestamp': timestamp,
            'type': 'send — db only, AES-256 encrypted',
            'created_at': timezone.localtime().isoformat(),
        }, indent=2, ensure_ascii=False))
    return send_path


def _send_to_email(to_email, subject, body, file_path):
    from django.core.mail import EmailMessage
    msg = EmailMessage(subject=subject, body=body,
        from_email=getattr(settings, 'EMAIL_HOST_USER', None) or 'noreply@cctv.local',
        to=[to_email])
    msg.attach_file(file_path)
    msg.send(fail_silently=False)


def _cleanup_old_backups(directory, keep_count, name_prefix="cctv_backup"):
    if not os.path.isdir(directory):
        return 0
    files = []
    for f in os.listdir(directory):
        if f.startswith(name_prefix + '_') and f.endswith('.zip'):
            full = os.path.join(directory, f)
            try:
                files.append((os.path.getmtime(full), full))
            except OSError:
                pass
    files.sort(reverse=True)
    deleted = 0
    for _, full in files[keep_count:]:
        try:
            os.remove(full); deleted += 1
        except Exception:
            pass
    return deleted


def run_backup(trigger='manual', user=None, is_daily=False, send_channels=True):
    start = time_now()
    s = BackupSetting.get_instance()

    if not s.backup_path:
        return BackupLog.objects.create(
            status=BackupLog.Status.FAILED, trigger=trigger, is_daily=is_daily,
            error="مسیر بک‌اپ تنظیم نشده", triggered_by_id=user.id if user else None,
        )

    # تصمیم درباره include_media
    include_media = s.include_media_in_daily if is_daily else s.include_media_in_hourly

    file_path = None
    error_msg = ""
    sent_email = False
    sent_telegram = False
    sent_bale = False
    status = BackupLog.Status.SUCCESS
    prefix = "cctv_daily" if is_daily else "cctv_backup"

    try:
        file_path = _create_backup_file(
            output_dir=s.backup_path,
            name_prefix=prefix,
            include_media=include_media,
            use_lzma=s.use_lzma_compression,
            vacuum=s.vacuum_sqlite_before_backup,
        )
        file_size = os.path.getsize(file_path)

        if send_channels:
            # ارسال خارج از سرور همیشه با نسخه سبک فقط-دیتابیس + رمز AES-256
            # انجام می‌شود — فایل کامل با media فقط روی سرور می‌ماند.
            send_email = s.email_enabled and s.email_to
            send_tg = s.telegram_enabled and s.telegram_token and s.telegram_chat_id
            send_bale = s.bale_enabled and s.bale_token and s.bale_chat_id

            if send_email or send_tg or send_bale:
                send_path = None
                try:
                    send_path = _create_send_file(
                        output_dir=s.backup_path,
                        password=s.send_encryption_password,
                    )
                    send_size = os.path.getsize(send_path)
                except Exception as e:
                    error_msg += f"ساخت فایل ارسالی رمزگذاری‌شده: {e} | "
                    status = BackupLog.Status.PARTIAL

                if send_path:
                    caption = (
                        f"📦 بک‌اپ {'روزانه' if is_daily else ''} CCTV (فقط دیتابیس)\n"
                        f"⏰ {timezone.localtime():%Y-%m-%d %H:%M}\n"
                        f"📏 {send_size / 1024 / 1024:.2f}MB\n"
                        f"🔐 رمزگذاری AES-256 — باز کردن با WinRAR/7-Zip"
                    )
                    if send_email:
                        try:
                            _send_to_email(
                                to_email=s.email_to,
                                subject=f"بک‌اپ {'روزانه' if is_daily else ''} CCTV — {timezone.localtime():%Y-%m-%d %H:%M}",
                                body=(f"بک‌اپ {trigger} — فقط دیتابیس\n"
                                      f"اندازه: {send_size / 1024 / 1024:.2f}MB\n"
                                      f"🔐 فایل با AES-256 رمزگذاری شده؛ با WinRAR/7-Zip و رمز تنظیم‌شده باز کنید."),
                                file_path=send_path,
                            )
                            sent_email = True
                        except Exception as e:
                            error_msg += f"ایمیل: {e} | "
                            status = BackupLog.Status.PARTIAL

                    if send_tg:
                        try:
                            _send_to_telegram(
                                token=s.telegram_token, chat_id=s.telegram_chat_id,
                                file_path=send_path, caption=caption,
                            )
                            sent_telegram = True
                        except Exception as e:
                            error_msg += f"تلگرام: {e} | "
                            status = BackupLog.Status.PARTIAL

                    if send_bale:
                        try:
                            _send_to_bale(
                                token=s.bale_token, chat_id=s.bale_chat_id,
                                file_path=send_path, caption=caption,
                            )
                            sent_bale = True
                        except Exception as e:
                            error_msg += f"بله: {e} | "
                            status = BackupLog.Status.PARTIAL

                    try:
                        os.remove(send_path)
                    except OSError:
                        pass

        keep = s.daily_keep_count if is_daily else s.keep_count
        deleted = _cleanup_old_backups(s.backup_path, keep, name_prefix=prefix)
        note = f"حجم: {file_size / 1024 / 1024:.2f}MB"
        if not include_media:
            note += " (بدون media)"
        if deleted:
            note += f" | {deleted} بک‌اپ قدیمی پاک شد"

        log = BackupLog.objects.create(
            status=status, trigger=trigger, is_daily=is_daily,
            file_path=file_path, file_size_bytes=file_size,
            duration_seconds=round(time_now() - start, 2),
            sent_email=sent_email, sent_telegram=sent_telegram, sent_bale=sent_bale,
            error=error_msg.strip(' |'), note=note,
            triggered_by_id=user.id if user else None,
        )
        if is_daily:
            s.last_daily_backup_at = timezone.now()
        else:
            s.last_backup_at = timezone.now()
        s.save()
        return log

    except Exception as e:
        logger.exception(f"[BACKUP] خطا: {e}")
        return BackupLog.objects.create(
            status=BackupLog.Status.FAILED, trigger=trigger, is_daily=is_daily,
            error=str(e)[:500], duration_seconds=round(time_now() - start, 2),
            file_path=file_path or "", triggered_by_id=user.id if user else None,
        )


def safety_backup_now(user=None, reason=""):
    s = BackupSetting.get_instance()
    if not s.safety_backup_enabled:
        return None
    if not s.backup_path:
        s.backup_path = os.path.join(str(settings.BASE_DIR), "safety_backups")
        s.save(update_fields=['backup_path', 'updated_at'])
    try:
        return run_backup(trigger=BackupLog.Trigger.SAFETY, user=user, send_channels=True)
    except Exception as e:
        logger.exception(f"[SAFETY] خطا: {e}")
        return None


def extract_backup_zip(zip_path, restore_db=True, restore_media=True):
    if not os.path.exists(zip_path):
        raise FileNotFoundError(f"فایل پیدا نشد: {zip_path}")
    result = {'db_restored': False, 'media_restored': 0, 'errors': []}
    with zipfile.ZipFile(zip_path, 'r') as zf:
        names = zf.namelist()
        if 'manifest.json' not in names:
            raise ValueError("فایل ZIP بک‌اپ معتبر نیست")
        if restore_db:
            db_engine = settings.DATABASES['default']['ENGINE']
            if 'sqlite' in db_engine and 'db.sqlite3' in names:
                db_path = str(settings.DATABASES['default']['NAME'])
                with zf.open('db.sqlite3') as src, open(db_path, 'wb') as dst:
                    shutil.copyfileobj(src, dst)
                result['db_restored'] = True
        if restore_media:
            media_root = str(settings.MEDIA_ROOT)
            os.makedirs(media_root, exist_ok=True)
            for name in names:
                if name.startswith('media/'):
                    rel = name[len('media/'):]
                    if not rel: continue
                    target = os.path.join(media_root, rel)
                    os.makedirs(os.path.dirname(target), exist_ok=True)
                    try:
                        with zf.open(name) as src, open(target, 'wb') as dst:
                            shutil.copyfileobj(src, dst)
                        result['media_restored'] += 1
                    except Exception as exc:
                        result['errors'].append(f"{rel}: {exc}")
    return result


# ═══════════════════════════════════════════════════════════════
# JSON API (برای React frontend)
# ═══════════════════════════════════════════════════════════════

def _settings_dict(s):
    return {
        'backup_path': s.backup_path,
        'is_auto_enabled': s.is_auto_enabled,
        'interval_hours': s.interval_hours,
        'daily_backup_enabled': s.daily_backup_enabled,
        'daily_backup_time': s.daily_backup_time,
        'daily_keep_count': s.daily_keep_count,
        'safety_backup_enabled': s.safety_backup_enabled,
        'use_lzma_compression': s.use_lzma_compression,
        'vacuum_sqlite_before_backup': s.vacuum_sqlite_before_backup,
        'include_media_in_hourly': s.include_media_in_hourly,
        'include_media_in_daily': s.include_media_in_daily,
        'email_enabled': s.email_enabled,
        'email_to': s.email_to,
        'telegram_enabled': s.telegram_enabled,
        'telegram_token': s.telegram_token,
        'telegram_chat_id': s.telegram_chat_id,
        'bale_enabled': s.bale_enabled,
        'bale_token': s.bale_token,
        'bale_chat_id': s.bale_chat_id,
        'send_encryption_password': s.send_encryption_password,
        'keep_count': s.keep_count,
        'last_backup_at': s.last_backup_at.isoformat() if s.last_backup_at else None,
        'last_daily_backup_at': s.last_daily_backup_at.isoformat() if s.last_daily_backup_at else None,
    }


def _log_dict(log):
    return {
        'id': log.id,
        'created_at': log.created_at.isoformat(),
        'status': log.status,
        'status_display': log.get_status_display(),
        'trigger': log.trigger,
        'trigger_display': log.get_trigger_display(),
        'is_daily': log.is_daily,
        'file_path': log.file_path,
        'file_size_mb': log.file_size_mb,
        'duration_seconds': log.duration_seconds,
        'sent_email': log.sent_email,
        'sent_telegram': log.sent_telegram,
        'sent_bale': log.sent_bale,
        'error': log.error,
        'note': log.note,
    }


# ─── RBAC helpers (محلی — import از views چرخه‌ای می‌شود) ────────

def _has_perm(user, code):
    if user.is_superuser:
        return True
    sp = getattr(user, 'staff_profile', None)
    return bool(sp and sp.is_active and sp.has_perm(code))


def _forbidden(msg='شما دسترسی لازم برای این عملیات را ندارید'):
    return Response({'error': msg}, status=403)


class BackupSettingsApiView(APIView):
    """GET تنظیمات، POST ذخیره"""
    permission_classes = [IsAdminUser]

    def get(self, request):
        if not _has_perm(request.user, 'backup_view'):
            return _forbidden()
        s = BackupSetting.get_instance()
        return Response(_settings_dict(s))

    def post(self, request):
        if not request.user.is_superuser:
            return Response({'error': 'فقط superuser'}, status=403)
        d = request.data
        s = BackupSetting.get_instance()
        bool_fields = [
            'is_auto_enabled', 'daily_backup_enabled', 'safety_backup_enabled',
            'use_lzma_compression', 'vacuum_sqlite_before_backup',
            'include_media_in_hourly', 'include_media_in_daily',
            'email_enabled', 'telegram_enabled', 'bale_enabled',
        ]
        for f in bool_fields:
            if f in d:
                setattr(s, f, bool(d[f]))
        for f in ['backup_path', 'daily_backup_time', 'email_to',
                  'telegram_token', 'telegram_chat_id',
                  'bale_token', 'bale_chat_id', 'send_encryption_password']:
            if f in d:
                setattr(s, f, str(d[f]).strip())
        for f in ['interval_hours', 'daily_keep_count', 'keep_count']:
            if f in d:
                try: setattr(s, f, max(1, int(d[f])))
                except: pass
        s.save()
        return Response({'success': True, 'settings': _settings_dict(s)})


class BackupRunApiView(APIView):
    """POST اجرای دستی"""
    permission_classes = [IsAdminUser]

    def post(self, request):
        if not request.user.is_superuser:
            return Response({'error': 'فقط superuser'}, status=403)
        is_daily = bool(request.data.get('is_daily', False))
        log = run_backup(trigger='manual', user=request.user, is_daily=is_daily)
        return Response({'log': _log_dict(log)})


class BackupLogsApiView(APIView):
    """GET لیست لاگ‌ها"""
    permission_classes = [IsAdminUser]

    def get(self, request):
        if not _has_perm(request.user, 'backup_view'):
            return _forbidden()
        limit = min(int(request.query_params.get('limit', 20)), 100)
        logs = BackupLog.objects.all()[:limit]
        return Response([_log_dict(log) for log in logs])


class BrowseDirectoryApiView(APIView):
    """فایل dialog روی همان کامپیوتر سرور"""
    permission_classes = [IsAdminUser]

    def get(self, request):
        if not request.user.is_superuser:
            return Response({'error': 'فقط superuser'}, status=403)
        try:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            directory = filedialog.askdirectory(title="انتخاب پوشه بک‌اپ")
            root.destroy()
            return Response({'path': directory or ''})
        except Exception as e:
            return Response({'error': f'باز کردن dialog ممکن نشد: {e}'}, status=500)


class BackupRestoreUploadApiView(APIView):
    """POST آپلود فایل ZIP"""
    permission_classes = [IsAdminUser]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        if not request.user.is_superuser:
            return Response({'error': 'فقط superuser'}, status=403)
        file = request.FILES.get('backup_file')
        if not file:
            return Response({'error': 'فایلی انتخاب نشده'}, status=400)
        if not file.name.endswith('.zip'):
            return Response({'error': 'فقط .zip'}, status=400)

        staging_dir = os.path.join(str(settings.BASE_DIR), 'restore_staging')
        os.makedirs(staging_dir, exist_ok=True)
        for old in os.listdir(staging_dir):
            try: os.remove(os.path.join(staging_dir, old))
            except OSError: pass

        staged_path = os.path.join(staging_dir, file.name)
        with open(staged_path, 'wb') as f:
            for chunk in file.chunks():
                f.write(chunk)

        try:
            with zipfile.ZipFile(staged_path) as zf:
                if 'manifest.json' not in zf.namelist():
                    os.remove(staged_path)
                    return Response({'error': 'فایل بک‌اپ معتبر نیست'}, status=400)
                with zf.open('manifest.json') as mf:
                    manifest = json.loads(mf.read())
        except Exception as e:
            return Response({'error': f'فایل خراب است: {e}'}, status=400)

        return Response({
            'staged': {
                'name': file.name,
                'size_mb': round(os.path.getsize(staged_path) / 1024 / 1024, 2),
                'manifest': manifest,
                'path': staged_path,
            }
        })


class BackupRestoreExecuteApiView(APIView):
    """POST اجرای بازیابی"""
    permission_classes = [IsAdminUser]

    def post(self, request):
        if not request.user.is_superuser:
            return Response({'error': 'فقط superuser'}, status=403)
        d = request.data
        if d.get('confirm', '').strip() != 'RESTORE':
            return Response({'error': 'باید RESTORE تایپ کنید'}, status=400)
        staged_path = d.get('staged_path', '')
        if not staged_path or not os.path.exists(staged_path):
            return Response({'error': 'فایل staged پیدا نشد'}, status=400)

        # safety backup
        safety_log = None
        try:
            safety_log = safety_backup_now(user=request.user, reason="قبل از restore")
        except Exception: pass

        try:
            result = extract_backup_zip(staged_path,
                restore_db=bool(d.get('restore_db', True)),
                restore_media=bool(d.get('restore_media', True)))
            return Response({
                'success': True,
                'result': result,
                'safety_log_id': safety_log.id if safety_log else None,
                'note': '⚠️ سرور را restart کنید تا تغییرات اعمال شود',
            })
        except Exception as e:
            return Response({'error': str(e)}, status=400)


# ═══════════════════════════════════════════════════════════════
# HTML Pages (Django admin)
# ═══════════════════════════════════════════════════════════════

@method_decorator(staff_member_required, name='dispatch')
class BrowseDirectoryView(View):
    """نسخه HTML برای صفحه Django admin"""
    def get(self, request):
        if not request.user.is_superuser:
            return JsonResponse({'error': 'فقط superuser'}, status=403)
        try:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            directory = filedialog.askdirectory(title="انتخاب پوشه بک‌اپ")
            root.destroy()
            return JsonResponse({'path': directory or ''})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


@method_decorator(staff_member_required, name='dispatch')
class BackupRestorePageView(View):
    def get(self, request):
        return HttpResponse(self._render(request))

    def post(self, request):
        if not request.user.is_superuser:
            return HttpResponse(self._render(request, error="فقط superuser"))
        action = request.POST.get('action', '')
        if action == 'upload':
            return self._upload(request)
        elif action == 'restore':
            return self._restore(request)
        return HttpResponse(self._render(request, error="حالت نامعتبر"))

    def _upload(self, request):
        file = request.FILES.get('backup_file')
        if not file: return HttpResponse(self._render(request, error="فایلی انتخاب نشده"))
        if not file.name.endswith('.zip'): return HttpResponse(self._render(request, error="فقط .zip"))
        staging_dir = os.path.join(str(settings.BASE_DIR), 'restore_staging')
        os.makedirs(staging_dir, exist_ok=True)
        for old in os.listdir(staging_dir):
            try: os.remove(os.path.join(staging_dir, old))
            except OSError: pass
        staged_path = os.path.join(staging_dir, file.name)
        with open(staged_path, 'wb') as f:
            for chunk in file.chunks(): f.write(chunk)
        try:
            with zipfile.ZipFile(staged_path) as zf:
                if 'manifest.json' not in zf.namelist():
                    os.remove(staged_path)
                    return HttpResponse(self._render(request, error="فایل معتبر نیست"))
                with zf.open('manifest.json') as mf:
                    manifest = json.loads(mf.read())
        except Exception as e:
            return HttpResponse(self._render(request, error=f"فایل خراب: {e}"))
        return HttpResponse(self._render(request, staged={
            'name': file.name,
            'size_mb': round(os.path.getsize(staged_path) / 1024 / 1024, 2),
            'manifest': manifest, 'path': staged_path,
        }))

    def _restore(self, request):
        if request.POST.get('confirm', '').strip() != 'RESTORE':
            return HttpResponse(self._render(request, error="باید RESTORE تایپ کنید"))
        staged_path = request.POST.get('staged_path', '')
        if not staged_path or not os.path.exists(staged_path):
            return HttpResponse(self._render(request, error="فایل staged پیدا نشد"))
        try:
            safety_log = safety_backup_now(user=request.user, reason="قبل از restore")
        except Exception:
            safety_log = None
        try:
            result = extract_backup_zip(staged_path,
                restore_db='restore_db' in request.POST,
                restore_media='restore_media' in request.POST)
            note = (f"⚠️ سرور را restart کنید.\n"
                    f"دیتابیس: {'بازیابی شد' if result['db_restored'] else 'نشد'}\n"
                    f"media: {result['media_restored']} فایل")
            return HttpResponse(self._render(request, success=note,
                safety_log_id=safety_log.id if safety_log else None))
        except Exception as e:
            return HttpResponse(self._render(request, error=f"خطا: {e}"))

    def _render(self, request, error=None, success=None, staged=None, safety_log_id=None):
        csrf = get_token(request)
        u = request.user
        is_super = u.is_superuser
        username = (u.get_full_name() if hasattr(u, 'get_full_name') else None) or getattr(u, 'phone', None) or str(u)
        msg_html = ""
        if error:
            msg_html = f"""<div style="background:#f8d7da;border:1px solid #dc3545;border-radius:8px;padding:14px;margin-bottom:20px;color:#721c24;"><strong>{error}</strong></div>"""
        if success:
            sn = f"<br><small>safety backup #{safety_log_id}</small>" if safety_log_id else ""
            msg_html = f"""<div style="background:#d4edda;border:1px solid #28a745;border-radius:8px;padding:14px;margin-bottom:20px;color:#155724;white-space:pre-line;"><strong>✅ {success}</strong>{sn}</div>"""
        staged_section = ""
        if staged:
            staged_section = f"""
            <div style="background:#fff;border-right:5px solid #ffc107;border-radius:12px;padding:24px;margin-bottom:20px;">
              <h2 style="margin:0 0 12px;color:#856404;font-size:18px;">⚠️ بازیابی</h2>
              <div style="background:#fff3cd;padding:14px;border-radius:6px;margin-bottom:12px;font-size:13px;">
                <b>📦 فایل:</b> {staged['name']} ({staged['size_mb']} MB)<br>
                <b>📅 تاریخ:</b> {staged['manifest'].get('created_at', '—')}<br>
                <b>🗜 فشرده‌سازی:</b> {staged['manifest'].get('compression', '—')}<br>
                <b>📁 فایل‌ها:</b> {staged['manifest'].get('files_added', '—')}
              </div>
              <div style="background:#f8d7da;padding:12px;border-radius:6px;margin-bottom:12px;font-size:13px;color:#721c24;">
                <b>⚠️ سرور را Stop کنید قبل از این کار</b>
              </div>
              <form method="post" onsubmit="return confirm('مطمئنید؟');">
                <input type="hidden" name="csrfmiddlewaretoken" value="{csrf}">
                <input type="hidden" name="action" value="restore">
                <input type="hidden" name="staged_path" value="{staged['path']}">
                <div><label><input type="checkbox" name="restore_db" checked> دیتابیس</label></div>
                <div><label><input type="checkbox" name="restore_media" checked> media</label></div>
                <div style="display:flex;gap:8px;align-items:center;margin-top:14px;">
                  <input type="text" name="confirm" placeholder="RESTORE" required style="padding:10px;border:1px solid #ddd;border-radius:6px;width:220px;">
                  <button type="submit" style="background:#dc3545;color:#fff;padding:10px 24px;border:none;border-radius:6px;font-weight:bold;cursor:pointer;">🔄 شروع</button>
                </div>
              </form>
            </div>"""
        disabled = "" if is_super else "disabled"
        return f"""
<!DOCTYPE html>
<html lang="fa" dir="rtl"><head><meta charset="UTF-8">
<title>بازیابی — DOORBINKAR</title>
<style>
  body {{ font-family:Tahoma,sans-serif; background:#f5f6fa; margin:0; padding:24px; color:#333; }}
  .container {{ max-width:900px; margin:0 auto; }}
  .header {{ display:flex; justify-content:space-between; margin-bottom:24px; }}
  h1 {{ color:#2c3e50; margin:0; font-size:24px; }}
  .nav-btn {{ background:#6c757d; color:#fff; padding:8px 16px; border-radius:6px; text-decoration:none; font-size:13px; margin-left:8px; }}
  .card {{ background:#fff; border-radius:12px; padding:24px; margin-bottom:20px; box-shadow:0 2px 8px rgba(0,0,0,0.06); }}
  .info {{ background:#e3f2fd; padding:12px; border-radius:6px; color:#0d47a1; font-size:13px; }}
</style></head><body>
<div class="container">
  <div class="header"><h1>🔄 بازیابی اطلاعات</h1>
    <div>
      <a href="/api/accounting/backup-page/" class="nav-btn">📦 بک‌اپ</a>
      <a href="/admin/" class="nav-btn">← Admin</a>
    </div></div>
  <div style="background:#fff;padding:12px 16px;border-radius:8px;margin-bottom:20px;">کاربر: <b>{username}</b></div>
  {msg_html}
  {staged_section}
  <div class="card">
    <h2 style="margin:0 0 12px;">📤 آپلود فایل بک‌اپ</h2>
    <form method="post" enctype="multipart/form-data">
      <input type="hidden" name="csrfmiddlewaretoken" value="{csrf}">
      <input type="hidden" name="action" value="upload">
      <input type="file" name="backup_file" accept=".zip" required {disabled} style="padding:8px;border:1px dashed #ccc;border-radius:6px;width:100%;">
      <div style="margin-top:14px;"><button type="submit" style="background:#0066cc;color:#fff;padding:10px 24px;border:none;border-radius:6px;font-weight:bold;cursor:pointer;" {disabled}>📤 آپلود</button></div>
    </form>
  </div>
  <div class="card">
    <h2 style="margin:0 0 12px;">💻 از CMD</h2>
    <div class="info"><code>python manage.py restore_backup "C:\\path\\to\\backup.zip"</code></div>
  </div>
</div></body></html>"""


@method_decorator(staff_member_required, name='dispatch')
class BackupPageView(View):
    def get(self, request):
        return HttpResponse(self._render(request))

    def post(self, request):
        if not request.user.is_superuser:
            return HttpResponse(self._render(request, error="فقط superuser"))
        action = request.POST.get('action', '')
        if action == 'save_settings':
            return self._save_settings(request)
        elif action == 'run_backup':
            return self._run_manual(request, is_daily=False)
        elif action == 'run_daily_backup':
            return self._run_manual(request, is_daily=True)
        return HttpResponse(self._render(request, error="حالت نامعتبر"))

    def _save_settings(self, request):
        s = BackupSetting.get_instance()
        s.backup_path = request.POST.get('backup_path', '').strip()
        bool_fields = ['is_auto_enabled', 'daily_backup_enabled', 'safety_backup_enabled',
                       'use_lzma_compression', 'vacuum_sqlite_before_backup',
                       'include_media_in_hourly', 'include_media_in_daily',
                       'email_enabled', 'telegram_enabled', 'bale_enabled']
        for f in bool_fields:
            setattr(s, f, request.POST.get(f) == 'on')
        s.daily_backup_time = request.POST.get('daily_backup_time', '23:30').strip() or '23:30'
        s.email_to = request.POST.get('email_to', '').strip()
        s.telegram_token = request.POST.get('telegram_token', '').strip()
        s.telegram_chat_id = request.POST.get('telegram_chat_id', '').strip()
        s.bale_token = request.POST.get('bale_token', '').strip()
        s.bale_chat_id = request.POST.get('bale_chat_id', '').strip()
        s.send_encryption_password = request.POST.get('send_encryption_password', '').strip()
        for f in ['interval_hours', 'daily_keep_count', 'keep_count']:
            try: setattr(s, f, max(1, int(request.POST.get(f) or 1)))
            except: pass
        s.save()
        return HttpResponse(self._render(request, msg=f"✅ تنظیمات ذخیره شد. مسیر فعلی: {s.backup_path or '(خالی)'}"))

    def _run_manual(self, request, is_daily=False):
        try:
            log = run_backup(trigger='manual', user=request.user, is_daily=is_daily)
            if log.status == BackupLog.Status.SUCCESS:
                ch = []
                if log.sent_email: ch.append("ایمیل")
                if log.sent_telegram: ch.append("تلگرام")
                if log.sent_bale: ch.append("بله")
                ch_text = " ("+" و ".join(ch)+")" if ch else ""
                kind = "روزانه" if is_daily else "ساعتی"
                msg = f"✅ بک‌اپ {kind} گرفته شد — {log.file_size_mb}MB{ch_text}\n📁 {log.file_path}"
            elif log.status == BackupLog.Status.PARTIAL:
                msg = f"⚠️ {log.error}"
            else:
                msg = f"❌ {log.error}"
            return HttpResponse(self._render(request, msg=msg))
        except Exception as e:
            return HttpResponse(self._render(request, error=str(e)))

    def _render(self, request, msg=None, error=None):
        csrf = get_token(request)
        s = BackupSetting.get_instance()
        logs = BackupLog.objects.all()[:20]
        u = request.user
        username = (u.get_full_name() if hasattr(u, 'get_full_name') else None) or getattr(u, 'phone', None) or str(u)
        is_super = u.is_superuser
        disabled = "" if is_super else "disabled"

        log_rows = ""
        for log in logs:
            color = {'success':'#28a745','partial':'#ffc107','failed':'#dc3545'}.get(log.status, '#888')
            ch = []
            if log.sent_email: ch.append("📧")
            if log.sent_telegram: ch.append("📲")
            if log.sent_bale: ch.append("🟢")
            kind = "📅 روزانه" if log.is_daily else ("🛡 ایمنی" if log.trigger == 'safety' else "⏰ ساعتی")
            log_rows += f"""
            <tr style="border-bottom:1px solid #eee;">
              <td style="padding:8px;font-size:12px;">{log.created_at:%Y-%m-%d %H:%M}</td>
              <td style="padding:8px;font-size:11px;">{kind}</td>
              <td style="padding:8px;"><span style="color:{color};font-weight:bold;font-size:12px;">{log.get_status_display()}</span></td>
              <td style="padding:8px;font-size:12px;">{log.get_trigger_display()}</td>
              <td style="padding:8px;font-size:12px;">{log.file_size_mb or '—'} MB</td>
              <td style="padding:8px;text-align:center;">{' '.join(ch) or '—'}</td>
              <td style="padding:8px;font-size:11px;color:#666;">{log.error[:60] if log.error else log.note or '—'}</td>
            </tr>"""

        last_b = timezone.localtime(s.last_backup_at).strftime('%Y-%m-%d %H:%M') if s.last_backup_at else 'هرگز'
        last_d = timezone.localtime(s.last_daily_backup_at).strftime('%Y-%m-%d %H:%M') if s.last_daily_backup_at else 'هرگز'

        msg_html = ""
        if msg:
            msg_html = f"""<div style="background:#d4edda;border:1px solid #28a745;border-radius:8px;padding:14px;margin-bottom:20px;color:#155724;font-weight:bold;white-space:pre-line;">{msg}</div>"""
        if error:
            msg_html = f"""<div style="background:#f8d7da;border:1px solid #dc3545;border-radius:8px;padding:14px;margin-bottom:20px;color:#721c24;font-weight:bold;">{error}</div>"""

        empty_row = '<tr><td colspan="7" style="text-align:center;padding:24px;color:#888;">هنوز بک‌اپی نیست</td></tr>' if not log_rows else ""

        python_path = os.path.join(str(getattr(settings, 'BASE_DIR', '')), 'venv', 'bin', 'python')
        project_path = str(getattr(settings, 'BASE_DIR', ''))

        return f"""
<!DOCTYPE html>
<html lang="fa" dir="rtl"><head><meta charset="UTF-8"><title>بک‌اپ — DOORBINKAR</title>
<style>
  *{{box-sizing:border-box;}}
  body{{font-family:Tahoma,sans-serif;background:#f5f6fa;margin:0;padding:24px;color:#333;}}
  .container{{max-width:1000px;margin:0 auto;}}
  .header{{display:flex;justify-content:space-between;align-items:center;margin-bottom:24px;}}
  h1{{color:#2c3e50;margin:0;font-size:24px;}}
  .nav-btn{{background:#6c757d;color:#fff;text-decoration:none;padding:8px 16px;border-radius:6px;font-size:13px;margin-left:8px;}}
  .nav-btn.restore{{background:#dc3545;}}
  .user-info{{background:#fff;border-radius:8px;padding:12px 16px;margin-bottom:20px;font-size:14px;}}
  .stat-row{{display:flex;gap:12px;margin-bottom:20px;}}
  .stat{{flex:1;background:#fff;padding:12px 16px;border-radius:8px;font-size:13px;}}
  .stat b{{display:block;font-size:11px;color:#666;margin-bottom:4px;}}
  .card{{background:#fff;border-radius:12px;padding:24px;margin-bottom:20px;box-shadow:0 2px 8px rgba(0,0,0,0.06);}}
  .card h2{{margin:0 0 16px;font-size:18px;color:#2c3e50;border-bottom:2px solid #f0f0f0;padding-bottom:8px;}}
  .grid{{display:grid;grid-template-columns:1fr 1fr;gap:16px;}}
  label{{display:block;font-size:12px;color:#666;margin-bottom:4px;font-weight:bold;}}
  input[type=text],input[type=email],input[type=number]{{width:100%;padding:9px 12px;border:1px solid #ddd;border-radius:6px;font-size:13px;}}
  .path-input{{display:flex;gap:8px;}}
  .path-input input{{flex:1;}}
  .browse-btn{{background:#0066cc;color:#fff;padding:0 16px;border:none;border-radius:6px;cursor:pointer;font-size:13px;white-space:nowrap;}}
  .save-notice{{background:#fff3cd;border:2px solid #ffc107;padding:10px 14px;border-radius:6px;margin-top:8px;font-size:12px;color:#856404;font-weight:bold;display:none;}}
  .checkbox-row{{display:flex;align-items:center;gap:8px;font-size:13px;padding:6px 0;}}
  button{{padding:10px 24px;border-radius:6px;border:none;cursor:pointer;color:#fff;font-weight:bold;}}
  .btn-save{{background:#0066cc;font-size:15px;padding:12px 36px;}}
  .btn-backup{{background:#28a745;}}
  .btn-daily{{background:#9c27b0;}}
  .help{{font-size:11px;color:#888;margin-top:4px;}}
  table{{width:100%;border-collapse:collapse;}}
  th{{background:#f8f9fa;text-align:right;padding:10px 8px;border-bottom:2px solid #dee2e6;font-size:12px;}}
  .auto-info{{background:#fff8e1;border:1px solid #ffe082;padding:14px;border-radius:8px;margin-top:14px;font-size:12px;line-height:1.8;color:#5d4037;}}
  .auto-info code{{background:#fff;padding:2px 6px;border-radius:4px;font-family:monospace;font-size:11px;}}
  .tip{{background:#e3f2fd;border-right:4px solid #0066cc;padding:10px 14px;border-radius:6px;margin-bottom:14px;font-size:12px;color:#0d47a1;line-height:1.8;}}
</style>
<script>
async function browsePath() {{
  try {{
    const r = await fetch('/api/accounting/browse-directory/');
    const data = await r.json();
    if (data.path) {{
      const input = document.querySelector('input[name=backup_path]');
      input.value = data.path;
      input.style.background = '#fff3cd';
      input.style.border = '2px solid #ffc107';
      document.getElementById('save-notice').style.display = 'block';
      const saveBtn = document.querySelector('.btn-save');
      if (saveBtn) {{
        saveBtn.style.animation = 'pulse 1s infinite';
        saveBtn.style.background = '#dc3545';
        saveBtn.textContent = '⚠️ ذخیره تنظیمات (مسیر هنوز اعمال نشده!)';
      }}
      alert('📁 مسیر انتخاب شد:\\n' + data.path + '\\n\\n⚠️ برای اعمال، حتماً دکمه «ذخیره تنظیمات» را بزنید!');
    }} else if (data.error) {{
      alert('خطا: ' + data.error);
    }}
  }} catch (e) {{
    alert('خطا: ' + e.message);
  }}
}}
</script>
<style>@keyframes pulse {{ 0%,100% {{ transform:scale(1); }} 50% {{ transform:scale(1.03); }} }}</style>
</head><body>
<div class="container">
  <div class="header"><h1>📦 سیستم بک‌اپ</h1>
    <div>
      <a href="/api/accounting/backup-restore-page/" class="nav-btn restore">🔄 بازیابی</a>
      <a href="/admin/" class="nav-btn">← Admin</a>
    </div></div>
  <div class="user-info">کاربر: <b>{username}</b></div>
  <div class="stat-row">
    <div class="stat"><b>آخرین بک‌اپ ساعتی</b>🕐 {last_b}</div>
    <div class="stat"><b>آخرین بک‌اپ روزانه</b>📅 {last_d}</div>
  </div>
  {msg_html}
  <div class="card" style="text-align:center;">
    <h2>گرفتن بک‌اپ دستی</h2>
    <div style="display:flex;gap:12px;justify-content:center;">
      <form method="post" onsubmit="return confirm('شروع شود؟');">
        <input type="hidden" name="csrfmiddlewaretoken" value="{csrf}">
        <input type="hidden" name="action" value="run_backup">
        <button type="submit" class="btn-backup" style="font-size:14px;padding:12px 32px;" {disabled}>📥 ساعتی</button>
      </form>
      <form method="post" onsubmit="return confirm('شروع شود؟');">
        <input type="hidden" name="csrfmiddlewaretoken" value="{csrf}">
        <input type="hidden" name="action" value="run_daily_backup">
        <button type="submit" class="btn-daily" style="font-size:14px;padding:12px 32px;" {disabled}>📅 روزانه</button>
      </form>
    </div>
  </div>
  <form method="post">
    <input type="hidden" name="csrfmiddlewaretoken" value="{csrf}">
    <input type="hidden" name="action" value="save_settings">
    <div class="card">
      <h2>📁 مسیر و کاهش حجم</h2>
      <div>
        <label>مسیر ذخیره *</label>
        <div class="path-input">
          <input type="text" name="backup_path" value="{s.backup_path}" placeholder="D:\\backups" {disabled}>
          <button type="button" class="browse-btn" onclick="browsePath()" {disabled}>📂 انتخاب پوشه</button>
        </div>
        <div class="save-notice" id="save-notice">⚠️ مسیر تغییر کرد ولی هنوز اعمال نشده. دکمه «ذخیره تنظیمات» پایین را بزنید!</div>
      </div>
      <div class="tip" style="margin-top:14px;">
        💡 <b>برای کاهش حجم بک‌اپ:</b>
        <ul style="margin:4px 0;padding-right:18px;">
          <li>LZMA: 30-50٪ کوچک‌تر از DEFLATE</li>
          <li>VACUUM: حذف فضای خالی SQLite (db معمولاً 50٪ کوچک‌تر می‌شود)</li>
          <li>بک‌اپ ساعتی بدون media: media حجم اصلی است، فقط در روزانه نگه دارید</li>
        </ul>
      </div>
      <div class="checkbox-row"><input type="checkbox" name="use_lzma_compression" id="lzma" {'checked' if s.use_lzma_compression else ''} {disabled}>
        <label for="lzma" style="margin:0;cursor:pointer;font-weight:normal;">🗜 فشرده‌سازی LZMA (پیشنهادی)</label></div>
      <div class="checkbox-row"><input type="checkbox" name="vacuum_sqlite_before_backup" id="vac" {'checked' if s.vacuum_sqlite_before_backup else ''} {disabled}>
        <label for="vac" style="margin:0;cursor:pointer;font-weight:normal;">⚡ VACUUM SQLite قبل از بک‌اپ</label></div>
      <div class="checkbox-row"><input type="checkbox" name="include_media_in_hourly" id="mh" {'checked' if s.include_media_in_hourly else ''} {disabled}>
        <label for="mh" style="margin:0;cursor:pointer;font-weight:normal;">📷 بک‌اپ ساعتی شامل media (پیشنهاد: خاموش)</label></div>
      <div class="checkbox-row"><input type="checkbox" name="include_media_in_daily" id="md" {'checked' if s.include_media_in_daily else ''} {disabled}>
        <label for="md" style="margin:0;cursor:pointer;font-weight:normal;">📷 بک‌اپ روزانه شامل media (پیشنهاد: روشن)</label></div>
      <div class="grid" style="margin-top:14px;">
        <div><label>حداکثر ساعتی</label><input type="number" name="keep_count" value="{s.keep_count}" min="1" {disabled}></div>
        <div><label>حداکثر روزانه</label><input type="number" name="daily_keep_count" value="{s.daily_keep_count}" min="1" {disabled}></div>
      </div>
      <div class="checkbox-row" style="margin-top:14px;"><input type="checkbox" name="safety_backup_enabled" id="sb" {'checked' if s.safety_backup_enabled else ''} {disabled}>
        <label for="sb" style="margin:0;cursor:pointer;font-weight:normal;">🛡 بک‌اپ قبل از ریست/بازیابی</label></div>
    </div>
    <div class="card"><h2>⏰ بک‌اپ خودکار</h2>
      <div class="checkbox-row"><input type="checkbox" name="is_auto_enabled" id="auto" {'checked' if s.is_auto_enabled else ''} {disabled}>
        <label for="auto" style="margin:0;cursor:pointer;font-weight:normal;">ساعتی</label></div>
      <div style="margin-top:8px;"><label>بازه (ساعت)</label><input type="number" name="interval_hours" value="{s.interval_hours}" min="1" max="168" {disabled}></div>
      <div class="checkbox-row" style="margin-top:14px;"><input type="checkbox" name="daily_backup_enabled" id="daily" {'checked' if s.daily_backup_enabled else ''} {disabled}>
        <label for="daily" style="margin:0;cursor:pointer;font-weight:normal;">📅 روزانه آخر شب</label></div>
      <div style="margin-top:8px;"><label>ساعت (HH:MM)</label><input type="text" name="daily_backup_time" value="{s.daily_backup_time}" {disabled}></div>
      <div class="auto-info"><b>زمان‌بندی خودکار (Linux cron):</b><br><br>
        دستور: <code>crontab -e</code><br><br>
        <b>📅 روزانه {s.daily_backup_time}</b> (HH:MM را به دقیقه/ساعت تبدیل کنید)<br>
        <code>30 23 * * * cd {project_path} && {python_path} manage.py run_daily_backup</code><br><br>
        <b>⏰ ساعتی</b> (در صورت فعال بودن)<br>
        <code>0 * * * * cd {project_path} && {python_path} manage.py run_backup --trigger auto</code><br><br>
        <span style="font-size:11px;">روی Windows از Task Scheduler با همان دستورات استفاده کنید.</span>
      </div>
    </div>
    <div class="card"><h2>📧 ایمیل</h2>
      <div class="checkbox-row"><input type="checkbox" name="email_enabled" id="em" {'checked' if s.email_enabled else ''} {disabled}>
        <label for="em" style="margin:0;cursor:pointer;font-weight:normal;">فعال</label></div>
      <div style="margin-top:10px;"><label>ایمیل مقصد</label><input type="email" name="email_to" value="{s.email_to}" placeholder="me@example.com" {disabled}></div>
    </div>
    <div class="card"><h2>📲 تلگرام</h2>
      <div class="checkbox-row"><input type="checkbox" name="telegram_enabled" id="tg" {'checked' if s.telegram_enabled else ''} {disabled}>
        <label for="tg" style="margin:0;cursor:pointer;font-weight:normal;">فعال</label></div>
      <div class="grid" style="margin-top:10px;">
        <div><label>توکن</label><input type="text" name="telegram_token" value="{s.telegram_token}" {disabled}></div>
        <div><label>Chat ID</label><input type="text" name="telegram_chat_id" value="{s.telegram_chat_id}" {disabled}></div>
      </div>
    </div>
    <div class="card"><h2>🟢 بله</h2>
      <div class="checkbox-row"><input type="checkbox" name="bale_enabled" id="bl" {'checked' if s.bale_enabled else ''} {disabled}>
        <label for="bl" style="margin:0;cursor:pointer;font-weight:normal;">فعال</label></div>
      <div class="grid" style="margin-top:10px;">
        <div><label>توکن بات بله</label><input type="text" name="bale_token" value="{s.bale_token}" {disabled}></div>
        <div><label>Chat ID</label><input type="text" name="bale_chat_id" value="{s.bale_chat_id}" {disabled}></div>
      </div>
      <div class="help">ساخت بات: در بله به @BotFather پیام دهید، newbot/ را بفرستید و توکن را اینجا وارد کنید. برای Chat ID یک پیام به بات بدهید و عدد chat.id را از getUpdates بردارید.</div>
    </div>
    <div class="card"><h2>🔐 رمزنگاری فایل ارسالی</h2>
      <div class="tip">ارسال به ایمیل/تلگرام/بله <b>فقط</b> با فایل رمزگذاری‌شده AES-256 و <b>فقط دیتابیس</b> (بدون media) انجام می‌شود. بدون وارد کردن رمز، هیچ فایلی ارسال نمی‌شود.</div>
      <div style="margin-top:10px;"><label>رمز فایل ارسالی *</label><input type="text" name="send_encryption_password" value="{s.send_encryption_password}" placeholder="یک رمز قوی انتخاب کنید" {disabled}></div>
      <div class="help">این رمز را جایی امن نگه دارید — برای باز کردن فایل در WinRAR/7-Zip لازم است.</div>
    </div>
    <div style="margin-top:16px;text-align:center;">
      <button type="submit" class="btn-save" {disabled}>💾 ذخیره تنظیمات</button>
    </div>
  </form>
  <div class="card"><h2>📋 تاریخچه</h2>
    <table><thead><tr>
      <th>تاریخ</th><th>دسته</th><th>وضعیت</th><th>منبع</th><th>اندازه</th><th>ارسال</th><th>توضیحات</th>
    </tr></thead><tbody>{log_rows}{empty_row}</tbody></table>
  </div>
</div></body></html>"""


class SystemResetApiView(APIView):
    """
    POST /api/accounting/system-reset/
    ریست سیستم از پنل ری‌اکت — دو حالت soft/hard، فقط superuser + تایید RESET.
    منطق ریست از admin_tools و قبل از اجرا safety backup گرفته می‌شود.
    """
    permission_classes = [IsAdminUser]

    def post(self, request):
        if not request.user.is_superuser:
            return Response({'error': 'فقط superuser'}, status=403)
        d = request.data
        mode = d.get('mode', '')
        if mode not in ('soft', 'hard'):
            return Response({'error': 'حالت نامعتبر است'}, status=400)
        if d.get('confirm', '').strip() != 'RESET':
            return Response({'error': 'باید RESET تایپ کنید'}, status=400)

        from .admin_tools import _soft_reset, _hard_reset

        safety_msg = ''
        try:
            sl = safety_backup_now(user=request.user, reason=f"قبل از {mode} reset (پنل)")
            if sl:
                safety_msg = f"safety backup #{sl.id}"
        except Exception as e:
            logger.warning(f"[RESET-API] safety backup خطا: {e}")

        try:
            report = _soft_reset() if mode == 'soft' else _hard_reset()
        except Exception as e:
            logger.exception(f"[RESET-API] خطا: {e}")
            return Response({'error': f'خطا در ریست: {e}'}, status=500)

        logger.warning(f"[RESET-API] {mode.upper()} توسط {request.user} — {report}")
        return Response({'success': True, 'mode': mode, 'report': report, 'safety': safety_msg})
