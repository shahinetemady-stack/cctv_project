"""
watchdog_minipc — پایش مینی‌پی‌سی چین (میزبان ربات‌های اینستاگرام/تلگرام/واتساپ
و رله Gemini) هر ۵ دقیقه از کران سرور.

چک‌ها: پاسخ رله Gemini (پورت 3299 تونل) + SSH به مینی‌پی‌سی (پورت 2022 تونل برگشتی)
و وضعیت سرویس‌های ig-bot / wa-bot / tg-bot. فقط هنگام «تغییر وضعیت» پیامک هشدار
به سوپریوزرها می‌رود (قطع → اخطار، وصل → اطلاع رفع) تا اسپم نشود.
وضعیت در کش «minipc_health» هم نگه داشته می‌شود.

نکته: ارسال پیامک فقط وقتی انجام می‌شود که «شماره خط» در تنظیمات پیامک پنل
پر شده باشد؛ در غیر این صورت فقط لاگ می‌شود.
"""
import json
import logging
import subprocess
import time

import requests
from django.core.cache import cache
from django.core.management.base import BaseCommand
from django.conf import settings

logger = logging.getLogger(__name__)

STATE_PATH = settings.BASE_DIR / ".watchdog_minipc.json"
SSH = ["ssh", "-i", "/root/.ssh/minipc_watch_key", "-p", "2022",
       "-o", "BatchMode=yes", "-o", "ConnectTimeout=10",
       "-o", "StrictHostKeyChecking=accept-new", "dbk@127.0.0.1"]


def check_relay() -> bool:
    """رله Gemini روی مینی‌پی‌سی (از مسیر تونل) — 403 یعنی زنده است."""
    try:
        r = requests.get("http://127.0.0.1:3299/", timeout=8)
        return r.status_code in (403, 404, 405)
    except Exception:
        return False


def check_bots() -> dict | None:
    """وضعیت سرویس‌های ربات روی مینی‌پی‌سی — None یعنی خود SSH هم وصل نشد."""
    try:
        out = subprocess.run(
            SSH + ["systemctl is-active ig-bot wa-bot; "
                   "(kill -0 $(cat ~/tg-bot/bot.pid) 2>/dev/null && echo tg-active) || echo tg-inactive"],
            capture_output=True, text=True, timeout=20,
        )
        if out.returncode != 0 and not out.stdout:
            return None
        lines = out.stdout.split()
        return {
            "ssh": True,
            "ig": "active" in lines[:1],
            "wa": len(lines) > 1 and lines[1] == "active",
            "tg": "tg-active" in out.stdout,
        }
    except Exception:
        return None


class Command(BaseCommand):
    help = "پایش مینی‌پی‌سی و هشدار پیامکی هنگام قطع/وصل"

    def handle(self, *args, **opts):
        relay_ok = check_relay()
        bots = check_bots()
        problems = []
        if not relay_ok:
            problems.append("رله Gemini")
        if bots is None:
            problems.append("عدم دسترسی SSH به مینی‌پی‌سی")
        else:
            for key, label in (("ig", "ربات اینستاگرام"), ("wa", "ربات واتساپ"), ("tg", "ربات تلگرام")):
                if not bots[key]:
                    problems.append(label)

        healthy = not problems
        state = {}
        try:
            state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
        was_healthy = state.get("healthy", True)

        cache.set("minipc_health", {
            "healthy": healthy, "relay": relay_ok, "bots": bots,
            "checked_at": time.time(),
        }, None)

        if healthy == was_healthy:
            self.stdout.write(f"{'OK' if healthy else 'DOWN'} — بدون تغییر وضعیت")
            return

        STATE_PATH.write_text(json.dumps({
            "healthy": healthy, "changed_at": time.time(),
        }, ensure_ascii=False), encoding="utf-8")

        if healthy:
            text = "دوربینکار: اتصال مینی‌پی‌سی و ربات‌ها (اینستاگرام/تلگرام/واتساپ) دوباره برقرار شد."
        else:
            text = ("دوربینکار: هشدار! مشکل در مینی‌پی‌سی ربات‌ها: "
                    + "، ".join(problems)
                    + ". چت‌بات سایت با موتور جایگزین کار می‌کند ولی ربات‌های پیام‌رسان ممکن است قطع باشند.")

        from apps.notifications.sms import send_bulk_sms, get_line_number
        from apps.users.models import User
        phones = [u.phone for u in User.objects.filter(is_superuser=True)
                  if u.phone and u.phone.startswith("09")]
        if not phones or not get_line_number():
            logger.warning(f"[WATCHDOG] {text} (پیامک ارسال نشد — خط یا شماره سوپریوزر تنظیم نیست)")
            self.stdout.write(text + " — پیامک ارسال نشد (خط/شماره تنظیم نیست)")
            return
        sent, err = send_bulk_sms(phones, text)
        logger.info(f"[WATCHDOG] {text} — پیامک: {sent} موفق {err}")
        self.stdout.write(f"{text} — پیامک به {sent} شماره ارسال شد")
