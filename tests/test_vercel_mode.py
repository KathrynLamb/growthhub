# tests/test_vercel_mode.py
"""Vercel mode: printables made straight away, retries via the protected cron URL."""
from datetime import timedelta
from unittest import mock

import pytest
from django.urls import reverse
from django.utils import timezone

from printables import pipeline
from printables.models import PrintableRequest

pytestmark = pytest.mark.django_db

FORM = {
    "child_name": "Maisie",
    "child_age": "4",
    "email": "p@example.com",
    "confirmed_parent": "on",
}
AJAX = {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}
CRON = reverse("core:cron")


def ok_response():
    resp = mock.Mock(status_code=200)
    resp.json.return_value = {"id": "email_1"}
    return resp


def fail_response():
    resp = mock.Mock(status_code=500)
    resp.json.return_value = {"name": "internal_server_error"}
    return resp


def test_inline_mode_sends_straight_away(client, settings):
    settings.PRINTABLE_PROCESS_INLINE = True
    settings.RESEND_API_KEY = "k"
    with mock.patch("printables.email.requests.post", return_value=ok_response()) as post:
        response = client.post(reverse("printables:request"), FORM, **AJAX)
    assert response.status_code == 201
    assert post.call_count == 1
    assert PrintableRequest.objects.get().status == PrintableRequest.Status.SENT


def test_inline_failure_still_thanks_parent_and_queues_retry(client, settings):
    settings.PRINTABLE_PROCESS_INLINE = True
    settings.RESEND_API_KEY = "k"
    with mock.patch("printables.email.requests.post", return_value=fail_response()):
        response = client.post(reverse("printables:request"), FORM, **AJAX)
    assert response.status_code == 201  # parent isn't shown an error
    req = PrintableRequest.objects.get()
    assert req.status == PrintableRequest.Status.QUEUED
    assert req.next_attempt_at > timezone.now()


def test_queue_mode_does_not_send_inline(client, settings):
    settings.PRINTABLE_PROCESS_INLINE = False
    with mock.patch("printables.pipeline.process") as process:
        client.post(reverse("printables:request"), FORM)
    process.assert_not_called()
    assert PrintableRequest.objects.get().status == PrintableRequest.Status.QUEUED


def test_process_now_only_claims_queued_rows():
    req = PrintableRequest.objects.create(email="p@example.com", child_name="M", child_age=4,
                                          ip_hash="x", status=PrintableRequest.Status.SENT)
    assert pipeline.process_now(req.pk) is False


def test_cron_url_hidden_without_secret(client, settings):
    settings.CRON_SECRET = ""
    assert client.get(CRON).status_code == 404


def test_cron_url_rejects_wrong_secret(client, settings):
    settings.CRON_SECRET = "right"
    assert client.get(CRON).status_code == 401
    assert client.get(CRON, HTTP_AUTHORIZATION="Bearer wrong").status_code == 401


def test_cron_url_retries_and_purges(client, settings):
    settings.CRON_SECRET = "right"
    settings.RESEND_API_KEY = "k"
    due = PrintableRequest.objects.create(
        email="p@example.com", child_name="Maisie", child_age=4, ip_hash="x", attempts=1,
        next_attempt_at=timezone.now() - timedelta(minutes=1),
    )
    old = PrintableRequest.objects.create(
        email="old@example.com", child_name="Old", child_age=4, ip_hash="x",
        status=PrintableRequest.Status.SENT, created_at=timezone.now() - timedelta(days=40),
    )
    with mock.patch("printables.email.requests.post", return_value=ok_response()):
        response = client.post(CRON, HTTP_AUTHORIZATION="Bearer right")
    assert response.status_code == 200
    assert response.json() == {"ok": True, "released": 0, "sent": 1, "failed": 0, "purged": 1}
    due.refresh_from_db()
    old.refresh_from_db()
    assert due.status == PrintableRequest.Status.SENT
    assert old.child_name == ""


def test_ssl_ca_setting_writes_cert(monkeypatch, tmp_path):
    """DB_SSL_CA (PEM text) becomes a file path the MySQL driver can use."""
    import importlib

    import config.settings as s

    monkeypatch.setenv("DB_ENGINE", "mysql")
    monkeypatch.setenv("DB_SSL_CA", "-----BEGIN CERTIFICATE-----\nabc\n-----END CERTIFICATE-----")
    monkeypatch.setenv("DJANGO_SECRET_KEY", "test")
    monkeypatch.setattr("tempfile.gettempdir", lambda: str(tmp_path))
    try:
        reloaded = importlib.reload(s)
        ca = reloaded.DATABASES["default"]["OPTIONS"]["ssl"]["ca"]
        assert ca == str(tmp_path / "db-ca.pem")
        assert "BEGIN CERTIFICATE" in (tmp_path / "db-ca.pem").read_text()
    finally:
        monkeypatch.undo()
        importlib.reload(s)
