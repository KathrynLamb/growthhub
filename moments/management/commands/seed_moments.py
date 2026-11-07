# moments/management/commands/seed_moments.py
import json
from pathlib import Path

from django.core.management.base import BaseCommand

from moments.models import Moment

SEED_FILE = Path(__file__).resolve().parents[2] / "seed" / "moments.json"


class Command(BaseCommand):
    help = "Load the starter moments as drafts. Existing slugs are left alone."

    def add_arguments(self, parser):
        parser.add_argument("--file", default=str(SEED_FILE))

    def handle(self, *args, **options):
        items = json.loads(Path(options["file"]).read_text(encoding="utf-8"))
        created = 0
        for item in items:
            _, was_created = Moment.objects.get_or_create(
                slug=item["slug"],
                defaults={**item, "status": Moment.Status.DRAFT},
            )
            created += int(was_created)
        self.stdout.write(
            self.style.SUCCESS(
                f"{created} new draft moment(s) created, {len(items) - created} already existed. "
                "Review and publish them in the admin."
            )
        )
