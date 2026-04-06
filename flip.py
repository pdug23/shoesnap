"""Flip a WebP image horizontally.

Usage: py flip.py path/to/shoe.webp
"""
import sys
from pathlib import Path
from PIL import Image

for arg in sys.argv[1:]:
    p = Path(arg)
    if not p.exists():
        print(f"Not found: {arg}")
        continue
    img = Image.open(p)
    img = img.transpose(Image.FLIP_LEFT_RIGHT)
    img.save(p, format="WEBP", quality=82, method=6)
    print(f"Flipped: {p.name}")
