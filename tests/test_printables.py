# tests/test_printables.py
from datetime import timedelta
from unittest import mock

import pytest
from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone

from printables import pipeline
from printables.models import PrintableRequest
from printables.pdf import build_pdf
from printables.story import StoryError, build_user_prompt, generate_offline, parse_story, personalise

pytestmark = pytest.mark.django_db

URL = reverse("printables:request")
AJAX = {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}


def valid_data(**overrides):
    data = {
        "child_name": "Maisie",
        "child_age": "4",
        "interests": "dinosaurs, the seaside",
        "email": "Parent@Example.com",
        "confirmed_parent": "on",
    }
    data.update(overrides)
    return data


# --- Form and view ----------------------------------------------------------


def test_valid_request_is_queued(client):
    response = client.post(URL + "?utm_source=instagram&utm_campaign=activitwins", valid_data())
    assert response.status_code == 302
    req = PrintableRequest.objects.get()
    assert req.status == PrintableRequest.Status.QUEUED
    assert req.email == "parent@example.com"
    assert req.utm_source == "instagram"
    assert req.utm_campaign == "activitwins"
    assert len(req.ip_hash) == 64 and "127.0.0.1" not in req.ip_hash


def test_ajax_success_returns_json(client):
    response = client.post(URL, valid_data(), **AJAX)
    assert response.status_code == 201
    assert response.json() == {"ok": True, "redirect": reverse("printables:thanks")}


def test_ajax_errors_are_json(client):
    response = client.post(URL, valid_data(child_name="M4isie!", confirmed_parent=""), **AJAX)
    assert response.status_code == 400
    errors = response.json()["errors"]
    assert "child_name" in errors and "confirmed_parent" in errors
    assert not PrintableRequest.objects.exists()


def test_honeypot_blocks_bots(client):
    client.post(URL, valid_data(website="http://spam.example"))
    assert not PrintableRequest.objects.exists()


def test_interests_are_sanitised(client):
    client.post(URL, valid_data(interests="trains {ignore rules} <script>`x`"))
    assert PrintableRequest.objects.get().interests == "trains ignore rules scriptx"


def test_rate_limit_per_email(client, settings):
    settings.PRINTABLE_LIMIT_PER_EMAIL_PER_DAY = 2
    for _ in range(2):
        assert client.post(URL, valid_data(), **AJAX).status_code == 201
    blocked = client.post(URL, valid_data(), **AJAX)
    assert blocked.status_code == 429
    assert "limit" in blocked.json()["message"]
    assert PrintableRequest.objects.count() == 2


def test_rate_limit_per_ip(client, settings):
    settings.PRINTABLE_LIMIT_PER_IP_PER_DAY = 1
    client.post(URL, valid_data(email="a@example.com"))
    blocked = client.post(URL, valid_data(email="b@example.com"), **AJAX)
    assert blocked.status_code == 429


def test_moment_prefill_only_for_published(client, make_moment):
    from moments.models import Moment

    make_moment("moving-house", status=Moment.Status.DRAFT)
    make_moment("new-baby-sibling")
    html = client.get(URL + "?moment=new-baby-sibling").content.decode()
    assert "selected>New Baby Sibling" in html
    assert "Moving House" not in html


# --- Story ------------------------------------------------------------------


def test_child_name_never_reaches_the_prompt(make_moment):
    prompt = build_user_prompt(4, "dinosaurs", make_moment())
    assert "Maisie" not in prompt
    assert "<notes>dinosaurs</notes>" in prompt


def test_parse_story_accepts_wrapped_json():
    text = 'Here you go:\n{"title": "{name} at sea", "pages": ["a {name}", "b", "c", "d", "e", "f", "g"]}'
    story = parse_story(text)
    assert story["title"] == "{name} at sea"
    assert len(story["pages"]) == 6


@pytest.mark.parametrize(
    "text",
    [
        "no json here",
        '{"title": "x", "pages": "not a list"}',
        '{"title": "x", "pages": ["a", "b", "c", "d"]}',  # never uses {name}
        '{"title": "x", "pages": ["{name}", "b"]}',  # too short
    ],
)
def test_parse_story_rejects_bad_output(text):
    with pytest.raises(StoryError):
        parse_story(text)


def test_personalise_swaps_placeholder():
    story = personalise(generate_offline(4, "", None), "Maisie")
    assert "{name}" not in story["title"] + "".join(story["pages"])
    assert "Maisie" in story["title"]


def test_pdf_is_valid():
    pdf = build_pdf(personalise(generate_offline(4, "", None), "Maisie"), "Maisie")
    assert pdf.startswith(b"%PDF")
    assert pdf.count(b"/Type /Page\n") + pdf.count(b"/Type /Page ") >= 8 or len(pdf) > 3000


# --- Pipeline ---------------------------------------------------------------


def make_request(**extra):
    defaults = dict(email="p@example.com", child_name="Maisie", child_age=4, confirmed_parent=True, ip_hash="x" * 64)
    defaults.update(extra)
    return PrintableRequest.objects.create(**defaults)


def test_pipeline_sends_and_marks_sent(settings):
    settings.RESEND_API_KEY = "test-key"
    req = make_request()
    fake = mock.Mock(status_code=200)
    fake.json.return_value = {"id": "email_123"}
    with mock.patch("printables.email.requests.post", return_value=fake) as post:
        result = pipeline.run_batch()
    assert result == {"released": 0, "sent": 1, "failed": 0}
    req.refresh_from_db()
    assert req.status == PrintableRequest.Status.SENT and req.attempts == 1
    payload = post.call_args.kwargs["json"]
    assert payload["to"] == ["p@example.com"]
    assert payload["attachments"][0]["filename"] == "my-story.pdf"
    assert post.call_args.kwargs["headers"]["Authorization"] == "Bearer test-key"


def test_pipeline_retries_then_fails(settings):
    settings.RESEND_API_KEY = "test-key"
    settings.PRINTABLE_MAX_ATTEMPTS = 2
    req = make_request()
    fake = mock.Mock(status_code=500)
    fake.json.return_value = {"name": "internal_server_error"}
    with mock.patch("printables.email.requests.post", return_value=fake):
        pipeline.run_batch()
        req.refresh_from_db()
        assert req.status == PrintableRequest.Status.QUEUED
        assert "Resend error 500" in req.last_error
        assert req.next_attempt_at > timezone.now()  # backoff, not an instant retry
        assert pipeline.run_batch()["failed"] == 0  # nothing due yet
        PrintableRequest.objects.update(next_attempt_at=timezone.now())
        pipeline.run_batch()
    req.refresh_from_db()
    assert req.status == PrintableRequest.Status.FAILED
    assert req.attempts == 2
    assert "Maisie" not in req.last_error and "p@example.com" not in req.last_error


def test_story_is_kept_between_retries(settings):
    """A retry after an email failure must not pay for a second story generation."""
    settings.RESEND_API_KEY = "test-key"
    req = make_request()
    fail = mock.Mock(status_code=500)
    fail.json.return_value = {}
    with mock.patch("printables.email.requests.post", return_value=fail):
        pipeline.run_batch()
    req.refresh_from_db()
    assert req.story is not None
    PrintableRequest.objects.update(next_attempt_at=timezone.now())
    ok = mock.Mock(status_code=200)
    ok.json.return_value = {"id": "1"}
    with mock.patch("printables.pipeline.generate_story") as gen, mock.patch(
        "printables.email.requests.post", return_value=ok
    ):
        pipeline.run_batch()
        gen.assert_not_called()
    req.refresh_from_db()
    assert req.status == PrintableRequest.Status.SENT


def test_stuck_requests_are_released():
    req = make_request(status=PrintableRequest.Status.PROCESSING, attempts=1,
                       claimed_at=timezone.now() - timedelta(hours=1))
    assert pipeline.release_stuck() == 1
    req.refresh_from_db()
    assert req.status == PrintableRequest.Status.QUEUED


def test_purge_clears_personal_data():
    old = make_request(status=PrintableRequest.Status.SENT, story={"title": "t", "pages": []},
                       created_at=timezone.now() - timedelta(days=40))
    new = make_request(status=PrintableRequest.Status.SENT)
    call_command("purge_printables")
    old.refresh_from_db()
    new.refresh_from_db()
    assert old.child_name == "" and old.story is None and old.purged_at is not None
    assert "p@example.com" not in old.email
    assert new.child_name == "Maisie"


# --- Health -----------------------------------------------------------------


def test_healthz(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "up"}


def test_forget_email_erases_only_that_parent():
    mine = make_request(email="me@example.com", status=PrintableRequest.Status.SENT)
    other = make_request(email="other@example.com", status=PrintableRequest.Status.SENT)
    call_command("forget_email", "Me@Example.com")
    mine.refresh_from_db()
    other.refresh_from_db()
    assert mine.child_name == "" and "me@example.com" not in mine.email
    assert other.child_name == "Maisie"
