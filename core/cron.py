# core/cron.py
"""Protected URL for scheduled work when there's no server cron (Vercel mode).

Called by a GitHub Actions schedule every 15 minutes and by Vercel Cron once a
day, both sending `Authorization: Bearer <CRON_SECRET>`. It retries failed or
queued printables and runs the daily data purge.
"""
import hmac
import logging

from django.conf import settings
from django.http import Http404, JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from printables.pipeline import run_batch
from printables.retention import purge_expired

logger = logging.getLogger(__name__)


@csrf_exempt
@never_cache
@require_http_methods(["GET", "POST"])
def run_cron(request):
    if not settings.CRON_SECRET:
        raise Http404  # feature off: don't even admit the URL exists
    supplied = request.headers.get("Authorization", "")
    expected = f"Bearer {settings.CRON_SECRET}"
    if not hmac.compare_digest(supplied.encode(), expected.encode()):
        logger.warning("Cron called with a bad or missing secret")
        return JsonResponse({"error": "Unauthorised."}, status=401)

    result = run_batch(limit=5)
    result["purged"] = purge_expired()
    logger.info("Cron run: %s", result)
    return JsonResponse({"ok": True, **result})
