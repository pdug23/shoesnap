"""Database health check — analyse shoebase.json for gaps and stats.

Usage:
    python health_check.py
"""

import json
import sys
from collections import Counter
from pathlib import Path

DATABASE_DIR = Path(__file__).resolve().parent
SHOEBASE_PATH = DATABASE_DIR / "shoebase.json"


def main():
    if not SHOEBASE_PATH.exists():
        print("shoebase.json not found")
        sys.exit(1)

    shoes = json.loads(SHOEBASE_PATH.read_text(encoding="utf-8"))

    print()
    print("=" * 50)
    print("  ShoeSnap Database Health Check")
    print("=" * 50)
    print()

    # Basic stats
    print(f"  Total shoes: {len(shoes)}")
    ids = [int(s["shoe_id"].split("_")[1]) for s in shoes]
    print(f"  ID range: shoe_{min(ids):04d} to shoe_{max(ids):04d}")
    print()

    # Brand distribution
    brands = Counter(s["brand"] for s in shoes)
    print(f"  Brands: {len(brands)}")
    for brand, count in brands.most_common():
        print(f"    {brand:<25} {count:>3}")
    print()

    # Data confidence
    confidence = Counter(s.get("data_confidence", "unknown") for s in shoes)
    print("  Data confidence:")
    for conf, count in confidence.most_common():
        pct = count / len(shoes) * 100
        print(f"    {conf:<15} {count:>3}  ({pct:.0f}%)")
    print()

    # Archetype distribution
    archetypes = {
        "daily_trainer": "is_daily_trainer",
        "super_trainer": "is_super_trainer",
        "recovery": "is_recovery_shoe",
        "workout": "is_workout_shoe",
        "race": "is_race_shoe",
        "trail": "is_trail_shoe",
        "walking": "is_walking_shoe",
    }
    print("  Archetypes:")
    for label, field in archetypes.items():
        count = sum(1 for s in shoes if s.get(field))
        print(f"    {label:<20} {count:>3}")
    print()

    # Release status
    status = Counter(s.get("release_status", "unknown") for s in shoes)
    print("  Release status:")
    for st, count in status.most_common():
        print(f"    {st:<20} {count:>3}")
    print()

    # Feel score distributions
    dims = ["cushion_softness_1to5", "bounce_1to5", "stability_1to5",
            "rocker_1to5", "ground_feel_1to5", "weight_feel_1to5"]
    dim_labels = ["Cushion", "Bounce", "Stability", "Rocker", "Ground Feel", "Weight"]

    print("  Feel score distributions:")
    print(f"    {'Dimension':<15} {'1':>4} {'2':>4} {'3':>4} {'4':>4} {'5':>4}  {'Avg':>5}")
    for dim, label in zip(dims, dim_labels):
        dist = Counter(s.get(dim) for s in shoes if s.get(dim))
        vals = [s.get(dim) for s in shoes if s.get(dim)]
        avg = sum(vals) / len(vals) if vals else 0
        print(f"    {label:<15} {dist.get(1,0):>4} {dist.get(2,0):>4} {dist.get(3,0):>4} {dist.get(4,0):>4} {dist.get(5,0):>4}  {avg:>5.1f}")
    print()

    # Surface split
    surface = Counter(s.get("surface", "unknown") for s in shoes)
    print("  Surface:")
    for sf, count in surface.most_common():
        print(f"    {sf:<15} {count:>3}")
    print()

    # Gaps and warnings
    print("  Potential gaps:")
    warnings = 0

    # Underrepresented brands
    small_brands = [b for b, c in brands.items() if c < 3]
    if small_brands:
        print(f"    Brands with <3 shoes: {', '.join(small_brands)}")
        warnings += 1

    # Missing similar_to references
    all_names = {s["full_name"].lower() for s in shoes}
    missing_refs = 0
    for s in shoes:
        sim = s.get("similar_to", "")
        if not sim:
            missing_refs += 1
    if missing_refs:
        print(f"    Shoes missing similar_to: {missing_refs}")
        warnings += 1

    # Placeholder confidence
    placeholders = [s for s in shoes if s.get("data_confidence") == "placeholder"]
    if placeholders:
        print(f"    Placeholder confidence ({len(placeholders)} shoes — need upgrade):")
        for s in placeholders:
            print(f"      {s['full_name']}")
        warnings += 1

    # Estimated that might have lab data now
    estimated = [s for s in shoes if s.get("data_confidence") == "estimated"]
    if estimated:
        print(f"    Estimated confidence: {len(estimated)} shoes (check RunRepeat for lab reviews)")
        warnings += 1

    if warnings == 0:
        print("    None found")

    print()


if __name__ == "__main__":
    main()
