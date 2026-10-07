"""
apps/publisher/crypto.py
─────────────────────────
رمزنگاری اعتبارنامه‌های پیام‌رسان‌ها با Fernet.
کلید از SECRET_KEY جنگو مشتق می‌شود (SHA-256 → urlsafe base64) تا
کلید جداگانه‌ای لازم نباشد — با تغییر SECRET_KEY همه رکوردها غیرقابل رمزگشایی می‌شوند.
"""

import base64
import hashlib
import json

from cryptography.fernet import Fernet
from django.conf import settings


def _fernet():
    key = base64.urlsafe_b64encode(hashlib.sha256(settings.SECRET_KEY.encode()).digest())
    return Fernet(key)


def encrypt_json(data: dict) -> str:
    """دیکشنری را به رشته رمزنگاری‌شده Fernet تبدیل می‌کند."""
    return _fernet().encrypt(json.dumps(data).encode()).decode()


def decrypt_json(token: str) -> dict:
    """رشته رمزنگاری‌شده را به دیکشنری برمی‌گرداند؛ توکن نامعتبر → خطای Fernet."""
    return json.loads(_fernet().decrypt(token.encode()).decode())
