# printables/management/commands/preview_printable.py
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from moments.models import Moment
from printables.pdf import build_pdf
from printables.story import generate_story, personalise


class Command(BaseCommand):
    help = "Write a sample printable PDF to disk without saving or emailing anything."

    def add_arguments(self, parser):
        parser.add_argument("--name", default="Maisie")
        parser.add_argument("--age", type=int, default=4)
        parser.add_argument("--interests", default="")
        parser.add_argument("--moment", help="Moment slug, e.g. new-baby-sibling")
        parser.add_argument("--out", default="sample-output/preview.pdf")

    def handle(self, *args, **opts):
        moment = None
        if opts["moment"]:
            moment = Moment.objects.filter(slug=opts["moment"]).first()
            if moment is None:
                raise CommandError(f"No moment with slug '{opts['moment']}'")
        story = personalise(generate_story(opts["age"], opts["interests"], moment), opts["name"])
        out = Path(opts["out"])
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(build_pdf(story, opts["name"]))
        self.stdout.write(self.style.SUCCESS(f"Wrote {out} ({story['title']})"))
