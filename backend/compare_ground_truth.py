import json
from pathlib import Path
from collections import Counter

PROJECT_ROOT = Path(__file__).resolve().parents[1]

GROUND_TRUTH = PROJECT_ROOT / "evaluation" / "ground_truth.json"
PREDICTION = PROJECT_ROOT / "submission" / "final_submission.json"


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


gt = load_json(GROUND_TRUTH)
pred = load_json(PREDICTION)

print("=" * 70)
print("SDOC - GROUND TRUTH COMPARISON")
print("=" * 70)

print(f"\nGround truth emails : {len(gt)}")
print(f"Prediction emails   : {len(pred)}")

common = sorted(set(gt) & set(pred))

print(f"Common emails       : {len(common)}")

if set(gt) != set(pred):
    print("\nWARNING: Email IDs do not match.")
    print("Missing predictions:", sorted(set(gt) - set(pred))[:20])
    print("Extra predictions  :", sorted(set(pred) - set(gt))[:20])


def accuracy(field):
    correct = sum(
        gt[email].get(field) == pred[email].get(field)
        for email in common
    )
    return correct / len(common) if common else 0


print("\nFIELD ACCURACY")
print("-" * 70)

for field in [
    "category",
    "status",
    "review_reason",
    "defect_fields",
    "has_defect",
]:
    print(f"{field:20s}: {accuracy(field):.4f}")


print("\nCATEGORY DISTRIBUTION")
print("-" * 70)

print("Ground truth:")
print(Counter(gt[email].get("category") for email in common))

print("\nPrediction:")
print(Counter(pred[email].get("category") for email in common))


print("\nSTATUS DISTRIBUTION")
print("-" * 70)

print("Ground truth:")
print(Counter(gt[email].get("status") for email in common))

print("\nPrediction:")
print(Counter(pred[email].get("status") for email in common))


# Category mismatches
category_errors = [
    email
    for email in common
    if gt[email].get("category") != pred[email].get("category")
]

status_errors = [
    email
    for email in common
    if gt[email].get("status") != pred[email].get("status")
]

defect_errors = [
    email
    for email in common
    if gt[email].get("defect_fields", [])
    != pred[email].get("defect_fields", [])
]

print("\nERROR COUNTS")
print("-" * 70)

print(f"Category errors     : {len(category_errors)}")
print(f"Status errors       : {len(status_errors)}")
print(f"Defect field errors : {len(defect_errors)}")


print("\nSAMPLE CATEGORY ERRORS")
print("-" * 70)

for email in category_errors[:20]:
    print(
        email,
        "| GT:", gt[email].get("category"),
        "| Pred:", pred[email].get("category"),
    )


print("\nSAMPLE STATUS ERRORS")
print("-" * 70)

for email in status_errors[:20]:
    print(
        email,
        "| GT:", gt[email].get("status"),
        "| Pred:", pred[email].get("status"),
    )


print("\nSAMPLE DEFECT FIELD ERRORS")
print("-" * 70)

for email in defect_errors[:20]:
    print(
        email,
        "| GT:", gt[email].get("defect_fields"),
        "| Pred:", pred[email].get("defect_fields"),
    )

print("\n" + "=" * 70)
print("COMPARISON COMPLETE")
print("=" * 70)