from __future__ import annotations

from pathlib import Path

from bom_extractor import extract_bom_from_pdf
from .utils import build_pdf_drawing, build_pdf_table, build_pdf_text


def test_extract_basic_table(tmp_path: Path) -> None:
    pdf_path = tmp_path / "drawing.pdf"
    data = [
        ["Item", "Qty", "Description", "Material"],
        ["1", "4", "Bolt M8", "Steel"],
        ["2", "2", "Nut M8", "Steel"],
    ]
    build_pdf_table(pdf_path, data)

    result = extract_bom_from_pdf(str(pdf_path))

    assert result.detected_columns == ["description", "material", "position", "quantity"]
    assert len(result.items) == 2
    first = result.items[0]
    assert first.position == "1"
    assert first.description == "Bolt M8"
    assert first.material == "Steel"
    assert first.quantity == 4


def test_extract_german_headers(tmp_path: Path) -> None:
    pdf_path = tmp_path / "zeichnung.pdf"
    data = [
        ["Pos.", "Benennung", "Menge", "Einheit"],
        ["10", "Schraube M10", "12 Stk", "Stk"],
        ["20", "Mutter M10", "8", "Stk"],
    ]
    build_pdf_table(pdf_path, data)

    result = extract_bom_from_pdf(str(pdf_path))

    assert len(result.items) == 2
    first = result.items[0]
    assert first.position == "10"
    assert first.quantity == 12
    assert first.unit == "Stk"


def test_extract_interprets_text_annotations(tmp_path: Path) -> None:
    pdf_path = tmp_path / "text.pdf"
    build_pdf_text(
        pdf_path,
        [
            "Pos 1 Schraube M8 Qty 4",
            "Pos 2 Mutter M8 (2x)",
            "3 Lager 6205 qty 2",
        ],
    )

    result = extract_bom_from_pdf(str(pdf_path))

    assert result.metadata["mode"] == "interpreted"
    assert result.metadata["annotation_items"] == 3
    assert len(result.items) >= 3
    first = result.items[0]
    assert first.position == "1"
    assert first.quantity == 4
    assert first.description and "Schraube" in first.description
    assert "quantity" in result.detected_columns


def test_extract_interprets_geometry(tmp_path: Path) -> None:
    pdf_path = tmp_path / "shapes.pdf"
    build_pdf_drawing(pdf_path)

    result = extract_bom_from_pdf(str(pdf_path))

    assert result.metadata["mode"] == "interpreted"
    assert result.metadata["geometry_items"] >= 1
    assert result.metadata["annotation_items"] == 0
    assert any("Rechteck" in (item.description or "") for item in result.items)
    assert all(item.quantity and item.quantity >= 1 for item in result.items)
