"""
Django Settings — CCTV Parts Shop
Django 5.0 | DRF | PostgreSQL
"""

from pathlib import Path
from decouple import config, Csv

BASE_DIR = Path(__file__).resolve().parent.parent

# ─── Security ────────────────────────────────────────────────────────────────
SECRET_KEY = config("SECRET_KEY", default="change-me-in-production-use-decouple")
DEBUG = config("DEBUG", default=True, cast=bool)
ALLOWED_HOSTS = config(
    "ALLOWED_HOSTS",
    default="localhost,127.0.0.1,0.0.0.0,::1,192.168.1.12",
    cast=Csv(),
)
# برای فرم‌های POST روی دامنه HTTPS (TLS در لبه CDN تمام می‌شود)
CSRF_TRUSTED_ORIGINS = config(
    "CSRF_TRUSTED_ORIGINS",
    default="http://localhost:3000,http://127.0.0.1:3000",
    cast=Csv(),
)
# سایت پشت nginx/CDN است — تشخیص https در build_absolute_uri (canonical/og:url درست شود)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# ─── Applications ─────────────────────────────────────────────────────────────
INSTALLED_APPS = [
    # Django built-ins
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sitemaps",
    # Third-party
    "rest_framework",
    "rest_framework.authtoken",
    "django_filters",
    "corsheaders",
    # JWT
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    # Local apps
    "apps.core",
    "apps.users",
    "apps.catalog",
    "apps.orders",
    "apps.inventory",
    "apps.notifications",
    "apps.payment",
    "apps.leads",
    "apps.accounting",
    "apps.education",
    "apps.assistant",
    "apps.payroll",
    "apps.expenses",
    "apps.production",
    "apps.chat",
    "apps.publisher",
    "django.contrib.humanize",

]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.core.middleware.CurrentUserMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.users.middleware.ActivityLogMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# ─── Database ─────────────────────────────────────────────────────────────────
# ─── Database ─────────────────────────────────────────────────────────────────
# پیش‌فرض: SQLite (بدون نیاز به نصب چیزی)
# برای PostgreSQL: در .env بگذارید USE_POSTGRES=True
_USE_POSTGRES = config("USE_POSTGRES", default=False, cast=bool)

if _USE_POSTGRES:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": config("DB_NAME", default="cctv_shop_db"),
            "USER": config("DB_USER", default="postgres"),
            "PASSWORD": config("DB_PASSWORD", default="postgres"),
            "HOST": config("DB_HOST", default="localhost"),
            "PORT": config("DB_PORT", default="5432"),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# ─── Auth ─────────────────────────────────────────────────────────────────────
AUTH_USER_MODEL = "users.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ─── Internationalization ─────────────────────────────────────────────────────
LANGUAGE_CODE = "fa-ir"
TIME_ZONE = "Asia/Tehran"
USE_I18N = True
USE_TZ = True

# ─── Cache ────────────────────────────────────────────────────────────────────
# FileBased چون پیش‌فرض locmem بین پروسه‌ها share نمی‌شود و صف وب‌هوک ترب
# (نوشته‌شده توسط ورکرهای gunicorn، خوانده‌شده توسط کران push_torob_updates)
# و فلگ‌های روزانه (ارزیابی باشگاه/بستانکاری) هرگز بین پروسه‌ها منتقل نمی‌شدند.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.filebased.FileBasedCache",
        "LOCATION": BASE_DIR / ".cache",
    }
}

# ─── Static & Media ───────────────────────────────────────────────────────────
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ─── Django REST Framework ────────────────────────────────────────────────────
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        # SessionAuthentication removed: with admin session cookie, frontend POSTs got 403 (CSRF)
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 24,
}

# ─── CORS ─────────────────────────────────────────────────────────────────────
CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS",
    default="http://localhost:3000,http://127.0.0.1:3000",
    cast=Csv(),
)
CORS_ALLOW_CREDENTIALS = True

# ─── Email ────────────────────────────────────────────────────────────────────
EMAIL_BACKEND = config(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.console.EmailBackend",
)
EMAIL_HOST = config("EMAIL_HOST", default="smtp.gmail.com")
EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)
EMAIL_USE_TLS = True
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
ADMIN_EMAIL = config("ADMIN_EMAIL", default="admin@example.com")


# ─── Behpardakht (Mellat) Payment Gateway ─────────────────────────────────────
BEHPARDAKHT_TERMINAL_ID = config("BEHPARDAKHT_TERMINAL_ID", default="")
BEHPARDAKHT_USERNAME = config("BEHPARDAKHT_USERNAME", default="")
BEHPARDAKHT_PASSWORD = config("BEHPARDAKHT_PASSWORD", default="")
BEHPARDAKHT_CALLBACK_URL = config(
    "BEHPARDAKHT_CALLBACK_URL",
    default="http://localhost:8000/api/payment/bank/verify/",
)

# ─── Business Logic Constants ─────────────────────────────────────────────────
# موجودی زیر این مقدار → هشدار
LOW_STOCK_THRESHOLD = config("LOW_STOCK_THRESHOLD", default=5, cast=int)
# مدت رزرو موجودی برای همکار (دقیقه)
RESERVATION_DURATION_MINUTES = config("RESERVATION_DURATION_MINUTES", default=120, cast=int)
# مهلت تأیید ادمین (دقیقه)
ADMIN_CONFIRM_DEADLINE_MINUTES = config("ADMIN_CONFIRM_DEADLINE_MINUTES", default=15, cast=int)

# ─── JWT (Simple JWT) ─────────────────────────────────────────────────────────
from datetime import timedelta

SIMPLE_JWT = {
    # توکن دسترسی: ۱ روز
    "ACCESS_TOKEN_LIFETIME": timedelta(days=1),
    # توکن تازه‌سازی: ۳۰ روز
    "REFRESH_TOKEN_LIFETIME": timedelta(days=30),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}


# ─── DRF Throttling ─────────────────────────────────────────────────────────────
REST_FRAMEWORK.update({
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.ScopedRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "60/min",
        "user": "600/min",
    },
})

# ─── Payment Frontend Redirect URLs ──────────────────────────────────────────
PAYMENT_SUCCESS_URL = config("PAYMENT_SUCCESS_URL", default="http://localhost:3000/payment/success/")
PAYMENT_FAIL_URL    = config("PAYMENT_FAIL_URL",    default="http://localhost:3000/payment/fail/")

# ─── Frontend URLs (for payment redirect) ────────────────────────────────────
FRONTEND_SUCCESS_URL = config("FRONTEND_SUCCESS_URL", default="http://localhost:3000/payment/success")
FRONTEND_FAILURE_URL = config("FRONTEND_FAILURE_URL", default="http://localhost:3000/payment/failure")

# سقف خرید مستقیم نقدی با پرداخت آنلاین (ریال) — فقط مشتری عمومی؛ بالای این مبلغ باید تماس/استعلام
DIRECT_PURCHASE_MAX_RIAL = config("DIRECT_PURCHASE_MAX_RIAL", default=200_000_000, cast=int)

# ─── AI Assistant (ربات مشاور هوشمند) ────────────────────────────────────────
# هر سرویس OpenAI-compatible — پیش‌فرض Moonshot/Kimi. کلید را در .env بگذارید.
AI_API_KEY  = config("AI_API_KEY",  default="")
AI_API_BASE = config("AI_API_BASE", default="https://api.moonshot.cn/v1")
AI_API_MODEL = config("AI_API_MODEL", default="moonshot-v1-8k")

# ─── Torob Product API v3 ────────────────────────────────────────────────────
# کلید عمومی ed25519 ترب برای بررسی JWT هدر X-Torob-Token — خالی یعنی بدون بررسی (توسعه)
TOROB_PUBLIC_KEY = config(
    "TOROB_PUBLIC_KEY",
    default="-----BEGIN PUBLIC KEY-----\nMCowBQYDK2VwAyEAt6Mu4T0pBORY11W+QeM35UsmLO3vsf+6yKpFDEImFk0=\n-----END PUBLIC KEY-----",
)
# توکن Bearer وب‌هوک ترب — از پشتیبانی ترب گرفته می‌شود؛ خالی یعنی ارسال وب‌هوک غیرفعال
TOROB_WEBHOOK_TOKEN = config("TOROB_WEBHOOK_TOKEN", default="")
