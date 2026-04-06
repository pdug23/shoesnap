"""Export scored shoes to TSV for Google Sheets paste.

Generates tab-separated output with exact column order matching the schema.
No header row (header already exists in the sheet).

Usage:
    python export_tsv.py scoring/scored/*-scored.json
"""

import json
import sys
from pathlib import Path

BATCHES_DIR = Path(__file__).resolve().parent / "output" / "batches"

# Exact column order (40 columns)
COLUMNS = [
    "shoe_id", "brand", "model", "version", "full_name", "alias_code",
    "is_daily_trainer", "is_super_trainer", "is_recovery_shoe",
    "is_workout_shoe", "is_race_shoe", "is_trail_shoe", "is_walking_shoe",
    "cushion_softness_1to5", "bounce_1to5", "stability_1to5",
    "rocker_1to5", "ground_feel_1to5", "weight_feel_1to5",
    "weight_g", "heel_drop_mm", "has_plate", "plate_tech_name",
    "plate_material", "fit_volume", "toe_box", "width_options",
    "support_type", "heel_geometry", "surface", "wet_grip",
    "release_status", "release_year", "release_quarter",
    "retail_price_category", "why_it_feels_this_way", "avoid_if",
    "similar_to", "notable_detail", "common_issues", "data_confidence",
]


def format_value(key: str, val) -> str:
    """Format a value for TSV output."""
    if val is None:
        return ""
    if isinstance(val, bool):
        return "TRUE" if val else "FALSE"
    if isinstance(val, list):
        # common_issues: join with pipe separator
        return " | ".join(str(v) for v in val)
    return str(val)


def next_batch_number() -> int:
    """Find the next batch number based on existing files."""
    BATCHES_DIR.mkdir(parents=True, exist_ok=True)
    existing = list(BATCHES_DIR.glob("batch_*.tsv"))
    if not existing:
        return 1
    nums = []
    for f in existing:
        try:
            num = int(f.stem.split("_")[1])
            nums.append(num)
        except (IndexError, ValueError):
            pass
    return max(nums, default=0) + 1


def main():
    if len(sys.argv) < 2:
        print("Usage: python export_tsv.py <scored_shoe.json> [...]")
        sys.exit(1)

    shoes = []
    for filepath in sys.argv[1:]:
        path = Path(filepath)
        if not path.exists():
            print(f"  File not found: {filepath}")
            continue
        shoe = json.loads(path.read_text(encoding="utf-8"))
        shoes.append(shoe)

    if not shoes:
        print("No shoes to export.")
        sys.exit(1)

    # Generate TSV
    lines = []
    for shoe in shoes:
        row = []
        for col in COLUMNS:
            row.append(format_value(col, shoe.get(col)))
        lines.append("\t".join(row))

    tsv_content = "\n".join(lines) + "\n"

    # Save to batch file
    batch_num = next_batch_number()
    batch_file = BATCHES_DIR / f"batch_{batch_num:03d}_{len(shoes)}shoes.tsv"
    batch_file.write_text(tsv_content, encoding="utf-8")

    # Print summary table
    print(f"\nBatch {batch_num}: {len(shoes)} shoes")
    print(f"Saved: {batch_file}")
    print()
    print("| Shoe | C | B | S | R | G | W | Confidence |")
    print("|------|---|---|---|---|---|---|------------|")
    for shoe in shoes:
        name = shoe.get("full_name", "?")[:30]
        c = shoe.get("cushion_softness_1to5", "?")
        b = shoe.get("bounce_1to5", "?")
        s = shoe.get("stability_1to5", "?")
        r = shoe.get("rocker_1to5", "?")
        g = shoe.get("ground_feel_1to5", "?")
        w = shoe.get("weight_feel_1to5", "?")
        conf = shoe.get("data_confidence", "?")
        print(f"| {name:<30} | {c} | {b} | {s} | {r} | {g} | {w} | {conf} |")


if __name__ == "__main__":
    main()
