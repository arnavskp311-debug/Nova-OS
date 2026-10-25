"""
NOVA OS: AI-Powered Desktop Trial Application for Windows.
Main application entry point.

Notice: This is a safe desktop application running inside Windows.
It does NOT modify bootloaders, registry, partitions, or system files.
"""

import sys
import os
import logging
from logging.handlers import RotatingFileHandler
import argparse
from pathlib import Path

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import Qt, qInstallMessageHandler, QtMsgType
from PySide6.QtGui import QIcon, QFont

from nova.config import APP_NAME, APP_VERSION, LOGS_DIR
from nova.ui.theme import setup_nova_palette, get_stylesheet, validate_font_size
from nova.ui.main_window import MainWindow

def setup_logging(debug: bool = False):
    """Sets up bounded rotating file and console logging to prevent unbounded disk growth."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOGS_DIR / "nova_os.log"
    level = logging.DEBUG if debug else logging.INFO

    # 5 MB max per file, 3 backups (max 15 MB total disk usage)
    rotating_handler = RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8"
    )

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] (%(name)s) %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            rotating_handler
        ]
    )
    logging.info(f"Starting {APP_NAME} v{APP_VERSION} on {sys.platform}")

def qt_message_handler(mode, context, message):
    """
    Catches Qt internal messages to filter spurious stylesheet font warnings
    while capturing critical Qt runtime faults into rotating logs.
    """
    # Filter benign point-size warnings triggered during stylesheet resolution
    if "Point size <= 0" in message:
        return

    if mode == QtMsgType.QtFatalMsg:
        logging.critical(f"Qt Fatal: {message} ({context.file}:{context.line})")
    elif mode == QtMsgType.QtCriticalMsg:
        logging.error(f"Qt Critical: {message}")
    elif mode == QtMsgType.QtWarningMsg:
        # Suppress noisy benign windowing messages
        if "QFont" not in message and "QWindowsWindow" not in message and "DirectWrite" not in message:
            logging.warning(f"Qt Warning: {message}")
    else:
        logging.debug(f"Qt Debug: {message}")

def handle_exception(exc_type, exc_value, exc_traceback):
    """Global exception handler to capture unhandled errors without silent crash."""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logging.critical("Unhandled Global Exception:", exc_info=(exc_type, exc_value, exc_traceback))

def main():
    parser = argparse.ArgumentParser(description=f"{APP_NAME} AI Desktop Trial for Windows")
    parser.add_argument("--debug", action="store_true", help="Enable verbose debug logging")
    parser.add_argument("--fullscreen", action="store_true", help="Launch in fullscreen mode")
    parser.add_argument("--safe-mode", action="store_true", help="Launch in Safe Recovery Mode (disables auto-started AI/voice modules)")
    parser.add_argument("--url", type=str, default=None, help="Open NOVA Browser directly to target URL")
    parser.add_argument("--version", action="version", version=f"{APP_NAME} v{APP_VERSION}")
    args = parser.parse_args()

    setup_logging(args.debug)
    sys.excepthook = handle_exception
    qInstallMessageHandler(qt_message_handler)

    if args.safe_mode:
        logging.warning("[SAFE MODE ACTIVE] Starting NOVA OS with diagnostic baseline configuration.")

    # Configure Qt application attributes
    QApplication.setApplicationName(APP_NAME)
    QApplication.setApplicationVersion(APP_VERSION)
    QApplication.setOrganizationName("NovaQuantum")

    app = QApplication(sys.argv)

    # Apply global typography and centralized high-contrast palette
    setup_nova_palette(app)
    app.setStyleSheet(get_stylesheet())

    window = MainWindow(initial_url=args.url)
    if args.fullscreen:
        window.showFullScreen()
    else:
        window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
