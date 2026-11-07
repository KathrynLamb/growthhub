# printables/retention.py
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from .models import PrintableRequest


def purge_expired(dry_run=False):
    """Clear personal data from finished requests older than the retention period."""
    cutoff = timezone.now() - timedelta(days=settings.PRINTABLE_RETENTION_DAYS)
    qs = PrintableRequest.objects.filter(created_at__lt=cutoff, purged_at__isnull=True).exclude(
        status__in=[PrintableRequest.Status.QUEUED, PrintableRequest.Status.PROCESSING]
    )
    count = qs.count()
    if not dry_run:
        for req in qs.iterator():
            req.purge_personal_data()
    return count
