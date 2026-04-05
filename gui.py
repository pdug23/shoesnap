"""PyQt5 GUI for the shoe image processor."""

import os
import subprocess
import sys

# Platform-appropriate fonts
if sys.platform == "darwin":
    FONT_UI = "SF Pro Text"
    FONT_MONO = "Menlo"
else:
    FONT_UI = "Segoe UI"
    FONT_MONO = "Consolas"
from pathlib import Path

from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QPixmap, QImage, QFont, QIcon
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QTextEdit, QProgressBar, QScrollArea,
    QCheckBox, QStackedWidget, QFrame, QMessageBox, QFileDialog,
    QSizePolicy, QApplication,
)

from scraper import ShoeResult
from worker import ScrapeWorker, ProcessWorker

THUMB_SIZE = 160
GRID_COLS = 5
OUTPUT_DIR = Path(__file__).parent / "output"


class ShoeCard(QFrame):
    """A single shoe thumbnail card with checkbox."""

    def __init__(self, shoe: ShoeResult, parent=None):
        super().__init__(parent)
        self.shoe = shoe
        self.setFrameStyle(QFrame.Box | QFrame.Raised)
        self.setLineWidth(1)
        self.setFixedSize(THUMB_SIZE + 20, THUMB_SIZE + 60)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(3)

        # Thumbnail
        self.image_label = QLabel()
        self.image_label.setFixedSize(THUMB_SIZE, THUMB_SIZE)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("background-color: #f0f0f0; border: 1px solid #ddd;")

        if shoe.thumbnail:
            self._set_thumbnail(shoe.thumbnail)
        else:
            self.image_label.setText("No image")

        layout.addWidget(self.image_label, alignment=Qt.AlignCenter)

        # Name label
        name = shoe.product_name or shoe.search_term
        name_label = QLabel(name)
        name_label.setWordWrap(True)
        name_label.setMaximumHeight(30)
        name_label.setAlignment(Qt.AlignCenter)
        name_label.setStyleSheet("font-size: 10px;")
        name_label.setToolTip(name)
        layout.addWidget(name_label)

        # Checkbox
        self.checkbox = QCheckBox("Select")
        self.checkbox.setChecked(True)
        layout.addWidget(self.checkbox, alignment=Qt.AlignCenter)

    def _set_thumbnail(self, data: bytes):
        img = QImage.fromData(data)
        if not img.isNull():
            pixmap = QPixmap.fromImage(img)
            scaled = pixmap.scaled(THUMB_SIZE, THUMB_SIZE, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.image_label.setPixmap(scaled)

    def is_selected(self) -> bool:
        return self.checkbox.isChecked()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ShoeSnap — Running Warehouse Scraper")
        self.setMinimumSize(950, 700)
        self.resize(1100, 800)

        self.shoe_cards: list[ShoeCard] = []
        self.all_results: list[ShoeResult] = []
        self.scrape_worker = None
        self.process_worker = None

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        self.stack = QStackedWidget()
        main_layout.addWidget(self.stack)

        self._build_input_page()
        self._build_selection_page()
        self._build_processing_page()

        self.stack.setCurrentIndex(0)

    # ── Page 1: Input ──

    def _build_input_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(12)

        title = QLabel("ShoeSnap")
        title.setFont(QFont(FONT_UI, 18, QFont.Bold))
        layout.addWidget(title)

        layout.addWidget(QLabel("Enter shoe names (one per line):"))

        self.input_text = QTextEdit()
        self.input_text.setFont(QFont(FONT_MONO, 11))
        self.input_text.setPlaceholderText("Nike Pegasus 41\nHoka Clifton 9\nBrooks Ghost 16")

        # Load shoes.txt if it exists
        shoes_file = Path(__file__).parent / "shoes.txt"
        if shoes_file.exists():
            self.input_text.setPlainText(shoes_file.read_text(encoding="utf-8").strip())

        layout.addWidget(self.input_text)

        # Options row
        opts = QHBoxLayout()
        self.headless_cb = QCheckBox("Run browser in background (headless)")
        self.headless_cb.setChecked(True)
        self.headless_cb.setToolTip("Uncheck to see the browser window — useful if CAPTCHAs appear")
        opts.addWidget(self.headless_cb)
        opts.addStretch()
        layout.addLayout(opts)

        # Buttons
        btn_row = QHBoxLayout()
        self.scrape_btn = QPushButton("  Scrape Running Warehouse  ")
        self.scrape_btn.setFont(QFont(FONT_UI, 12, QFont.Bold))
        self.scrape_btn.setMinimumHeight(40)
        self.scrape_btn.setStyleSheet("""
            QPushButton { background-color: #2563eb; color: white; border-radius: 6px; padding: 8px 24px; }
            QPushButton:hover { background-color: #1d4ed8; }
            QPushButton:disabled { background-color: #93c5fd; }
        """)
        self.scrape_btn.clicked.connect(self._start_scrape)
        btn_row.addStretch()
        btn_row.addWidget(self.scrape_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        # Progress
        self.input_progress = QProgressBar()
        self.input_progress.setVisible(False)
        layout.addWidget(self.input_progress)

        self.input_status = QLabel("")
        self.input_status.setStyleSheet("color: #666;")
        layout.addWidget(self.input_status)

        self.stack.addWidget(page)

    # ── Page 2: Selection Grid ──

    def _build_selection_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(8)

        # Header
        header = QHBoxLayout()
        self.result_count_label = QLabel("Results:")
        self.result_count_label.setFont(QFont(FONT_UI, 12, QFont.Bold))
        header.addWidget(self.result_count_label)
        header.addStretch()

        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(lambda: self._set_all_selected(True))
        header.addWidget(select_all_btn)

        deselect_all_btn = QPushButton("Deselect All")
        deselect_all_btn.clicked.connect(lambda: self._set_all_selected(False))
        header.addWidget(deselect_all_btn)

        back_btn = QPushButton("Back")
        back_btn.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        header.addWidget(back_btn)

        layout.addLayout(header)

        # Scrollable grid
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setSpacing(8)
        self.scroll.setWidget(self.grid_container)
        layout.addWidget(self.scroll)

        # Process button
        btn_row = QHBoxLayout()
        self.process_btn = QPushButton("  Remove Backgrounds & Save WebPs  ")
        self.process_btn.setFont(QFont(FONT_UI, 12, QFont.Bold))
        self.process_btn.setMinimumHeight(40)
        self.process_btn.setStyleSheet("""
            QPushButton { background-color: #16a34a; color: white; border-radius: 6px; padding: 8px 24px; }
            QPushButton:hover { background-color: #15803d; }
            QPushButton:disabled { background-color: #86efac; }
        """)
        self.process_btn.clicked.connect(self._start_processing)
        btn_row.addStretch()
        btn_row.addWidget(self.process_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.stack.addWidget(page)

    # ── Page 3: Processing ──

    def _build_processing_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(12)

        title = QLabel("Processing Shoes")
        title.setFont(QFont(FONT_UI, 16, QFont.Bold))
        layout.addWidget(title)

        self.proc_progress = QProgressBar()
        layout.addWidget(self.proc_progress)

        self.proc_status = QLabel("")
        self.proc_status.setFont(QFont(FONT_UI, 11))
        layout.addWidget(self.proc_status)

        self.proc_log = QTextEdit()
        self.proc_log.setReadOnly(True)
        self.proc_log.setFont(QFont(FONT_MONO, 10))
        layout.addWidget(self.proc_log)

        # Done buttons
        btn_row = QHBoxLayout()
        self.open_folder_btn = QPushButton("  Open Output Folder  ")
        self.open_folder_btn.setMinimumHeight(36)
        self.open_folder_btn.setVisible(False)
        self.open_folder_btn.clicked.connect(self._open_output_folder)
        btn_row.addWidget(self.open_folder_btn)

        self.start_over_btn = QPushButton("  Start Over  ")
        self.start_over_btn.setMinimumHeight(36)
        self.start_over_btn.setVisible(False)
        self.start_over_btn.clicked.connect(self._start_over)
        btn_row.addWidget(self.start_over_btn)

        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.stack.addWidget(page)

    # ── Actions ──

    def _start_scrape(self):
        text = self.input_text.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "No Input", "Enter at least one shoe name.")
            return

        shoe_names = [line.strip() for line in text.splitlines() if line.strip()]
        if not shoe_names:
            QMessageBox.warning(self, "No Input", "Enter at least one shoe name.")
            return

        self.scrape_btn.setEnabled(False)
        self.input_progress.setVisible(True)
        self.input_progress.setRange(0, len(shoe_names))
        self.input_status.setText("Starting browser...")

        # Clear previous results
        self.shoe_cards.clear()
        self.all_results.clear()
        self._clear_grid()

        self.scrape_worker = ScrapeWorker(shoe_names, headless=self.headless_cb.isChecked())
        self.scrape_worker.progress.connect(self._on_scrape_progress)
        self.scrape_worker.shoe_found.connect(self._on_shoe_found)
        self.scrape_worker.finished_signal.connect(self._on_scrape_done)
        self.scrape_worker.error.connect(self._on_scrape_error)
        self.scrape_worker.start()

    def _on_scrape_progress(self, current, total, message):
        self.input_progress.setRange(0, total)
        self.input_progress.setValue(current)
        self.input_status.setText(message)

    def _on_shoe_found(self, result: ShoeResult):
        card = ShoeCard(result)
        self.shoe_cards.append(card)
        idx = len(self.shoe_cards) - 1
        row, col = divmod(idx, GRID_COLS)
        self.grid_layout.addWidget(card, row, col)

    def _on_scrape_done(self, results: list):
        self.all_results = results
        self.scrape_btn.setEnabled(True)
        self.input_progress.setVisible(False)

        if not results:
            self.input_status.setText("No shoes found. Try different search terms.")
            QMessageBox.information(self, "No Results", "No shoe images were found. Try different search terms or uncheck headless mode.")
            return

        self.input_status.setText(f"Found {len(results)} shoes!")
        self.result_count_label.setText(f"Found {len(results)} shoes — select which to process:")
        self.stack.setCurrentIndex(1)

    def _on_scrape_error(self, msg):
        self.scrape_btn.setEnabled(True)
        self.input_progress.setVisible(False)
        self.input_status.setText(f"Error: {msg}")
        QMessageBox.critical(self, "Scraping Error", f"An error occurred:\n\n{msg}")

    def _start_processing(self):
        selected = [card.shoe for card in self.shoe_cards if card.is_selected()]
        if not selected:
            QMessageBox.warning(self, "Nothing Selected", "Select at least one shoe to process.")
            return

        self.stack.setCurrentIndex(2)
        self.proc_progress.setRange(0, len(selected))
        self.proc_progress.setValue(0)
        self.proc_log.clear()
        self.proc_status.setText(f"Processing {len(selected)} shoes...")
        self.open_folder_btn.setVisible(False)
        self.start_over_btn.setVisible(False)

        self.process_worker = ProcessWorker(selected, OUTPUT_DIR)
        self.process_worker.progress.connect(self._on_proc_progress)
        self.process_worker.shoe_processed.connect(self._on_shoe_processed)
        self.process_worker.finished_signal.connect(self._on_proc_done)
        self.process_worker.error.connect(self._on_proc_error)
        self.process_worker.start()

    def _on_proc_progress(self, current, total, message):
        self.proc_progress.setRange(0, total)
        self.proc_progress.setValue(current)
        self.proc_status.setText(message)

    def _on_shoe_processed(self, name, path):
        self.proc_log.append(f"  Saved: {name} -> {path}")

    def _on_proc_done(self):
        self.proc_status.setText("All shoes processed!")
        self.proc_log.append(f"\nOutput folder: {OUTPUT_DIR}")
        self.open_folder_btn.setVisible(True)
        self.start_over_btn.setVisible(True)

    def _on_proc_error(self, msg):
        self.proc_status.setText(f"Error: {msg}")
        self.proc_log.append(f"\nERROR: {msg}")
        self.start_over_btn.setVisible(True)
        QMessageBox.critical(self, "Processing Error", f"An error occurred:\n\n{msg}")

    # ── Helpers ──

    def _set_all_selected(self, selected: bool):
        for card in self.shoe_cards:
            card.checkbox.setChecked(selected)

    def _clear_grid(self):
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _open_output_folder(self):
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        if sys.platform == "win32":
            os.startfile(str(OUTPUT_DIR))
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(OUTPUT_DIR)])
        else:
            subprocess.Popen(["xdg-open", str(OUTPUT_DIR)])

    def _start_over(self):
        self.stack.setCurrentIndex(0)
