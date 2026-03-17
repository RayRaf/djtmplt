"""
config/urls.py — Root URL configuration.
"""
from django.contrib import admin
from django.http import JsonResponse
from django.urls import path

from config.health import build_readiness_report


def health_check(request):
    """Lightweight health check for Docker / load balancer probes."""
    return JsonResponse({"status": "ok"})


def readiness_check(request):
    """Readiness check for database/cache/migrations-aware probes."""
    report = build_readiness_report(check_migrations=True)
    status_code = 200 if report["status"] == "ok" else 503
    return JsonResponse(report, status=status_code)


urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health_check, name="health-check"),
    path("ready/", readiness_check, name="readiness-check"),
    # path("api/", include("apps.core.urls")),
]
