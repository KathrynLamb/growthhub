# printables/models.py
import uuid
from datetime import timedelta

from django.db import models
from django.utils import timezone

from moments.models import Moment


class PrintableRequest(models.Model):
    """A parent's request for a free personalised draw-your-own story PDF.

    Lifecycle: queued -> processing -> sent (or failed after max attempts).
    Personal details are cleared after PRINTABLE_RETENTION_DAYS by the
    purge_printables command; the anonymous row stays for reporting.
    """

    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        PROCESSING = "processing", "Processing"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"

    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    email = models.EmailField()
    child_name = models.CharField(max_length=30)
    child_age = models.PositiveSmallIntegerField()
    interests = models.CharField(max_length=120, blank=True)
    moment = models.ForeignKey(Moment, null=True, blank=True, on_delete=models.SET_NULL, related_name="printables")

    confirmed_parent = models.BooleanField(default=False)
    marketing_opt_in = models.BooleanField(default=False)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.QUEUED, db_index=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    last_error = models.CharField(max_length=255, blank=True)
    story = models.JSONField(null=True, blank=True)

    ip_hash = models.CharField(max_length=64, db_index=True)
    utm_source = models.CharField(max_length=60, blank=True)
    utm_medium = models.CharField(max_length=60, blank=True)
    utm_campaign = models.CharField(max_length=60, blank=True)

    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    claimed_at = models.DateTimeField(null=True, blank=True)
    next_attempt_at = models.DateTimeField(null=True, blank=True, db_index=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    purged_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["email", "created_at"])]

    def __str__(self):
        return f"Printable {self.token} ({self.status})"

    def mark_failed_or_requeue(self, message, max_attempts):
        """Record a failure. Requeue with backoff (5, 10, 20 min...) unless out of attempts."""
        self.last_error = message[:255]
        if self.attempts >= max_attempts:
            self.status = self.Status.FAILED
        else:
            self.status = self.Status.QUEUED
            self.next_attempt_at = timezone.now() + timedelta(minutes=5 * 2 ** max(self.attempts - 1, 0))
        self.save(update_fields=["last_error", "status", "next_attempt_at"])

    def purge_personal_data(self):
        self.email = f"purged-{self.pk}@invalid.example"
        self.child_name = ""
        self.interests = ""
        self.story = None
        self.purged_at = timezone.now()
        self.save(update_fields=["email", "child_name", "interests", "story", "purged_at"])
