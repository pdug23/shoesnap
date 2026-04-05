"""QThread workers for scraping and background removal."""

import re
from pathlib import Path

import requests
from PyQt5.QtCore import QThread, pyqtSignal

from scraper import ShoeScraper, ShoeResult


def sanitize_filename(name: str) -> str:
    """Sanitize a string for use as a Windows filename."""
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    name = name.replace(' ', '_')
    name = name.strip('._')
    return name[:200] if name else "shoe"


class ScrapeWorker(QThread):
    progress = pyqtSignal(int, int, str)       # current, total, message
    shoe_found = pyqtSignal(object)             # ShoeResult (emitted per batch)
    finished_signal = pyqtSignal(list)           # list[ShoeResult]
    error = pyqtSignal(str)

    def __init__(self, shoe_names: list[str], headless: bool = True):
        super().__init__()
        self.shoe_names = shoe_names
        self.headless = headless

    def run(self):
        try:
            scraper = ShoeScraper(headless=self.headless)
            all_results = []

            def on_progress(current, total, message):
                self.progress.emit(current, total, message)

            results = scraper.scrape_shoes(self.shoe_names, progress_callback=on_progress)

            # Download thumbnails
            for i, result in enumerate(results):
                self.progress.emit(i, len(results), f"Loading thumbnail: {result.product_name}")
                try:
                    resp = requests.get(result.image_url, timeout=10)
                    if resp.status_code == 200:
                        result.thumbnail = resp.content
                except Exception:
                    pass
                self.shoe_found.emit(result)
                all_results.append(result)

            self.finished_signal.emit(all_results)
        except Exception as e:
            self.error.emit(str(e))


class ProcessWorker(QThread):
    progress = pyqtSignal(int, int, str)        # current, total, message
    shoe_processed = pyqtSignal(str, str)        # shoe_name, output_path
    finished_signal = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, shoes: list[ShoeResult], output_dir: Path):
        super().__init__()
        self.shoes = shoes
        self.output_dir = Path(output_dir)
        self.remover = None

    def run(self):
        try:
            self.progress.emit(0, len(self.shoes), "Loading background removal model (first time may download ~170MB)...")
            from background_remover import BackgroundRemover
            self.remover = BackgroundRemover()

            for i, shoe in enumerate(self.shoes):
                name = shoe.product_name or shoe.search_term
                self.progress.emit(i, len(self.shoes), f"Processing: {name}")

                try:
                    # Download full-size image
                    image_data = shoe.thumbnail
                    if not image_data:
                        resp = requests.get(shoe.image_url, timeout=30)
                        resp.raise_for_status()
                        image_data = resp.content

                    # Try to get a higher-res version of the image
                    hi_res = self._try_high_res(shoe.image_url)
                    if hi_res:
                        image_data = hi_res

                    # Remove background and save
                    filename = sanitize_filename(name) + ".webp"
                    output_path = self.output_dir / filename

                    # Handle duplicate filenames
                    counter = 1
                    while output_path.exists():
                        filename = sanitize_filename(name) + f"_{counter}.webp"
                        output_path = self.output_dir / filename
                        counter += 1

                    self.remover.process_and_save(image_data, output_path)
                    self.shoe_processed.emit(name, str(output_path))

                except Exception as e:
                    self.progress.emit(i, len(self.shoes), f"Error processing {name}: {e}")

            self.progress.emit(len(self.shoes), len(self.shoes), "All done!")
            self.finished_signal.emit()

        except Exception as e:
            self.error.emit(str(e))

    def _try_high_res(self, url: str) -> bytes | None:
        """Try to get a higher resolution version of the image URL."""
        # Common patterns: replace thumbnail size indicators
        for pattern, replacement in [
            (r'_t\.', '_l.'),    # thumbnail -> large
            (r'_s\.', '_l.'),    # small -> large
            (r'/s/', '/l/'),
            (r'width=\d+', 'width=800'),
            (r'height=\d+', 'height=800'),
            (r'\?w=\d+', '?w=800'),
        ]:
            import re as re_mod
            modified = re_mod.sub(pattern, replacement, url, count=1)
            if modified != url:
                try:
                    resp = requests.get(modified, timeout=10)
                    if resp.status_code == 200 and len(resp.content) > 1000:
                        return resp.content
                except Exception:
                    pass
        return None
