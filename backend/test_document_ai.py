from app.document_parser import read_attachment, detect_doc_type
from app.document_ai import extract_document_with_ai


def main():
    filename = input("Enter document path: ").strip()

    with open(filename, "rb") as file:
        data = file.read()

    # Step 1: Read document
    text = read_attachment(data, filename)

    print("\n" + "=" * 60)
    print("EXTRACTED TEXT")
    print("=" * 60)
    print(text[:5000])

    # Step 2: Detect document type
    document_type = detect_doc_type(text)

    print("\n" + "=" * 60)
    print("DOCUMENT TYPE")
    print("=" * 60)
    print(document_type)

    # Step 3: Gemini extraction
    result = extract_document_with_ai(
        document_text=text,
        document_type=document_type,
    )

    print("\n" + "=" * 60)
    print("GEMINI EXTRACTION")
    print("=" * 60)

    import json

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()