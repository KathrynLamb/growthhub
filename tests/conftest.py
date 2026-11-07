# tests/conftest.py
import pytest
from django.utils import timezone

from moments.models import Moment


@pytest.fixture(autouse=True)
def no_external_keys(settings):
    """Tests never call real APIs unless a test opts in with a mock."""
    settings.ANTHROPIC_API_KEY = ""
    settings.RESEND_API_KEY = ""


@pytest.fixture
def make_moment(db):
    def _make(slug="new-baby-sibling", status=Moment.Status.PUBLISHED, age_band="3-5", **extra):
        defaults = dict(
            slug=slug,
            short_name=slug.replace("-", " ").title(),
            title=f"A story for {slug}",
            age_band=age_band,
            summary="Summary text.",
            why_it_helps="Because it helps.",
            tips="Tip one\nTip two",
            sample_story="{name} did a brave thing.",
            status=status,
            published_at=timezone.now() if status == Moment.Status.PUBLISHED else None,
        )
        defaults.update(extra)
        return Moment.objects.create(**defaults)

    return _make
