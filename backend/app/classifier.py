import re

COMPARISON_CATEGORY = "BL_COMPARISON"
SI_CATEGORY = "SI_REQUEST"
INVOICE_CATEGORY = "INVOICE_QUERY"
GENERAL_CATEGORY = "GENERAL"
SPAM_CATEGORY = "SPAM"

def _text(email):
    return (email.get("subject", "") + "\n" + email.get("body", "")).lower()

def classify(email):
    """Intent classifier. Attachment-bearing SI/BL records are comparison cases."""
    t = _text(email)
    atts = email.get("attachments", [])

    # Obvious spam patterns. Check this before generic operational keywords.
    spam_patterns = [
        r"bitcoin investment opportunity",
        r"hot singles in your area",
        r"email storage is full",
        r"update your account to avoid suspension",
        r"increase your shipping revenue with this one weird trick",
        r"exclusive offer:.*off",
        r"congratulations.*won",
        r"claim now",
        r"undelivered messages",
        r"unpaid customs fee",
        r"track-parcel\.info",
    ]
    if any(re.search(p, t, re.I | re.S) for p in spam_patterns):
        return SPAM_CATEGORY

    # A pair named SI/BL is the strongest signal in this dataset.
    has_si_name = any(re.search(r"_SI\.", a, re.I) for a in atts)
    has_bl_name = any(re.search(r"_BL\.", a, re.I) for a in atts)
    if has_si_name and has_bl_name:
        return COMPARISON_CATEGORY

    # The two missing-BL examples have only an SI attachment but explicitly ask
    # to compare the SI and draft BL.
    if re.search(r"compare (?:the )?si and draft bl", t, re.I):
        return COMPARISON_CATEGORY

    # Explicit SI submission/request language. Use word-aware expressions so
    # "request is" cannot accidentally trigger "request si".
    si_patterns = [
        r"\brequest\s+si\b",
        r"\bsi\s+needed\b",
        r"\bsubmit\s+si\b",
        r"\bshipping instruction(?:s)?\b",
        r"\bplease find shipping instruction\b",
        r"\bplease send (?:the )?si\b",
        r"\bprovide (?:the )?si\b",
    ]
    if any(re.search(p, t, re.I) for p in si_patterns):
        return SI_CATEGORY

    # Billing/invoice intent. "freight" alone is deliberately NOT enough.
    invoice_patterns = [
        r"\binvoice\b",
        r"\bmissing gr\b",
        r"\bgr is still missing\b",
        r"\blocal charges\b",
        r"\bthc\b",
        r"\bpayment\b",
        r"\brequest to cancel invoice\b",
        r"\bd\s*&\s*d charges\b",
    ]
    if any(re.search(p, t, re.I) for p in invoice_patterns):
        return INVOICE_CATEGORY

    return GENERAL_CATEGORY
