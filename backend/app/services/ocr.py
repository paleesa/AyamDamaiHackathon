from pathlib import Path

import cv2
import easyocr
import fitz


_reader = None


def get_reader():
    global _reader

    if _reader is None:
        print("Loading EasyOCR...")
        _reader = easyocr.Reader(
            ["en"],
            gpu=False,
        )

    return _reader


def preprocess_image(image_path: Path) -> Path:
    """
    Improve scanned document image before OCR.
    """

    image = cv2.imread(str(image_path))

    if image is None:
        raise RuntimeError(
            f"Unable to read image: {image_path}"
        )

    # Convert to grayscale.
    gray = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2GRAY,
    )

    # Improve contrast.
    clahe = cv2.createCLAHE(
        clipLimit=2.0,
        tileGridSize=(8, 8),
    )

    enhanced = clahe.apply(gray)

    # Mild denoising.
    denoised = cv2.fastNlMeansDenoising(
        enhanced,
        None,
        10,
        7,
        21,
    )

    # Threshold.
    _, thresholded = cv2.threshold(
        denoised,
        0,
        255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU,
    )

    output_path = image_path.with_name(
        image_path.stem + "_processed.png"
    )

    cv2.imwrite(
        str(output_path),
        thresholded,
    )

    return output_path


def ocr_pdf(pdf_path: str | Path) -> str:

    pdf_path = Path(pdf_path)

    reader = get_reader()

    document = fitz.open(pdf_path)

    all_text = []

    try:

        for page_number, page in enumerate(
            document,
            start=1,
        ):

            print(
                f"OCR page {page_number}/{len(document)}"
            )

            # 300 DPI.
            matrix = fitz.Matrix(
                300 / 72,
                300 / 72,
            )

            pix = page.get_pixmap(
                matrix=matrix,
                alpha=False,
            )

            image_path = (
                pdf_path.parent
                / f"{pdf_path.stem}_page_{page_number}.png"
            )

            pix.save(image_path)

            processed_path = preprocess_image(
                image_path
            )

            results = reader.readtext(
                str(processed_path),
                detail=1,
                paragraph=False,
            )

            page_lines = []

            for bbox, text, confidence in results:

                print(
                    f"[{confidence:.2f}] {text}"
                )

                page_lines.append(text)

            all_text.append(
                "\n".join(page_lines)
            )

    finally:
        document.close()

    return "\n\n".join(all_text).strip()