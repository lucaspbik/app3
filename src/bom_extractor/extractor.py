"""Core logic for extracting bills of materials from PDF engineering drawings."""
from __future__ import annotations

from dataclasses import dataclass, field
import io
import re
from typing import Dict, Iterable, List, Optional, Sequence, Tuple, Union

import pdfplumber

__all__ = [
    "BOMItem",
    "BOMExtractionResult",
    "BOMExtractionError",
    "extract_bom_from_pdf",
    "extract_bom_from_bytes",
]


TABLE_SETTINGS: Sequence[Dict[str, Union[str, float]]] = (
    {"vertical_strategy": "lines", "horizontal_strategy": "lines"},
    {"vertical_strategy": "text", "horizontal_strategy": "text"},
    {"vertical_strategy": "lines", "horizontal_strategy": "text"},
)


HEADER_ALIASES: Dict[str, Tuple[str, ...]] = {
    "position": (
        "position",
        "pos",
        "pos.",
        "item",
        "itemno",
        "item no",
        "item no.",
        "no",
        "nr",
        "index",
    ),
    "part_number": (
        "part",
        "partno",
        "part no",
        "part-number",
        "article",
        "artikel",
        "artnr",
        "art.nr",
        "drawing",
        "drawing no",
        "zeichnungs",
        "zeichnungsnr",
        "zeichnung",
        "bestell",
        "order",
        "item code",
        "teilenummer",
    ),
    "description": (
        "description",
        "descr",
        "desc",
        "bezeichnung",
        "benennung",
        "designation",
        "title",
        "titel",
        "beschreibung",
    ),
    "quantity": (
        "qty",
        "qty.",
        "quantity",
        "menge",
        "anzahl",
        "stück",
        "stückzahl",
        "stk",
        "st",
        "pcs",
        "qty/qty",
    ),
    "unit": (
        "unit",
        "einheit",
        "uom",
        "ein",
        "maßeinheit",
    ),
    "material": (
        "material",
        "werkstoff",
        "mat",
    ),
    "comment": (
        "comment",
        "comments",
        "bemerkung",
        "bemerkungen",
        "note",
        "notes",
        "remark",
        "remarks",
    ),
}

# Regular expression used to detect numbers (supporting comma as decimal separator)
QUANTITY_RE = re.compile(
    r"(?P<value>-?\d+(?:[\.,]\d+)?)\s*(?P<unit>[a-zA-Z%\u00b0\/]*)"
)


class BOMExtractionError(RuntimeError):
    """Raised when the extractor cannot locate a valid bill of materials table."""


@dataclass
class BOMItem:
    """Container for a single bill of materials entry."""

    position: Optional[str] = None
    part_number: Optional[str] = None
    description: Optional[str] = None
    quantity: Optional[Union[int, float]] = None
    unit: Optional[str] = None
    material: Optional[str] = None
    comment: Optional[str] = None
    extras: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Union[str, int, float, Dict[str, str], None]]:
        """Convert the item into a serialisable dictionary."""

        data = {
            "position": self.position,
            "part_number": self.part_number,
            "description": self.description,
            "quantity": self.quantity,
            "unit": self.unit,
            "material": self.material,
            "comment": self.comment,
            "extras": {k: v for k, v in self.extras.items() if v},
        }
        return {k: v for k, v in data.items() if v is not None and (v != {} or k == "extras")}


@dataclass
class BOMExtractionResult:
    """Represents a complete bill of materials extracted from a drawing."""

    items: List[BOMItem]
    detected_columns: List[str]
    metadata: Dict[str, Union[str, List[int], int]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, object]:
        return {
            "items": [item.to_dict() for item in self.items],
            "detected_columns": self.detected_columns,
            "metadata": self.metadata,
        }


def extract_bom_from_pdf(path: Union[str, io.BytesIO]) -> BOMExtractionResult:
    """Extract a bill of materials from a PDF file located at *path*."""

    with pdfplumber.open(path) as pdf:
        return _extract_from_pdf_document(pdf, source=getattr(path, "name", str(path)))


def extract_bom_from_bytes(content: bytes, source: Optional[str] = None) -> BOMExtractionResult:
    """Extract a bill of materials from in-memory PDF data."""

    buffer = io.BytesIO(content)
    buffer.name = source or "<memory>"
    with pdfplumber.open(buffer) as pdf:
        return _extract_from_pdf_document(pdf, source=buffer.name)


def _extract_from_pdf_document(pdf: pdfplumber.PDF, source: Optional[str]) -> BOMExtractionResult:
    items: List[BOMItem] = []
    detected_columns: List[str] = []
    pages_used: List[int] = []
    tables_seen = 0

    for page_index, page in enumerate(pdf.pages, start=1):
        for table in _iter_tables(page):
            tables_seen += 1
            table_items, columns = _process_table(table)
            if table_items:
                items.extend(table_items)
                detected_columns.extend(col for col in columns if col not in detected_columns)
                pages_used.append(page_index)

    if not items:
        raise BOMExtractionError(
            "Keine Stückliste in der PDF gefunden. Bitte stellen Sie sicher, dass die Zeichnung eine tabellarische "
            "Stückliste mit Spaltenüberschriften enthält."
        )

    metadata: Dict[str, Union[str, List[int], int]] = {
        "source": source or "<unknown>",
        "pages": sorted(set(pages_used)),
        "tables_checked": tables_seen,
    }

    return BOMExtractionResult(items=items, detected_columns=detected_columns, metadata=metadata)


def _iter_tables(page: pdfplumber.page.Page) -> Iterable[List[List[Optional[str]]]]:
    """Yield tables extracted from a PDF page using different detection strategies."""

    yielded: List[List[List[Optional[str]]]] = []
    for settings in TABLE_SETTINGS:
        try:
            tables = page.extract_tables(table_settings=settings)
        except NotImplementedError:
            continue
        if not tables:
            continue
        for table in tables:
            # Avoid returning duplicate tables produced by different strategies.
            if table not in yielded:
                yielded.append(table)
                yield table


def _process_table(raw_table: Sequence[Sequence[Optional[str]]]) -> Tuple[List[BOMItem], List[str]]:
    """Attempt to interpret a raw table as a bill of materials."""

    cleaned_table = [_clean_row(row) for row in raw_table if any(_cell_has_content(cell) for cell in row)]
    if not cleaned_table:
        return [], []

    header_index, header_map, header_names = _find_header_row(cleaned_table)
    if header_index is None:
        return [], []

    data_rows = cleaned_table[header_index + 1 :]
    if not data_rows:
        return [], []

    items: List[BOMItem] = []
    for row in data_rows:
        item = _row_to_item(row, header_map, header_names)
        if item:
            items.append(item)

    normalized_columns = sorted(set(header_map.values()))
    return items, normalized_columns


def _clean_row(row: Sequence[Optional[str]]) -> List[str]:
    return [_normalise_cell(cell) for cell in row]


def _normalise_cell(cell: Optional[str]) -> str:
    if cell is None:
        return ""
    text = str(cell)
    text = text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _cell_has_content(cell: Optional[str]) -> bool:
    return bool(_normalise_cell(cell))


def _find_header_row(table: Sequence[Sequence[str]]) -> Tuple[Optional[int], Dict[int, str], Dict[int, str]]:
    """Locate the header row within a table and return column mappings."""

    best_index: Optional[int] = None
    best_map: Dict[int, str] = {}
    best_header_names: Dict[int, str] = {}
    best_score = 0

    for idx, row in enumerate(table):
        mapping: Dict[int, str] = {}
        names: Dict[int, str] = {}
        score = 0

        for col_index, cell in enumerate(row):
            if not cell:
                continue
            normalised = _normalise_header(cell)
            if not normalised:
                continue
            match = _match_header(normalised)
            names[col_index] = normalised
            if match and match not in mapping.values():
                mapping[col_index] = match
                score += 1

        # Require at least two recognised columns for a confident BOM header.
        if score >= 2 and score > best_score:
            best_index = idx
            best_map = mapping
            best_header_names = names
            best_score = score

    return best_index, best_map, best_header_names


def _normalise_header(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _match_header(value: str) -> Optional[str]:
    for canonical, aliases in HEADER_ALIASES.items():
        if value in aliases:
            return canonical
    return None


def _row_to_item(row: Sequence[str], header_map: Dict[int, str], header_names: Dict[int, str]) -> Optional[BOMItem]:
    recognised: Dict[str, str] = {}
    extras: Dict[str, str] = {}

    for idx, cell in enumerate(row):
        if not cell:
            continue
        if idx in header_map:
            recognised[header_map[idx]] = cell
        else:
            header_name = header_names.get(idx, f"column_{idx}")
            extras[header_name] = cell

    if not recognised and not extras:
        return None

    quantity_value: Optional[Union[int, float]] = None
    unit_value: Optional[str] = None
    if "quantity" in recognised:
        quantity_value, unit_value = _parse_quantity(recognised.get("quantity"))

    # If the unit column exists separately, it has precedence
    if "unit" in recognised and recognised["unit"]:
        unit_value = recognised["unit"]

    item = BOMItem(
        position=recognised.get("position"),
        part_number=recognised.get("part_number"),
        description=recognised.get("description"),
        quantity=quantity_value,
        unit=unit_value,
        material=recognised.get("material"),
        comment=recognised.get("comment"),
        extras=extras,
    )

    # If a recognised field still contains data that should be treated as extra (e.g. quantity without value)
    # we keep the original text in extras for traceability.
    for key, value in recognised.items():
        if key not in {"position", "part_number", "description", "quantity", "unit", "material", "comment"}:
            item.extras[key] = value

    # If we failed to parse a numeric quantity keep the raw text inside extras.
    if "quantity" in recognised and quantity_value is None:
        item.extras.setdefault("quantity_raw", recognised["quantity"])

    return item


def _parse_quantity(value: Optional[str]) -> Tuple[Optional[Union[int, float]], Optional[str]]:
    if not value:
        return None, None

    match = QUANTITY_RE.search(value)
    if not match:
        return None, None

    raw_value = match.group("value").replace(",", ".")
    try:
        numeric = float(raw_value)
    except ValueError:
        return None, match.group("unit") or None

    if numeric.is_integer():
        numeric_value: Union[int, float] = int(numeric)
    else:
        numeric_value = numeric

    unit = match.group("unit") or None
    return numeric_value, unit
