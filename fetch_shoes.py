"""ShoeSnap Image Fetcher — Bulk download shoe images from Google Images.

Usage:
    1. Put shoe names in shoes.txt (one per line)
    2. Run: python fetch_shoes.py
    3. For each shoe, pick the best image from 5 options
    4. Images are saved to fetched/ with clean filenames
    5. Drag the fetched/ folder into ShoeSnap to process

Options:
    python fetch_shoes.py                  # uses shoes.txt
    python fetch_shoes.py my_list.txt      # uses custom file
    python fetch_shoes.py --auto           # auto-pick first result (no prompts)
"""

import re
import sys
import json
import time
import random
from pathlib import Path
from urllib.parse import quote_plus

import requests

FETCH_DIR = Path(__file__).parent / "fetched"
DEFAULT_LIST = Path(__file__).parent / "shoes.txt"

# Google Images returns results embedded in HTML — we extract image URLs
# from the page source. This avoids needing an API key.
SEARCH_URL = "https://www.google.com/search?q={}&tbm=isch&tbs=isz:l"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def sanitize_filename(name: str) -> str:
    """Turn a shoe name into a clean filename."""
    name = name.lower().strip()
    name = re.sub(r'[®™©]', '', name)
    name = re.sub(r'[\s_\.]+', '-', name)
    name = re.sub(r'[^a-z0-9\-]', '', name)
    name = re.sub(r'-{2,}', '-', name)
    name = name.strip('-')
    return name[:200] if name else "shoe"


def extract_image_urls(html: str, max_results: int = 8) -> list[str]:
    """Extract image URLs from Google Images HTML source."""
    urls = []

    # Pattern 1: full-size image URLs in metadata
    # Google embeds them as escaped strings in various JSON-like structures
    patterns = [
        r'"(https?://[^"]+\.(?:jpg|jpeg|png|webp)(?:\?[^"]*)?)"',
        r'\["(https?://[^"]+\.(?:jpg|jpeg|png|webp)(?:\?[^"]*)?)"',
    ]

    seen = set()
    for pattern in patterns:
        for match in re.finditer(pattern, html, re.IGNORECASE):
            url = match.group(1)
            # Filter out Google's own thumbnails and icons
            if "gstatic.com" in url:
                continue
            if "google.com" in url:
                continue
            if "googleapis.com" in url:
                continue
            if url in seen:
                continue
            # Skip tiny images (likely thumbnails)
            if any(dim in url.lower() for dim in ['=s64', '=s72', '=s96', '=s128', 'favicon']):
                continue
            seen.add(url)
            urls.append(url)
            if len(urls) >= max_results:
                return urls

    return urls


def search_shoe_images(shoe_name: str) -> list[str]:
    """Search Google Images for a shoe and return image URLs."""
    query = f"{shoe_name} running shoe side view"
    url = SEARCH_URL.format(quote_plus(query))

    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        return extract_image_urls(resp.text)
    except Exception as e:
        print(f"  Search failed: {e}")
        return []


def download_image(url: str, timeout: int = 15) -> bytes | None:
    """Download an image URL and return bytes, or None on failure."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout, stream=True)
        resp.raise_for_status()

        # Check content type
        content_type = resp.headers.get("Content-Type", "")
        if "image" not in content_type and "octet-stream" not in content_type:
            return None

        # Read up to 15MB
        data = resp.content
        if len(data) < 5000:  # too small, probably an error page
            return None
        return data
    except Exception:
        return None


def pick_image_interactive(shoe_name: str, urls: list[str]) -> bytes | None:
    """Let the user pick from available images by downloading and showing sizes."""
    if not urls:
        print(f"  No images found for '{shoe_name}'")
        return None

    print(f"\n  Found {len(urls)} images for '{shoe_name}':")

    # Download all candidates and show info
    candidates = []
    for i, url in enumerate(urls[:6]):
        data = download_image(url)
        if data:
            size_kb = len(data) / 1024
            # Try to get dimensions
            try:
                from PIL import Image
                from io import BytesIO
                img = Image.open(BytesIO(data))
                w, h = img.size
                dim_str = f"{w}x{h}"
            except Exception:
                dim_str = "unknown"

            candidates.append(data)
            domain = re.search(r'https?://([^/]+)', url)
            source = domain.group(1) if domain else "unknown"
            print(f"    [{len(candidates)}] {dim_str}  {size_kb:.0f}KB  ({source})")
        else:
            # Don't show failed downloads
            pass

    if not candidates:
        print(f"  All downloads failed for '{shoe_name}'")
        return None

    # Let user pick
    while True:
        choice = input(f"  Pick 1-{len(candidates)} (or 's' to skip): ").strip().lower()
        if choice == 's':
            return None
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(candidates):
                return candidates[idx]
        except ValueError:
            pass
        print(f"  Enter a number 1-{len(candidates)} or 's' to skip")


def pick_image_auto(shoe_name: str, urls: list[str]) -> bytes | None:
    """Auto-pick the largest image (likely highest quality)."""
    if not urls:
        print(f"  No images found for '{shoe_name}'")
        return None

    best_data = None
    best_size = 0

    for url in urls[:5]:
        data = download_image(url)
        if data and len(data) > best_size:
            best_data = data
            best_size = len(data)

    if best_data:
        print(f"  Auto-picked {best_size / 1024:.0f}KB image")
    else:
        print(f"  All downloads failed")

    return best_data


def main():
    auto_mode = "--auto" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    list_file = Path(args[0]) if args else DEFAULT_LIST

    if not list_file.exists():
        print(f"Shoe list not found: {list_file}")
        print(f"Create a file with one shoe name per line.")
        sys.exit(1)

    shoe_names = [
        line.strip()
        for line in list_file.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]

    if not shoe_names:
        print("No shoe names found in the file.")
        sys.exit(1)

    FETCH_DIR.mkdir(exist_ok=True)

    print(f"ShoeSnap Image Fetcher")
    print(f"{'=' * 40}")
    print(f"Shoes to fetch: {len(shoe_names)}")
    print(f"Output folder:  {FETCH_DIR}")
    print(f"Mode:           {'auto' if auto_mode else 'interactive'}")
    print()

    fetched = 0
    skipped = 0
    failed = 0

    for i, name in enumerate(shoe_names):
        print(f"[{i + 1}/{len(shoe_names)}] {name}")

        filename = sanitize_filename(name)
        out_path = FETCH_DIR / f"{filename}.jpg"

        # Skip if already fetched
        if out_path.exists():
            print(f"  Already exists, skipping")
            skipped += 1
            continue

        # Search
        urls = search_shoe_images(name)

        # Pick
        if auto_mode:
            data = pick_image_auto(name, urls)
        else:
            data = pick_image_interactive(name, urls)

        if data:
            out_path.write_bytes(data)
            print(f"  Saved: {out_path.name}")
            fetched += 1
        else:
            failed += 1

        # Small delay between searches to be polite
        if i < len(shoe_names) - 1:
            time.sleep(random.uniform(1.0, 2.5))

    print(f"\n{'=' * 40}")
    print(f"Done! Fetched: {fetched} | Skipped: {skipped} | Failed: {failed}")
    print(f"Output: {FETCH_DIR}")
    print(f"\nNext step: drag the fetched/ folder into ShoeSnap to process all images.")


if __name__ == "__main__":
    main()
