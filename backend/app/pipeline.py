from __future__ import annotations

from .classifier import classify
from .comparator import compare_fields, normalize_fields
from .document_parser import (
    detect_doc_type,
    extract_fields,
    is_missing_value,
    read_attachment,
    DocumentReadError,
)

REVIEW_WRONG_DOC = "wrong_doc_type"
REVIEW_MISSING_ATTACHMENT = "missing_attachment"
REVIEW_UNREADABLE = "unreadable"
REVIEW_MISSING_VALUE = "missing_value"

def _result(category, status="OK", review_reason=None,
            defect_fields=None, has_defect=False):
    return {
        "category": category,
        "status": status,
        "review_reason": review_reason,
        "defect_fields": defect_fields or [],
        "has_defect": has_defect,
    }

def _attachment_by_name(email, suffix):
    return [a for a in email.get("attachments", [])
            if a.lower().endswith(suffix.lower())]

def process_email(email, inbox):
    category = classify(email)

    if category != "BL_COMPARISON":
        return _result(category)

    si_paths = _attachment_by_name(email, "_SI.txt")
    si_paths += [a for a in email.get("attachments", [])
                 if "_SI." in a.upper() and a not in si_paths]

    bl_paths = [a for a in email.get("attachments", [])
                if "_BL." in a.upper()]

    # The dataset uses SI/BL filename conventions. Content validation below
    # prevents wrong documents from being accepted.
    if not si_paths or not bl_paths:
        return _result(
            category,
            status="NEEDS_REVIEW",
            review_reason=REVIEW_MISSING_ATTACHMENT,
        )

    si_path = si_paths[0]
    bl_path = bl_paths[0]

    try:
        si_text = read_attachment(inbox.read_bytes(si_path), si_path)
    except Exception:
        return _result(category, "NEEDS_REVIEW", REVIEW_UNREADABLE)

    try:
        bl_text = read_attachment(inbox.read_bytes(bl_path), bl_path)
    except Exception:
        return _result(category, "NEEDS_REVIEW", REVIEW_UNREADABLE)

    si_type = detect_doc_type(si_text)
    bl_type = detect_doc_type(bl_text)

    if si_type == "UNREADABLE" or bl_type == "UNREADABLE":
        return _result(category, "NEEDS_REVIEW", REVIEW_UNREADABLE)

    if si_type != "SI" or bl_type != "BL":
        return _result(category, "NEEDS_REVIEW", REVIEW_WRONG_DOC)

    raw_si = extract_fields(si_text)
    raw_bl = extract_fields(bl_text)

    missing = [
        field for field in raw_si
        if is_missing_value(raw_si.get(field))
        or is_missing_value(raw_bl.get(field))
    ]

    if missing:
        return _result(
            category,
            status="NEEDS_REVIEW",
            review_reason=REVIEW_MISSING_VALUE,
        )

    si = normalize_fields(raw_si)
    bl = normalize_fields(raw_bl)

    defects = compare_fields(si, bl)

    if defects:
        return _result(
            category,
            status="MISMATCH",
            defect_fields=defects,
            has_defect=True,
        )

    return _result(category)

def process_inbox(inbox):
    submission = {}
    for email in inbox:
        submission[email["email_id"]] = process_email(email, inbox)
    return submission
