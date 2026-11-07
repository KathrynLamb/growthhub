# core/urls_helpers.py
from django.conf import settings


def public_url(request, path):
    """Absolute URL as the public sees it.

    When the app sits behind flipwhizz.com/stories, the request host is the
    origin server, so we build links from PUBLIC_BASE_URL instead.
    """
    if settings.PUBLIC_BASE_URL:
        return settings.PUBLIC_BASE_URL + path
    return request.build_absolute_uri(path)
