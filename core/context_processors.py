# core/context_processors.py
from django.conf import settings

from .urls_helpers import public_url


def site(request):
    return {
        "SITE_NAME": settings.SITE_NAME,
        "FLIPWHIZZ_URL": settings.FLIPWHIZZ_URL,
        "canonical_url": public_url(request, request.path),
    }
