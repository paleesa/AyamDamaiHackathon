from pathlib import Path
import sys

# Allow the test to import the "app" package
BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.document_ai import extract_pdf_with_ai


PROJECT_ROOT = BACKEND_DIR.parent

PDF_PATH = (
    PROJECT_ROOT
    / "data"
    / "sdoc-hackathon-bundle"
    / "attachments"
    / "email_512_BL.pdf"
)


print("=" * 70)
print("GEMINI DIRECT PDF TEST")
print("=" * 70)

print(f"PDF: {PDF_PATH}")
print()

if not PDF_PATH.exists():
    print("ERROR: PDF file not found!")
    print(PDF_PATH)
    raise SystemExit(1)

try:
    result = extract_pdf_with_ai(
        pdf_path=PDF_PATH,
        document_type="BL",
    )

    print()
    print("=" * 70)
    print("RESULT")
    print("=" * 70)

    print(result)

except Exception as exc:
    print()
    print("=" * 70)
    print("ERROR")
    print("=" * 70)
    print(type(exc).__name__)
    print(exc)