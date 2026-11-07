# core/models.py
from django.db import models
from django.utils import timezone


class Incident(models.Model):
    """A simple incident log, filled in from the admin when something breaks.

    Kept deliberately small: what happened, how bad, when, why, and what
    changed so it doesn't happen again. See RUNBOOK.md for the process.
    """

    class Severity(models.TextChoices):
        SEV1 = "sev1", "SEV1: service down"
        SEV2 = "sev2", "SEV2: feature broken"
        SEV3 = "sev3", "SEV3: degraded or minor"

    title = models.CharField(max_length=200)
    severity = models.CharField(max_length=10, choices=Severity.choices, default=Severity.SEV3)
    started_at = models.DateTimeField(default=timezone.now)
    resolved_at = models.DateTimeField(null=True, blank=True)
    impact = models.TextField(help_text="Who or what was affected, in plain English.")
    root_cause = models.TextField(blank=True)
    actions_taken = models.TextField(blank=True)
    follow_ups = models.TextField(blank=True, help_text="Changes to stop it happening again.")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"[{self.get_severity_display()}] {self.title}"

    @property
    def is_open(self):
        return self.resolved_at is None

    @property
    def duration(self):
        end = self.resolved_at or timezone.now()
        return end - self.started_at
