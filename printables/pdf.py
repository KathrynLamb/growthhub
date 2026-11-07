# printables/pdf.py
"""Builds the draw-your-own storybook PDF with ReportLab.

One cover, one page per story page (text at the top, a big frame to draw in),
and a final page linking back to FlipWhizz.
"""
from io import BytesIO
from textwrap import wrap

from django.conf import settings
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

RAINBOW = ["#F2546A", "#F7A93E", "#8AC7E0", "#A270C9"]
INK = HexColor("#2B2440")
SOFT = HexColor("#9B88CF")
ROSE = HexColor("#DB79AC")

WIDTH, HEIGHT = A4
MARGIN = 18 * mm


def _rainbow_band(c, y, height=3 * mm):
    segment = (WIDTH - 2 * MARGIN) / len(RAINBOW)
    for i, colour in enumerate(RAINBOW):
        c.setFillColor(HexColor(colour))
        c.rect(MARGIN + i * segment, y, segment, height, stroke=0, fill=1)


def _wrapped(c, text, x, y, font="Helvetica", size=18, leading=25, width_chars=44, centre=False):
    c.setFont(font, size)
    c.setFillColor(INK)
    for line in wrap(text, width_chars):
        if centre:
            c.drawCentredString(WIDTH / 2, y, line)
        else:
            c.drawString(x, y, line)
        y -= leading
    return y


def _draw_frame(c, top, bottom, label):
    c.setStrokeColor(SOFT)
    c.setLineWidth(1.5)
    c.setDash(6, 4)
    c.roundRect(MARGIN, bottom, WIDTH - 2 * MARGIN, top - bottom, 8 * mm, stroke=1, fill=0)
    c.setDash()
    c.setFont("Helvetica-Oblique", 10)
    c.setFillColor(SOFT)
    c.drawCentredString(WIDTH / 2, bottom + 5 * mm, label)


def _footer(c, page_no):
    c.setFont("Helvetica", 9)
    c.setFillColor(SOFT)
    c.drawCentredString(WIDTH / 2, 10 * mm, f"{page_no}")


def build_pdf(story, child_name, utm_campaign="free-printable"):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    c.setTitle(story["title"])
    c.setAuthor(f"{child_name} and FlipWhizz")

    # Cover
    _rainbow_band(c, HEIGHT - MARGIN)
    y = _wrapped(c, story["title"], 0, HEIGHT - 45 * mm, font="Helvetica-Bold", size=30, leading=36, width_chars=24, centre=True)
    c.setFont("Helvetica", 14)
    c.setFillColor(ROSE)
    c.drawCentredString(WIDTH / 2, y - 6 * mm, f"Written and illustrated by {child_name}")
    _draw_frame(c, y - 20 * mm, 40 * mm, "Draw the cover here")
    c.showPage()

    # Story pages
    for number, text in enumerate(story["pages"], start=1):
        _rainbow_band(c, HEIGHT - MARGIN)
        y = _wrapped(c, text, MARGIN, HEIGHT - 35 * mm)
        _draw_frame(c, y - 8 * mm, 22 * mm, "Draw this part of the story")
        _footer(c, number)
        c.showPage()

    # The end
    _rainbow_band(c, HEIGHT - MARGIN)
    c.setFont("Helvetica-Bold", 34)
    c.setFillColor(INK)
    c.drawCentredString(WIDTH / 2, HEIGHT - 70 * mm, "The End")
    link = f"{settings.FLIPWHIZZ_URL}/?utm_source=growthhub&utm_medium=pdf&utm_campaign={utm_campaign}"
    y = _wrapped(
        c,
        f"Want {child_name}'s story as a real illustrated book? "
        "Make one together at flipwhizz.com",
        0,
        HEIGHT - 100 * mm,
        size=14,
        leading=20,
        width_chars=46,
        centre=True,
    )
    c.linkURL(link, (MARGIN, y - 4 * mm, WIDTH - MARGIN, HEIGHT - 95 * mm), relative=0)
    _draw_frame(c, y - 12 * mm, 30 * mm, "Draw your favourite part of the story")
    c.showPage()

    c.save()
    return buffer.getvalue()
