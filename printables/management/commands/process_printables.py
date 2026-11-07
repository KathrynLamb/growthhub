# printables/management/commands/process_printables.py
from django.core.management.base import BaseCommand

from printables.pipeline import run_batch


class Command(BaseCommand):
    help = "Generate and email queued printables. Run from cron every minute."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=10)

    def handle(self, *args, **options):
        result = run_batch(limit=options["limit"])
        self.stdout.write(
            f"released={result['released']} sent={result['sent']} failed={result['failed']}"
        )
