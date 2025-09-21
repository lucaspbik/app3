from __future__ import annotations

from pathlib import Path

from bom_extractor import BOMExtractionResult, BOMItem, LearningEngine, extract_bom_from_pdf
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
    assert first.confidence is not None
    assert 0.0 <= first.confidence <= 1.0
    assert "learning_feedback" in result.metadata


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
    assert all(item.confidence is not None for item in result.items)


def test_extract_interprets_geometry(tmp_path: Path) -> None:
    pdf_path = tmp_path / "shapes.pdf"
    build_pdf_drawing(pdf_path)

    result = extract_bom_from_pdf(str(pdf_path))

    assert result.metadata["mode"] == "interpreted"
    assert result.metadata["geometry_items"] >= 1
    assert result.metadata["annotation_items"] == 0
    assert any(item.extras.get("component_type") == "Blech" for item in result.items)
    assert all(item.quantity and item.quantity >= 1 for item in result.items)
    component_types = {
        item.extras.get("component_type")
        for item in result.items
        if item.extras.get("source") == "geometry" and item.extras.get("component_type")
    }
    assert {"Blech", "Rohr", "Flansch"} <= component_types
    assert all(item.confidence is not None for item in result.items)


def test_component_keywords_in_table(tmp_path: Path) -> None:
    pdf_path = tmp_path / "components_table.pdf"
    data = [
        ["Pos", "Benennung", "Menge"],
        ["1", "Rohr DN50", "3"],
        ["2", "Rohrbogen 90°", "2"],
        ["3", "Blech 5 mm", "1"],
        ["4", "Flansch PN16", "6"],
        ["5", "Rohrende Kappe", "2"],
    ]
    build_pdf_table(pdf_path, data)

    result = extract_bom_from_pdf(str(pdf_path))

    components = {
        item.extras.get("component_type") for item in result.items if item.extras.get("component_type")
    }
    assert {"Rohr", "Rohrbogen", "Blech", "Flansch", "Rohrende"} <= components
    classified_items = [item for item in result.items if item.extras.get("component_type")]
    assert all(item.extras.get("component_source") == "text" for item in classified_items)


def test_component_keywords_in_text(tmp_path: Path) -> None:
    pdf_path = tmp_path / "components_text.pdf"
    build_pdf_text(
        pdf_path,
        [
            "1 Rohr DN80 qty 2",
            "2 Rohrbogen 90° qty 3",
            "3 Flansch PN16 qty 4",
            "4 Blech 8mm qty 1",
            "5 Rohrende Endkappe qty 2",
            "6 Stahlrohr DN50 qty 1",
        ],
    )

    result = extract_bom_from_pdf(str(pdf_path))

    components = {
        item.extras.get("component_type") for item in result.items if item.extras.get("component_type")
    }
    assert {"Rohr", "Rohrbogen", "Blech", "Flansch", "Rohrende"} <= components
    classified_items = [item for item in result.items if item.extras.get("component_type")]
    assert all(item.extras.get("component_source") == "text" for item in classified_items)

    dn_item = next(item for item in result.items if item.description and "DN80" in item.description)
    assert dn_item.extras.get("component_type") == "Rohr"
    assert dn_item.part_number is None

    stahl_item = next(
        item for item in result.items if item.description and "Stahlrohr" in item.description
    )
    assert stahl_item.extras.get("component_type") == "Rohr"
    assert stahl_item.part_number is None


def test_learning_feedback_updates_confidence(tmp_path: Path) -> None:
    engine = LearningEngine(storage_path=tmp_path / "state.json")
    base_item = BOMItem(description="Rohr DN50", quantity=2, extras={"source": "text", "component_code": "rohr"})
    before_result = BOMExtractionResult(
        items=[
            BOMItem(
                **{
                    **base_item.__dict__,
                    "extras": dict(base_item.extras),
                }
            )
        ],
        detected_columns=[],
        metadata={"mode": "interpreted"},
    )
    engine.annotate_result(before_result)
    before_confidence = before_result.items[0].confidence or 0.0

    engine.record_feedback([(base_item, True)], metadata={"mode": "interpreted"})

    after_item = BOMItem(description="Rohr DN50", quantity=2, extras={"source": "text", "component_code": "rohr"})
    after_result = BOMExtractionResult(
        items=[after_item],
        detected_columns=[],
        metadata={"mode": "interpreted"},
    )
    engine.annotate_result(after_result)
    after_confidence = after_result.items[0].confidence or 0.0

    assert after_confidence >= before_confidence
    summary = engine.summary()
    assert summary["total_feedback"] >= 1
