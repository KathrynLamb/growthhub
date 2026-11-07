# printables/limits.py
"""Rate and cost limits for the free printable.

Limits are counted from the database, so they hold across server restarts and
multiple worker processes without needing Redis.
"""
import hashlib
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from .models import PrintableRequest


class LimitExceeded(Exception):
    def __init__(self, message):
        super().__init__(message)
        self.message = message


def hash_ip(ip):
    return hashlib.sha256(f"{settings.IP_HASH_SALT}:{ip}".encode()).hexdigest()


def client_ip(request):
    # Behind Apache or nginx on the same box, REMOTE_ADDR is the real client
    # unless a proxy header is set. Only trust the first X-Forwarded-For hop.
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


def check_limits(email, ip_hash):
    since = timezone.now() - timedelta(days=1)
    recent = PrintableRequest.objects.filter(created_at__gte=since)

    if recent.count() >= settings.PRINTABLE_GLOBAL_LIMIT_PER_DAY:
        raise LimitExceeded("We've had lots of requests today. Please try again tomorrow.")
    if recent.filter(email=email).count() >= settings.PRINTABLE_LIMIT_PER_EMAIL_PER_DAY:
        raise LimitExceeded("You've reached today's limit for this email. Please try again tomorrow.")
    if recent.filter(ip_hash=ip_hash).count() >= settings.PRINTABLE_LIMIT_PER_IP_PER_DAY:
        raise LimitExceeded("You've reached today's limit. Please try again tomorrow.")
