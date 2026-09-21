from __future__ import annotations

import json
import time
from pathlib import Path

from app.document_parser import read_attachment, detect_doc_type
from app.document_ai import (
    extract_document_with_ai,
    extract_pdf_with_ai,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]

ATTACHMENTS_DIR = (
    PROJECT_ROOT
    / "data"
    / "sdoc-hackathon-bundle"
    / "attachments"
)

OUTPUT_DIR = PROJECT_ROOT / "submission"

OUTPUT_FILE = OUTPUT_DIR / "document_extractions.json"


def load_cache():
    if not OUTPUT_FILE.exists():
        return {}

    try:
        with open(OUTPUT_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception:
        print("Warning: existing cache could not be loaded.")
        return {}


def save_cache(cache):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            cache,
            file,
            indent=2,
            ensure_ascii=False,
        )


def process_document(path: Path):
    print(f"    Processing: {path.name}")

    # =========================================================
    # 1. Try normal document text extraction
    # =========================================================
    try:
        with open(path, "rb") as file:
            data = file.read()

        text = read_attachment(data, path.name)

        document_type = detect_doc_type(text)

        print(f"    Detected type from text: {document_type}")

        # If the document is readable but isn't an SI or BL,
        # we don't need it for the current extraction pipeline.
        if document_type not in {"SI", "BL"}:
            print("    Skipping: not SI/BL")
            return None

        # Normal text-based document
        result = extract_document_with_ai(
            document_text=text,
            document_type=document_type,
        )

        return result

    # =========================================================
    # 2. Normal extraction failed
    # =========================================================
    except Exception as exc:
        error_text = str(exc)

        print(
            f"    Normal extraction failed: "
            f"{type(exc).__name__}: {error_text}"
        )

        if path.suffix.lower() != ".pdf":
            raise

        # Corrupted PDFs cannot be reliably processed by Gemini.
        # Do not waste API quota on them.
        if (
            "EOF marker not found" in error_text
            or "Stream has ended unexpectedly" in error_text
            or "PdfStreamError" in error_text
        ):
            print("    PDF appears corrupted/unreadable.")
            print("    Skipping Gemini fallback.")
            print("    Marking document as UNREADABLE.")

            return {
                "document_type": "UNREADABLE",
                "status": "UNREADABLE",
                "error": error_text,
            }

        # Scanned/image-based PDF:
        # normal extraction failed, but the PDF itself may still be valid.
        print("    Trying Gemini direct PDF understanding...")

        result = extract_pdf_with_ai(
            pdf_path=path,
            document_type="UNREADABLE",
        )

        return result

def main():
    print("=" * 70)
    print("SDOC AI - BATCH DOCUMENT EXTRACTION")
    print("=" * 70)

    if not ATTACHMENTS_DIR.exists():
        raise FileNotFoundError(
            f"Attachments folder not found:\n{ATTACHMENTS_DIR}"
        )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    cache = load_cache()

    files = sorted(
        [
            path
            for path in ATTACHMENTS_DIR.iterdir()
            if path.is_file()
        ]
    )

    print(f"\nFound {len(files)} attachment files.")
    print(f"Already cached: {len(cache)}")

    processed = 0
    skipped = 0
    failed = 0

    for index, path in enumerate(files, start=1):

        print("\n" + "-" * 70)
        print(f"[{index}/{len(files)}] {path.name}")

        # =====================================================
        # CACHE HANDLING
        # =====================================================
        if path.name in cache:

            cached_result = cache[path.name]

            # Retry previous failures.
            if cached_result.get("status") == "ERROR":
                print("    Previous attempt failed. Retrying...")

            else:
                # Successful extraction or intentional skip.
                print("    Using cached result.")
                skipped += 1
                continue

        # =====================================================
        # PROCESS DOCUMENT
        # =====================================================
        try:

            result = process_document(path)

            if result is None:

                cache[path.name] = {
                    "status": "SKIPPED"
                }

            else:

                cache[path.name] = result

            # Save after EVERY document.
            save_cache(cache)

            processed += 1

            # Small delay between requests.
            time.sleep(0.5)

        except Exception as exc:

            error_text = str(exc)

            print(
                f"    ERROR: {type(exc).__name__}: {error_text}"
            )

            # Save failure so it can be retried later.
            cache[path.name] = {
                "status": "ERROR",
                "error": error_text,
            }

            save_cache(cache)

            failed += 1

            # =================================================
            # STOP IF GEMINI QUOTA IS EXHAUSTED
            # =================================================
            if (
                "429" in error_text
                or "RESOURCE_EXHAUSTED" in error_text
                or "quota" in error_text.lower()
            ):

                print("\n" + "=" * 70)
                print("GEMINI QUOTA EXHAUSTED")
                print("=" * 70)

                print("Progress has been saved.")
                print(
                    "Run this script again when quota is available."
                )

                break

    print("\n" + "=" * 70)
    print("BATCH COMPLETE")
    print("=" * 70)

    print(f"Total files : {len(files)}")
    print(f"Processed   : {processed}")
    print(f"Cached      : {skipped}")
    print(f"Failed      : {failed}")

    print("\nOutput:")
    print(OUTPUT_FILE)


if __name__ == "__main__":
    main()