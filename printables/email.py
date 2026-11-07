# printables/email.py
"""Sends the printable through the Resend HTTP API.

Uses plain requests rather than an SDK so the integration is visible: auth
header, JSON body, base64 attachment, timeout, and explicit error handling.
"""
import base64
import logging
from html import escape

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

RESEND_URL = "https://api.resend.com/emails"


class EmailError(Exception):
    pass


def build_html(child_name, title):
    name = escape(child_name)
    return f"""
<div style="font-family:Helvetica,Arial,sans-serif;color:#2B2440;max-width:520px;margin:auto">
  <div style="height:4px;background:linear-gradient(90deg,#F2546A,#F7A93E,#8AC7E0,#A270C9)"></div>
  <h1 style="font-family:Georgia,serif">{escape(title)}</h1>
  <p>Here's {name}'s free draw-your-own story. Print it, read it together, and let {name} draw the pictures.</p>
  <p>Tip: ask {name} what happens next after each page before they draw it.</p>
  <p>If you'd like {name}'s story as a real illustrated book, you can make one together at
     <a href="{settings.FLIPWHIZZ_URL}/?utm_source=growthhub&utm_medium=email&utm_campaign=free-printable">flipwhizz.com</a>.</p>
  <p>Katy at FlipWhizz</p>
</div>
"""


def send_printable(to_email, child_name, title, pdf_bytes):
    if not settings.RESEND_API_KEY:
        logger.warning("RESEND_API_KEY not set: email not sent (development mode)")
        return {"id": "dev-not-sent"}

    payload = {
        "from": settings.RESEND_FROM,
        "to": [to_email],
        "subject": f"{child_name}'s story is ready to print",
        "html": build_html(child_name, title),
        "attachments": [
            {"filename": "my-story.pdf", "content": base64.b64encode(pdf_bytes).decode("ascii")}
        ],
    }
    try:
        response = requests.post(
            RESEND_URL,
            json=payload,
            headers={"Authorization": f"Bearer {settings.RESEND_API_KEY}"},
            timeout=20,
        )
    except requests.RequestException as exc:
        raise EmailError(f"Resend unreachable: {exc.__class__.__name__}") from exc

    if response.status_code >= 400:
        # Resend returns JSON like {"name": "...", "message": "..."}; keep it short and PII-free.
        try:
            detail = response.json().get("name", "")
        except ValueError:
            detail = ""
        raise EmailError(f"Resend error {response.status_code} {detail}".strip())
    return response.json()
