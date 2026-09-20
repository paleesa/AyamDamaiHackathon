from __future__ import annotations

import io
import re
from typing import Dict, Optional

from pypdf import PdfReader
from docx import Document
from openpyxl import load_workbook

FIELDS = [
    "shipper",
    "consignee",
    "notify_party",
    "port_of_loading",
    "port_of_discharge",
    "container_count",
    "gross_weight_kg",
]

class DocumentReadError(Exception):
    pass

def read_attachment(data: bytes, filename: str) -> str:
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    try:
        if ext == "txt":
            return data.decode("utf-8", errors="replace")

        if ext == "pdf":
            reader = PdfReader(io.BytesIO(data))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
            if not text.strip():
                raise DocumentReadError("PDF contained no extractable text")
            return text

        if ext == "docx":
            doc = Document(io.BytesIO(data))
            parts = [p.text for p in doc.paragraphs if p.text.strip()]
            for table in doc.tables:
                for row in table.rows:
                    vals = [cell.text.strip() for cell in row.cells]
                    if any(vals):
                        parts.append(" | ".join(vals))
            text = "\n".join(parts)
            if not text.strip():
                raise DocumentReadError("DOCX contained no extractable text")
            return text

        if ext == "xlsx":
            wb = load_workbook(io.BytesIO(data), data_only=True, read_only=True)
            parts = []
            for ws in wb.worksheets:
                parts.append(f"[SHEET {ws.title}]")
                for row in ws.iter_rows(values_only=True):
                    vals = ["" if v is None else str(v) for v in row]
                    if any(vals):
                        parts.append(" | ".join(vals))
            text = "\n".join(parts)
            if not text.strip():
                raise DocumentReadError("XLSX contained no extractable text")
            return text

        raise DocumentReadError(f"Unsupported attachment type: .{ext}")
    except DocumentReadError:
        raise
    except Exception as exc:
        raise DocumentReadError(f"{type(exc).__name__}: {exc}") from exc

def detect_doc_type(text: str) -> str:
    if not text or not text.strip():
        return "UNREADABLE"
    if text.startswith("[ERROR"):
        return "UNREADABLE"

    low = text.lower()

    # Important ordering: "BILL OF LADING INSTRUCTION" is an SI document,
    # not a BL.
    if "commercial invoice" in low or "invoice no." in low:
        return "INVOICE"
    if "packing list" in low:
        return "PACKING_LIST"
    if "certificate of origin" in low:
        return "CERTIFICATE"
    if (
        "shipping instruction" in low
        or "bl instruction" in low
        or "[sheet s.i.]" in low
        or "bill of lading instruction" in low
    ):
        return "SI"
    if (
        "bill of lading" in low
        or re.search(r"\bb/l\s*(?:no|number)", low)
        or re.search(r"\bbl\s+no\.", low)
    ):
        return "BL"
    return "OTHER"

def _clean(v: str) -> str:
    v = v.strip()
    v = re.sub(r"^[\s|:=-]+", "", v)
    return v.strip()

def _extract_field(lines, field: str) -> Optional[str]:
    patterns = {
        "shipper": [r"^shipper(?:/exporter)?"],
        "consignee": [r"^consignee", r"^to the order of"],
        "notify_party": [r"^notify"],
        "port_of_loading": [
            r"^port\s+of\s+loading", r"^load\s+port", r"^pol"
        ],
        "port_of_discharge": [
            r"^port\s+of\s+discharge", r"^discharge\s+port", r"^pod"
        ],
        "container_count": [
            r"^container\s+count",
            r"^no\.?\s+of\s+containers",
            r"^total\s+containers",
        ],
        "gross_weight_kg": [
            r"^gross\s*(?:weight|wt)",
            r"^total\s+gross\s+(?:weight|wt)",
        ],
    }

    matches = []
    for i, line in enumerate(lines):
        s = line.strip()
        low = s.lower()
        if not any(re.search(p, low) for p in patterns[field]):
            continue

        positions = [x for x in (s.find(":"), s.find("|")) if x >= 0]
        if positions:
            pos = min(positions)
            value = s[pos + 1:].strip()
            if value:
                matches.append((i, _clean(value.split("|")[0])))
            else:
                # Explicit blank label = missing value.
                if field != "gross_weight_kg":
                    return None
                continue
        else:
            matches.append((i, None))

    # Gross-weight tables often contain a header followed by line items and a
    # TOTAL Gross Weight row. Prefer an actual value on the same line.
    if field == "gross_weight_kg":
        for _, value in reversed(matches):
            if value and re.search(r"\d", value):
                return value
        return None

    # For label-only layouts (common in PDFs/DOCX), value is on the next line.
    for i, value in matches:
        if value is not None:
            return value
        for j in range(i + 1, min(i + 6, len(lines))):
            nxt = lines[j].strip()
            if nxt:
                return _clean(nxt.split("|")[0])

    return None

def extract_fields(text: str) -> Dict[str, Optional[str]]:
    lines = text.splitlines()
    return {field: _extract_field(lines, field) for field in FIELDS}

def is_missing_value(value) -> bool:
    if value is None:
        return True
    s = str(value).strip().upper()
    if not s:
        return True
    if s in {
        "N/A", "NA", "TBA", "TBC", "TBD", "TO BE ADVISED",
        "TO FOLLOW", "PENDING", "UNKNOWN", "-", "—", "NIL", "NONE"
    }:
        return True
    return re.fullmatch(r"[_\-\s.]+(?:MT|KG|KGS)?", s) is not None
