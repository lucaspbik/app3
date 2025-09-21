"""FastAPI entry point for the Stücklisten-Extraktionsdienst."""
from __future__ import annotations

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from bom_extractor import BOMExtractionError, extract_bom_from_bytes
from .schemas import BOMResponseModel
from .ui import WEB_INTERFACE_HTML

app = FastAPI(
    title="BOM Extractor",
    description=(
        "Extrahiert Stücklisten aus technischen Zeichnungen im PDF-Format. "
        "Die API akzeptiert PDF-Dateien als Multipart-Uploads und liefert eine strukturierte Stückliste zurück."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_class=HTMLResponse)
def render_interface() -> HTMLResponse:
    """Serve the embedded single-page web interface."""

    return HTMLResponse(content=WEB_INTERFACE_HTML)


@app.get("/health")
def healthcheck() -> dict:
    """Simple health endpoint that documents the service."""

    return {
        "status": "ok",
        "message": "Nutzen Sie POST /extract, um eine Stückliste aus einer PDF zu extrahieren.",
    }


@app.post("/extract", response_model=BOMResponseModel)
async def extract_bom(file: UploadFile = File(...)) -> BOMResponseModel:
    """Extract a bill of materials from an uploaded PDF drawing."""

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Bitte laden Sie eine PDF-Datei hoch.")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Die übermittelte Datei ist leer.")

    try:
        result = extract_bom_from_bytes(content, source=file.filename)
    except BOMExtractionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive programming
        raise HTTPException(status_code=500, detail="Fehler beim Lesen der PDF-Datei.") from exc

    return BOMResponseModel(**result.to_dict())


__all__ = ["app"]
