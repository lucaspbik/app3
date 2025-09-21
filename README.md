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
   ```

   Aktivieren Sie die Umgebung anschließend passend zu Ihrem Betriebssystem:

   - **Linux/macOS (bash/zsh):**

     ```bash
     source .venv/bin/activate
     ```

   - **Windows PowerShell:**

     ```powershell
     .\.venv\Scripts\Activate.ps1
     ```

   - **Windows-Eingabeaufforderung (cmd):**

     ```bat
     .\.venv\Scripts\activate.bat
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

Nach dem Start öffnet `http://127.0.0.1:8000/` eine komfortable Weboberfläche. Dort lassen sich PDF-Zeichnungen bequem
auswählen und mit einem Klick analysieren. Die extrahierten Stücklisten werden tabellarisch dargestellt,
Metadaten und erkannte Spalten werden übersichtlich aufbereitet.

Die API kann weiterhin direkt genutzt werden: Unter `http://127.0.0.1:8000/docs` steht die automatische FastAPI-
Dokumentation zur Verfügung, der Endpunkt `POST /extract` akzeptiert PDF-Dateien als Multipart-Uploads und liefert eine
strukturierte Antwort.

## Tests

```bash
pytest
```

Die Tests erzeugen automatisch Beispiel-PDFs und verifizieren die Extraktionslogik sowie den API-Endpunkt.
