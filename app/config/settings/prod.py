# ──────────────────────────────────────────────────────────────
#  config/settings/prod.py — Production overrides
# ──────────────────────────────────────────────────────────────
from .base import *  # noqa: F401,F403

DEBUG = False

# ── Security hardening ───────────────────────────────────────
SECURE_SSL_REDIRECT = os.environ.get("SECURE_SSL_REDIRECT", "1") == "1"  # noqa: F405
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True

# ── CORS must be explicit in production ──────────────────────
CORS_ALLOW_ALL_ORIGINS = False

# ── Email (configure for your provider) ──────────────────────
EMAIL_BACKEND = os.environ.get(  # noqa: F405
    "EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend"
)
EMAIL_HOST = os.environ.get("EMAIL_HOST", "")  # noqa: F405
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))  # noqa: F405
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "1") == "1"  # noqa: F405
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")  # noqa: F405
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")  # noqa: F405
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "noreply@example.com")  # noqa: F405
