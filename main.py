"""
NOVA OS: AI-Powered Desktop Trial Application for Windows.
Main application entry point.

Notice: This is a safe desktop application running inside Windows.
It does NOT modify bootloaders, registry, partitions, or system files.
"""

import sys
import os
import logging
import argparse
from pathlib import Path

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

from nova.config import APP_NAME, APP_VERSION, LOGS_DIR
from nova.ui.main_window import MainWindow

def setup_logging(debug: bool = False):
    """Sets up file and console logging."""
    log_file = LOGS_DIR / "nova_os.log"
    level = logging.DEBUG if debug else logging.INFO

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] (%(name)s) %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_file, encoding="utf-8")
        ]
    )
    logging.info(f"Starting {APP_NAME} v{APP_VERSION} on {sys.platform}")

def handle_exception(exc_type, exc_value, exc_traceback):
    """Global exception handler to capture unhandled errors."""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logging.error("Unhandled Exception:", exc_info=(exc_type, exc_value, exc_traceback))

def main():
    parser = argparse.ArgumentParser(description=f"{APP_NAME} AI Desktop Trial for Windows")
    parser.add_argument("--debug", action="store_true", help="Enable verbose debug logging")
    parser.add_argument("--fullscreen", action="store_true", help="Launch in fullscreen mode")
    parser.add_argument("--url", type=str, default=None, help="Open NOVA Browser directly to target URL")
    parser.add_argument("--version", action="version", version=f"{APP_NAME} v{APP_VERSION}")
    args = parser.parse_args()

    setup_logging(args.debug)
    sys.excepthook = handle_exception

    # Configure Qt application attributes
    QApplication.setApplicationName(APP_NAME)
    QApplication.setApplicationVersion(APP_VERSION)
    QApplication.setOrganizationName("NovaQuantum")

    app = QApplication(sys.argv)

    window = MainWindow(initial_url=args.url)
    if args.fullscreen:
        window.showFullScreen()
    else:
        window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
