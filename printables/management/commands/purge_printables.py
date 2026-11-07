# printables/management/commands/purge_printables.py
from django.core.management.base import BaseCommand

from printables.retention import purge_expired


class Command(BaseCommand):
    help = "Clear personal data from printable requests older than PRINTABLE_RETENTION_DAYS. Run daily."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        count = purge_expired(dry_run=options["dry_run"])
        if options["dry_run"]:
            self.stdout.write(f"Would purge {count} request(s).")
        else:
            self.stdout.write(self.style.SUCCESS(f"Purged personal data from {count} request(s)."))
