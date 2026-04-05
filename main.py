"""ShoeSnap — Scrape Running Warehouse, remove backgrounds, save web-ready WebPs."""

import sys
from PyQt5.QtWidgets import QApplication
from gui import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
