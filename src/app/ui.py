"""HTML markup for the embedded web interface."""
from __future__ import annotations


WEB_INTERFACE_HTML = """<!DOCTYPE html>
<html lang=\"de\">
<head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>Stücklisten-Extractor</title>
    <style>
        :root {
            color-scheme: light dark;
            font-family: \"Inter\", \"Segoe UI\", system-ui, -apple-system, sans-serif;
            font-size: 16px;
            line-height: 1.6;
        }

        body {
            margin: 0;
            background: #f3f4f6;
            color: #1f2937;
        }

        body.dark {
            background: #111827;
            color: #f9fafb;
        }

        main {
            max-width: 960px;
            margin: 0 auto;
            padding: 2.5rem 1.5rem 3rem;
        }

        h1 {
            font-size: 2rem;
            margin-bottom: 0.75rem;
            letter-spacing: -0.03em;
        }

        p.lead {
            margin-top: 0;
            margin-bottom: 2rem;
            color: #4b5563;
            max-width: 640px;
        }

        .card {
            background: rgba(255, 255, 255, 0.92);
            border-radius: 16px;
            padding: 1.75rem;
            margin-top: 1.5rem;
            box-shadow: 0 18px 40px rgba(15, 23, 42, 0.12);
            backdrop-filter: blur(6px);
        }

        body.dark .card {
            background: rgba(17, 24, 39, 0.85);
            box-shadow: 0 18px 40px rgba(0, 0, 0, 0.4);
        }

        form {
            display: grid;
            gap: 1rem;
        }

        label {
            font-weight: 600;
        }

        input[type=\"file\"] {
            padding: 0.75rem;
            border: 2px dashed #cbd5f5;
            border-radius: 12px;
            cursor: pointer;
            background: rgba(99, 102, 241, 0.08);
            transition: border 0.2s ease, background 0.2s ease;
        }

        input[type=\"file\"]:hover {
            border-color: #6366f1;
            background: rgba(99, 102, 241, 0.14);
        }

        button {
            justify-self: start;
            padding: 0.75rem 1.75rem;
            border-radius: 999px;
            border: none;
            font-weight: 600;
            letter-spacing: 0.02em;
            background: linear-gradient(135deg, #6366f1, #2563eb);
            color: #ffffff;
            cursor: pointer;
            box-shadow: 0 12px 25px rgba(37, 99, 235, 0.35);
            transition: transform 0.15s ease, box-shadow 0.15s ease;
        }

        button:hover {
            transform: translateY(-1px);
            box-shadow: 0 16px 30px rgba(37, 99, 235, 0.35);
        }

        button:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
            box-shadow: none;
        }

        .notice {
            min-height: 2.5rem;
            border-radius: 12px;
            padding: 0.85rem 1.1rem;
            margin-top: 0.5rem;
            background: rgba(99, 102, 241, 0.08);
            color: #3730a3;
            display: flex;
            align-items: center;
        }

        .notice.info {
            background: rgba(59, 130, 246, 0.12);
            color: #1d4ed8;
        }

        .notice.success {
            background: rgba(34, 197, 94, 0.12);
            color: #15803d;
        }

        .notice.error {
            background: rgba(248, 113, 113, 0.12);
            color: #b91c1c;
        }

        .hidden {
            display: none !important;
        }

        .result-grid {
            display: grid;
            gap: 1.5rem;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        }

        dl.meta {
            display: grid;
            grid-template-columns: minmax(120px, 1fr) minmax(160px, 2fr);
            gap: 0.4rem 1rem;
            margin: 0;
        }

        dl.meta dt {
            font-weight: 600;
            color: #4338ca;
        }

        dl.meta dd {
            margin: 0;
        }

        ul.tag-list {
            display: flex;
            flex-wrap: wrap;
            gap: 0.4rem;
            padding: 0;
            margin: 0;
            list-style: none;
        }

        ul.tag-list li {
            background: rgba(37, 99, 235, 0.08);
            color: #1d4ed8;
            padding: 0.35rem 0.75rem;
            border-radius: 999px;
            font-size: 0.85rem;
        }

        .table-wrapper {
            margin-top: 1.75rem;
            overflow-x: auto;
            border-radius: 12px;
            border: 1px solid rgba(148, 163, 184, 0.35);
        }

        table {
            width: 100%;
            border-collapse: collapse;
            min-width: 480px;
        }

        thead {
            background: linear-gradient(135deg, rgba(99, 102, 241, 0.9), rgba(59, 130, 246, 0.9));
            color: #fff;
        }

        th, td {
            padding: 0.75rem 0.9rem;
            text-align: left;
            border-bottom: 1px solid rgba(148, 163, 184, 0.25);
            vertical-align: top;
            font-size: 0.95rem;
        }

        tbody tr:nth-child(even) {
            background: rgba(99, 102, 241, 0.04);
        }

        .muted {
            color: #6b7280;
        }

        footer {
            margin-top: 2.5rem;
            text-align: center;
            color: #9ca3af;
            font-size: 0.85rem;
        }

        @media (prefers-color-scheme: dark) {
            body {
                background: #0f172a;
                color: #e2e8f0;
            }

            p.lead {
                color: #cbd5f5;
            }

            input[type=\"file\"] {
                border-color: rgba(99, 102, 241, 0.35);
                background: rgba(99, 102, 241, 0.12);
            }

            .card {
                background: rgba(15, 23, 42, 0.85);
                box-shadow: 0 18px 40px rgba(2, 6, 23, 0.75);
            }

            dl.meta dt {
                color: #a5b4fc;
            }

            ul.tag-list li {
                background: rgba(59, 130, 246, 0.12);
                color: #bfdbfe;
            }

            tbody tr:nth-child(even) {
                background: rgba(59, 130, 246, 0.08);
            }

            th, td {
                border-bottom-color: rgba(71, 85, 105, 0.35);
            }

            .muted {
                color: #94a3b8;
            }

            footer {
                color: #64748b;
            }
        }
    </style>
</head>
<body>
    <main>
        <header>
            <h1>Stücklisten-Extractor</h1>
            <p class=\"lead\">Analysieren Sie technische Zeichnungen im PDF-Format und erhalten Sie eine strukturierte Stückliste direkt im Browser.</p>
        </header>

        <section class=\"card\">
            <form id=\"upload-form\">
                <div>
                    <label for=\"file\">PDF-Datei hochladen</label>
                    <input id=\"file\" type=\"file\" accept=\"application/pdf\" required />
                    <p class=\"muted\">Die Datei wird ausschließlich lokal verarbeitet und nicht gespeichert.</p>
                </div>
                <button id=\"submit-button\" type=\"submit\">Stückliste extrahieren</button>
            </form>
            <div id=\"status\" class=\"notice\" role=\"status\" aria-live=\"polite\"></div>
        </section>

        <section id=\"result\" class=\"card hidden\" aria-live=\"polite\">
            <h2>Ergebnis</h2>
            <div class=\"result-grid\">
                <div>
                    <h3>Metadaten</h3>
                    <div id=\"metadata-container\">
                        <dl id=\"metadata-list\" class=\"meta\"></dl>
                        <p id=\"metadata-empty\" class=\"muted\">Keine Metadaten vorhanden.</p>
                    </div>
                </div>
                <div>
                    <h3>Erkannte Spalten</h3>
                    <ul id=\"column-list\" class=\"tag-list\"></ul>
                </div>
            </div>
            <div class=\"table-wrapper\">
                <table id=\"items-table\" aria-live=\"polite\">
                    <thead></thead>
                    <tbody></tbody>
                </table>
            </div>
        </section>

        <footer>
            Bereitgestellt vom integrierten FastAPI-Dienst &mdash; Endpunkt: <code>POST /extract</code>
        </footer>
    </main>

    <script>
        (function () {
            const form = document.getElementById('upload-form');
            const fileInput = document.getElementById('file');
            const submitButton = document.getElementById('submit-button');
            const statusBox = document.getElementById('status');
            const resultSection = document.getElementById('result');
            const metadataList = document.getElementById('metadata-list');
            const metadataEmpty = document.getElementById('metadata-empty');
            const columnList = document.getElementById('column-list');
            const tableHead = document.querySelector('#items-table thead');
            const tableBody = document.querySelector('#items-table tbody');

            const defaultColumns = [
                { key: 'position', label: 'Position' },
                { key: 'part_number', label: 'Artikelnummer' },
                { key: 'description', label: 'Beschreibung' },
                { key: 'quantity', label: 'Menge' },
                { key: 'unit', label: 'Einheit' },
                { key: 'material', label: 'Material' },
                { key: 'comment', label: 'Kommentar' }
            ];

            form.addEventListener('submit', async (event) => {
                event.preventDefault();
                clearNotice();
                resultSection.classList.add('hidden');

                const file = fileInput.files[0];
                if (!file) {
                    showNotice('Bitte wählen Sie eine PDF-Datei aus.', 'error');
                    return;
                }
                if (!file.name.toLowerCase().endsWith('.pdf')) {
                    showNotice('Die ausgewählte Datei ist keine PDF.', 'error');
                    return;
                }

                const data = new FormData();
                data.append('file', file);

                setLoading(true);
                showNotice('Die Datei wird analysiert …', 'info');

                try {
                    const response = await fetch('/extract', {
                        method: 'POST',
                        body: data
                    });

                    let payload = null;
                    try {
                        payload = await response.json();
                    } catch (parseError) {
                        payload = null;
                    }

                    if (!response.ok) {
                        const detail = payload && payload.detail ? payload.detail : `Die Analyse ist fehlgeschlagen (Status ${response.status}).`;
                        throw new Error(detail);
                    }

                    if (!payload || typeof payload !== 'object') {
                        throw new Error('Unerwartetes Antwortformat.');
                    }

                    renderResult(payload);
                    showNotice('Die Stückliste wurde erfolgreich extrahiert.', 'success');
                } catch (error) {
                    showNotice(error.message || 'Unbekannter Fehler bei der Analyse.', 'error');
                } finally {
                    setLoading(false);
                }
            });

            function setLoading(isLoading) {
                submitButton.disabled = isLoading;
                fileInput.disabled = isLoading;
            }

            function showNotice(message, kind) {
                statusBox.textContent = '';
                statusBox.className = 'notice ' + kind;
                statusBox.textContent = message;
            }

            function clearNotice() {
                statusBox.textContent = '';
                statusBox.className = 'notice';
            }

            function renderResult(data) {
                if (!data || !Array.isArray(data.items)) {
                    throw new Error('Unerwartetes Antwortformat.');
                }

                renderMetadata(data.metadata || {});
                renderDetectedColumns(data.detected_columns || []);
                renderTable(data.items || []);
                resultSection.classList.remove('hidden');
            }

            function renderMetadata(metadata) {
                metadataList.innerHTML = '';
                const entries = Object.entries(metadata || {});

                if (entries.length === 0) {
                    metadataEmpty.classList.remove('hidden');
                    return;
                }

                metadataEmpty.classList.add('hidden');

                entries.forEach(([key, value]) => {
                    const term = document.createElement('dt');
                    term.textContent = prettifyLabel(key);
                    metadataList.appendChild(term);

                    const detail = document.createElement('dd');
                    detail.textContent = formatValue(value);
                    metadataList.appendChild(detail);
                });
            }

            function renderDetectedColumns(columns) {
                columnList.innerHTML = '';

                if (!Array.isArray(columns) || columns.length === 0) {
                    const empty = document.createElement('li');
                    empty.className = 'muted';
                    empty.textContent = 'Keine Angabe';
                    columnList.appendChild(empty);
                    return;
                }

                columns.forEach((column) => {
                    const item = document.createElement('li');
                    item.textContent = prettifyLabel(column);
                    columnList.appendChild(item);
                });
            }

            function renderTable(items) {
                tableHead.innerHTML = '';
                tableBody.innerHTML = '';

                if (!Array.isArray(items) || items.length === 0) {
                    const row = document.createElement('tr');
                    const cell = document.createElement('td');
                    cell.colSpan = 1;
                    cell.textContent = 'Keine Einträge gefunden.';
                    row.appendChild(cell);
                    tableBody.appendChild(row);
                    return;
                }

                const availableColumns = [];

                defaultColumns.forEach((column) => {
                    const hasValues = items.some((item) => hasValue(item[column.key]));
                    if (hasValues) {
                        availableColumns.push({ ...column, fromExtras: false });
                    }
                });

                const extraKeys = new Set();

                items.forEach((item) => {
                    if (item.extras && typeof item.extras === 'object') {
                        Object.entries(item.extras).forEach(([key, value]) => {
                            if (hasValue(value)) {
                                extraKeys.add(key);
                            }
                        });
                    }

                    Object.keys(item).forEach((key) => {
                        if (key === 'extras') {
                            return;
                        }
                        if (defaultColumns.some((column) => column.key === key)) {
                            return;
                        }
                        if (hasValue(item[key])) {
                            extraKeys.add(key);
                        }
                    });
                });

                Array.from(extraKeys).sort((a, b) => a.localeCompare(b, 'de')).forEach((key) => {
                    availableColumns.push({
                        key: key,
                        label: prettifyLabel(key),
                        fromExtras: !defaultColumns.some((column) => column.key === key)
                    });
                });

                if (availableColumns.length === 0) {
                    availableColumns.push({ key: 'description', label: 'Beschreibung', fromExtras: false });
                }

                const headerRow = document.createElement('tr');
                availableColumns.forEach((column) => {
                    const th = document.createElement('th');
                    th.scope = 'col';
                    th.textContent = column.label;
                    headerRow.appendChild(th);
                });
                tableHead.appendChild(headerRow);

                items.forEach((item) => {
                    const row = document.createElement('tr');
                    availableColumns.forEach((column) => {
                        const td = document.createElement('td');
                        let value;
                        if (column.fromExtras && item.extras && Object.prototype.hasOwnProperty.call(item.extras, column.key)) {
                            value = item.extras[column.key];
                        } else {
                            value = item[column.key];
                        }
                        td.textContent = formatValue(value);
                        row.appendChild(td);
                    });
                    tableBody.appendChild(row);
                });
            }

            function prettifyLabel(label) {
                return String(label)
                    .replace(/_/g, ' ')
                    .replace(/\b\w/g, (char) => char.toUpperCase());
            }

            function hasValue(value) {
                if (value === null || value === undefined) {
                    return false;
                }
                if (typeof value === 'number') {
                    return true;
                }
                if (Array.isArray(value)) {
                    return value.length > 0;
                }
                if (typeof value === 'string') {
                    return value.trim() !== '';
                }
                return true;
            }

            function formatValue(value) {
                if (value === null || value === undefined) {
                    return '';
                }
                if (Array.isArray(value)) {
                    return value.map((entry) => formatValue(entry)).join(', ');
                }
                if (typeof value === 'number') {
                    return value.toLocaleString('de-DE');
                }
                return String(value);
            }
        })();
    </script>
</body>
</html>
"""


__all__ = ["WEB_INTERFACE_HTML"]
