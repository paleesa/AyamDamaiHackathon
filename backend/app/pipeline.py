from __future__ import annotations

import json
import re
from pathlib import Path

from app.comparator import normalize_fields, compare_documents


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CACHE_FILE = PROJECT_ROOT / "submission" / "document_extractions.json"
OUTPUT_FILE = PROJECT_ROOT / "submission" / "document_comparisons.json"


def get_email_id(filename: str) -> str | None:
    """
    Convert:
        email_004_BL.txt -> email_004
        email_004_SI.xlsx -> email_004
    """
    match = re.match(r"^(email_\d+)_(SI|BL)\.", filename, re.IGNORECASE)

    if not match:
        return None

    return match.group(1)


def load_extractions():
    with open(CACHE_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def group_documents(extractions):
    """
    Group extracted documents by email ID.

    Example:
    {
        "email_004": {
            "SI": {...},
            "BL": {...}
        }
    }
    """

    grouped = {}

    for filename, result in extractions.items():

        email_id = get_email_id(filename)

        if email_id is None:
            continue

        if not isinstance(result, dict):
            continue

        # Ignore skipped files and actual processing errors.
        if result.get("status") in {"ERROR", "SKIPPED"}:
            continue

        document_type = result.get("document_type")

        # Normal SI / BL
        if document_type in {"SI", "BL"}:

            if email_id not in grouped:
                grouped[email_id] = {}

            grouped[email_id][document_type] = {
                "filename": filename,
                "data": result,
                "readable": True,
            }

        # Preserve corrupted/unreadable PDFs.
        elif document_type == "UNREADABLE":

            filename_upper = filename.upper()

            if "_BL." in filename_upper:
                document_type = "BL"
            elif "_SI." in filename_upper:
                document_type = "SI"
            else:
                continue

            if email_id not in grouped:
                grouped[email_id] = {}

            grouped[email_id][document_type] = {
                "filename": filename,
                "data": result,
                "readable": False,
            }

    return grouped


def compare_email_documents(email_id, documents):
    """
    Compare SI and BL for one email.
    """

    si = documents.get("SI")
    bl = documents.get("BL")
    
        # Document exists but cannot be read.
    if si is not None and not si.get("readable", True):
        return {
            "status": "NEEDS_REVIEW",
            "defect_fields": [],
            "review_reason": "Shipping Instruction (SI) is unreadable.",
            "si_file": si["filename"],
        }

    if bl is not None and not bl.get("readable", True):
        return {
            "status": "NEEDS_REVIEW",
            "defect_fields": [],
            "review_reason": "Bill of Lading (BL) is unreadable.",
            "bl_file": bl["filename"],
        }

    # No SI and no BL
    if si is None and bl is None:
        return {
            "status": "NEEDS_REVIEW",
            "defect_fields": [],
            "review_reason": "No usable SI or BL document found.",
        }

    # SI missing
    if si is None:
        return {
            "status": "NEEDS_REVIEW",
            "defect_fields": [],
            "review_reason": "Shipping Instruction (SI) is missing.",
        }

    # BL missing
    # A document may exist but be unreadable/corrupted.
    # Treat this as NEEDS_REVIEW rather than inventing values.
    if bl is None:
        return {
            "status": "NEEDS_REVIEW",
            "defect_fields": [],
            "review_reason": "Bill of Lading (BL) is missing or unreadable.",
        }

    si_data = normalize_fields(si["data"])
    bl_data = normalize_fields(bl["data"])

    comparison = compare_documents(si_data, bl_data)

    result = {
        "status": comparison["status"],
        "defect_fields": comparison["defect_fields"],
        "review_fields": comparison["review_fields"],
        "review_reason": None,
        "si_file": si["filename"],
        "bl_file": bl["filename"],
        "si_fields": si_data,
        "bl_fields": bl_data,
    }

    if comparison["status"] == "NEEDS_REVIEW":
        result["review_reason"] = (
            "One or more comparison fields are missing."
        )

    return result


def run_pipeline():
    print("=" * 70)
    print("SDOC AI - DOCUMENT COMPARISON PIPELINE")
    print("=" * 70)

    extractions = load_extractions()

    print(f"\nLoaded {len(extractions)} cached documents.")

    grouped = group_documents(extractions)

    print(f"Found {len(grouped)} email groups.")

    comparisons = {}

    for email_id in sorted(grouped.keys()):

        result = compare_email_documents(
            email_id,
            grouped[email_id],
        )

        comparisons[email_id] = result

    # Save results
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
        json.dump(
            comparisons,
            file,
            indent=2,
            ensure_ascii=False,
        )

    # Statistics
    statuses = {}

    for result in comparisons.values():
        status = result["status"]
        statuses[status] = statuses.get(status, 0) + 1

    print("\n" + "=" * 70)
    print("COMPARISON COMPLETE")
    print("=" * 70)

    print(f"Email groups : {len(comparisons)}")

    print("\nStatuses:")

    for status, count in sorted(statuses.items()):
        print(f"  {status}: {count}")

    print(f"\nOutput:")
    print(OUTPUT_FILE)


if __name__ == "__main__":
    run_pipeline()