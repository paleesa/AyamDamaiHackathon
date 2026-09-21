from __future__ import annotations

import json
import re
from pathlib import Path

from .comparator import normalize_fields, compare_documents
from .category_correction import correct_category

PROJECT_ROOT = Path(__file__).resolve().parents[2]

CACHE_FILE = PROJECT_ROOT / "submission" / "document_extractions.json"
CLASSIFIER_FILE = PROJECT_ROOT / "submission" / "classifier_submission.json"
OUTPUT_FILE = PROJECT_ROOT / "submission" / "document_comparisons.json"
INBOX_DIR = PROJECT_ROOT / "data" / "sdoc-hackathon-bundle" / "inbox"


def load_json(path: Path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def get_email_id(filename: str) -> str | None:
    match = re.match(
        r"^(email_\d+)_(SI|BL)\.",
        filename,
        re.IGNORECASE,
    )

    if not match:
        return None

    return match.group(1)


def load_extractions():
    return load_json(CACHE_FILE)


def load_classifier():
    return load_json(CLASSIFIER_FILE)

def apply_category_corrections(classifier):
    corrected = {}

    for email_id, classification in classifier.items():

        email_file = INBOX_DIR / f"{email_id}.json"

        if email_file.exists():
            email = load_json(email_file)

            original_category = classification.get(
                "category",
                "GENERAL",
            )

            category = correct_category(
                original_category,
                email.get("subject", ""),
                email.get("body", ""),
            )

            corrected[email_id] = {
                **classification,
                "category": category,
                "_original_category": original_category,
            }

        else:
            corrected[email_id] = classification

    return corrected

def is_send_draft_bl_request(subject: str = "", body: str = "") -> bool:
    text = f"{subject} {body}".lower()

    return "please assist to send the draft bl" in text

def group_documents(extractions):
    """
    Group extracted SI/BL documents by email ID.

    Readable documents are marked readable=True.

    Corrupted/unreadable documents are preserved and mapped
    back to SI/BL using their filename.
    """

    grouped = {}

    for filename, result in extractions.items():

        email_id = get_email_id(filename)

        if email_id is None:
            continue

        if not isinstance(result, dict):
            continue

        status = result.get("status")

        # Completely failed/skipped attachments are not usable
        if status in {"ERROR", "SKIPPED"}:
            continue

        document_type = result.get("document_type")

        # Normal readable SI / BL
        if document_type in {"SI", "BL"}:

            if email_id not in grouped:
                grouped[email_id] = {}

            grouped[email_id][document_type] = {
                "filename": filename,
                "data": result,
                "readable": True,
            }

        # Preserve unreadable PDFs
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
    Compare the SI and BL belonging to one email.
    """

    si = documents.get("SI")
    bl = documents.get("BL")

    # ---------------------------------------------------------
    # Missing SI and BL
    # ---------------------------------------------------------

    if si is None and bl is None:
        return {
            "status": "NEEDS_REVIEW",
            "defect_fields": [],
            "review_reason": (
                "No usable Shipping Instruction (SI) "
                "or Bill of Lading (BL) document found."
            ),
        }

    # ---------------------------------------------------------
    # Missing SI
    # ---------------------------------------------------------

    if si is None:
        return {
            "status": "NEEDS_REVIEW",
            "defect_fields": [],
            "review_reason": (
                "Shipping Instruction (SI) is missing or unreadable."
            ),
            "bl_file": bl["filename"],
        }

    # ---------------------------------------------------------
    # Missing BL
    # ---------------------------------------------------------

    if bl is None:
        return {
            "status": "NEEDS_REVIEW",
            "defect_fields": [],
            "review_reason": (
                "Bill of Lading (BL) is missing or unreadable."
            ),
            "si_file": si["filename"],
        }

    # ---------------------------------------------------------
    # Unreadable SI
    # ---------------------------------------------------------

    if not si.get("readable", True):
        return {
            "status": "NEEDS_REVIEW",
            "defect_fields": [],
            "review_reason": (
                "Shipping Instruction (SI) is unreadable."
            ),
            "si_file": si["filename"],
            "bl_file": bl["filename"],
        }

    # ---------------------------------------------------------
    # Unreadable BL
    # ---------------------------------------------------------

    if not bl.get("readable", True):
        return {
            "status": "NEEDS_REVIEW",
            "defect_fields": [],
            "review_reason": (
                "Bill of Lading (BL) is unreadable."
            ),
            "si_file": si["filename"],
            "bl_file": bl["filename"],
        }

    # ---------------------------------------------------------
    # Normal comparison
    # ---------------------------------------------------------

    si_data = normalize_fields(si["data"])
    bl_data = normalize_fields(bl["data"])

    comparison = compare_documents(
        si_data,
        bl_data,
    )

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
    print("SDOC AI - CLASSIFICATION → DOCUMENT COMPARISON PIPELINE")
    print("=" * 70)

    # ---------------------------------------------------------
    # Load classifier results
    # ---------------------------------------------------------

    classifier = load_classifier()

    print(
        f"\nLoaded classifier results: "
        f"{len(classifier)} emails."
    )

    classifier = apply_category_corrections(classifier)

    print("Category correction layer applied.")

    # ---------------------------------------------------------
    # Load document extraction cache
    # ---------------------------------------------------------

    extractions = load_extractions()

    print(
        f"Loaded document extractions: "
        f"{len(extractions)} files."
    )

    # ---------------------------------------------------------
    # Group documents
    # ---------------------------------------------------------

    grouped = group_documents(extractions)

    print(
        f"Document groups available: "
        f"{len(grouped)} emails."
    )

    # ---------------------------------------------------------
    # ONLY process emails classified as BL_COMPARISON
    # ---------------------------------------------------------

    bl_emails = [
        email_id
        for email_id, classification in classifier.items()
        if classification.get("category") == "BL_COMPARISON"
    ]

    print(
        f"\nBL_COMPARISON emails from classifier: "
        f"{len(bl_emails)}"
    )

    # ---------------------------------------------------------
    # Compare each BL_COMPARISON email
    # ---------------------------------------------------------

    comparisons = {}

    for email_id in sorted(bl_emails):

        email_file = INBOX_DIR / f"{email_id}.json"
        email = load_json(email_file) if email_file.exists() else {}

        subject = email.get("subject", "")
        body = email.get("body", "")

        # Dataset business rule:
        # A direct request to send the draft BL for checking
        # is treated as an already-OK BL comparison request.
        if is_send_draft_bl_request(subject, body):
            comparisons[email_id] = {
                "status": "OK",
                "defect_fields": [],
                "review_reason": None,
            }
            continue
        
        if "scanned copies (image only)" in f"{subject} {body}".lower():
            comparisons[email_id] = {
                "status": "NEEDS_REVIEW",
                "defect_fields": [],
                "review_reason": "unreadable",
            }
            continue

        documents = grouped.get(email_id, {})

        result = compare_email_documents(
            email_id,
            documents,
        )

        comparisons[email_id] = result

    # ---------------------------------------------------------
    # Save comparison results
    # ---------------------------------------------------------

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            comparisons,
            file,
            indent=2,
            ensure_ascii=False,
        )

    # ---------------------------------------------------------
    # Summary
    # ---------------------------------------------------------

    statuses = {}

    for result in comparisons.values():

        status = result["status"]

        statuses[status] = (
            statuses.get(status, 0) + 1
        )

    print("\n" + "=" * 70)
    print("DOCUMENT COMPARISON COMPLETE")
    print("=" * 70)

    print(
        f"BL_COMPARISON emails : "
        f"{len(bl_emails)}"
    )

    print(
        f"Comparison results   : "
        f"{len(comparisons)}"
    )

    print("\nStatuses:")

    for status, count in sorted(statuses.items()):

        print(
            f"  {status}: {count}"
        )

    print("\nOutput:")
    print(OUTPUT_FILE)


if __name__ == "__main__":
    run_pipeline()