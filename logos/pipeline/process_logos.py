"""Batch process all logos in logos_raw/ -> logos/ as SVG.

Converts bitmap logos to clean white-on-transparent SVGs by:
1. Thresholding to a binary mask
2. Tracing contours to SVG paths
3. Centring within a 400x160 viewBox

Usage:
    python process_logos.py
"""

import sys
from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image

from logo_pipeline import (
    CANVAS_W, CANVAS_H, FILL_PCT, BW_THRESHOLD,
    is_svg, process_logo_svg,
)

_PIPELINE_DIR = Path(__file__).resolve().parent       # logos/pipeline/
_LOGOS_DIR = _PIPELINE_DIR.parent                     # logos/
LOGOS_RAW = _LOGOS_DIR / "raw"
LOGOS_OUT = _LOGOS_DIR / "processed"


def bitmap_to_mask(data: bytes) -> np.ndarray:
    """Convert a logo image to a binary mask (True = logo pixel)."""
    img = Image.open(BytesIO(data)).convert("RGBA")
    arr = np.array(img)
    alpha = arr[:, :, 3].astype(np.float32)
    rgb = arr[:, :, :3].astype(np.float32)
    gray = 0.299 * rgb[:, :, 0] + 0.587 * rgb[:, :, 1] + 0.114 * rgb[:, :, 2]

    # Detect if logo is on transparent background
    transparent_pct = (arr[:, :, 3] < 10).sum() / arr[:, :, 3].size

    if transparent_pct > 0.3:
        # Logo on transparent bg — use alpha as the mask
        mask = alpha > 30
    else:
        # Logo on solid bg — dark pixels are the logo
        mask = gray < BW_THRESHOLD
        # Also respect existing alpha
        mask = mask & (alpha > 30)

    return mask


def trace_mask_to_svg_paths(mask: np.ndarray) -> str:
    """Trace a binary mask into SVG path data using contour following.

    Uses a simple marching-squares-like approach: find connected regions
    of True pixels and convert their outlines to SVG path commands.
    """
    from scipy import ndimage

    # Label connected components
    labelled, num_features = ndimage.label(mask)
    if num_features == 0:
        return ""

    paths = []
    for lbl in range(1, num_features + 1):
        component = (labelled == lbl).astype(np.uint8)

        # Skip tiny components (noise)
        if component.sum() < 20:
            continue

        # Get contour by finding edge pixels
        # An edge pixel is one that has at least one 0-neighbour
        eroded = ndimage.binary_erosion(component)
        contour = component.astype(bool) & ~eroded

        rows, cols = np.where(contour)
        if len(rows) == 0:
            continue

        # For a cleaner SVG, we'll use the bounding box approach with
        # pixel-level path data. For each row of contour pixels, emit
        # horizontal line segments.
        # Group contour pixels by row for efficient path generation
        path_data = _pixels_to_path(component)
        if path_data:
            paths.append(path_data)

    return "\n".join(paths)


def _pixels_to_path(component: np.ndarray) -> str:
    """Convert a binary component mask to an SVG path using scanline approach.

    For each row, finds runs of filled pixels and creates rectangles.
    Then combines into a single path for efficiency.
    """
    h, w = component.shape
    commands = []

    for y in range(h):
        row = component[y]
        x = 0
        while x < w:
            if row[x]:
                # Start of a run
                x_start = x
                while x < w and row[x]:
                    x += 1
                # Emit a rectangle as a path segment
                commands.append(f"M{x_start},{y}h{x - x_start}v1h{-(x - x_start)}z")
            else:
                x += 1

    if not commands:
        return ""

    return f'<path d="{" ".join(commands)}"/>'


def build_svg(paths_str: str, orig_w: int, orig_h: int) -> str:
    """Build a complete SVG with the traced paths centred on a 400x160 canvas."""
    if not paths_str.strip():
        return ""

    # Calculate scaling to fit within canvas at FILL_PCT
    target_w = CANVAS_W * FILL_PCT
    target_h = CANVAS_H * FILL_PCT
    scale = min(target_w / orig_w, target_h / orig_h) if orig_w > 0 and orig_h > 0 else 1

    scaled_w = orig_w * scale
    scaled_h = orig_h * scale
    offset_x = (CANVAS_W - scaled_w) / 2
    offset_y = (CANVAS_H - scaled_h) / 2

    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {CANVAS_W} {CANVAS_H}" width="{CANVAS_W}" height="{CANVAS_H}">
  <g transform="translate({offset_x:.2f},{offset_y:.2f}) scale({scale:.6f})" fill="white">
{paths_str}
  </g>
</svg>'''

    return svg


def process_one(raw_path: Path, out_dir: Path) -> str | None:
    """Process a single logo file. Returns output filename or None on failure."""
    data = raw_path.read_bytes()
    stem = raw_path.stem.replace("-raw", "")
    if not stem.endswith("-logo"):
        stem = stem + "-logo" if "-logo" not in stem else stem

    # If source is already SVG, just recolour it
    if is_svg(data):
        svg_str = process_logo_svg(data)
        out_path = out_dir / f"{stem}.svg"
        out_path.write_text(svg_str, encoding="utf-8")
        return out_path.name

    # Bitmap -> SVG trace
    mask = bitmap_to_mask(data)
    if not mask.any():
        print(f"  Warning: no logo content detected in {raw_path.name}")
        return None

    # Crop mask to content bounding box
    rows, cols = np.where(mask)
    y0, y1 = rows.min(), rows.max() + 1
    x0, x1 = cols.min(), cols.max() + 1
    cropped = mask[y0:y1, x0:x1]

    # Trace to SVG paths
    paths_str = trace_mask_to_svg_paths(cropped)
    if not paths_str:
        print(f"  Warning: tracing produced no paths for {raw_path.name}")
        return None

    # Build complete SVG
    svg_str = build_svg(paths_str, x1 - x0, y1 - y0)
    out_path = out_dir / f"{stem}.svg"
    out_path.write_text(svg_str, encoding="utf-8")
    return out_path.name


def main():
    if not LOGOS_RAW.exists():
        print(f"No logos_raw/ folder found.")
        sys.exit(1)

    LOGOS_OUT.mkdir(exist_ok=True)

    raw_files = sorted(LOGOS_RAW.glob("*"))
    raw_files = [f for f in raw_files if f.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp", ".svg", ".avif")]

    if not raw_files:
        print("No logo files found in logos_raw/")
        sys.exit(1)

    print(f"Processing {len(raw_files)} logos to SVG")
    print(f"{'=' * 40}")

    success = 0
    failed = 0

    for f in raw_files:
        print(f"  {f.name}...", end=" ")
        result = process_one(f, LOGOS_OUT)
        if result:
            print(f"-> {result}")
            success += 1
        else:
            print("FAILED")
            failed += 1

    print(f"\n{'=' * 40}")
    print(f"Done! {success} processed, {failed} failed")
    print(f"Output: {LOGOS_OUT}")


if __name__ == "__main__":
    main()
