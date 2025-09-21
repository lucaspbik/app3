# Stücklisten-Extractor

Diese Anwendung extrahiert aus technischen Zeichnungen im PDF-Format automatisch Stücklisten (Bill of Materials).
Sie besteht aus einer wiederverwendbaren Python-Bibliothek und einem kleinen FastAPI-Dienst, über den sich die
Extraktion als Webservice aufrufen lässt.

## Funktionen

- Erkennung gängiger Stücklisten-Tabellen mit deutsch- und englischsprachigen Spaltenüberschriften.
- Automatische Interpretation wichtiger Spalten wie Position, Artikelnummer, Beschreibung, Menge, Einheit und Material.
- Robuste PDF-Auswertung auf Basis von [pdfplumber](https://github.com/jsvine/pdfplumber).
- REST-Schnittstelle (FastAPI) zur Integration in bestehende Systeme.
- Umfangreiche Tests inklusive Erzeugung von Beispiel-PDFs.

## Installation

1. Optional ein virtuelles Python-Umfeld anlegen:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

2. Abhängigkeiten installieren:

   ```bash
   pip install -r requirements.txt
   ```

## Verwendung der Bibliothek

```python
from bom_extractor import extract_bom_from_pdf

result = extract_bom_from_pdf("/pfad/zur/zeichnung.pdf")
for item in result.items:
    print(item.to_dict())
```

Die Funktion gibt ein `BOMExtractionResult`-Objekt zurück, welches die erkannten Einträge, die gefundenen Spalten sowie
Metadaten wie die ausgewerteten Seiten enthält.

## Start des Webservices

```bash
uvicorn app.main:app --reload
```

Anschließend steht unter `http://127.0.0.1:8000/docs` eine interaktive Dokumentation zur Verfügung. Über den Endpunkt
`POST /extract` kann eine PDF-Datei hochgeladen werden. Die Antwort enthält die extrahierte Stückliste sowie Metadaten
zur Verarbeitung.

## Tests

```bash
pytest
```

Die Tests erzeugen automatisch Beispiel-PDFs und verifizieren die Extraktionslogik sowie den API-Endpunkt.
