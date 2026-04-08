"""Merge approved scored shoes into database/shoebase.json.

Validates, deduplicates, assigns IDs, sorts by brand, and updates
the changelog.

Usage:
    python update_shoebase.py scoring/scored/*-scored.json
"""

import json
import sys
from datetime import datetime
from pathlib import Path

SCORING_DIR = Path(__file__).resolve().parent
DATABASE_DIR = SCORING_DIR.parent / "database"
IMAGES_DIR = SCORING_DIR.parent / "images"
CINDA_DATA_DIR = SCORING_DIR.parent.parent / "cinda-0ab63566" / "src" / "data"

SHOEBASE_PATH = DATABASE_DIR / "shoebase.json"
CHANGELOG_PATH = DATABASE_DIR / "changelog.md"
SHOES_TXT = IMAGES_DIR / "shoes.txt"


def sync_to_cinda(content: str):
    """Copy shoebase.json to the Cinda repo if it exists."""
    cinda_path = CINDA_DATA_DIR / "shoebase.json"
    if CINDA_DATA_DIR.exists():
        cinda_path.write_text(content, encoding="utf-8")
        print(f"  Synced to Cinda: {cinda_path}")
    else:
        print(f"  Warning: Cinda data dir not found ({CINDA_DATA_DIR}), skipping sync")


def load_shoebase() -> list:
    if SHOEBASE_PATH.exists():
        return json.loads(SHOEBASE_PATH.read_text(encoding="utf-8"))
    return []


def save_shoebase(data: list):
    content = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    SHOEBASE_PATH.write_text(content, encoding="utf-8")
    sync_to_cinda(content)


def next_shoe_id(shoebase: list) -> int:
    """Get the next numeric ID."""
    if not shoebase:
        return 1
    return max(int(s["shoe_id"].split("_")[1]) for s in shoebase) + 1


def is_duplicate(shoebase: list, shoe: dict) -> bool:
    for s in shoebase:
        if (s["brand"].lower() == shoe["brand"].lower() and
            s["model"].lower() == shoe["model"].lower() and
            str(s.get("version", "")).lower() == str(shoe.get("version", "")).lower()):
            return True
    return False


def append_to_image_queue(shoe_names: list[str]):
    """Add shoe full_names to images/shoes.txt if not already there."""
    SHOES_TXT.parent.mkdir(parents=True, exist_ok=True)
    existing = set()
    if SHOES_TXT.exists():
        existing = set(
            line.strip().lower()
            for line in SHOES_TXT.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")
        )

    new_entries = []
    for name in shoe_names:
        if name.lower() not in existing:
            new_entries.append(name)

    if new_entries:
        with SHOES_TXT.open("a", encoding="utf-8") as f:
            for name in new_entries:
                f.write(f"{name}\n")
        print(f"  Added {len(new_entries)} shoes to image queue ({SHOES_TXT.name})")


def update_changelog(added_shoes: list[dict], batch_info: str):
    """Append to changelog."""
    CHANGELOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    entry = f"\n## {timestamp} — {batch_info}\n\n"
    for shoe in added_shoes:
        entry += f"- {shoe['shoe_id']}: {shoe['full_name']} ({shoe.get('data_confidence', '?')})\n"
    entry += "\n"

    with CHANGELOG_PATH.open("a", encoding="utf-8") as f:
        f.write(entry)


def main():
    if len(sys.argv) < 2:
        print("Usage: python update_shoebase.py <scored_shoe.json> [...]")
        print()
        print("  --check-upgrades  List all 'estimated' shoes that could be upgraded to 'lab'")
        sys.exit(1)

    # Handle --check-upgrades stub
    if "--check-upgrades" in sys.argv:
        shoebase = load_shoebase()
        estimated = [s for s in shoebase if s.get("data_confidence") == "estimated"]
        print(f"\n{len(estimated)} shoes with 'estimated' confidence (could upgrade to 'lab'):\n")
        for s in estimated:
            print(f"  {s['shoe_id']}: {s['full_name']}")
        print(f"\nCheck RunRepeat for lab reviews of these shoes.")
        return

    shoebase = load_shoebase()
    next_id = next_shoe_id(shoebase)

    new_shoes = []
    skipped = []

    for filepath in sys.argv[1:]:
        if filepath.startswith("--"):
            continue
        path = Path(filepath)
        if not path.exists():
            print(f"  File not found: {filepath}")
            continue

        shoe = json.loads(path.read_text(encoding="utf-8"))

        if is_duplicate(shoebase, shoe):
            print(f"  SKIP (duplicate): {shoe.get('full_name', path.stem)}")
            skipped.append(shoe)
            continue

        # Reassign shoe_id to ensure continuity
        shoe["shoe_id"] = f"shoe_{next_id:04d}"
        next_id += 1

        new_shoes.append(shoe)
        print(f"  ADD:  {shoe['shoe_id']} — {shoe.get('full_name', '?')}")

    if not new_shoes:
        print("\nNo new shoes to add.")
        return

    # Confirm
    print(f"\nReady to add {len(new_shoes)} shoes to shoebase.json")
    print(f"({len(skipped)} skipped as duplicates)")
    confirm = input("Proceed? [y/N]: ").strip().lower()

    if confirm != "y":
        print("Aborted.")
        return

    # Merge and sort
    shoebase.extend(new_shoes)
    shoebase.sort(key=lambda s: (s["brand"].lower(), s["model"].lower(), str(s.get("version", ""))))

    # Save
    save_shoebase(shoebase)
    print(f"\nSaved {len(shoebase)} total shoes to {SHOEBASE_PATH}")

    # Update changelog
    update_changelog(new_shoes, f"Added {len(new_shoes)} shoes")

    # Add to image queue
    shoe_names = [s["full_name"] for s in new_shoes if s.get("full_name")]
    append_to_image_queue(shoe_names)


if __name__ == "__main__":
    main()
