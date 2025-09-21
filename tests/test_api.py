from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from .utils import build_pdf_table, build_pdf_text


client = TestClient(app)


def test_extract_endpoint(tmp_path: Path) -> None:
    pdf_path = tmp_path / "bom.pdf"
    data = [
        ["Item", "Qty", "Description"],
        ["1", "5", "Washer"],
        ["2", "3", "Screw"],
    ]
    build_pdf_table(pdf_path, data)

    with pdf_path.open("rb") as pdf_file:
        response = client.post(
            "/extract", files={"file": (pdf_path.name, pdf_file, "application/pdf")}
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"][0]["description"] == "Washer"
    assert payload["items"][0]["quantity"] == 5
    assert "confidence" in payload["items"][0]
    assert payload["items"][0]["confidence"] is not None
    assert payload["metadata"]["source"] == "bom.pdf"


def test_extract_endpoint_interprets_annotations(tmp_path: Path) -> None:
    pdf_path = tmp_path / "callouts.pdf"
    build_pdf_text(
        pdf_path,
        [
            "Pos 1 Schraube M8 Qty 4",
            "Pos 2 Mutter M8 (2x)",
        ],
    )

    with pdf_path.open("rb") as pdf_file:
        response = client.post(
            "/extract", files={"file": (pdf_path.name, pdf_file, "application/pdf")}
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["metadata"]["mode"] == "interpreted"
    assert payload["metadata"]["annotation_items"] == 2
    assert payload["items"][0]["quantity"] == 4
    assert payload["items"][0]["description"]


def test_web_interface_served() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "Stücklisten-Extractor" in response.text
    assert "upload-form" in response.text


def test_feedback_endpoint(tmp_path: Path) -> None:
    pdf_path = tmp_path / "feedback.pdf"
    data = [
        ["Item", "Qty", "Description"],
        ["1", "2", "Bracket"],
        ["2", "4", "Bolt"],
    ]
    build_pdf_table(pdf_path, data)

    with pdf_path.open("rb") as pdf_file:
        extract_response = client.post(
            "/extract", files={"file": (pdf_path.name, pdf_file, "application/pdf")}
        )

    assert extract_response.status_code == 200
    payload = extract_response.json()
    ratings = [{"item": item, "correct": True} for item in payload["items"]]

    feedback_response = client.post(
        "/feedback",
        json={
            "document": payload["metadata"].get("source"),
            "ratings": ratings,
            "metadata": payload["metadata"],
        },
    )

    assert feedback_response.status_code == 200
    summary = feedback_response.json()["summary"]
    assert summary["total_feedback"] >= len(ratings)

    summary_response = client.get("/feedback/summary")
    assert summary_response.status_code == 200
    summary_payload = summary_response.json()
    assert summary_payload["total_feedback"] >= len(ratings)
