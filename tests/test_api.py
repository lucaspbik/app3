from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from .utils import build_pdf_table


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
    assert payload["metadata"]["source"] == "bom.pdf"
