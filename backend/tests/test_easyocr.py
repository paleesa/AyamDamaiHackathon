from pathlib import Path

import fitz
import easyocr


PROJECT_ROOT = Path(__file__).resolve().parents[1]

PDF_PATH = (
    PROJECT_ROOT
    / "data"
    / "sdoc-hackathon-bundle"
    / "attachments"
    / "email_512_BL.pdf"
)


def main():
    print("=" * 70)
    print("EASYOCR TEST")
    print("=" * 70)

    print("\nLoading EasyOCR...")

    reader = easyocr.Reader(
        ["en"],
        gpu=False,
    )

    print("EasyOCR loaded.")

    document = fitz.open(PDF_PATH)

    all_text = []

    for page_number, page in enumerate(document, start=1):

        print(
            f"\nProcessing page {page_number}/{len(document)}..."
        )

        # Render PDF page at high resolution.
        matrix = fitz.Matrix(
            300 / 72,
            300 / 72,
        )

        pix = page.get_pixmap(
            matrix=matrix,
            alpha=False,
        )

        image_path = (
            PROJECT_ROOT
            / "submission"
            / f"_ocr_page_{page_number}.png"
        )

        pix.save(image_path)

        print(f"Image saved: {image_path}")

        results = reader.readtext(
            str(image_path)
        )

        page_text = []

        for bbox, text, confidence in results:

            print(
                f"[{confidence:.2f}] {text}"
            )

            page_text.append(text)

        all_text.append(
            "\n".join(page_text)
        )

    document.close()

    final_text = "\n\n".join(all_text)

    output_path = (
        PROJECT_ROOT
        / "submission"
        / "email_512_BL_ocr.txt"
    )

    output_path.write_text(
        final_text,
        encoding="utf-8",
    )

    print("\n" + "=" * 70)
    print("OCR COMPLETE")
    print("=" * 70)

    print(
        f"Characters extracted: {len(final_text)}"
    )

    print(
        f"Saved OCR text to:\n{output_path}"
    )


if __name__ == "__main__":
    main()