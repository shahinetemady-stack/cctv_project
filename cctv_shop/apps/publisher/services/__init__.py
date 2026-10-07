"""
apps/publisher/services/__init__.py
────────────────────────────────────
رجیستری سرویس‌های انتشار + داده اولیه پلتفرم‌ها.
"""

from .base import BaseMessengerService, PublishError
from .bale import BaleService
from .eitaa import EitaaService
from .instagram import InstagramService
from .rubika import RubikaService
from .telegram import TelegramService
from .whatsapp import WhatsAppService

SERVICES = {
    "telegram": TelegramService,
    "bale": BaleService,
    "rubika": RubikaService,
    "eitaa": EitaaService,
    "whatsapp": WhatsAppService,
    "instagram": InstagramService,
}

# داده اولیه پلتفرم‌ها — در مایگریشن 0002_seed_platforms ساخته می‌شود
PLATFORMS_SEED = [
    {"slug": "telegram", "name": "تلگرام", "sort_order": 1},
    {"slug": "bale", "name": "بله", "sort_order": 2},
    {"slug": "eitaa", "name": "ایتا", "sort_order": 3},
    {"slug": "rubika", "name": "روبیکا", "sort_order": 4},
    {"slug": "whatsapp", "name": "واتساپ", "sort_order": 5},
    {"slug": "instagram", "name": "اینستاگرام", "sort_order": 6},
]


def get_service(platform) -> BaseMessengerService:
    """
    سرویس متناظر با یک Platform را با اعتبارنامه فعالش می‌سازد.
    platform: نمونه مدل Platform. در نبود سرویس/اعتبارنامه PublishError.
    """
    service_cls = SERVICES.get(platform.slug)
    if service_cls is None:
        raise PublishError(f"سرویسی برای پلتفرم «{platform.slug}» پیاده‌سازی نشده است")
    credential = getattr(platform, "credential", None)
    if credential is None or not credential.is_active:
        raise PublishError(f"اعتبارنامه پلتفرم «{platform.name}» پیکربندی نشده است")
    return service_cls(credential)
