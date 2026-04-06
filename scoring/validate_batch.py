"""Validate a batch of scored shoes before export.

Checks all 40 columns, enums, ranges, duplicates, and text quality.

Usage:
    python validate_batch.py scoring/scored/*-scored.json
"""

import json
import re
import sys
from pathlib import Path

DATABASE_DIR = Path(__file__).resolve().parent.parent / "database"

# Exact enum values
ENUMS = {
    "fit_volume": {"low", "standard", "high"},
    "toe_box": {"narrow", "standard", "roomy"},
    "width_options": {"standard only", "standard and wide"},
    "support_type": {"neutral", "stable_neutral", "stability"},
    "heel_geometry": {"standard", "aggressive_forefoot"},
    "surface": {"road", "road/trail", "trail"},
    "wet_grip": {"poor", "average", "good", "excellent"},
    "release_status": {"rare to find", "available", "not yet released"},
    "retail_price_category": {"Budget", "Core", "Premium", "Super-premium"},
    "data_confidence": {"lab", "estimated", "placeholder"},
    "plate_material": {"carbon", "nylon", "fiberglass", None, ""},
}

FEEL_DIMS = [
    "cushion_softness_1to5", "bounce_1to5", "stability_1to5",
    "rocker_1to5", "ground_feel_1to5", "weight_feel_1to5",
]

BOOL_FIELDS = [
    "is_daily_trainer", "is_super_trainer", "is_recovery_shoe",
    "is_workout_shoe", "is_race_shoe", "is_trail_shoe", "is_walking_shoe",
    "has_plate",
]

# Lab numbers that should NOT appear in text columns
LAB_NUMBER_PATTERNS = [
    r'\d+\.?\d*\s*HA\b',
    r'\d+\.?\d*\s*AC\b',
    r'\d+\.?\d*\s*%\s*(?:energy|return)',
    r'\d+\.?\d*\s*mm\s*(?:stack|heel|forefoot)',
    r'\d+\.?\d*\s*(?:N|newtons)',
    r'durometer',
]

TEXT_COLUMNS = ["why_it_feels_this_way", "avoid_if", "notable_detail"]


def load_shoebase() -> list:
    sb_path = DATABASE_DIR / "shoebase.json"
    if sb_path.exists():
        return json.loads(sb_path.read_text(encoding="utf-8"))
    return []


def validate_shoe(shoe: dict, shoebase: list, errors: list, warnings: list):
    """Validate a single scored shoe."""
    name = shoe.get("full_name", shoe.get("shoe_id", "unknown"))

    # Check shoe_id format
    sid = shoe.get("shoe_id", "")
    if not re.match(r'^shoe_\d{4}$', sid):
        errors.append(f"{name}: Invalid shoe_id format '{sid}' (expected shoe_NNNN)")

    # Check required fields present
    required = ["brand", "model", "full_name", "weight_g", "heel_drop_mm"]
    for field in required:
        if not shoe.get(field):
            warnings.append(f"{name}: Missing {field}")

    # Check feel scores are 1-5 integers
    for dim in FEEL_DIMS:
        val = shoe.get(dim)
        if val is None:
            errors.append(f"{name}: Missing {dim}")
        elif not isinstance(val, int) or val < 1 or val > 5:
            errors.append(f"{name}: {dim} = {val} (must be int 1-5)")

    # Check booleans
    for field in BOOL_FIELDS:
        val = shoe.get(field)
        if val not in (True, False):
            errors.append(f"{name}: {field} = {val} (must be True/False)")

    # Check enums
    for field, allowed in ENUMS.items():
        val = shoe.get(field)
        if val is not None and val != "" and val not in allowed:
            errors.append(f"{name}: {field} = '{val}' (allowed: {allowed})")

    # Check text columns for lab numbers
    for col in TEXT_COLUMNS:
        text = shoe.get(col, "")
        if not text or "NEEDS HUMAN INPUT" in text:
            warnings.append(f"{name}: {col} needs human input")
            continue
        for pattern in LAB_NUMBER_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                errors.append(f"{name}: {col} contains lab measurement (found: {pattern})")
                break

    # Check common_issues format
    issues = shoe.get("common_issues", [])
    if isinstance(issues, list):
        for issue in issues:
            if isinstance(issue, str) and ":" not in issue:
                warnings.append(f"{name}: common_issues entry missing key:value format: '{issue}'")
    elif isinstance(issues, str):
        errors.append(f"{name}: common_issues should be a list, got string")

    # Check for duplicates
    brand = shoe.get("brand", "").lower()
    model = shoe.get("model", "").lower()
    version = str(shoe.get("version", "")).lower()
    for existing in shoebase:
        if (existing["brand"].lower() == brand and
            existing["model"].lower() == model and
            str(existing.get("version", "")).lower() == version):
            warnings.append(f"{name}: DUPLICATE — already exists as {existing['shoe_id']}")
            break

    # Check archetype rules
    if shoe.get("is_super_trainer") and shoe.get("is_race_shoe"):
        warnings.append(f"{name}: Super trainer should NOT also be race shoe")
    if shoe.get("is_daily_trainer") and not shoe.get("is_recovery_shoe"):
        warnings.append(f"{name}: Daily trainer should also be recovery shoe (all daily trainers are)")


def main():
    if len(sys.argv) < 2:
        print("Usage: python validate_batch.py <scored_shoe.json> [...]")
        sys.exit(1)

    shoebase = load_shoebase()
    all_errors = []
    all_warnings = []
    shoes_checked = 0

    for filepath in sys.argv[1:]:
        path = Path(filepath)
        if not path.exists():
            print(f"  File not found: {filepath}")
            continue

        shoe = json.loads(path.read_text(encoding="utf-8"))
        errors = []
        warnings = []
        validate_shoe(shoe, shoebase, errors, warnings)

        name = shoe.get("full_name", path.stem)
        shoes_checked += 1

        if errors:
            print(f"\n  FAIL: {name}")
            for e in errors:
                print(f"    ERROR: {e}")
        if warnings:
            if not errors:
                print(f"\n  WARN: {name}")
            for w in warnings:
                print(f"    WARN:  {w}")
        if not errors and not warnings:
            print(f"  PASS: {name}")

        all_errors.extend(errors)
        all_warnings.extend(warnings)

    print(f"\n{'=' * 40}")
    print(f"Checked: {shoes_checked} shoes")
    print(f"Errors:  {len(all_errors)}")
    print(f"Warnings: {len(all_warnings)}")

    if all_errors:
        print("\nBATCH FAILED — fix errors before export")
        sys.exit(1)
    elif all_warnings:
        print("\nBATCH PASSED with warnings — review before export")
    else:
        print("\nBATCH PASSED — ready for export")


if __name__ == "__main__":
    main()
