import json
from pathlib import Path
import sys

from google import genai

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.config import GEMINI_API_KEY


client = genai.Client(api_key=GEMINI_API_KEY)


CATEGORIES = [
    "BL_COMPARISON",
    "SI_REQUEST",
    "INVOICE_QUERY",
    "GENERAL",
    "SPAM",
]


CLASSIFIER_PROMPT = """
You are an email classifier for a shipping documentation operations team.

Classify EVERY email into EXACTLY ONE of these categories:

1. BL_COMPARISON
The email asks someone to check, compare, verify, review, or confirm
shipping documents, especially a Shipping Instruction (SI) against a
draft Bill of Lading (BL).

2. SI_REQUEST
The email is requesting, sending, asking for, or discussing Shipping
Instructions without primarily asking to compare an SI against a BL.

3. INVOICE_QUERY
The email is about invoices, billing, charges, payment, local charges,
THC, freight charges, or other financial/documentation charges.

4. GENERAL
General operational or shipping communication that does not belong
to the categories above.

5. SPAM
Clearly irrelevant, unsolicited, promotional, malicious, or suspicious email.

Important:
- Focus on the meaning of the email, not only the subject.
- The subject may be misleading.
- Attachments may provide useful clues.
- Do not classify an email as BL_COMPARISON merely because it contains a BL.
- BL_COMPARISON requires an intent to check, compare, verify, review,
  or confirm shipping documents.

Return ONLY valid JSON.

The response must have this exact structure:

{
  "classifications": [
    {
      "email_id": "email_001",
      "category": "BL_COMPARISON"
    }
  ]
}

Include exactly one classification for every email provided.
"""


def classify_emails(emails: list[dict]) -> dict[str, str]:
    """
    Classify multiple emails in one Gemini request.
    Returns:
        {
            "email_001": "BL_COMPARISON",
            "email_002": "INVOICE_QUERY"
        }
    """

    email_blocks = []

    for email in emails:
        email_id = email.get("email_id", "")

        subject = email.get("subject", "")
        body = email.get("body", "")

        attachments = email.get("attachments", [])

        attachment_names = "\n".join(
            f"- {attachment}" for attachment in attachments
        )

        email_blocks.append(
            f"""
EMAIL ID: {email_id}

Subject:
{subject}

Body:
{body}

Attachments:
{attachment_names if attachment_names else "None"}

------------------------------
"""
        )

    prompt = CLASSIFIER_PROMPT + "\n".join(email_blocks)

    response = client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=prompt,
        config={
            "response_mime_type": "application/json",
        },
    )

    result = json.loads(response.text)

    classifications = result.get("classifications", [])

    output = {}

    for item in classifications:
        email_id = item.get("email_id")
        category = item.get("category")

        if category not in CATEGORIES:
            raise ValueError(
                f"Invalid category for {email_id}: {category}"
            )

        output[email_id] = category

    # Make sure Gemini did not miss an email.
    expected_ids = {email["email_id"] for email in emails}
    returned_ids = set(output.keys())

    missing_ids = expected_ids - returned_ids

    if missing_ids:
        raise ValueError(
            f"Gemini did not classify these emails: {sorted(missing_ids)}"
        )

    return output