"""ShoeSnap Logo Fetcher — GUI tool for downloading brand logos.

Usage:
    1. Put brand names in brands.txt (one per line)
    2. Run: python fetch_logos.py
    3. Click the best logo for each brand
    4. Logos are saved to logos_raw/ then processed to logos/
"""

import re
import sys
from io import BytesIO
from pathlib import Path
from urllib.parse import quote_plus
from html import unescape
from urllib.parse import unquote

import requests
import numpy as np
from PIL import Image

from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QPixmap, QImage, QFont, QPalette, QColor
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QProgressBar, QScrollArea, QFrame,
)

from logo_pipeline import process_logo, process_logo_svg, is_svg

_PIPELINE_DIR = Path(__file__).resolve().parent       # logos/pipeline/
_LOGOS_DIR = _PIPELINE_DIR.parent                     # logos/
_REPO_DIR = _LOGOS_DIR.parent                         # repo root
LOGOS_RAW_DIR = _LOGOS_DIR / "raw"
LOGOS_DIR = _LOGOS_DIR / "processed"
DEFAULT_LIST = _REPO_DIR / "brands.txt"

SEARCH_URL = "https://www.bing.com/images/search?q={}&qft=+filterui:imagesize-large+filterui:photo-transparent&form=IRFLTR&first=1"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

if sys.platform == "darwin":
    FONT_UI = "SF Pro Text"
    FONT_MONO = "Menlo"
else:
    FONT_UI = "Segoe UI"
    FONT_MONO = "Consolas"

BG = "#1e1e1e"
BG_LIGHT = "#2d2d2d"
BG_LIGHTER = "#3a3a3a"
TEXT = "#e0e0e0"
TEXT_DIM = "#888888"
ACCENT = "#3b82f6"
GREEN = "#22c55e"
RED = "#ef4444"
ORANGE = "#f59e0b"


def sanitize_filename(name: str) -> str:
    name = name.lower().strip()
    name = re.sub(r'[®™©]', '', name)
    name = re.sub(r'[\s_\.]+', '-', name)
    name = re.sub(r'[^a-z0-9\-]', '', name)
    name = re.sub(r'-{2,}', '-', name)
    name = name.strip('-')
    return name[:200] if name else "brand"


def extract_image_urls(html: str, max_results: int = 10) -> list[str]:
    decoded = unescape(html)
    urls = []
    seen = set()
    for match in re.finditer(r'"murl"\s*:\s*"(https?://[^"]+)"', decoded):
        url = unquote(match.group(1))
        if url in seen:
            continue
        if "bing.com" in url or "microsoft.com" in url:
            continue
        seen.add(url)
        urls.append(url)
        if len(urls) >= max_results:
            break
    return urls


def download_image(url: str, timeout: int = 15) -> bytes | None:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout)
        resp.raise_for_status()
        content_type = resp.headers.get("Content-Type", "")
        if not any(t in content_type for t in ["image", "octet-stream", "svg"]):
            return None
        data = resp.content
        if len(data) < 500:
            return None
        return data
    except Exception:
        return None


def _parse_svg_dimensions(data: bytes) -> tuple[int, int]:
    """Try to extract width/height from an SVG's viewBox or attributes."""
    try:
        text = data.decode("utf-8", errors="ignore")
        # Try viewBox first
        vb = re.search(r'viewBox\s*=\s*"([^"]+)"', text)
        if vb:
            parts = vb.group(1).replace(',', ' ').split()
            if len(parts) == 4:
                return int(float(parts[2])), int(float(parts[3]))
        # Try width/height attributes
        w_m = re.search(r'width\s*=\s*"([\d.]+)', text)
        h_m = re.search(r'height\s*=\s*"([\d.]+)', text)
        if w_m and h_m:
            return int(float(w_m.group(1))), int(float(h_m.group(1)))
    except Exception:
        pass
    return 0, 0


# ── Logo scoring ──

def score_logo(data: bytes, w: int, h: int, source: str, url: str) -> float:
    """Score how likely an image is to be a clean brand logo."""
    score = 0.0

    # SVGs get a massive bonus — they're always preferred
    if is_svg(data):
        score += 50

    if w == 0 or h == 0:
        if is_svg(data):
            return score + 20  # SVG without parsed dimensions is still good
        return -100

    # ── Aspect ratio: logos are typically landscape or square ──
    ratio = w / h
    if 1.0 <= ratio <= 5.0:
        score += 15
    elif ratio < 0.5 or ratio > 8.0:
        score -= 20

    # ── Transparency: logos on transparent backgrounds are best ──
    try:
        img = Image.open(BytesIO(data)).convert("RGBA")
        arr = np.array(img)
        alpha = arr[:, :, 3]
        transparent_pct = (alpha < 10).sum() / alpha.size
        # Good logos on transparent bg have lots of transparent pixels
        if transparent_pct > 0.5:
            score += 30  # mostly transparent = clean logo
        elif transparent_pct > 0.2:
            score += 15
        # Very few transparent pixels = probably has a background
        elif transparent_pct < 0.05:
            score -= 10

        # ── Simplicity: logos should have relatively few unique colours ──
        opaque = alpha > 128
        if opaque.any():
            rgb = arr[:, :, :3][opaque]
            # Sample up to 1000 pixels for speed
            sample = rgb[::max(1, len(rgb) // 1000)]
            unique_approx = len(np.unique(sample // 32, axis=0))
            if unique_approx < 20:
                score += 15  # simple colour palette
            elif unique_approx > 100:
                score -= 10  # too complex, probably a photo

    except Exception:
        pass

    # ── Resolution: prefer reasonable sizes, not massive ──
    pixels = w * h
    if 10_000 <= pixels <= 4_000_000:
        score += 10
    elif pixels > 4_000_000:
        score += 5  # usable but large

    # ── URL hints ──
    url_lower = url.lower()
    if "logo" in url_lower:
        score += 10
    if "svg" in url_lower:
        score += 15
    if any(bad in url_lower for bad in ["shoe", "product", "runner", "photo", "lifestyle"]):
        score -= 20

    # ── Source domain hints ──
    source_lower = source.lower()
    if any(good in source_lower for good in ["wikipedia", "wikimedia", "worldvectorlogo", "brandsoftheworld", "logos-world"]):
        score += 15

    return score


# ── Search worker ──

class SearchWorker(QThread):
    finished = pyqtSignal(str, list)
    progress = pyqtSignal(str)

    def __init__(self, brand_name: str):
        super().__init__()
        self.brand_name = brand_name

    def run(self):
        all_urls = []

        # Search 1: SVG logos (preferred)
        self.progress.emit(f"Searching for {self.brand_name} SVG logo...")
        svg_query = f"{self.brand_name} logo SVG vector"
        try:
            resp = requests.get(SEARCH_URL.format(quote_plus(svg_query)), headers=HEADERS, timeout=15)
            resp.raise_for_status()
            all_urls.extend(extract_image_urls(resp.text, max_results=8))
        except Exception:
            pass

        # Search 2: transparent PNG logos (fallback)
        self.progress.emit(f"Searching for {self.brand_name} transparent logo...")
        png_query = f"{self.brand_name} logo transparent PNG"
        try:
            resp = requests.get(SEARCH_URL.format(quote_plus(png_query)), headers=HEADERS, timeout=15)
            resp.raise_for_status()
            # Deduplicate
            existing = set(all_urls)
            for u in extract_image_urls(resp.text, max_results=8):
                if u not in existing:
                    all_urls.append(u)
                    existing.add(u)
        except Exception:
            pass

        urls = all_urls
        if not urls:
            self.progress.emit("No logos found")
            self.finished.emit(self.brand_name, [])
            return

        candidates = []
        for i, img_url in enumerate(urls):
            self.progress.emit(f"Downloading {i + 1}/{len(urls)}...")
            data = download_image(img_url)
            if data:
                if is_svg(data):
                    # SVG — try to extract dimensions from viewBox/width/height
                    w, h = _parse_svg_dimensions(data)
                else:
                    try:
                        img = Image.open(BytesIO(data))
                        w, h = img.size
                    except Exception:
                        continue
                domain = re.search(r'https?://([^/]+)', img_url)
                source = domain.group(1) if domain else "unknown"
                sc = score_logo(data, w, h, source, img_url)
                candidates.append((data, w, h, source, sc))

        candidates.sort(key=lambda c: c[4], reverse=True)
        self.finished.emit(self.brand_name, candidates[:8])


# ── Logo card ──

class LogoCard(QFrame):
    clicked = pyqtSignal(int)

    def __init__(self, index: int, data: bytes, width: int, height: int, source: str, score: float = 0):
        super().__init__()
        self.index = index
        self.data = data
        self.setCursor(Qt.PointingHandCursor)
        self.setFrameStyle(QFrame.Box)
        self.setLineWidth(2)
        self._selected = False
        self._update_style()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        # Image preview — checkerboard background to show transparency
        self.image_label = QLabel()
        self.image_label.setFixedSize(180, 100)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet(
            "background-color: #ffffff; border: 1px solid #555;"
        )

        self.is_svg = is_svg(data)
        qimg = QImage.fromData(data)
        if not qimg.isNull():
            pixmap = QPixmap.fromImage(qimg)
            scaled = pixmap.scaled(180, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.image_label.setPixmap(scaled)
        elif self.is_svg:
            self.image_label.setText("SVG (preview N/A)")
            self.image_label.setStyleSheet("background-color: #333; border: 1px solid #555; color: #aaa;")
        else:
            self.image_label.setText("Failed")

        layout.addWidget(self.image_label, alignment=Qt.AlignCenter)

        fmt = "SVG" if self.is_svg else "PNG"
        dim_str = f"{width}x{height}" if width > 0 else "vector"
        info = QLabel(f"{fmt}  |  {dim_str}")
        info.setAlignment(Qt.AlignCenter)
        info.setFont(QFont(FONT_MONO, 9))
        info.setStyleSheet(f"color: {TEXT_DIM}; border: none;")
        layout.addWidget(info)

        source_label = QLabel(source[:30])
        source_label.setAlignment(Qt.AlignCenter)
        source_label.setFont(QFont(FONT_UI, 8))
        source_label.setStyleSheet(f"color: {TEXT_DIM}; border: none;")
        layout.addWidget(source_label)

    def _update_style(self):
        if self._selected:
            self.setStyleSheet(f"LogoCard {{ border: 2px solid {GREEN}; background-color: {BG_LIGHT}; border-radius: 8px; }}")
        else:
            self.setStyleSheet(f"LogoCard {{ border: 2px solid {BG_LIGHTER}; background-color: {BG_LIGHT}; border-radius: 8px; }}")

    def set_selected(self, selected: bool):
        self._selected = selected
        self._update_style()

    def mousePressEvent(self, event):
        self.clicked.emit(self.index)


# ── Main window ──

class FetcherWindow(QMainWindow):
    def __init__(self, brand_names: list[str]):
        super().__init__()
        self.setWindowTitle("ShoeSnap Logo Fetcher")
        self.setMinimumSize(900, 500)
        self.resize(1000, 550)

        self.brand_names = brand_names
        self.current_index = -1
        self.candidates = []
        self.cards: list[LogoCard] = []
        self.worker = None

        self.prefetch_cache: dict[int, list] = {}
        self.prefetch_in_flight: set[int] = set()
        self.prefetch_workers: list[SearchWorker] = []
        self.PREFETCH_AHEAD = 3

        self.fetched = 0
        self.skipped = 0
        self.failed = 0

        LOGOS_RAW_DIR.mkdir(exist_ok=True)
        LOGOS_DIR.mkdir(exist_ok=True)

        self._build_ui()
        self._apply_theme()
        self._prefetch_ahead()
        self._advance()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("ShoeSnap Logo Fetcher")
        title.setFont(QFont(FONT_UI, 16, QFont.Bold))
        header.addWidget(title)
        header.addStretch()
        self.counter_label = QLabel("")
        self.counter_label.setFont(QFont(FONT_UI, 12))
        self.counter_label.setStyleSheet(f"color: {TEXT_DIM};")
        header.addWidget(self.counter_label)
        layout.addLayout(header)

        self.brand_label = QLabel("")
        self.brand_label.setFont(QFont(FONT_UI, 20, QFont.Bold))
        self.brand_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.brand_label)

        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setFont(QFont(FONT_UI, 10))
        self.status_label.setStyleSheet(f"color: {TEXT_DIM};")
        layout.addWidget(self.status_label)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setMinimumHeight(200)
        self.grid_container = QWidget()
        self.grid_layout = QHBoxLayout(self.grid_container)
        self.grid_layout.setSpacing(10)
        self.grid_layout.setContentsMargins(8, 8, 8, 8)
        self.grid_layout.addStretch()
        self.scroll.setWidget(self.grid_container)
        layout.addWidget(self.scroll)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.restart_btn = QPushButton("Restart")
        self.restart_btn.setFont(QFont(FONT_UI, 11))
        self.restart_btn.setMinimumHeight(36)
        self.restart_btn.clicked.connect(self._restart)
        btn_row.addWidget(self.restart_btn)

        self.back_btn = QPushButton("Back")
        self.back_btn.setFont(QFont(FONT_UI, 11))
        self.back_btn.setMinimumHeight(36)
        self.back_btn.clicked.connect(self._go_back)
        btn_row.addWidget(self.back_btn)

        self.skip_btn = QPushButton("Skip")
        self.skip_btn.setFont(QFont(FONT_UI, 11))
        self.skip_btn.setMinimumHeight(36)
        self.skip_btn.clicked.connect(self._skip)
        btn_row.addWidget(self.skip_btn)

        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setRange(0, len(self.brand_names))
        layout.addWidget(self.progress_bar)

    def _apply_theme(self):
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{ background-color: {BG}; color: {TEXT}; }}
            QScrollArea {{ border: 1px solid {BG_LIGHTER}; border-radius: 8px; background-color: {BG}; }}
            QPushButton {{ background-color: {BG_LIGHTER}; color: {TEXT}; border: none; border-radius: 6px; padding: 8px 20px; }}
            QPushButton:hover {{ background-color: #4a4a4a; }}
            QPushButton:disabled {{ background-color: {BG_LIGHTER}; color: {TEXT_DIM}; }}
            QProgressBar {{ background-color: {BG_LIGHT}; border: none; border-radius: 3px; }}
            QProgressBar::chunk {{ background-color: {ACCENT}; border-radius: 3px; }}
        """)

    def _clear_grid(self):
        self.cards.clear()
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.grid_layout.addStretch()

    def _prefetch_ahead(self):
        idx = self.current_index + 1
        launched = 0
        while launched < self.PREFETCH_AHEAD and idx < len(self.brand_names):
            filename = sanitize_filename(self.brand_names[idx])
            if (LOGOS_DIR / f"{filename}-logo.svg").exists() or (LOGOS_DIR / f"{filename}-logo.webp").exists():
                idx += 1
                continue
            if idx in self.prefetch_cache or idx in self.prefetch_in_flight:
                launched += 1
                idx += 1
                continue
            self.prefetch_in_flight.add(idx)
            name = self.brand_names[idx]
            worker = SearchWorker(name)
            pi = idx
            worker.finished.connect(
                lambda sn, cands, pi=pi: self._on_prefetch_done(pi, cands)
            )
            worker.start()
            self.prefetch_workers.append(worker)
            launched += 1
            idx += 1

    def _on_prefetch_done(self, index: int, candidates: list):
        self.prefetch_cache[index] = candidates
        self.prefetch_in_flight.discard(index)
        self._prefetch_ahead()

    def _show_brand(self, index: int):
        self.current_index = index
        self.progress_bar.setValue(self.current_index)

        if self.current_index >= len(self.brand_names):
            self._show_complete()
            return

        name = self.brand_names[self.current_index]
        filename = sanitize_filename(name)

        if (LOGOS_DIR / f"{filename}-logo.svg").exists() or (LOGOS_DIR / f"{filename}-logo.webp").exists():
            self.skipped += 1
            self._show_brand(self.current_index + 1)
            return

        self.brand_label.setText(name)
        self.counter_label.setText(f"{self.current_index + 1} / {len(self.brand_names)}")
        self.skip_btn.setEnabled(False)
        self.back_btn.setEnabled(self.current_index > 0)
        self._clear_grid()

        if self.current_index in self.prefetch_cache:
            cached = self.prefetch_cache.pop(self.current_index)
            self._on_search_done(name, cached)
            return

        self.status_label.setText("Searching...")
        self.status_label.setStyleSheet(f"color: {ORANGE};")

        self.worker = SearchWorker(name)
        self.worker.progress.connect(lambda msg: self.status_label.setText(msg))
        self.worker.finished.connect(self._on_search_done)
        self.worker.start()

    def _advance(self):
        self._show_brand(self.current_index + 1)

    def _on_search_done(self, brand_name: str, candidates: list):
        self.candidates = candidates
        self._clear_grid()

        if not candidates:
            self.status_label.setText("No logos found")
            self.status_label.setStyleSheet(f"color: {RED};")
            self.skip_btn.setEnabled(True)
            self.back_btn.setEnabled(self.current_index > 0)
            self._prefetch_ahead()
            return

        self.status_label.setText("Click a logo to save it  |  Sorted best → worst")
        self.status_label.setStyleSheet(f"color: {TEXT_DIM};")

        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)

        for i, (data, w, h, source, sc) in enumerate(candidates):
            card = LogoCard(i, data, w, h, source, sc)
            card.clicked.connect(self._on_card_clicked)
            self.cards.append(card)
            self.grid_layout.addWidget(card)

        self.grid_layout.addStretch()
        self.skip_btn.setEnabled(True)
        self.back_btn.setEnabled(self.current_index > 0)
        self._prefetch_ahead()

    def _on_card_clicked(self, index: int):
        if index < 0 or index >= len(self.candidates):
            return

        for i, card in enumerate(self.cards):
            card.set_selected(i == index)

        data = self.candidates[index][0]
        name = self.brand_names[self.current_index]
        filename = sanitize_filename(name)

        # Save raw
        raw_ext = "svg" if is_svg(data) else "png"
        raw_path = LOGOS_RAW_DIR / f"{filename}-logo-raw.{raw_ext}"
        raw_path.write_bytes(data)

        # Process through pipeline and save
        try:
            if is_svg(data):
                # SVG → processed SVG
                svg_str = process_logo_svg(data)
                out_path = LOGOS_DIR / f"{filename}-logo.svg"
                out_path.write_text(svg_str, encoding="utf-8")
                self.status_label.setText(f"Saved: {filename}-logo.svg")
            else:
                # Bitmap → processed WebP
                processed = process_logo(data)
                out_path = LOGOS_DIR / f"{filename}-logo.webp"
                out_path.write_bytes(processed)
                self.status_label.setText(f"Saved: {filename}-logo.webp")
            self.status_label.setStyleSheet(f"color: {GREEN};")
        except Exception as e:
            self.status_label.setText(f"Processing failed: {e}")
            self.status_label.setStyleSheet(f"color: {RED};")

        self.fetched += 1

        for card in self.cards:
            card.setEnabled(False)
        self.skip_btn.setEnabled(False)

        QTimer.singleShot(400, self._advance)

    def _skip(self):
        self.failed += 1
        self._advance()

    def _go_back(self):
        if self.current_index <= 0:
            return
        prev_idx = self.current_index - 1
        filename = sanitize_filename(self.brand_names[prev_idx])
        for path in [
            LOGOS_DIR / f"{filename}-logo.webp",
            LOGOS_RAW_DIR / f"{filename}-logo-raw.png",
        ]:
            if path.exists():
                path.unlink()
        self.fetched = max(0, self.fetched - 1)
        self._show_brand(prev_idx)

    def _restart(self):
        self.current_index = -1
        self.prefetch_cache.clear()
        self.prefetch_in_flight.clear()
        self._prefetch_ahead()
        self._advance()

    def _show_complete(self):
        self._clear_grid()
        self.brand_label.setText("All done!")
        self.counter_label.setText("")
        self.status_label.setText(
            f"Fetched: {self.fetched}  |  Already had: {self.skipped}  |  Skipped: {self.failed}"
        )
        self.status_label.setStyleSheet(f"color: {GREEN};")
        self.skip_btn.setText("Close")
        self.skip_btn.setEnabled(True)
        self.skip_btn.clicked.disconnect()
        self.skip_btn.clicked.connect(self.close)
        self.back_btn.setEnabled(False)
        self.progress_bar.setValue(len(self.brand_names))


def main():
    list_file = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_LIST

    if not list_file.exists():
        print(f"Brand list not found: {list_file}")
        sys.exit(1)

    brand_names = [
        line.strip()
        for line in list_file.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]

    if not brand_names:
        print("No brand names found.")
        sys.exit(1)

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(BG))
    palette.setColor(QPalette.WindowText, QColor(TEXT))
    palette.setColor(QPalette.Base, QColor(BG_LIGHT))
    palette.setColor(QPalette.Text, QColor(TEXT))
    palette.setColor(QPalette.Button, QColor(BG_LIGHTER))
    palette.setColor(QPalette.ButtonText, QColor(TEXT))
    palette.setColor(QPalette.Highlight, QColor(ACCENT))
    app.setPalette(palette)

    window = FetcherWindow(brand_names)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
