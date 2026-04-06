"""ShoeSnap Image Fetcher — GUI tool for bulk downloading shoe images.

Usage:
    1. Put shoe names in shoes.txt (one per line)
    2. Run: python fetch_shoes.py
    3. For each shoe, pick the best image from the visual preview
    4. Images are saved to fetched/ with clean filenames
    5. Drag the fetched/ folder into ShoeSnap to process
"""

import re
import sys
import time
import random
from io import BytesIO
from pathlib import Path
from urllib.parse import quote_plus

import requests
from PIL import Image

from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt5.QtGui import QPixmap, QImage, QFont, QPalette, QColor
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QProgressBar, QScrollArea, QFrame,
    QSizePolicy, QMessageBox,
)

FETCH_DIR = Path(__file__).parent / "fetched"
DEFAULT_LIST = Path(__file__).parent / "shoes.txt"

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

# Platform fonts
if sys.platform == "darwin":
    FONT_UI = "SF Pro Text"
    FONT_MONO = "Menlo"
else:
    FONT_UI = "Segoe UI"
    FONT_MONO = "Consolas"

# Theme
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
    return name[:200] if name else "shoe"


def extract_image_urls(html: str, max_results: int = 8) -> list[str]:
    urls = []
    patterns = [
        r'"(https?://[^"]+\.(?:jpg|jpeg|png|webp)(?:\?[^"]*)?)"',
        r'\["(https?://[^"]+\.(?:jpg|jpeg|png|webp)(?:\?[^"]*)?)"',
    ]
    seen = set()
    for pattern in patterns:
        for match in re.finditer(pattern, html, re.IGNORECASE):
            url = match.group(1)
            if any(skip in url for skip in ["gstatic.com", "google.com", "googleapis.com"]):
                continue
            if any(dim in url.lower() for dim in ['=s64', '=s72', '=s96', '=s128', 'favicon']):
                continue
            if url in seen:
                continue
            seen.add(url)
            urls.append(url)
            if len(urls) >= max_results:
                return urls
    return urls


def download_image(url: str, timeout: int = 15) -> bytes | None:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout)
        resp.raise_for_status()
        content_type = resp.headers.get("Content-Type", "")
        if "image" not in content_type and "octet-stream" not in content_type:
            return None
        data = resp.content
        if len(data) < 5000:
            return None
        return data
    except Exception:
        return None


# ── Search worker (runs in background thread) ──

class SearchWorker(QThread):
    """Search for a shoe and download candidate images."""
    finished = pyqtSignal(str, list)  # shoe_name, list of (bytes, width, height, source)
    progress = pyqtSignal(str)

    def __init__(self, shoe_name: str):
        super().__init__()
        self.shoe_name = shoe_name

    def run(self):
        self.progress.emit(f"Searching for {self.shoe_name}...")
        query = f"{self.shoe_name} running shoe side view"
        url = SEARCH_URL.format(quote_plus(query))

        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            urls = extract_image_urls(resp.text)
        except Exception as e:
            self.progress.emit(f"Search failed: {e}")
            self.finished.emit(self.shoe_name, [])
            return

        candidates = []
        for i, img_url in enumerate(urls[:6]):
            self.progress.emit(f"Downloading image {i + 1}/{min(len(urls), 6)}...")
            data = download_image(img_url)
            if data:
                try:
                    img = Image.open(BytesIO(data))
                    w, h = img.size
                except Exception:
                    w, h = 0, 0
                domain = re.search(r'https?://([^/]+)', img_url)
                source = domain.group(1) if domain else "unknown"
                candidates.append((data, w, h, source))

        self.finished.emit(self.shoe_name, candidates)


# ── Image candidate card ──

class ImageCard(QFrame):
    """Clickable image preview card."""
    clicked = pyqtSignal(int)

    def __init__(self, index: int, data: bytes, width: int, height: int, source: str):
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

        # Image preview
        self.image_label = QLabel()
        self.image_label.setFixedSize(220, 160)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet(f"background-color: #ffffff; border: 1px solid {BG_LIGHTER};")

        qimg = QImage.fromData(data)
        if not qimg.isNull():
            pixmap = QPixmap.fromImage(qimg)
            scaled = pixmap.scaled(220, 160, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.image_label.setPixmap(scaled)
        else:
            self.image_label.setText("Failed")

        layout.addWidget(self.image_label, alignment=Qt.AlignCenter)

        # Info
        size_kb = len(data) / 1024
        info = QLabel(f"{width}x{height}  |  {size_kb:.0f}KB")
        info.setAlignment(Qt.AlignCenter)
        info.setFont(QFont(FONT_MONO, 9))
        info.setStyleSheet(f"color: {TEXT_DIM}; border: none;")
        layout.addWidget(info)

        source_label = QLabel(source)
        source_label.setAlignment(Qt.AlignCenter)
        source_label.setFont(QFont(FONT_UI, 8))
        source_label.setStyleSheet(f"color: {TEXT_DIM}; border: none;")
        layout.addWidget(source_label)

    def _update_style(self):
        if self._selected:
            self.setStyleSheet(f"ImageCard {{ border: 2px solid {GREEN}; background-color: {BG_LIGHT}; border-radius: 8px; }}")
        else:
            self.setStyleSheet(f"ImageCard {{ border: 2px solid {BG_LIGHTER}; background-color: {BG_LIGHT}; border-radius: 8px; }}")

    def set_selected(self, selected: bool):
        self._selected = selected
        self._update_style()

    def mousePressEvent(self, event):
        self.clicked.emit(self.index)


# ── Main window ──

class FetcherWindow(QMainWindow):
    def __init__(self, shoe_names: list[str]):
        super().__init__()
        self.setWindowTitle("ShoeSnap Image Fetcher")
        self.setMinimumSize(900, 600)
        self.resize(1000, 650)

        self.shoe_names = shoe_names
        self.current_index = -1
        self.candidates = []  # list of (bytes, w, h, source)
        self.cards: list[ImageCard] = []
        self.selected_card = -1
        self.worker = None

        self.fetched = 0
        self.skipped = 0
        self.failed = 0

        FETCH_DIR.mkdir(exist_ok=True)

        self._build_ui()
        self._apply_theme()
        self._advance()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        # Header
        header = QHBoxLayout()
        self.title_label = QLabel("ShoeSnap Image Fetcher")
        self.title_label.setFont(QFont(FONT_UI, 16, QFont.Bold))
        header.addWidget(self.title_label)
        header.addStretch()

        self.counter_label = QLabel("")
        self.counter_label.setFont(QFont(FONT_UI, 12))
        self.counter_label.setStyleSheet(f"color: {TEXT_DIM};")
        header.addWidget(self.counter_label)
        layout.addLayout(header)

        # Current shoe name
        self.shoe_label = QLabel("")
        self.shoe_label.setFont(QFont(FONT_UI, 20, QFont.Bold))
        self.shoe_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.shoe_label)

        # Status
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setFont(QFont(FONT_UI, 10))
        self.status_label.setStyleSheet(f"color: {TEXT_DIM};")
        layout.addWidget(self.status_label)

        # Scrollable image grid
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setMinimumHeight(280)
        self.grid_container = QWidget()
        self.grid_layout = QHBoxLayout(self.grid_container)
        self.grid_layout.setSpacing(10)
        self.grid_layout.setContentsMargins(8, 8, 8, 8)
        self.grid_layout.addStretch()
        self.scroll.setWidget(self.grid_container)
        layout.addWidget(self.scroll)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.skip_btn = QPushButton("Skip")
        self.skip_btn.setFont(QFont(FONT_UI, 11))
        self.skip_btn.setMinimumHeight(40)
        self.skip_btn.setMinimumWidth(100)
        self.skip_btn.clicked.connect(self._skip)
        btn_row.addWidget(self.skip_btn)

        btn_row.addStretch()

        self.use_btn = QPushButton("Use This Image")
        self.use_btn.setFont(QFont(FONT_UI, 12, QFont.Bold))
        self.use_btn.setMinimumHeight(40)
        self.use_btn.setMinimumWidth(180)
        self.use_btn.setEnabled(False)
        self.use_btn.clicked.connect(self._use_selected)
        btn_row.addWidget(self.use_btn)

        layout.addLayout(btn_row)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setRange(0, len(self.shoe_names))
        layout.addWidget(self.progress_bar)

    def _apply_theme(self):
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{
                background-color: {BG};
                color: {TEXT};
            }}
            QScrollArea {{
                border: 1px solid {BG_LIGHTER};
                border-radius: 8px;
                background-color: {BG};
            }}
            QPushButton {{
                background-color: {ACCENT};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
            }}
            QPushButton:hover {{
                background-color: #2563eb;
            }}
            QPushButton:disabled {{
                background-color: {BG_LIGHTER};
                color: {TEXT_DIM};
            }}
            QPushButton#skipBtn {{
                background-color: {BG_LIGHTER};
                color: {TEXT};
            }}
            QPushButton#skipBtn:hover {{
                background-color: #4a4a4a;
            }}
            QProgressBar {{
                background-color: {BG_LIGHT};
                border: none;
                border-radius: 3px;
            }}
            QProgressBar::chunk {{
                background-color: {ACCENT};
                border-radius: 3px;
            }}
        """)
        self.skip_btn.setObjectName("skipBtn")
        self.skip_btn.setStyle(self.skip_btn.style())

    def _clear_grid(self):
        self.cards.clear()
        self.selected_card = -1
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.grid_layout.addStretch()

    def _advance(self):
        self.current_index += 1
        self.progress_bar.setValue(self.current_index)

        if self.current_index >= len(self.shoe_names):
            self._show_complete()
            return

        name = self.shoe_names[self.current_index]
        filename = sanitize_filename(name)
        out_path = FETCH_DIR / f"{filename}.jpg"

        # Skip if already fetched
        if out_path.exists():
            self.skipped += 1
            self._advance()
            return

        self.shoe_label.setText(name)
        self.counter_label.setText(f"{self.current_index + 1} / {len(self.shoe_names)}")
        self.status_label.setText("Searching...")
        self.status_label.setStyleSheet(f"color: {ORANGE};")
        self.use_btn.setEnabled(False)
        self.skip_btn.setEnabled(False)
        self._clear_grid()

        # Start search
        self.worker = SearchWorker(name)
        self.worker.progress.connect(self._on_search_progress)
        self.worker.finished.connect(self._on_search_done)
        self.worker.start()

    def _on_search_progress(self, msg: str):
        self.status_label.setText(msg)

    def _on_search_done(self, shoe_name: str, candidates: list):
        self.candidates = candidates
        self._clear_grid()

        if not candidates:
            self.status_label.setText("No images found")
            self.status_label.setStyleSheet(f"color: {RED};")
            self.skip_btn.setEnabled(True)
            return

        self.status_label.setText(f"Click an image to select it")
        self.status_label.setStyleSheet(f"color: {TEXT_DIM};")

        # Remove the trailing stretch before adding cards
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)

        for i, (data, w, h, source) in enumerate(candidates):
            card = ImageCard(i, data, w, h, source)
            card.clicked.connect(self._on_card_clicked)
            self.cards.append(card)
            self.grid_layout.addWidget(card)

        self.grid_layout.addStretch()
        self.skip_btn.setEnabled(True)

    def _on_card_clicked(self, index: int):
        self.selected_card = index
        for i, card in enumerate(self.cards):
            card.set_selected(i == index)
        self.use_btn.setEnabled(True)

    def _use_selected(self):
        if self.selected_card < 0 or self.selected_card >= len(self.candidates):
            return

        data = self.candidates[self.selected_card][0]
        name = self.shoe_names[self.current_index]
        filename = sanitize_filename(name)
        out_path = FETCH_DIR / f"{filename}.jpg"
        out_path.write_bytes(data)

        self.status_label.setText(f"Saved: {filename}.jpg")
        self.status_label.setStyleSheet(f"color: {GREEN};")
        self.fetched += 1

        # Brief pause so user sees the "Saved" message
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(300, self._advance)

    def _skip(self):
        self.failed += 1
        self._advance()

    def _show_complete(self):
        self._clear_grid()
        self.shoe_label.setText("All done!")
        self.counter_label.setText("")
        self.status_label.setText(
            f"Fetched: {self.fetched}  |  Skipped (already had): {self.skipped}  |  Skipped: {self.failed}"
        )
        self.status_label.setStyleSheet(f"color: {GREEN};")
        self.use_btn.setVisible(False)
        self.skip_btn.setText("Close")
        self.skip_btn.setEnabled(True)
        self.skip_btn.clicked.disconnect()
        self.skip_btn.clicked.connect(self.close)
        self.progress_bar.setValue(len(self.shoe_names))


def main():
    list_file = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_LIST

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

    window = FetcherWindow(shoe_names)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
