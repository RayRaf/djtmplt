# ──────────────────────────────────────────────────────────────
#  config/settings/prod.py — Production overrides
# ──────────────────────────────────────────────────────────────
import sentry_sdk

from .base import *  # noqa: F401,F403

DEBUG = False

# ── Startup guards ───────────────────────────────────────────
_secret_key = os.environ.get("SECRET_KEY", "change-me-in-production")  # noqa: F405
if _secret_key == "change-me-in-production":
    raise ValueError("SECRET_KEY env var must be set to a strong random value in production.")

_allowed_hosts_raw = os.environ.get("ALLOWED_HOSTS", "")  # noqa: F405
if not _allowed_hosts_raw.strip() or _allowed_hosts_raw.strip() == "*":
    raise ValueError("ALLOWED_HOSTS env var must be set to your domain(s) in production (e.g. 'example.com,www.example.com').")

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

# ── Sentry ────────────────────────────────────────────────────
_sentry_dsn = os.environ.get("SENTRY_DSN", "")  # noqa: F405
if _sentry_dsn:
    sentry_sdk.init(
        dsn=_sentry_dsn,
        traces_sample_rate=float(os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "0.1")),  # noqa: F405
        send_default_pii=False,
    )
