import json

from app.document_parser import read_attachment, detect_doc_type
from app.document_ai import extract_document_with_ai
from app.comparator import normalize_fields, compare_documents


def load_and_extract(path):
    with open(path, "rb") as file:
        data = file.read()

    text = read_attachment(data, path)
    document_type = detect_doc_type(text)

    result = extract_document_with_ai(
        document_text=text,
        document_type=document_type,
    )

    return result


def main():
    si_path = input("Enter SI document path: ").strip()
    bl_path = input("Enter BL document path: ").strip()

    print("\nExtracting SI...")
    si = load_and_extract(si_path)

    print("Extracting BL...")
    bl = load_and_extract(bl_path)

    print("\n" + "=" * 60)
    print("SI EXTRACTION")
    print("=" * 60)
    print(json.dumps(si, indent=2))

    print("\n" + "=" * 60)
    print("BL EXTRACTION")
    print("=" * 60)
    print(json.dumps(bl, indent=2))

    si_normalized = normalize_fields(si)
    bl_normalized = normalize_fields(bl)

    comparison = compare_documents(
        si_normalized,
        bl_normalized,
    )
    print("\n" + "=" * 60)
    print("NORMALIZED SI")
    print("=" * 60)
    print(json.dumps(si_normalized, indent=2))

    print("\n" + "=" * 60)
    print("NORMALIZED BL")
    print("=" * 60)
    print(json.dumps(bl_normalized, indent=2))

    print("\n" + "=" * 60)
    print("COMPARISON RESULT")
    print("=" * 60)

    print("STATUS:", comparison["status"])

    if comparison["defect_fields"]:
        print("\nDEFECT FIELDS:")

        for field in comparison["defect_fields"]:
            print(
                f"- {field}: "
                f"SI={si_normalized.get(field)!r} | "
                f"BL={bl_normalized.get(field)!r}"
            )

    if comparison["review_fields"]:
        print("\nREVIEW FIELDS:")

        for field in comparison["review_fields"]:
            print(
                f"- {field}: "
                f"SI={si_normalized.get(field)!r} | "
                f"BL={bl_normalized.get(field)!r}"
        )


if __name__ == "__main__":
    main()