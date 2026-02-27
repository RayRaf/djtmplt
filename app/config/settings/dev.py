# ──────────────────────────────────────────────────────────────
#  config/settings/dev.py — Local development overrides
# ──────────────────────────────────────────────────────────────
from .base import *  # noqa: F401,F403

DEBUG = True

ALLOWED_HOSTS = ["*"]

# Allow all CORS in dev
CORS_ALLOW_ALL_ORIGINS = True

# Django Debug Toolbar (optional, uncomment if installed)
# INSTALLED_APPS += ["debug_toolbar"]
# MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")
# INTERNAL_IPS = ["127.0.0.1", "172.0.0.0/8"]

# Use console email backend in dev
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Simpler static files storage in dev
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"

# More verbose logging in dev
LOGGING["root"]["level"] = "DEBUG"  # noqa: F405
