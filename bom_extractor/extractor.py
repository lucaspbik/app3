"""Core logic for extracting bills of materials from PDF engineering drawings."""
from __future__ import annotations

from dataclasses import dataclass, field
import io
import re
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple, Union

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

POINT_TO_MM = 25.4 / 72.0

CALLOUT_PATTERN = re.compile(
    r"""
    ^\s*
    (?:[-•\u2022]\s*)?
    (?:(?P<label>(?:pos(?:ition)?|item|nr|no\.?|#)\s*)?(?P<position>\d{1,3}[A-Za-z]?))
    (?:\s*[\.:)\-])?
    \s+
    (?P<rest>.+)
    $
    """,
    re.IGNORECASE | re.VERBOSE,
)

ALT_CALLOUT_PATTERN = re.compile(
    r"^(?P<position>[A-Za-z]\d{1,3})\s*[:\-]\s*(?P<rest>.+)$"
)

SIMPLE_ENUM_PATTERN = re.compile(r"^(?P<position>\d{1,3})\s+(?P<rest>.+)$")

ITEM_KEYWORDS = (
    "qty",
    "quantity",
    "anzahl",
    "menge",
    "stk",
    "stück",
    "st",
    "pcs",
    "pieces",
    "x",
    "off",
    "ea",
)

SHAPE_LABELS = {
    "rectangle": "Rechteck",
    "curve": "Kontur",
    "circle": "Kreis",
}


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
        fallback_items, fallback_columns, fallback_metadata = _interpret_without_table(pdf)
        metadata: Dict[str, Union[str, List[int], int]] = {
            "source": source or "<unknown>",
            "tables_checked": tables_seen,
        }
        metadata.update(fallback_metadata)
        metadata.setdefault("pages", [])
        return BOMExtractionResult(
            items=fallback_items,
            detected_columns=fallback_columns,
            metadata=metadata,
        )

    metadata = {
        "source": source or "<unknown>",
        "pages": sorted(set(pages_used)),
        "tables_checked": tables_seen,
        "mode": "table",
    }

    return BOMExtractionResult(
        items=items,
        detected_columns=sorted(set(detected_columns)),
        metadata=metadata,
    )


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


def _interpret_without_table(
    pdf: pdfplumber.PDF,
) -> Tuple[List[BOMItem], List[str], Dict[str, Union[str, List[int], int]]]:
    """Create a synthetic BOM by interpreting annotations and geometry."""

    used_positions: Set[str] = set()
    text_items, used_positions, next_position, text_meta = _interpret_textual_annotations(
        pdf, used_positions=used_positions, start_position=1
    )
    geometry_items, used_positions, next_position, geometry_meta = _interpret_geometry_components(
        pdf, used_positions=used_positions, start_position=next_position
    )

    items = text_items + geometry_items
    metadata: Dict[str, Union[str, List[int], int]] = {
        "mode": "interpreted",
        "annotation_items": len(text_items),
        "geometry_items": len(geometry_items),
        "lines_checked": text_meta.get("lines_checked", 0),
        "shapes_considered": geometry_meta.get("shapes_considered", 0),
    }

    pages = sorted(set(text_meta.get("pages", [])) | set(geometry_meta.get("pages", [])))
    if pages:
        metadata["pages"] = pages

    if not items:
        placeholder_position = "1"
        if placeholder_position in used_positions:
            placeholder_position, _ = _allocate_position(used_positions, next_position)
        else:
            used_positions.add(placeholder_position)
        placeholder = BOMItem(
            position=placeholder_position,
            description="Automatisch generierte Sammelposition",
            quantity=1,
            unit="assembly",
            comment="Keine interpretierbaren Komponenten gefunden – bitte Zeichnung prüfen.",
            extras={"source": "fallback", "confidence": "sehr gering"},
        )
        items.append(placeholder)
        metadata["fallback_placeholder"] = 1

    detected_columns = _infer_detected_columns(items)
    return items, detected_columns, metadata


def _interpret_textual_annotations(
    pdf: pdfplumber.PDF,
    *,
    used_positions: Optional[Set[str]] = None,
    start_position: int = 1,
) -> Tuple[List[BOMItem], Set[str], int, Dict[str, Union[List[int], int]]]:
    """Derive BOM entries from free-text annotations and callouts."""

    if used_positions is None:
        used_positions = set()

    items: List[BOMItem] = []
    pages_with_items: Set[int] = set()
    lines_checked = 0
    next_position = max(start_position, 1)

    for page_index, page in enumerate(pdf.pages, start=1):
        try:
            raw_text = page.extract_text(x_tolerance=2, y_tolerance=2)
        except TypeError:
            raw_text = page.extract_text()
        if not raw_text:
            continue

        for raw_line in raw_text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            lines_checked += 1
            parsed = _interpret_annotation_line(line)
            if not parsed:
                continue

            extras = parsed.get("extras") or {}
            position = parsed.get("position")
            if position:
                position = str(position)
                if position in used_positions:
                    extras.setdefault(
                        "note", "Position mehrfach erkannt, automatisch neu nummeriert"
                    )
                    position, next_position = _allocate_position(used_positions, next_position)
                else:
                    used_positions.add(position)
                    if position.isdigit():
                        next_position = max(next_position, int(position) + 1)
            else:
                position, next_position = _allocate_position(used_positions, next_position)

            extras.setdefault("source", "text")

            item = BOMItem(
                position=position,
                part_number=parsed.get("part_number"),
                description=parsed.get("description"),
                quantity=parsed.get("quantity"),
                unit=parsed.get("unit"),
                comment=parsed.get("comment"),
                extras={key: str(value) for key, value in extras.items() if value},
            )
            items.append(item)
            pages_with_items.add(page_index)

    metadata: Dict[str, Union[List[int], int]] = {
        "pages": sorted(pages_with_items),
        "lines_checked": lines_checked,
    }
    return items, used_positions, next_position, metadata


def _interpret_annotation_line(line: str) -> Optional[Dict[str, object]]:
    """Parse a single textual annotation into structured BOM attributes."""

    text = line.strip()
    if not text:
        return None

    text = text.strip("-•\u2022 ")
    if not text:
        return None

    position, rest = _extract_position_and_rest(text)
    if rest is None:
        return None
    if position is None and not _line_looks_like_item(rest):
        return None

    quantity, unit, remainder = _extract_quantity_from_text(rest)
    remainder, comment = _extract_comment(remainder)
    part_number, description = _extract_part_number_and_description(remainder)

    if not description and not part_number:
        return None

    extras: Dict[str, str] = {"source": "text", "raw": line.strip()}
    score = 0
    if position:
        score += 1
    if part_number:
        score += 1
    if quantity is not None:
        score += 1
    if description:
        score += 1
    if score >= 3:
        extras["confidence"] = "hoch"
    elif score >= 2:
        extras["confidence"] = "mittel"
    else:
        extras["confidence"] = "niedrig"

    return {
        "position": position,
        "part_number": part_number,
        "description": description or part_number,
        "quantity": quantity,
        "unit": unit,
        "comment": comment,
        "extras": extras,
    }


def _extract_position_and_rest(text: str) -> Tuple[Optional[str], Optional[str]]:
    for pattern in (CALLOUT_PATTERN, ALT_CALLOUT_PATTERN, SIMPLE_ENUM_PATTERN):
        match = pattern.match(text)
        if not match:
            continue
        rest = match.group("rest") if "rest" in match.groupdict() else None
        if rest:
            rest = rest.strip()
        if not rest or not re.search(r"[A-Za-z]", rest):
            continue
        return match.group("position"), rest

    if re.search(r"[A-Za-z]", text):
        return None, text.strip()
    return None, None


def _extract_quantity_from_text(text: str) -> Tuple[Optional[Union[int, float]], Optional[str], str]:
    if not text:
        return None, None, ""

    matches = list(QUANTITY_RE.finditer(text))
    chosen_match = None
    for match in reversed(matches):
        start, end = match.span()
        prefix = text[max(0, start - 6) : start].lower()
        suffix = text[end : min(len(text), end + 6)].lower()
        if any(keyword in prefix for keyword in ITEM_KEYWORDS) or any(
            keyword in suffix for keyword in ITEM_KEYWORDS
        ):
            chosen_match = match
            break
        if (start > 0 and text[start - 1] == "(") or (end < len(text) and text[end : end + 1] == ")"):
            chosen_match = match
            break

    if not chosen_match and len(matches) == 1:
        match = matches[0]
        if re.search(r"[A-Za-z]", text[: match.start()]) or re.search(
            r"(qty|pcs|stk|x)", text[match.end() :].lower()
        ):
            chosen_match = match

    if not chosen_match:
        return None, None, text

    quantity_value, unit_value = _parse_quantity(chosen_match.group(0))
    if unit_value and unit_value.lower() == "x":
        unit_value = "pcs"

    start, end = chosen_match.span()
    before = text[:start]
    after = text[end:]
    if before.endswith("(") and after.startswith(")"):
        before = before[:-1]
        after = after[1:]
    cleaned = f"{before} {after}".strip()
    cleaned = re.sub(
        r"\b(?:qty|quantity|menge|anzahl|stk|stück|st|pcs|pieces|ea|off)\b",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip(" -:;,")

    return quantity_value, unit_value, cleaned


def _extract_comment(text: str) -> Tuple[str, Optional[str]]:
    if not text:
        return "", None

    comment_match = re.search(r"\(([^)]+)\)\s*$", text)
    if not comment_match:
        return text.strip(), None

    comment = comment_match.group(1).strip()
    cleaned = text[: comment_match.start()].strip()
    return cleaned, comment or None


def _extract_part_number_and_description(text: str) -> Tuple[Optional[str], str]:
    working = text.strip(" -:;,")
    if not working:
        return None, ""

    for separator in (" - ", " – ", " — ", ":"):
        if separator in working:
            left, right = working.split(separator, 1)
            left = left.strip(" -:;,")
            right = right.strip(" -:;,")
            if _looks_like_part_number(left) and right:
                return left, right
            if _looks_like_part_number(right) and left:
                return right, left

    tokens = working.split()
    part_index: Optional[int] = None
    part_number: Optional[str] = None
    for idx, token in enumerate(tokens):
        cleaned = token.strip(",;:/()[]")
        if _looks_like_part_number(cleaned):
            part_index = idx
            part_number = cleaned
            break

    description_tokens = [token for i, token in enumerate(tokens) if i != part_index]
    description = " ".join(description_tokens).strip(" -:;,")
    description = re.sub(r"\s{2,}", " ", description)

    return part_number, description


def _looks_like_part_number(token: str) -> bool:
    candidate = token.strip()
    if not candidate or len(candidate) < 2:
        return False

    lowered = candidate.lower()
    for unit_suffix in ("mm", "cm", "m", "kg", "g", "nm"):
        if lowered.endswith(unit_suffix) and candidate[:- len(unit_suffix)].isdigit():
            return False

    has_digit = any(ch.isdigit() for ch in candidate)
    has_alpha = any(ch.isalpha() for ch in candidate)
    if has_digit and has_alpha:
        return True
    if has_digit and any(sep in candidate for sep in "-_/."):
        return True
    if candidate.replace("-", "").isdigit() and "-" in candidate and len(candidate) >= 4:
        return True
    if candidate.isdigit() and len(candidate) >= 4:
        return True
    return False


def _line_looks_like_item(text: str) -> bool:
    lowered = text.lower()
    if any(keyword in lowered for keyword in ITEM_KEYWORDS):
        return True
    if re.search(r"\b\d+\s*(?:x|pcs|stk|st|off|ea)\b", lowered):
        return True
    if re.search(r"\b[a-z]+\b", lowered) and re.search(r"\d", text):
        return True
    if re.search(r"[A-Za-z]+-[A-Za-z0-9]+", text):
        return True
    return False


def _interpret_geometry_components(
    pdf: pdfplumber.PDF,
    *,
    used_positions: Set[str],
    start_position: int,
) -> Tuple[List[BOMItem], Set[str], int, Dict[str, Union[List[int], int]]]:
    """Cluster geometric primitives into pseudo BOM entries."""

    shapes: Dict[Tuple[str, float, float], Dict[str, object]] = {}
    pages_with_shapes: Set[int] = set()
    shapes_considered = 0
    next_position = max(start_position, 1)

    for page_index, page in enumerate(pdf.pages, start=1):
        page_width = getattr(page, "width", None)
        page_height = getattr(page, "height", None)

        for rect in getattr(page, "rects", []):
            width = float(rect.get("width", 0))
            height = float(rect.get("height", 0))
            if min(width, height) < 10:
                continue
            if page_width and page_height:
                if (
                    width >= page_width * 0.9
                    or height >= page_height * 0.9
                    or rect.get("x0", 0) <= 2
                    or rect.get("y0", 0) <= 2
                    or rect.get("x1", 0) >= page_width - 2
                    or rect.get("y1", 0) >= page_height - 2
                ):
                    continue

            major, minor = _shape_dimension_key(width, height)
            key = ("rectangle", major, minor)
            bucket = shapes.setdefault(key, {"count": 0, "pages": set()})
            bucket["count"] += 1
            bucket["pages"].add(page_index)
            pages_with_shapes.add(page_index)
            shapes_considered += 1

        for curve in getattr(page, "curves", []):
            points = curve.get("points") or []
            coords: List[Tuple[float, float]] = []
            for point in points:
                if isinstance(point, (tuple, list)) and len(point) >= 2:
                    coords.append((float(point[0]), float(point[1])))
                elif isinstance(point, dict) and {"x", "y"} <= set(point.keys()):
                    coords.append((float(point["x"]), float(point["y"])))
            if len(coords) < 2:
                continue

            xs = [pt[0] for pt in coords]
            ys = [pt[1] for pt in coords]
            width = max(xs) - min(xs)
            height = max(ys) - min(ys)
            if max(width, height) < 10:
                continue
            if page_width and page_height:
                if width >= page_width * 0.9 or height >= page_height * 0.9:
                    continue

            shape_type = "circle" if abs(width - height) <= 5 else "curve"
            major, minor = _shape_dimension_key(width, height)
            key = (shape_type, major, minor)
            bucket = shapes.setdefault(key, {"count": 0, "pages": set()})
            bucket["count"] += 1
            bucket["pages"].add(page_index)
            pages_with_shapes.add(page_index)
            shapes_considered += 1

    items: List[BOMItem] = []
    for shape_key in sorted(shapes.keys()):
        shape_type, major, minor = shape_key
        data = shapes[shape_key]
        position, next_position = _allocate_position(used_positions, next_position)
        description = _format_shape_description(shape_type, major, minor)
        extras = {
            "source": "geometry",
            "shape": SHAPE_LABELS.get(shape_type, shape_type),
            "pages": ",".join(str(page) for page in sorted(data["pages"])),
        }
        item = BOMItem(
            position=position,
            description=description,
            quantity=int(data["count"]),
            unit="pcs",
            extras=extras,
        )
        items.append(item)

    metadata: Dict[str, Union[List[int], int]] = {
        "pages": sorted(pages_with_shapes),
        "shapes_considered": shapes_considered,
    }
    return items, used_positions, next_position, metadata


def _shape_dimension_key(width: float, height: float) -> Tuple[float, float]:
    major = _round_mm(max(width, height))
    minor = _round_mm(min(width, height))
    return major, minor


def _round_mm(value: float) -> float:
    return round(value * POINT_TO_MM, 1)


def _format_shape_description(shape_type: str, major: float, minor: float) -> str:
    label = SHAPE_LABELS.get(shape_type, shape_type.capitalize())
    if shape_type == "circle" or abs(major - minor) <= 0.2:
        return f"{label} Ø {major:.1f} mm"
    return f"{label} {major:.1f} × {minor:.1f} mm"


def _allocate_position(used_positions: Set[str], start_index: int) -> Tuple[str, int]:
    index = max(start_index, 1)
    while str(index) in used_positions:
        index += 1
    position = str(index)
    used_positions.add(position)
    return position, index + 1


def _infer_detected_columns(items: Iterable[BOMItem]) -> List[str]:
    columns: List[str] = []
    for item in items:
        for field_name in ("position", "part_number", "description", "quantity", "unit", "material", "comment"):
            value = getattr(item, field_name)
            if value is not None and value != "":
                columns.append(field_name)
    return sorted(dict.fromkeys(columns))
