"""ShoeSnap — Shoe intelligence workbench for Cinda.

CLI entry point with menu-driven access to all pipelines.
"""

import sys
from pathlib import Path

# Add pipeline directories to path so imports work
REPO_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_DIR / "images" / "pipeline"))
sys.path.insert(0, str(REPO_DIR / "logos" / "pipeline"))
sys.path.insert(0, str(REPO_DIR / "scoring"))


def show_menu():
    print()
    print("=" * 44)
    print("  ShoeSnap — Shoe Intelligence Workbench")
    print("=" * 44)
    print()
    print("  Image Pipeline")
    print("    1. Process shoe images (drag-and-drop)")
    print("    2. Fetch shoe images (from Bing)")
    print()
    print("  Logo Pipeline")
    print("    3. Fetch brand logos")
    print("    4. Process logos (raw -> SVG)")
    print()
    print("  Scoring Pipeline")
    print("    5. Score a shoe from review")
    print("    6. Validate a batch")
    print("    7. Export batch to TSV")
    print("    8. Update shoebase.json")
    print()
    print("  Database")
    print("    9. Database health check")
    print()
    print("    0. Exit")
    print()


def main():
    while True:
        show_menu()
        choice = input("  Choose: ").strip()

        if choice == "0":
            break
        elif choice == "1":
            from shoe_processor import main as sp_main
            sp_main()
            break  # GUI takes over the event loop
        elif choice == "2":
            from fetch_shoes import main as fs_main
            fs_main()
            break
        elif choice == "3":
            from fetch_logos import main as fl_main
            fl_main()
            break
        elif choice == "4":
            from process_logos import main as pl_main
            pl_main()
        elif choice == "5":
            print("  Scoring pipeline — coming soon (drop reviews in scoring/reviews/)")
        elif choice == "6":
            print("  Batch validation — coming soon")
        elif choice == "7":
            print("  TSV export — coming soon")
        elif choice == "8":
            print("  Shoebase update — coming soon")
        elif choice == "9":
            print("  Health check — coming soon")
        else:
            print("  Invalid choice")


if __name__ == "__main__":
    main()
