"""ShoeSnap — Drag-and-drop batch background removal tool."""

# Fix DLL search paths BEFORE importing PyQt5 — PyQt5 alters the DLL search
# order on Windows, which prevents onnxruntime from finding its own DLLs.
import os
import sys

if sys.platform == "win32":
    try:
        import onnxruntime as _ort
        _ort_capi = os.path.join(os.path.dirname(_ort.__file__), "capi")
        if os.path.isdir(_ort_capi):
            os.add_dll_directory(_ort_capi)
    except Exception:
        pass  # onnxruntime DLL fix is best-effort

import json
import re
import subprocess
from datetime import datetime
from io import BytesIO
from pathlib import Path
from PIL import Image
import pillow_avif  # noqa: F401 — registers AVIF codec with Pillow

from PyQt5.QtCore import (
    Qt, QThread, pyqtSignal, QMimeData, QSize, QEvent,
)
from PyQt5.QtGui import (
    QPixmap, QImage, QFont, QKeySequence, QPalette, QColor, QDragEnterEvent,
    QDropEvent, QPainter, QPen, QIcon,
)
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QProgressBar, QShortcut,
    QSizePolicy, QFrame,
)

# Platform-appropriate fonts
if sys.platform == "darwin":
    FONT_UI = "SF Pro Text"
    FONT_MONO = "Menlo"
else:
    FONT_UI = "Segoe UI"
    FONT_MONO = "Consolas"

from image_pipeline import process_pipeline


APP_DIR = Path(__file__).resolve().parent           # images/pipeline/
IMAGES_DIR = APP_DIR.parent                          # images/
REPO_DIR = IMAGES_DIR.parent                         # repo root
OUTPUT_DIR = IMAGES_DIR / "processed"
LOG_FILE = OUTPUT_DIR / "processing_log.json"
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tiff", ".tif", ".avif"}
OUTPUT_EXT = ".webp"

# ── Colors ──
BG = "#1e1e1e"
BG_LIGHT = "#2d2d2d"
BG_LIGHTER = "#3a3a3a"
TEXT = "#e0e0e0"
TEXT_DIM = "#888888"
ACCENT = "#3b82f6"
ACCENT_HOVER = "#2563eb"
GREEN = "#22c55e"
RED = "#ef4444"
ORANGE = "#f59e0b"


def suggested_name(original: str) -> str:
    """Derive a clean filename from the original."""
    stem = Path(original).stem
    name = stem.lower()
    # Strip special chars like ®, ™, ©
    name = re.sub(r'[®™©]', '', name)
    # Replace spaces, underscores, dots with hyphens
    name = re.sub(r'[\s_\.]+', '-', name)
    # Remove anything that isn't alphanumeric or hyphen
    name = re.sub(r'[^a-z0-9\-]', '', name)
    # Collapse multiple hyphens
    name = re.sub(r'-{2,}', '-', name)
    name = name.strip('-')
    return name or "shoe"


def unique_path(name: str, output_dir: Path) -> Path:
    """Return a unique output path, appending -2, -3, etc. if needed."""
    path = output_dir / f"{name}{OUTPUT_EXT}"
    if not path.exists():
        return path
    counter = 2
    while True:
        path = output_dir / f"{name}-{counter}{OUTPUT_EXT}"
        if not path.exists():
            return path
        counter += 1


def unique_name(name: str, output_dir: Path) -> str:
    """Return the unique stem (without .png) for the output."""
    p = unique_path(name, output_dir)
    return p.stem


# ── Background Removal Worker ──

_rembg_remove = None
_rembg_session = None


def _get_rembg_remove():
    """Lazy-load rembg.remove and BiRefNet session once, on first use."""
    global _rembg_remove, _rembg_session
    if _rembg_remove is None:
        import traceback as _tb
        try:
            from rembg import remove, new_session
            _rembg_remove = remove
            _rembg_session = new_session("birefnet-general")
        except Exception:
            _tb.print_exc()
            raise
    return _rembg_remove


class RemoveBgWorker(QThread):
    finished = pyqtSignal(bytes)  # PNG bytes with transparency
    error = pyqtSignal(str)

    def __init__(self, image_bytes: bytes, remove_fn):
        super().__init__()
        self.image_bytes = image_bytes
        self.remove_fn = remove_fn

    def run(self):
        import traceback as _tb
        try:
            result = self.remove_fn(
                self.image_bytes,
                session=_rembg_session,
                alpha_matting=True,
                alpha_matting_foreground_threshold=230,
                alpha_matting_background_threshold=20,
                alpha_matting_erode_size=10,
            )
            self.finished.emit(result)
        except Exception as e:
            _tb.print_exc()
            self.error.emit(str(e))


# ── Drop Zone / Preview Widget ──

class DropPreview(QLabel):
    files_dropped = pyqtSignal(list)

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(600, 400)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {BG_LIGHT};
                border: 2px dashed {TEXT_DIM};
                border-radius: 12px;
                color: {TEXT_DIM};
                font-size: 18px;
            }}
        """)
        self._show_drop_prompt()

    def _show_drop_prompt(self):
        self.setPixmap(QPixmap())
        self.setText("Drag && Drop Images Here\n\npng · jpg · bmp · webp · tiff · avif")
        self.setStyleSheet(self.styleSheet().replace("border: 2px solid", "border: 2px dashed"))

    def show_image(self, pixmap: QPixmap):
        self.setText("")
        scaled = pixmap.scaled(
            self.size() - QSize(20, 20),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self.setPixmap(scaled)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet(self.styleSheet().replace("dashed", "solid"))

    def dragLeaveEvent(self, event):
        self.setStyleSheet(self.styleSheet().replace("solid", "dashed"))

    def dropEvent(self, event: QDropEvent):
        self.setStyleSheet(self.styleSheet().replace("solid", "dashed"))
        files = []
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if Path(path).suffix.lower() in IMAGE_EXTS:
                files.append(path)
        if files:
            self.files_dropped.emit(files)

    def resizeEvent(self, event):
        # Re-scale current pixmap on resize
        pm = self.pixmap()
        if pm and not pm.isNull():
            # We store the original in the parent
            pass
        super().resizeEvent(event)


# ── Main Window ──

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ShoeSnap")
        self.setMinimumSize(700, 550)
        self.resize(800, 650)

        # State
        self.image_queue: list[str] = []
        self.current_index = -1
        self.current_pixmap: QPixmap | None = None
        self.current_bytes: bytes | None = None
        self.worker: RemoveBgWorker | None = None
        self.processing = False
        self.auto_mode = False
        self.log: list[dict] = []

        self._load_existing_log()
        self._build_ui()
        self._setup_shortcuts()
        self._apply_theme()

    def _load_existing_log(self):
        """Load existing log so duplicate detection works across sessions."""
        if LOG_FILE.exists():
            try:
                self.log = json.loads(LOG_FILE.read_text(encoding="utf-8"))
            except Exception:
                self.log = []

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        # Drop zone / preview
        self.preview = DropPreview()
        self.preview.files_dropped.connect(self._on_files_dropped)
        layout.addWidget(self.preview, stretch=1)

        # Counter label
        self.counter_label = QLabel("")
        self.counter_label.setAlignment(Qt.AlignCenter)
        self.counter_label.setFont(QFont(FONT_UI, 11))
        layout.addWidget(self.counter_label)

        # Filename row
        name_row = QHBoxLayout()
        name_row.setSpacing(8)

        self.name_field = QLineEdit()
        self.name_field.setPlaceholderText("filename (without .webp)")
        self.name_field.setFont(QFont(FONT_MONO, 13))
        self.name_field.setMinimumHeight(38)
        self.name_field.returnPressed.connect(self._process_current)
        name_row.addWidget(self.name_field, stretch=1)

        self.png_label = QLabel(".webp")
        self.png_label.setFont(QFont(FONT_MONO, 13))
        self.png_label.setStyleSheet(f"color: {TEXT_DIM};")
        name_row.addWidget(self.png_label)

        self.process_btn = QPushButton("Process")
        self.process_btn.setFont(QFont(FONT_UI, 11, QFont.Bold))
        self.process_btn.setMinimumHeight(38)
        self.process_btn.setMinimumWidth(100)
        self.process_btn.clicked.connect(self._process_current)
        name_row.addWidget(self.process_btn)

        self.skip_btn = QPushButton("Skip")
        self.skip_btn.setFont(QFont(FONT_UI, 11))
        self.skip_btn.setMinimumHeight(38)
        self.skip_btn.clicked.connect(self._skip_current)
        name_row.addWidget(self.skip_btn)

        self.auto_btn = QPushButton("Process All")
        self.auto_btn.setFont(QFont(FONT_UI, 11, QFont.Bold))
        self.auto_btn.setMinimumHeight(38)
        self.auto_btn.clicked.connect(self._start_auto_mode)
        name_row.addWidget(self.auto_btn)

        layout.addLayout(name_row)

        # Status label
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setFont(QFont(FONT_UI, 10))
        layout.addWidget(self.status_label)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        layout.addWidget(self.progress_bar)

        # Initially hide input controls
        self._set_controls_visible(False)

    def _setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+O"), self, self._open_output_folder)
        QShortcut(QKeySequence("Ctrl+Q"), self, self.close)
        QShortcut(QKeySequence(Qt.Key_Escape), self, self._skip_current)

    def _apply_theme(self):
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{
                background-color: {BG};
                color: {TEXT};
            }}
            QLineEdit {{
                background-color: {BG_LIGHTER};
                color: {TEXT};
                border: 2px solid {BG_LIGHTER};
                border-radius: 6px;
                padding: 4px 10px;
                selection-background-color: {ACCENT};
            }}
            QLineEdit:focus {{
                border-color: {ACCENT};
            }}
            QPushButton {{
                background-color: {ACCENT};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 16px;
            }}
            QPushButton:hover {{
                background-color: {ACCENT_HOVER};
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
        # Re-apply after setObjectName
        self.skip_btn.setStyle(self.skip_btn.style())

    def _set_controls_visible(self, visible: bool):
        self.name_field.setVisible(visible)
        self.png_label.setVisible(visible)
        self.process_btn.setVisible(visible)
        self.skip_btn.setVisible(visible)
        self.auto_btn.setVisible(visible)
        self.counter_label.setVisible(visible)

    def _set_status(self, text: str, color: str = TEXT_DIM):
        self.status_label.setText(text)
        self.status_label.setStyleSheet(f"color: {color};")

    # ── File Handling ──

    def _on_files_dropped(self, files: list[str]):
        self.image_queue = sorted(files)
        self.current_index = -1
        self.progress_bar.setRange(0, len(self.image_queue))
        self.progress_bar.setValue(0)
        self._set_controls_visible(True)
        self._set_status(f"Loaded {len(self.image_queue)} images")
        self._advance()

    def _advance(self):
        self.current_index += 1
        if self.current_index >= len(self.image_queue):
            self._show_complete()
            return

        filepath = self.image_queue[self.current_index]
        self.progress_bar.setValue(self.current_index)

        # Load image
        try:
            raw = Path(filepath).read_bytes()
            self.current_bytes = raw
            img = QImage.fromData(raw)
            if img.isNull():
                # Qt can't decode this format (e.g. AVIF) — fall back to Pillow
                pil_img = Image.open(BytesIO(raw)).convert("RGBA")
                buf = BytesIO()
                pil_img.save(buf, format="PNG")
                png_data = buf.getvalue()
                self.current_bytes = png_data
                img = QImage.fromData(png_data)
                if img.isNull():
                    raise ValueError("Could not decode image")
            self.current_pixmap = QPixmap.fromImage(img)
            self.preview.show_image(self.current_pixmap)
        except Exception as e:
            self._set_status(f"Error loading {Path(filepath).name}: {e}", RED)
            self._log_entry(filepath, "", "error", str(e))
            self._set_processing(False)
            self._show_error_with_skip()
            return

        # Update counter
        total = len(self.image_queue)
        self.counter_label.setText(f"Image {self.current_index + 1} / {total}")

        # Suggest filename
        name = suggested_name(Path(filepath).name)
        name = unique_name(name, OUTPUT_DIR)
        self.name_field.setText(name)
        self.name_field.selectAll()
        self.name_field.setFocus()

        self._set_status(f"{Path(filepath).name}", TEXT_DIM)
        self.process_btn.setText("Process")
        self._set_processing(False)

        # In auto mode, start processing immediately
        if self.auto_mode:
            self._process_current()

    # ── Processing ──

    def _process_current(self):
        if self.processing or self.current_index >= len(self.image_queue):
            return

        if not self.current_bytes:
            self._advance()
            return

        self._set_processing(True)
        self._set_status("Loading rembg..." if _rembg_remove is None else "Removing background...", ORANGE)

        # Import rembg on the main thread (avoids QThread + sys.exit conflicts)
        try:
            remove_fn = _get_rembg_remove()
        except Exception as e:
            self._set_status(f"rembg failed to load: {e}", RED)
            self._set_processing(False)
            return

        self._set_status("Removing background...", ORANGE)
        self.worker = RemoveBgWorker(self.current_bytes, remove_fn)
        self.worker.finished.connect(self._on_bg_removed)
        self.worker.error.connect(self._on_bg_error)
        self.worker.start()

    def _on_bg_removed(self, png_bytes: bytes):
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        # Run full post-processing pipeline (defringe, feather, mirror, canvas, WebP)
        try:
            final_bytes = process_pipeline(png_bytes)
        except Exception as e:
            self._set_status(f"Post-processing failed: {e}", RED)
            self._log_entry(
                self.image_queue[self.current_index], "", "error", f"Pipeline: {e}",
            )
            self._set_processing(False)
            self._show_error_with_skip()
            return

        name = self.name_field.text().strip()
        if not name:
            name = "shoe"
        # Re-sanitize user input
        name = re.sub(r'[<>:"/\\|?*]', '', name)
        name = name.strip('. ')
        if not name:
            name = "shoe"

        out_path = unique_path(name, OUTPUT_DIR)
        try:
            out_path.write_bytes(final_bytes)
            self._set_status(f"Saved: {out_path.name}", GREEN)
            self._log_entry(
                self.image_queue[self.current_index],
                out_path.name,
                "success",
            )
            self._mark_has_image(out_path.stem)
        except Exception as e:
            self._set_status(f"Save error: {e}", RED)
            self._log_entry(
                self.image_queue[self.current_index],
                "",
                "error",
                str(e),
            )
            self._set_processing(False)
            self._show_error_with_skip()
            return

        self._set_processing(False)
        self._advance()

    def _on_bg_error(self, msg: str):
        self._set_status(f"Background removal failed: {msg}", RED)
        self._log_entry(
            self.image_queue[self.current_index],
            "",
            "error",
            msg,
        )
        self._set_processing(False)
        self._show_error_with_skip()

    def _skip_current(self):
        if self.processing or self.current_index >= len(self.image_queue):
            return
        if self.current_index >= 0:
            self._log_entry(
                self.image_queue[self.current_index],
                "",
                "skipped",
            )
            self._set_status("Skipped", TEXT_DIM)
        self._advance()

    def _start_auto_mode(self):
        """Process all remaining images automatically using suggested filenames."""
        self.auto_mode = True
        self.auto_btn.setEnabled(False)
        self.auto_btn.setText("Processing...")
        self.skip_btn.setEnabled(False)
        self._process_current()

    def _stop_auto_mode(self):
        self.auto_mode = False
        self.auto_btn.setEnabled(True)
        self.auto_btn.setText("Process All")

    def _show_error_with_skip(self):
        """Show skip button so user can read the error and advance when ready."""
        if self.auto_mode:
            # In auto mode, skip errors and keep going
            self._advance()
            return
        self.skip_btn.setVisible(True)
        self.skip_btn.setEnabled(True)
        self.process_btn.setVisible(True)
        self.process_btn.setEnabled(True)
        self.process_btn.setText("Retry")

    def _set_processing(self, active: bool):
        self.processing = active
        self.name_field.setEnabled(not active)
        self.process_btn.setEnabled(not active)
        self.skip_btn.setEnabled(not active)

    # ── Completion ──

    def _show_complete(self):
        self._stop_auto_mode()
        self.progress_bar.setValue(len(self.image_queue))
        self._set_controls_visible(False)

        success = sum(1 for e in self.log[-len(self.image_queue):] if e.get("status") == "success")
        skipped = sum(1 for e in self.log[-len(self.image_queue):] if e.get("status") == "skipped")
        errors = sum(1 for e in self.log[-len(self.image_queue):] if e.get("status") == "error")

        self.preview.setText(
            f"Batch Complete!\n\n"
            f"{success} processed  ·  {skipped} skipped  ·  {errors} errors\n\n"
            f"Drag more images to continue"
        )
        self.preview.setStyleSheet(
            self.preview.styleSheet()  # keep existing base
        )

        self._set_status(
            "Ctrl+O: Open output folder  |  Drop more images to continue",
            TEXT_DIM,
        )

        # Write log
        self._save_log()

    # ── Logging ──

    def _log_entry(self, original: str, output_name: str, status: str, error_msg: str = ""):
        entry = {
            "original": Path(original).name,
            "output": output_name,
            "status": status,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        }
        if error_msg:
            entry["error"] = error_msg
        self.log.append(entry)

    def _save_log(self):
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        try:
            LOG_FILE.write_text(
                json.dumps(self.log, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception:
            pass

    # ── Utilities ──

    def _mark_has_image(self, filename_stem: str):
        """Mark a shoe as having an image in shoebase.json."""
        try:
            db_path = REPO_DIR / "database" / "shoebase.json"
            if not db_path.exists():
                return
            shoes = json.loads(db_path.read_text(encoding="utf-8"))
            slug = filename_stem.lower()
            for s in shoes:
                shoe_slug = re.sub(r'[^a-z0-9]+', '-', s["full_name"].lower()).strip('-')
                if shoe_slug == slug:
                    s["has_image"] = True
                    db_path.write_text(
                        json.dumps(shoes, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8",
                    )
                    break
        except Exception:
            pass  # non-critical — don't block image processing

    def _open_output_folder(self):
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        if sys.platform == "win32":
            os.startfile(str(OUTPUT_DIR))
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(OUTPUT_DIR)])
        else:
            subprocess.Popen(["xdg-open", str(OUTPUT_DIR)])


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Dark palette as a base
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(BG))
    palette.setColor(QPalette.WindowText, QColor(TEXT))
    palette.setColor(QPalette.Base, QColor(BG_LIGHT))
    palette.setColor(QPalette.AlternateBase, QColor(BG_LIGHTER))
    palette.setColor(QPalette.Text, QColor(TEXT))
    palette.setColor(QPalette.Button, QColor(BG_LIGHTER))
    palette.setColor(QPalette.ButtonText, QColor(TEXT))
    palette.setColor(QPalette.Highlight, QColor(ACCENT))
    palette.setColor(QPalette.HighlightedText, QColor("#ffffff"))
    app.setPalette(palette)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
