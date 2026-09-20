import json
from pathlib import Path

from google import genai

from app.config import GEMINI_API_KEY


client = genai.Client(api_key=GEMINI_API_KEY)


DOCUMENT_EXTRACTION_PROMPT = """
You are a document extraction AI for a shipping documentation
operations system.

Extract structured information from the provided shipping document.

The document may be:
- Shipping Instruction (SI)
- Bill of Lading (BL)
- Invoice
- Packing List
- Certificate
- Other shipping document

IMPORTANT:
The document may be a scanned PDF or an image-based document.
Carefully inspect the visual content of the document.

Extract ONLY information that is actually present.

Do NOT guess or invent missing values.

Return ONLY valid JSON using exactly this structure:

{{
  "document_type": null,
  "shipper": null,
  "consignee": null,
  "notify_party": null,
  "port_of_loading": null,
  "port_of_discharge": null,
  "container_count": null,
  "gross_weight_kg": null,
  "vessel": null,
  "voyage": null,
  "container_numbers": [],
  "seal_numbers": [],
  "commodity": null
}}

Rules:

- document_type must be one of:
  "SI", "BL", "INVOICE", "PACKING_LIST",
  "CERTIFICATE", "OTHER", or "UNREADABLE".

- gross_weight_kg must be a number in kilograms.
- If weight is given in MT or tons, convert it to kilograms.
- If weight is given in LB or LBS, convert it to kilograms.
- container_count must be a number when available.
- container_numbers must always be an array.
- seal_numbers must always be an array.
- Missing values must be null.
- Never guess missing information.

- For shipper, consignee, and notify_party:
  extract the company/person name only.
  Do not include street addresses, phone numbers,
  email addresses, or other contact details.

- For port_of_loading and port_of_discharge:
  preserve the port name and location code if present.

- Preserve actual business names and locations as written.

- Carefully distinguish visually similar characters such as:
  O/0, I/1, S/5, B/8.

- If a value is unclear and cannot be reliably determined,
  return null rather than guessing.

DOCUMENT TYPE DETECTED BY THE SYSTEM:
{document_type}

DOCUMENT CONTENT:
{document_text}
"""


def extract_document_with_ai(
    document_text: str,
    document_type: str,
) -> dict:
    """
    Extract structured information from text using Gemini.
    Used when normal document text extraction succeeds.
    """

    if not document_text or not document_text.strip():
        raise ValueError("Document text is empty")

    prompt = DOCUMENT_EXTRACTION_PROMPT.format(
        document_type=document_type,
        document_text=document_text,
    )

    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt,
        config={
            "response_mime_type": "application/json",
        },
    )

    return json.loads(response.text)


def extract_pdf_with_ai(
    pdf_path: str | Path,
    document_type: str = "UNREADABLE",
) -> dict:
    """
    Send the original PDF directly to Gemini for visual document understanding.
    """

    pdf_path = Path(pdf_path)

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    print(f"    Uploading PDF to Gemini: {pdf_path.name}")

    uploaded_file = client.files.upload(
        file=str(pdf_path),
    )

    print(f"    Gemini file uploaded: {uploaded_file.name}")

    prompt = DOCUMENT_EXTRACTION_PROMPT.format(
        document_type=document_type,
        document_text=(
            "The document is provided as a PDF file. "
            "Inspect the PDF visually, including scanned pages. "
            "Extract the requested fields directly from the document. "
            "Do not rely on an OCR text layer."
        ),
    )

    interaction = client.interactions.create(
        model="gemini-3.6-flash",
        input=[
            {
                "type": "document",
                "uri": uploaded_file.uri,
                "mime_type": uploaded_file.mime_type,
            },
            {
                "type": "text",
                "text": prompt,
            },
        ],
    )

    print("RAW GEMINI OUTPUT:")
    print(repr(interaction.output_text))

    raw_output = interaction.output_text.strip()

    if raw_output.startswith("```"):
        raw_output = raw_output.replace("```json", "", 1)
        raw_output = raw_output.replace("```", "", 1)
        raw_output = raw_output.strip()

    result = json.loads(raw_output)

    print("    Gemini PDF extraction successful.")

    return result