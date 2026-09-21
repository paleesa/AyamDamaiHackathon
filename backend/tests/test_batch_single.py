from pathlib import Path
import sys

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from batch_document_ai import process_document


PROJECT_ROOT = BACKEND_DIR.parent

PDF_PATH = (
    PROJECT_ROOT
    / "data"
    / "sdoc-hackathon-bundle"
    / "attachments"
    / "email_512_BL.pdf"
)


print("=" * 70)
print("BATCH SINGLE DOCUMENT TEST")
print("=" * 70)

print(f"File: {PDF_PATH}")
print()

result = process_document(PDF_PATH)

print()
print("=" * 70)
print("RESULT")
print("=" * 70)

print(result)