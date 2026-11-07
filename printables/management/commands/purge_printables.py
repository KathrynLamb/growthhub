# printables/management/commands/purge_printables.py
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from printables.models import PrintableRequest


class Command(BaseCommand):
    help = "Clear personal data from printable requests older than PRINTABLE_RETENTION_DAYS. Run daily."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(days=settings.PRINTABLE_RETENTION_DAYS)
        qs = PrintableRequest.objects.filter(created_at__lt=cutoff, purged_at__isnull=True).exclude(
            status__in=[PrintableRequest.Status.QUEUED, PrintableRequest.Status.PROCESSING]
        )
        count = qs.count()
        if options["dry_run"]:
            self.stdout.write(f"Would purge {count} request(s).")
            return
        for req in qs.iterator():
            req.purge_personal_data()
        self.stdout.write(self.style.SUCCESS(f"Purged personal data from {count} request(s)."))
