"""Post-processing pipeline for shoe images.

Handles shadow removal, canvas sizing, auto-mirroring, edge feathering,
colour defringing, and WebP export.  Every function works on Pillow Image
objects in RGBA mode.
"""

from io import BytesIO

import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

# ── Defaults ──

CANVAS_W = 400
CANVAS_H = 250
MAX_SHOE_W = 350
MAX_SHOE_H = 200
WEBP_QUALITY = 82          # 80-85 range, good balance of size vs clarity
FEATHER_RADIUS = 1.2        # px – subtle edge softening
DEFRINGE_RADIUS = 2         # px – how far inward to sample replacement colour
SHARPEN_AMOUNT = 0.4        # unsharp-mask strength (0 = off, 1 = full)
SHARPEN_RADIUS = 1.0        # unsharp-mask blur radius
CONTRAST_BOOST = 1.08       # 1.0 = no change, 1.1 = +10 %
WB_CLIP_PCT = 0.5           # % of pixels to clip at each end for auto-levels


def load_rgba(data: bytes) -> Image.Image:
    """Open image bytes and ensure RGBA mode."""
    return Image.open(BytesIO(data)).convert("RGBA")


# ── Shadow cleanup ──

SHADOW_ALPHA_FLOOR = 128     # pixels above this are "shoe body"
SHADOW_MIN_BODY_RATIO = 0.02 # disconnected blobs smaller than 2% of the shoe → remove
SHADOW_SURVIVAL_PCT = 0.70   # if we'd keep < 70% of visible pixels, bail out

def remove_shadows(img: Image.Image) -> Image.Image:
    """Remove floor shadows, reflections, and stray semi-transparent artifacts.

    Strategy:
    1. Build a binary mask of the shoe *body* (alpha >= SHADOW_ALPHA_FLOOR).
    2. Label connected components — the largest blob is the shoe.
    3. Zero out any disconnected blobs that are much smaller than the shoe
       (catches isolated shadow patches, dust, reflections).
    4. Zero out all semi-transparent pixels that sit *below* the shoe body's
       bottom edge (catches floor shadows that may still be connected via a
       thin strip of partial alpha at the sole).
    5. Safety check: if the cleanup would remove too many visible pixels,
       return the original image untouched.
    """
    alpha = np.array(img.getchannel("A"))
    total_visible = int((alpha > 0).sum())

    if total_visible == 0:
        return img

    # Step 1: binary mask of the solid shoe body
    body = alpha >= SHADOW_ALPHA_FLOOR

    if not body.any():
        return img  # no body pixels found — don't destroy the image

    # Step 2: label connected components
    labelled, num_features = ndimage.label(body)
    if num_features == 0:
        return img

    # Find the largest component (the shoe)
    component_sizes = ndimage.sum(body, labelled, range(1, num_features + 1))
    shoe_label = int(np.argmax(component_sizes)) + 1  # labels are 1-indexed
    shoe_size = component_sizes[shoe_label - 1]

    # Step 3: remove small disconnected blobs everywhere
    keep_mask = np.zeros_like(alpha, dtype=bool)
    for lbl in range(1, num_features + 1):
        if component_sizes[lbl - 1] >= shoe_size * SHADOW_MIN_BODY_RATIO:
            keep_mask |= (labelled == lbl)

    # For semi-transparent pixels (not in body mask), check if they neighbour
    # a kept body pixel — if not, they're floating artifacts
    semi_transparent = (alpha > 0) & (alpha < SHADOW_ALPHA_FLOOR)

    # Dilate the keep mask generously so edge detail adjacent to the shoe survives
    dilated_keep = ndimage.binary_dilation(keep_mask, iterations=6)

    # Semi-transparent pixels connected to the shoe body survive
    connected_semi = semi_transparent & dilated_keep

    # Step 4: anything below the shoe body's bottom edge that isn't strongly
    # connected is almost certainly a floor shadow
    shoe_rows = np.where(keep_mask.any(axis=1))[0]
    if len(shoe_rows) > 0:
        shoe_bottom = shoe_rows.max()
        # Give a small margin below the sole (some shoes have visible sole tread)
        margin = max(5, int((shoe_rows.max() - shoe_rows.min()) * 0.03))
        below_sole = np.zeros_like(alpha, dtype=bool)
        below_sole[shoe_bottom + margin:, :] = True
        # Remove semi-transparent pixels well below the sole
        connected_semi[below_sole] = False

    # Build candidate alpha
    new_alpha = np.zeros_like(alpha)
    new_alpha[keep_mask] = alpha[keep_mask]
    new_alpha[connected_semi] = alpha[connected_semi]

    # Step 5: safety check — if we'd remove too many pixels, bail out
    surviving = int((new_alpha > 0).sum())
    if surviving < total_visible * SHADOW_SURVIVAL_PCT:
        return img  # cleanup is too aggressive, return original

    img = img.copy()
    img.putalpha(Image.fromarray(new_alpha))
    return img


# ── Auto-mirror ──

def detect_toe_direction(img: Image.Image) -> str:
    """Detect whether the shoe toe points 'left' or 'right'.

    Heuristic: running shoes taper toward the toe.  We compare the number of
    opaque pixels in the left 25 % of the bounding box vs the right 25 %.
    The side with *fewer* opaque pixels is the tapered (toe) end.
    """
    alpha = np.array(img.getchannel("A"))
    rows, cols = np.where(alpha > 20)  # ignore near-transparent fringe
    if len(rows) == 0:
        return "right"  # empty image, nothing to flip

    x0, x1 = cols.min(), cols.max()
    bbox_w = x1 - x0
    quarter = bbox_w // 4

    left_mask = cols <= (x0 + quarter)
    right_mask = cols >= (x1 - quarter)

    left_count = int(left_mask.sum())
    right_count = int(right_mask.sum())

    return "left" if left_count < right_count else "right"


def auto_mirror(img: Image.Image, target: str = "right") -> Image.Image:
    """Flip the shoe horizontally so the toe points toward *target*."""
    direction = detect_toe_direction(img)
    if direction != target:
        return img.transpose(Image.FLIP_LEFT_RIGHT)
    return img


# ── Edge feathering ──

def feather_edges(img: Image.Image, radius: float = FEATHER_RADIUS) -> Image.Image:
    """Soften the alpha channel edges with a small Gaussian blur.

    Only the *edge pixels* are affected — interior opacity stays at 100 %
    and fully transparent areas stay at 0 %.
    """
    alpha = img.getchannel("A")

    # Blur the entire alpha channel
    blurred = alpha.filter(ImageFilter.GaussianBlur(radius))

    # Build a mask of "edge pixels": not fully opaque AND not fully transparent
    alpha_np = np.array(alpha)
    blurred_np = np.array(blurred)

    # Keep original alpha for fully opaque interior and fully transparent exterior.
    # Blend only at the transition zone.
    is_edge = (alpha_np > 0) & (alpha_np < 255)
    # Also include pixels that *became* partially transparent from the blur
    is_edge |= (blurred_np != alpha_np)

    result_alpha = np.where(is_edge, blurred_np, alpha_np)
    # Ensure we never *add* opacity where there was none
    result_alpha = np.minimum(result_alpha, alpha_np + 30).astype(np.uint8)

    img = img.copy()
    img.putalpha(Image.fromarray(result_alpha))
    return img


# ── Colour defringing ──

def defringe(img: Image.Image, radius: int = DEFRINGE_RADIUS) -> Image.Image:
    """Remove background colour bleed from edge pixels.

    Edge pixels often retain the original background's colour as a halo.
    We detect the edge band and replace each edge pixel's RGB with the
    average RGB of nearby *interior* (fully opaque) pixels, keeping alpha
    as-is.
    """
    arr = np.array(img, dtype=np.float32)  # H, W, 4
    alpha = arr[:, :, 3]

    # Edge pixels: partially transparent (1-254)
    edge_mask = (alpha > 0) & (alpha < 255)

    if not edge_mask.any():
        return img

    # Interior pixels: fully opaque
    interior_mask = alpha == 255

    # For each edge pixel, average the RGB of interior pixels within `radius`.
    # We do this efficiently with a box blur of the interior colours.
    interior_rgb = arr[:, :, :3].copy()
    interior_rgb[~interior_mask] = 0  # zero out non-interior

    count = np.zeros_like(alpha)
    count[interior_mask] = 1

    # Box-blur both the colour sum and the count
    kernel_size = radius * 2 + 1
    from PIL import ImageFilter

    for c in range(3):
        channel = Image.fromarray(interior_rgb[:, :, c].astype(np.uint8))
        blurred = channel.filter(ImageFilter.BoxBlur(radius))
        interior_rgb[:, :, c] = np.array(blurred, dtype=np.float32)

    count_img = Image.fromarray((count * 255).astype(np.uint8))
    count_blurred = np.array(
        count_img.filter(ImageFilter.BoxBlur(radius)), dtype=np.float32
    ) / 255.0

    # Avoid division by zero
    safe_count = np.maximum(count_blurred, 0.001)

    # Average interior colour in the neighbourhood
    avg_rgb = interior_rgb / safe_count[:, :, np.newaxis]
    avg_rgb = np.clip(avg_rgb, 0, 255)

    # Replace edge pixel RGB with the averaged interior colour
    result = arr.copy()
    for c in range(3):
        result[:, :, c] = np.where(edge_mask, avg_rgb[:, :, c], arr[:, :, c])

    return Image.fromarray(result.astype(np.uint8), "RGBA")


# ── White balance (auto-levels) ──

def auto_white_balance(img: Image.Image, clip_pct: float = WB_CLIP_PCT) -> Image.Image:
    """Normalise colour temperature by stretching each RGB channel's histogram.

    For each of R, G, B we find the *clip_pct* and *(100 - clip_pct)*
    percentiles among opaque pixels, then linearly stretch that range to
    0-255.  This removes colour casts from inconsistent studio lighting
    so shoes look cohesive side-by-side.

    Only opaque pixels (alpha > 0) contribute to the histogram — the
    transparent background is ignored.
    """
    arr = np.array(img)  # H, W, 4  uint8
    alpha = arr[:, :, 3]
    opaque = alpha > 0

    if not opaque.any():
        return img

    result = arr.copy()
    for c in range(3):
        channel = arr[:, :, c]
        values = channel[opaque]

        lo = np.percentile(values, clip_pct)
        hi = np.percentile(values, 100 - clip_pct)

        if hi - lo < 30:
            # Channel has a narrow range — stretching would blow it out
            continue

        if hi - lo > 200:
            # Channel already spans most of 0-255 — no correction needed
            continue

        stretched = (channel.astype(np.float32) - lo) / (hi - lo) * 255.0
        stretched = np.clip(stretched, 0, 255).astype(np.uint8)
        # Only apply to opaque pixels
        result[:, :, c] = np.where(opaque, stretched, channel)

    return Image.fromarray(result, "RGBA")


# ── Contrast boost ──

def boost_contrast(img: Image.Image, factor: float = CONTRAST_BOOST) -> Image.Image:
    """Apply a subtle S-curve contrast boost to make the shoe pop.

    Uses a simple midpoint-based linear contrast adjustment on opaque
    pixels only.  factor > 1 increases contrast, < 1 decreases.
    """
    arr = np.array(img, dtype=np.float32)
    alpha = arr[:, :, 3]
    opaque = alpha > 0

    if not opaque.any():
        return img

    for c in range(3):
        channel = arr[:, :, c]
        # Contrast around the channel's mean among opaque pixels
        mean = channel[opaque].mean()
        adjusted = (channel - mean) * factor + mean
        arr[:, :, c] = np.where(opaque, adjusted, channel)

    arr[:, :, :3] = np.clip(arr[:, :, :3], 0, 255)
    return Image.fromarray(arr.astype(np.uint8), "RGBA")


# ── Post-resize sharpening ──

def sharpen(
    img: Image.Image,
    amount: float = SHARPEN_AMOUNT,
    radius: float = SHARPEN_RADIUS,
) -> Image.Image:
    """Apply unsharp-mask sharpening to compensate for downscale softness.

    We blur, compute the difference from the original, and add back a
    fraction (*amount*) of that difference.  Only the RGB channels are
    sharpened — alpha is untouched.
    """
    if amount <= 0:
        return img

    # Separate alpha
    r, g, b, a = img.split()
    rgb = Image.merge("RGB", (r, g, b))

    # Unsharp mask: sharp = original + amount * (original - blurred)
    blurred = rgb.filter(ImageFilter.GaussianBlur(radius))

    rgb_np = np.array(rgb, dtype=np.float32)
    blur_np = np.array(blurred, dtype=np.float32)

    sharpened = rgb_np + amount * (rgb_np - blur_np)
    sharpened = np.clip(sharpened, 0, 255).astype(np.uint8)

    result = Image.fromarray(sharpened, "RGB")
    result.putalpha(a)
    return result


# ── Canvas fitting ──

def fit_to_canvas(
    img: Image.Image,
    canvas_w: int = CANVAS_W,
    canvas_h: int = CANVAS_H,
    max_w: int = MAX_SHOE_W,
    max_h: int = MAX_SHOE_H,
) -> Image.Image:
    """Place the shoe centred on a transparent canvas.

    The shoe is scaled to fit within *max_w* x *max_h* (preserving aspect
    ratio), then pasted in the centre of a *canvas_w* x *canvas_h* canvas.
    """
    # Crop to bounding box first (remove excess transparency)
    bbox = img.getchannel("A").getbbox()
    if bbox:
        img = img.crop(bbox)

    # Scale to fit within max dimensions
    w, h = img.size
    scale = min(max_w / w, max_h / h, 1.0)  # never upscale
    if scale < 1.0:
        new_w = int(w * scale)
        new_h = int(h * scale)
        img = img.resize((new_w, new_h), Image.LANCZOS)

    # Centre on canvas
    canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    x = (canvas_w - img.width) // 2
    y = (canvas_h - img.height) // 2
    canvas.paste(img, (x, y), img)
    return canvas


# ── Export ──

def export_webp(img: Image.Image, quality: int = WEBP_QUALITY) -> bytes:
    """Save as lossy WebP with alpha, return bytes."""
    buf = BytesIO()
    img.save(buf, format="WEBP", quality=quality, method=6)
    return buf.getvalue()


# ── Full pipeline ──

def process_pipeline(
    png_bytes: bytes,
    canvas_w: int = CANVAS_W,
    canvas_h: int = CANVAS_H,
    max_w: int = MAX_SHOE_W,
    max_h: int = MAX_SHOE_H,
    toe_direction: str = "right",
    quality: int = WEBP_QUALITY,
) -> bytes:
    """Run the complete post-processing pipeline on background-removed PNG bytes.

    Returns WebP bytes ready to save.

    Pipeline order:
    1. Defringe (remove background colour halo)
    2. Feather edges (soften alpha boundary)
    3. Auto white-balance (normalise colour temperature)
    4. Contrast boost (make the shoe pop)
    5. Auto-mirror (toe pointing target direction)
    6. Fit to canvas (scale + centre)
    7. Sharpen (compensate for downscale softness)
    8. Export as WebP
    """
    img = load_rgba(png_bytes)

    # ── Safe geometric/structural steps ──
    img = auto_mirror(img, target=toe_direction)
    img = fit_to_canvas(img, canvas_w, canvas_h, max_w, max_h)
    img = sharpen(img)

    return export_webp(img, quality)
