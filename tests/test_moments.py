# tests/test_moments.py
import pytest
from django.urls import reverse

from moments.models import Moment

pytestmark = pytest.mark.django_db


def test_only_published_moments_are_listed(client, make_moment):
    make_moment("new-baby-sibling")
    make_moment("moving-house", status=Moment.Status.DRAFT)
    html = client.get(reverse("moments:list")).content.decode()
    assert "New Baby Sibling" in html
    assert "Moving House" not in html


def test_draft_detail_is_404(client, make_moment):
    make_moment("moving-house", status=Moment.Status.DRAFT)
    assert client.get(reverse("moments:detail", args=["moving-house"])).status_code == 404


def test_detail_renders_sample_name(client, make_moment):
    make_moment("new-baby-sibling", sample_name="Priya")
    html = client.get(reverse("moments:detail", args=["new-baby-sibling"])).content.decode()
    assert "Priya did a brave thing." in html
    assert "application/ld+json" in html


def test_api_list_shape_and_cors(client, make_moment):
    make_moment("new-baby-sibling")
    make_moment("moving-house", status=Moment.Status.DRAFT)
    response = client.get(reverse("moments:api_list"))
    assert response.status_code == 200
    assert response["Access-Control-Allow-Origin"] == "*"
    data = response.json()
    assert data["count"] == 1
    item = data["results"][0]
    assert set(item) == {"slug", "title", "short_name", "age_band", "summary", "url", "published_at", "updated_at"}
    assert item["url"].startswith("http://testserver/moments/new-baby-sibling/")


def test_api_age_filter_and_bad_input(client, make_moment):
    make_moment("first-day-at-nursery", age_band="1-3")
    make_moment("starting-school", age_band="3-5")
    assert client.get(reverse("moments:api_list"), {"age": "1-3"}).json()["count"] == 1
    bad = client.get(reverse("moments:api_list"), {"age": "teen"})
    assert bad.status_code == 400
    assert "error" in bad.json()


def test_api_detail_includes_tips_and_404s_drafts(client, make_moment):
    make_moment("new-baby-sibling")
    make_moment("moving-house", status=Moment.Status.DRAFT)
    data = client.get(reverse("moments:api_detail", args=["new-baby-sibling"])).json()
    assert data["tips"] == ["Tip one", "Tip two"]
    assert client.get(reverse("moments:api_detail", args=["moving-house"])).status_code == 404


def test_publish_sets_review_fields(make_moment, django_user_model):
    user = django_user_model.objects.create_user("katy")
    moment = make_moment("moving-house", status=Moment.Status.DRAFT)
    moment.publish(user=user)
    moment.refresh_from_db()
    assert moment.status == Moment.Status.PUBLISHED
    assert moment.reviewed_by == user
    assert moment.published_at is not None


def test_sitemap_lists_published_only(client, make_moment):
    make_moment("new-baby-sibling")
    make_moment("moving-house", status=Moment.Status.DRAFT)
    xml = client.get("/sitemap.xml").content.decode()
    assert "/moments/new-baby-sibling/" in xml
    assert "/moments/moving-house/" not in xml


def test_seed_command_creates_drafts():
    from django.core.management import call_command

    call_command("seed_moments")
    assert Moment.objects.count() == 10
    assert not Moment.objects.published().exists()
    call_command("seed_moments")  # idempotent
    assert Moment.objects.count() == 10


def test_public_base_url_used_behind_proxy(client, make_moment, settings):
    """Behind flipwhizz.com/stories, links must point at flipwhizz.com, not the origin."""
    settings.PUBLIC_BASE_URL = "https://flipwhizz.com"
    make_moment("new-baby-sibling")
    api = client.get(reverse("moments:api_list")).json()
    assert api["results"][0]["url"] == "https://flipwhizz.com/moments/new-baby-sibling/"
    html = client.get(reverse("moments:detail", args=["new-baby-sibling"])).content.decode()
    assert '<link rel="canonical" href="https://flipwhizz.com/moments/new-baby-sibling/">' in html
    assert "https://flipwhizz.com/moments/new-baby-sibling/" in client.get("/sitemap.xml").content.decode()
    assert "Sitemap: https://flipwhizz.com/sitemap.xml" in client.get("/robots.txt").content.decode()
