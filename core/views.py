# core/views.py
import logging

from django.db import connection
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from moments.models import Moment

from .urls_helpers import public_url

logger = logging.getLogger(__name__)


@require_GET
def home(request):
    moments = Moment.objects.published()[:12]
    return render(request, "core/home.html", {"moments": moments})


@never_cache
@require_GET
def healthz(request):
    """Health check for uptime monitors. Returns 200 only if the database answers."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:
        logger.exception("Health check failed: database unreachable")
        return JsonResponse({"status": "error", "database": "down"}, status=503)
    return JsonResponse({"status": "ok", "database": "up"})


def robots_txt(request):
    lines = [
        "User-agent: *",
        "Disallow: /admin/",
        "Disallow: /internal/",
        "Disallow: /free-printable/thanks/",
        f"Sitemap: {public_url(request, reverse('sitemap'))}",
    ]
    return HttpResponse("\n".join(lines) + "\n", content_type="text/plain")
