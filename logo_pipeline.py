"""Logo processing pipeline — standardise brand logos to a consistent spec.

Spec:
    Canvas: 400x160px, transparent background
    Content: Centred, filling ~85% of constraining dimension
    Colour: Single flat colour (black on transparent)
    Format: WebP output
    Padding: ~5% margin from canvas edges

Usage:
    from logo_pipeline import process_logo
    webp_bytes = process_logo(image_bytes)
"""

from io import BytesIO

import numpy as np
from PIL import Image, ImageFilter

# ── Defaults ──

CANVAS_W = 400
CANVAS_H = 160
FILL_PCT = 0.85      # logo fills 85% of the constraining dimension
WEBP_QUALITY = 90     # higher quality for logos (sharp edges matter)
BW_THRESHOLD = 128    # threshold for separating logo from background
LOGO_COLOUR = (255, 255, 255)  # white logos on transparent background


def load_rgba(data: bytes) -> Image.Image:
    """Open image bytes and ensure RGBA mode."""
    return Image.open(BytesIO(data)).convert("RGBA")


def to_single_colour(img: Image.Image, threshold: int = BW_THRESHOLD) -> Image.Image:
    """Convert a logo image to single-colour white on transparent.

    Handles three common cases:
    1. Dark logo on light/white background → detect dark pixels as the logo
    2. Light/white logo on transparent background → detect via existing alpha
    3. Coloured logo → convert to luminance, threshold

    The result is always white pixels with alpha derived from how "logo-like"
    each pixel is, giving smooth anti-aliased edges.
    """
    arr = np.array(img)
    has_alpha = arr.shape[2] == 4
    alpha = arr[:, :, 3].astype(np.float32) if has_alpha else np.full(arr.shape[:2], 255, dtype=np.float32)

    # Convert to grayscale
    rgb = arr[:, :, :3].astype(np.float32)
    gray = 0.299 * rgb[:, :, 0] + 0.587 * rgb[:, :, 1] + 0.114 * rgb[:, :, 2]

    # Detect if this is a logo-on-transparent-background image
    # (lots of fully transparent pixels with some opaque content)
    if has_alpha:
        transparent_pct = (arr[:, :, 3] < 10).sum() / arr[:, :, 3].size
    else:
        transparent_pct = 0

    if transparent_pct > 0.3:
        # Case: logo already on transparent background
        # Use existing alpha as the logo mask directly
        logo_alpha = alpha.copy()
    else:
        # Case: logo on a solid background (likely white/light)
        # Dark pixels = logo, light pixels = background
        logo_alpha = (255.0 - gray)
        logo_alpha = np.clip((logo_alpha - (255 - threshold * 2)) * 2, 0, 255)
        # Combine with existing alpha
        logo_alpha = np.minimum(logo_alpha, alpha)

    logo_alpha = np.clip(logo_alpha, 0, 255).astype(np.uint8)

    # Set all RGB to white, use computed alpha
    result = np.full((*arr.shape[:2], 4), 255, dtype=np.uint8)
    result[:, :, 3] = logo_alpha

    return Image.fromarray(result, "RGBA")


def crop_to_content(img: Image.Image) -> Image.Image:
    """Crop to the bounding box of non-transparent pixels."""
    bbox = img.getchannel("A").getbbox()
    if bbox:
        return img.crop(bbox)
    return img


def fit_to_canvas(
    img: Image.Image,
    canvas_w: int = CANVAS_W,
    canvas_h: int = CANVAS_H,
    fill_pct: float = FILL_PCT,
) -> Image.Image:
    """Centre the logo on a transparent canvas.

    Scales to fill fill_pct of the constraining dimension, so wide logos
    like "New Balance" fill the width and tall logos like "On" fill the
    height. The result is equal visual weight across different logo shapes.
    """
    w, h = img.size
    if w == 0 or h == 0:
        return Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))

    # Available space with margin
    max_w = int(canvas_w * fill_pct)
    max_h = int(canvas_h * fill_pct)

    # Scale to fit — unlike shoes, we DO upscale small logos
    scale = min(max_w / w, max_h / h)
    new_w = max(1, int(w * scale))
    new_h = max(1, int(h * scale))
    img = img.resize((new_w, new_h), Image.LANCZOS)

    # Centre on canvas
    canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    x = (canvas_w - img.width) // 2
    y = (canvas_h - img.height) // 2
    canvas.paste(img, (x, y), img)
    return canvas


def export_webp(img: Image.Image, quality: int = WEBP_QUALITY) -> bytes:
    """Save as WebP with alpha, return bytes."""
    buf = BytesIO()
    img.save(buf, format="WEBP", quality=quality, method=6)
    return buf.getvalue()


def process_logo(image_bytes: bytes) -> bytes:
    """Run the full logo processing pipeline.

    Pipeline:
    1. Convert to single-colour black silhouette
    2. Crop to content bounding box
    3. Fit to 400x160 canvas (centred, ~85% fill)
    4. Export as WebP

    Returns WebP bytes.
    """
    img = load_rgba(image_bytes)
    img = to_single_colour(img)
    img = crop_to_content(img)
    img = fit_to_canvas(img)
    return export_webp(img)
