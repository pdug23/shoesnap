# ShoeSnap

Scrape running shoe images, cut them out with AI, and export polished, web-ready WebP files — perfect for shoe cards, product catalogs, and comparison apps.

## Features

- **Web scraping mode** — Search Running Warehouse by shoe name, preview results in a grid, and batch-process selected images
- **Drag-and-drop mode** — Drop local images (PNG, JPG, WEBP, AVIF, TIFF, BMP) for one-by-one background removal with custom naming
- **AI background removal** — Uses [rembg](https://github.com/danielgatis/rembg) (U2Net) for clean cutouts
- **Shadow cleanup** — Removes floor shadows, reflections, and stray artifacts
- **Edge polish** — Alpha-edge feathering and colour defringing to eliminate harsh cutout artifacts
- **Auto white-balance** — Normalises colour temperature across different product photos
- **Contrast & sharpening** — Subtle contrast boost and post-resize unsharp mask so shoes pop on cards
- **Auto-mirror** — Detects toe direction and flips so all shoes face the same way (toe pointing right)
- **Standardised canvas** — Every output is 400 x 250 px with the shoe centred (max 350 x 200 px), so `<img>` tags use fixed dimensions and every shoe looks proportional
- **WebP export** — Lossy WebP with alpha at quality 82, targeting 40-80 KB per file
- **Cross-platform** — Works on Windows and macOS
- **Anti-detection scraping** — SeleniumBase UC Mode to handle bot protection

## Processing Pipeline

```
rembg background removal
  → shadow cleanup
    → colour defringe
      → edge feathering
        → white balance
          → contrast boost
            → auto-mirror (toe right)
              → fit to 400×250 canvas
                → sharpen
                  → WebP export
```

## Requirements

- Python 3.10+
- Windows or macOS

## Installation

```bash
git clone https://github.com/YOUR_USERNAME/shoesnap.git
cd shoesnap
pip install -r requirements.txt
```

> **Note:** The first run downloads the U2Net model (~170 MB). This is a one-time download.

## Usage

### Scraper + background removal workflow

```bash
python main.py
```

1. Enter shoe names (one per line) or edit `shoes.txt`
2. Click **Scrape Running Warehouse**
3. Select which shoes to process from the thumbnail grid
4. Click **Remove Backgrounds & Save WebPs**
5. Output goes to the `output/` folder

### Drag-and-drop background removal

```bash
python shoe_processor.py
```

1. Drag image files onto the window
2. Edit the suggested filename
3. Press **Process** (or Enter) to remove the background and save
4. Press **Skip** (or Escape) to skip an image

### Quick launch

- **Windows:** Double-click `run.bat`
- **macOS / Linux:** `./run.sh`

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Enter` | Process current image |
| `Escape` | Skip current image |
| `Ctrl+O` | Open output folder |
| `Ctrl+Q` | Quit |

## Output Spec

| Property | Value |
|----------|-------|
| Canvas size | 400 x 250 px |
| Shoe bounding box | Centred, max 350 x 200 px |
| Format | WebP (lossy + alpha) |
| Quality | 82 |
| Target file size | 40-80 KB |
| Toe direction | Right |
| Background | Transparent |

## Project Structure

```
shoesnap/
├── main.py                 # Entry point (scraper workflow)
├── shoe_processor.py       # Standalone drag-and-drop background remover
├── gui.py                  # Scraper workflow GUI (3-page stacked UI)
├── scraper.py              # Running Warehouse scraper (SeleniumBase UC Mode)
├── background_remover.py   # rembg wrapper with lazy loading
├── image_pipeline.py       # Post-processing pipeline (9-step)
├── worker.py               # QThread workers for async scraping/processing
├── requirements.txt        # Python dependencies
├── shoes.txt               # Default shoe search terms
├── run.bat                 # Windows launcher
└── run.sh                  # macOS / Linux launcher
```

## License

MIT
