"""FastAPI entry point for the Stücklisten-Extraktionsdienst."""
from __future__ import annotations

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from bom_extractor import BOMExtractionError, BOMItem, extract_bom_from_bytes
from bom_extractor.learning import get_learning_engine
from .schemas import (
    BOMResponseModel,
    FeedbackRequestModel,
    FeedbackResponseModel,
    FeedbackSummaryModel,
)
from .ui import WEB_INTERFACE_HTML

app = FastAPI(
    title="BOM Extractor",
    description=(
        "Extrahiert Stücklisten aus technischen Zeichnungen im PDF-Format. "
        "Die API akzeptiert PDF-Dateien als Multipart-Uploads und liefert eine strukturierte Stückliste zurück."
    ),
    version="1.0.0",
)

learning_engine = get_learning_engine()

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


@app.post("/feedback", response_model=FeedbackResponseModel)
def submit_feedback(payload: FeedbackRequestModel) -> FeedbackResponseModel:
    """Receive user feedback about extracted BOM entries and update the learner."""

    if not payload.ratings:
        raise HTTPException(status_code=400, detail="Keine Bewertungen übermittelt.")

    ratings = []
    for entry in payload.ratings:
        item = BOMItem(**entry.item.dict())
        ratings.append((item, entry.correct))

    metadata = dict(payload.metadata or {})
    if payload.document and "document" not in metadata:
        metadata["document"] = payload.document

    summary = learning_engine.record_feedback(ratings, metadata=metadata)
    return FeedbackResponseModel(status="ok", summary=summary)


@app.get("/feedback/summary", response_model=FeedbackSummaryModel)
def get_feedback_summary() -> FeedbackSummaryModel:
    """Return the aggregated learning summary."""

    summary = learning_engine.summary()
    return FeedbackSummaryModel(**summary)


__all__ = ["app"]
