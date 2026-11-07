# printables/management/commands/forget_email.py
from django.core.management.base import BaseCommand

from printables.models import PrintableRequest


class Command(BaseCommand):
    help = "Erase personal data for one email address (UK GDPR erasure request)."

    def add_arguments(self, parser):
        parser.add_argument("email")

    def handle(self, *args, **opts):
        rows = PrintableRequest.objects.filter(email=opts["email"].strip().lower(), purged_at__isnull=True)
        count = 0
        for req in rows:
            req.purge_personal_data()
            count += 1
        self.stdout.write(self.style.SUCCESS(f"Erased personal data from {count} request(s)."))
