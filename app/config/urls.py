"""
config/urls.py — Root URL configuration.
"""
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse


def health_check(request):
    """Lightweight health check for Docker / load balancer probes."""
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health_check, name="health-check"),
    # path("api/", include("apps.core.urls")),
]
