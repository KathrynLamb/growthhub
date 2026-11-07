# printables/pipeline.py
"""Processes queued printable requests. Run by cron via `manage.py process_printables`.

Each request is claimed inside a transaction with SELECT ... FOR UPDATE
(SKIP LOCKED where supported), so two overlapping cron runs never process the
same request twice.
"""
import logging
from datetime import timedelta

from django.conf import settings
from django.db import connection, transaction
from django.db.models import Q
from django.utils import timezone

from .email import EmailError, send_printable
from .models import PrintableRequest
from .pdf import build_pdf
from .story import StoryError, generate_story, personalise

logger = logging.getLogger(__name__)

STUCK_AFTER = timedelta(minutes=15)


def claim_next():
    with transaction.atomic():
        qs = (
            PrintableRequest.objects.filter(status=PrintableRequest.Status.QUEUED)
            .filter(Q(next_attempt_at__isnull=True) | Q(next_attempt_at__lte=timezone.now()))
            .order_by("created_at")
        )
        if connection.features.has_select_for_update_skip_locked:
            qs = qs.select_for_update(skip_locked=True)
        req = qs.first()
        if req is None:
            return None
        req.status = PrintableRequest.Status.PROCESSING
        req.attempts += 1
        req.claimed_at = timezone.now()
        req.save(update_fields=["status", "attempts", "claimed_at"])
        return req


def process(req):
    """Generate, render and send one request. Never logs the child's name or email."""
    try:
        if not req.story:
            req.story = generate_story(req.child_age, req.interests, req.moment)
            req.save(update_fields=["story"])
        story = personalise(req.story, req.child_name)
        pdf_bytes = build_pdf(story, req.child_name, utm_campaign=req.utm_campaign or "free-printable")
        send_printable(req.email, req.child_name, story["title"], pdf_bytes)
    except (StoryError, EmailError) as exc:
        logger.warning("Printable %s failed (attempt %s): %s", req.token, req.attempts, exc)
        req.mark_failed_or_requeue(str(exc), settings.PRINTABLE_MAX_ATTEMPTS)
        return False
    except Exception as exc:  # unexpected: log the trace, keep PII out of last_error
        logger.exception("Printable %s crashed (attempt %s)", req.token, req.attempts)
        req.mark_failed_or_requeue(f"Unexpected {exc.__class__.__name__}", settings.PRINTABLE_MAX_ATTEMPTS)
        return False

    req.status = PrintableRequest.Status.SENT
    req.sent_at = timezone.now()
    req.last_error = ""
    req.save(update_fields=["status", "sent_at", "last_error"])
    logger.info("Printable %s sent", req.token)
    return True


def release_stuck():
    """Requeue anything left in 'processing' by a crashed run."""
    cutoff = timezone.now() - STUCK_AFTER
    stuck = PrintableRequest.objects.filter(status=PrintableRequest.Status.PROCESSING, claimed_at__lt=cutoff)
    count = 0
    for req in stuck:
        req.mark_failed_or_requeue("Stuck in processing; released", settings.PRINTABLE_MAX_ATTEMPTS)
        count += 1
    return count


def run_batch(limit=10):
    released = release_stuck()
    sent = failed = 0
    for _ in range(limit):
        req = claim_next()
        if req is None:
            break
        if process(req):
            sent += 1
        else:
            failed += 1
    return {"released": released, "sent": sent, "failed": failed}
