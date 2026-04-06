"""Logo processing pipeline — standardise brand logos to a consistent spec.

Spec:
    Canvas: 400x160px viewBox, transparent background
    Content: Centred, filling ~85% of constraining dimension
    Colour: White on transparent
    Format: SVG (preferred) or WebP fallback
    Padding: ~5% margin from canvas edges

Usage:
    from logo_pipeline import process_logo_svg, process_logo
    svg_str = process_logo_svg(svg_bytes)     # SVG → SVG
    webp_bytes = process_logo(image_bytes)     # bitmap → WebP
"""

import re
import xml.etree.ElementTree as ET
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


# ── SVG processing ──

def is_svg(data: bytes) -> bool:
    """Check if the data looks like an SVG file."""
    try:
        head = data[:500].decode("utf-8", errors="ignore").lower().strip()
        return "<svg" in head or "<?xml" in head and "svg" in head
    except Exception:
        return False


def process_logo_svg(svg_data: bytes) -> str:
    """Process an SVG logo: force all colours to white, set viewBox to 400x160.

    Returns the processed SVG as a string.
    """
    svg_text = svg_data.decode("utf-8", errors="ignore")

    # Strip XML declaration if present — we'll add a clean one
    svg_text = re.sub(r'<\?xml[^?]*\?>\s*', '', svg_text)

    # Parse the SVG
    # Register common SVG namespaces to avoid ns0: prefixes
    ET.register_namespace('', 'http://www.w3.org/2000/svg')
    ET.register_namespace('xlink', 'http://www.w3.org/1999/xlink')

    root = ET.fromstring(svg_text)

    # Get the SVG namespace (if any)
    ns_match = re.match(r'\{(.+?)\}', root.tag)
    ns = ns_match.group(1) if ns_match else ''
    ns_prefix = f'{{{ns}}}' if ns else ''

    # ── Force all colours to white ──
    _force_white(root, ns_prefix)

    # Add a default white fill to the root element
    root.set('fill', 'white')

    # ── Set viewBox to 400x160 ──
    # Preserve the original viewBox aspect ratio and centre within 400x160
    orig_vb = root.get('viewBox')
    if orig_vb:
        parts = orig_vb.replace(',', ' ').split()
        if len(parts) == 4:
            vb_x, vb_y, vb_w, vb_h = [float(p) for p in parts]
        else:
            vb_w, vb_h = 400, 160
            vb_x, vb_y = 0, 0
    else:
        # Try width/height attributes
        w_attr = root.get('width', '400')
        h_attr = root.get('height', '160')
        vb_w = float(re.sub(r'[^0-9.]', '', w_attr) or '400')
        vb_h = float(re.sub(r'[^0-9.]', '', h_attr) or '160')
        vb_x, vb_y = 0, 0

    # Calculate scaling to fit within 400x160 at 85% fill
    target_w = CANVAS_W * FILL_PCT
    target_h = CANVAS_H * FILL_PCT
    scale = min(target_w / vb_w, target_h / vb_h) if vb_w > 0 and vb_h > 0 else 1

    # Scaled dimensions
    scaled_w = vb_w * scale
    scaled_h = vb_h * scale

    # Offset to centre
    offset_x = (CANVAS_W - scaled_w) / 2
    offset_y = (CANVAS_H - scaled_h) / 2

    # Wrap content in a group with transform to centre it
    root.set('viewBox', f'0 0 {CANVAS_W} {CANVAS_H}')
    root.set('width', str(CANVAS_W))
    root.set('height', str(CANVAS_H))

    # Create a wrapper group
    wrapper = ET.Element(f'{ns_prefix}g')
    wrapper.set('transform', f'translate({offset_x:.2f},{offset_y:.2f}) scale({scale:.6f}) translate({-vb_x:.2f},{-vb_y:.2f})')

    # Move all children into the wrapper
    children = list(root)
    for child in children:
        # Skip defs, they stay at root level
        tag_local = child.tag.split('}')[-1] if '}' in child.tag else child.tag
        if tag_local == 'defs':
            continue
        root.remove(child)
        wrapper.append(child)

    root.append(wrapper)

    # Serialize
    svg_output = ET.tostring(root, encoding='unicode')

    # Add XML declaration
    svg_output = '<?xml version="1.0" encoding="UTF-8"?>\n' + svg_output

    return svg_output


def _force_white(element: ET.Element, ns_prefix: str):
    """Recursively force all fill and stroke colours to white in an SVG element."""
    # Attributes to recolour
    for attr in ('fill', 'stroke', 'stop-color', 'flood-color', 'lighting-color'):
        val = element.get(attr, '').lower().strip()
        if val and val != 'none' and val != 'transparent':
            element.set(attr, 'white')

    # Handle inline style attribute
    style = element.get('style', '')
    if style:
        # Replace colour values in style
        style = re.sub(r'fill\s*:\s*[^;]+', 'fill: white', style)
        style = re.sub(r'stroke\s*:\s*[^;]+', 'stroke: white', style)
        style = re.sub(r'stop-color\s*:\s*[^;]+', 'stop-color: white', style)
        element.set('style', style)

    # Recurse into children
    for child in element:
        _force_white(child, ns_prefix)


# ── Bitmap processing ──

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
