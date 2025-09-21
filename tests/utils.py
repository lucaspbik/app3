"""Utilities shared by the test-suite."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable, Sequence

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle


def build_pdf_table(path: Path, data: Sequence[Sequence[str]]) -> Path:
    """Create a simple PDF file containing a table."""

    doc = SimpleDocTemplate(str(path), pagesize=A4)
    table = Table(data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ]
        )
    )
    doc.build([table])
    return path


def build_pdf_text(path: Path, lines: Iterable[str]) -> Path:
    """Create a PDF that only contains free text (used for negative tests)."""

    from reportlab.pdfgen import canvas

    c = canvas.Canvas(str(path), pagesize=A4)
    text_object = c.beginText(40, A4[1] - 50)
    for line in lines:
        text_object.textLine(line)
    c.drawText(text_object)
    c.showPage()
    c.save()
    return path


def build_pdf_drawing(path: Path) -> Path:
    """Create a minimalist drawing with geometric primitives for interpretation tests."""

    from reportlab.pdfgen import canvas

    c = canvas.Canvas(str(path), pagesize=A4)
    rectangles = [
        (40, A4[1] - 120, 80, 40),
        (160, A4[1] - 120, 80, 40),
        (40, A4[1] - 200, 80, 40),
        (220, A4[1] - 220, 60, 60),
    ]
    for x, y, width, height in rectangles:
        c.rect(x, y, width, height, stroke=1, fill=0)

    circles = [
        (360, A4[1] - 260, 25),
        (420, A4[1] - 260, 25),
    ]
    for x, y, radius in circles:
        c.circle(x, y, radius, stroke=1, fill=0)

    c.showPage()
    c.save()
    return path