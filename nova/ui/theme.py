"""
Cybernetic Sci-Fi Dark-Mode Theme and QSS Generator for NOVA OS.
Supports dynamic accent colors, glowing borders, high-contrast typography,
and centralized dark palette enforcement to eliminate unreadable dark text.
"""

from typing import Any
from PySide6.QtGui import QPalette, QColor
from PySide6.QtWidgets import QApplication
from nova.config import ACCENT_COLORS, DEFAULT_ACCENT

# Centralized High-Contrast Text & Palette Constants
COLOR_PRIMARY_TEXT = "#EAF4FF"     # Crisp, luminous off-white with cyan tint for primary body & titles
COLOR_SECONDARY_TEXT = "#A9BCD4"   # Highly legible muted steel blue for labels, subtitles, & metadata
COLOR_INPUT_TEXT = "#EAF4FF"       # Crisp white-blue for active text inputs
COLOR_PLACEHOLDER_TEXT = "#8497B0" # Readable placeholder slate
COLOR_DISABLED_TEXT = "#718096"    # Clear distinguishable muted slate for disabled states
COLOR_DARK_SURFACE = "#080A10"     # Foundation desktop surface
COLOR_PANEL_SURFACE = "#090E1A"    # Window & container surface
COLOR_CARD_SURFACE = "#0D1527"     # Card & section surface
COLOR_BUTTON_SURFACE = "#141B2D"   # Neutral button base
COLOR_INPUT_SURFACE = "#0A0E19"    # Input box background
COLOR_SELECTION_BG = "#0052CC"     # High-contrast deep cyber blue selection
COLOR_SELECTION_FG = "#FFFFFF"     # High-contrast pure white text selection


def validate_font_size(size: Any, default: int = 11, min_size: int = 6, max_size: int = 72) -> int:
    """
    Validates font size to strictly ensure positive, finite integer point sizes.
    Rejects negative, zero, non-finite, and out-of-range values, returning a safe default.
    Prevents Qt 'QFont::setPointSize: Point size <= 0' warnings.
    """
    try:
        if size is None:
            return default
        val = int(float(size))
        if val <= 0:
            return default
        return max(min_size, min(max_size, val))
    except (ValueError, TypeError, OverflowError):
        return default


def setup_nova_palette(app: QApplication = None):
    """
    Configures a centralized dark QPalette on the application instance.
    Guarantees that any Qt widget, dialog, popup, or dynamically created component
    defaults to high-contrast readable text (#EAF4FF) rather than Windows system black.
    Also ensures a validated positive point size on the application font.
    """
    palette = QPalette()

    # Active & Inactive window colors
    palette.setColor(QPalette.Window, QColor(COLOR_DARK_SURFACE))
    palette.setColor(QPalette.WindowText, QColor(COLOR_PRIMARY_TEXT))
    palette.setColor(QPalette.Base, QColor(COLOR_INPUT_SURFACE))
    palette.setColor(QPalette.AlternateBase, QColor("#0F1628"))
    palette.setColor(QPalette.ToolTipBase, QColor("#0B0F1C"))
    palette.setColor(QPalette.ToolTipText, QColor("#00F0FF"))
    palette.setColor(QPalette.Text, QColor(COLOR_PRIMARY_TEXT))
    palette.setColor(QPalette.Button, QColor(COLOR_BUTTON_SURFACE))
    palette.setColor(QPalette.ButtonText, QColor(COLOR_PRIMARY_TEXT))
    palette.setColor(QPalette.BrightText, QColor("#00F0FF"))
    palette.setColor(QPalette.Link, QColor("#00F0FF"))
    palette.setColor(QPalette.Highlight, QColor(COLOR_SELECTION_BG))
    palette.setColor(QPalette.HighlightedText, QColor(COLOR_SELECTION_FG))
    palette.setColor(QPalette.PlaceholderText, QColor(COLOR_PLACEHOLDER_TEXT))

    # Disabled state colors - visible and distinct, never pitch black
    palette.setColor(QPalette.Disabled, QPalette.WindowText, QColor(COLOR_DISABLED_TEXT))
    palette.setColor(QPalette.Disabled, QPalette.Text, QColor(COLOR_DISABLED_TEXT))
    palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(COLOR_DISABLED_TEXT))
    palette.setColor(QPalette.Disabled, QPalette.Highlight, QColor("#1E2840"))
    palette.setColor(QPalette.Disabled, QPalette.HighlightedText, QColor(COLOR_DISABLED_TEXT))

    target_app = app or QApplication.instance()
    if target_app:
        target_app.setPalette(palette)
        # Enforce valid positive point size on application base font
        app_font = target_app.font()
        app_font.setFamily("Segoe UI")
        app_font.setPointSize(validate_font_size(11))
        target_app.setFont(app_font)
    return palette


def get_stylesheet(accent_name: str = DEFAULT_ACCENT) -> str:
    accent = ACCENT_COLORS.get(accent_name, ACCENT_COLORS[DEFAULT_ACCENT])

    return f"""
    /* =========================================================================
       NOVA OS Master Cyberpunk High-Contrast Dark Theme
       ========================================================================= */

    /* Global Base Rule: High contrast luminous readable text everywhere */
    * {{
        font-family: 'Segoe UI', 'SF Pro Display', 'Roboto', 'Helvetica Neue', sans-serif;
        color: {COLOR_PRIMARY_TEXT};
        font-size: 13px;
    }}

    QWidget {{
        color: {COLOR_PRIMARY_TEXT};
        selection-background-color: {COLOR_SELECTION_BG};
        selection-color: {COLOR_SELECTION_FG};
    }}

    QMainWindow, QDialog, QWidget#DesktopWidget, QWidget#MainWindow {{
        background-color: {COLOR_DARK_SURFACE};
        color: {COLOR_PRIMARY_TEXT};
    }}

    /* Panels & Containers - 100% Opaque Cyber Dark */
    QFrame#GlassPanel, QWidget#GlassPanel {{
        background-color: {COLOR_PANEL_SURFACE};
        border: 1px solid rgba(0, 240, 255, 0.35);
        border-radius: 10px;
        color: {COLOR_PRIMARY_TEXT};
    }}

    QFrame#AccentCard, QWidget#AccentCard {{
        background-color: {COLOR_CARD_SURFACE};
        border: 1px solid rgba(0, 240, 255, 0.22);
        border-radius: 8px;
        color: {COLOR_PRIMARY_TEXT};
    }}

    /* Labels */
    QLabel {{
        background: transparent;
        color: {COLOR_PRIMARY_TEXT};
    }}

    QLabel:disabled {{
        color: {COLOR_DISABLED_TEXT};
    }}

    QLabel#HeaderTitle {{
        font-size: 17px;
        font-weight: 700;
        color: #FFFFFF;
        letter-spacing: 0.8px;
    }}

    QLabel#AccentLabel {{
        color: {accent};
        font-weight: 600;
    }}

    QLabel#MutedLabel {{
        color: {COLOR_SECONDARY_TEXT};
        font-size: 11px;
    }}

    QLabel#MetricValue {{
        font-size: 26px;
        font-weight: bold;
        color: #FFFFFF;
    }}

    /* Group Boxes */
    QGroupBox {{
        font-weight: bold;
        color: #00F0FF;
        border: 1px solid rgba(0, 240, 255, 0.25);
        border-radius: 8px;
        margin-top: 14px;
        padding-top: 16px;
        padding-left: 8px;
        padding-right: 8px;
        padding-bottom: 8px;
        background-color: transparent;
    }}

    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        left: 10px;
        padding: 0 4px;
        color: #00F0FF;
        font-size: 12px;
        font-weight: bold;
    }}

    QGroupBox QLabel {{
        color: {COLOR_PRIMARY_TEXT};
    }}

    QGroupBox QCheckBox {{
        color: {COLOR_PRIMARY_TEXT};
    }}

    /* CheckBoxes & RadioButtons */
    QCheckBox, QRadioButton {{
        color: {COLOR_PRIMARY_TEXT};
        spacing: 8px;
        background: transparent;
        font-size: 12px;
    }}

    QCheckBox:hover, QRadioButton:hover {{
        color: #FFFFFF;
    }}

    QCheckBox:disabled, QRadioButton:disabled {{
        color: {COLOR_DISABLED_TEXT};
    }}

    QCheckBox::indicator, QRadioButton::indicator {{
        width: 16px;
        height: 16px;
        background-color: #0D1424;
        border: 1px solid rgba(0, 240, 255, 0.4);
        border-radius: 4px;
    }}

    QRadioButton::indicator {{
        border-radius: 8px;
    }}

    QCheckBox::indicator:hover, QRadioButton::indicator:hover {{
        border: 1px solid #00F0FF;
        background-color: #121E36;
    }}

    QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
        background-color: #0052CC;
        border: 1px solid #00F0FF;
    }}

    QCheckBox::indicator:disabled, QRadioButton::indicator:disabled {{
        background-color: #080D1A;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }}

    /* Buttons */
    QPushButton {{
        background-color: {COLOR_BUTTON_SURFACE};
        color: {COLOR_PRIMARY_TEXT};
        border: 1px solid rgba(255, 255, 255, 0.14);
        border-radius: 6px;
        padding: 7px 14px;
        font-weight: 500;
    }}

    QPushButton:hover {{
        background-color: #1C263F;
        border: 1px solid {accent};
        color: #FFFFFF;
    }}

    QPushButton:pressed {{
        background-color: #0F1628;
        color: {COLOR_PRIMARY_TEXT};
    }}

    QPushButton:disabled {{
        background-color: #0D1322;
        border: 1px solid rgba(255, 255, 255, 0.05);
        color: {COLOR_DISABLED_TEXT};
    }}

    QPushButton#PrimaryButton {{
        background-color: #0052CC;
        color: #FFFFFF;
        font-weight: 700;
        border: 1px solid #00F0FF;
    }}

    QPushButton#PrimaryButton:hover {{
        background-color: #0066FF;
        border: 1px solid #00F0FF;
        color: #FFFFFF;
    }}

    QPushButton#PrimaryButton:disabled {{
        background-color: #111A2E;
        border: 1px solid rgba(255, 255, 255, 0.08);
        color: {COLOR_DISABLED_TEXT};
    }}

    QPushButton#DangerButton {{
        background-color: #240C12;
        color: #FF5277;
        border: 1px solid #FF2A55;
    }}

    QPushButton#DangerButton:hover {{
        background-color: #FF2A55;
        color: #FFFFFF;
    }}

    QPushButton#DangerButton:disabled {{
        background-color: #14080A;
        border: 1px solid rgba(255, 42, 85, 0.2);
        color: {COLOR_DISABLED_TEXT};
    }}

    /* Text Inputs */
    QLineEdit, QTextEdit, QPlainTextEdit {{
        background-color: {COLOR_INPUT_SURFACE};
        color: {COLOR_INPUT_TEXT};
        border: 1px solid rgba(255, 255, 255, 0.15);
        border-radius: 6px;
        padding: 8px;
        selection-background-color: {COLOR_SELECTION_BG};
        selection-color: {COLOR_SELECTION_FG};
    }}

    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
        border: 1px solid {accent};
        background-color: #0D1220;
        color: #FFFFFF;
    }}

    QLineEdit:disabled, QTextEdit:disabled, QPlainTextEdit:disabled {{
        color: {COLOR_DISABLED_TEXT};
        background-color: #080D18;
        border: 1px solid rgba(255, 255, 255, 0.06);
    }}

    /* ComboBox */
    QComboBox {{
        background-color: #121829;
        color: {COLOR_PRIMARY_TEXT};
        border: 1px solid rgba(255, 255, 255, 0.15);
        border-radius: 6px;
        padding: 6px 12px;
        min-width: 130px;
    }}

    QComboBox:hover {{
        border: 1px solid {accent};
        color: #FFFFFF;
    }}

    QComboBox:disabled {{
        color: {COLOR_DISABLED_TEXT};
        background-color: #0C101D;
        border: 1px solid rgba(255, 255, 255, 0.06);
    }}

    QComboBox::drop-down {{
        subcontrol-origin: padding;
        subcontrol-position: top right;
        width: 25px;
        border-left: 1px solid rgba(255, 255, 255, 0.1);
    }}

    QComboBox QAbstractItemView {{
        background-color: #0F1422;
        border: 1px solid {accent};
        selection-background-color: {COLOR_SELECTION_BG};
        selection-color: {COLOR_SELECTION_FG};
        color: {COLOR_PRIMARY_TEXT};
        padding: 4px;
        outline: none;
    }}

    QComboBox QAbstractItemView::item {{
        color: {COLOR_PRIMARY_TEXT};
        padding: 6px 10px;
        min-height: 22px;
    }}

    QComboBox QAbstractItemView::item:selected {{
        background-color: {COLOR_SELECTION_BG};
        color: #FFFFFF;
    }}

    /* Scrollbars */
    QScrollBar:vertical {{
        background: #090C14;
        width: 8px;
        margin: 0px;
        border-radius: 4px;
    }}

    QScrollBar::handle:vertical {{
        background: #1E2840;
        min-height: 20px;
        border-radius: 4px;
    }}

    QScrollBar::handle:vertical:hover {{
        background: {accent};
    }}

    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}

    QScrollBar:horizontal {{
        background: #090C14;
        height: 8px;
        margin: 0px;
        border-radius: 4px;
    }}

    QScrollBar::handle:horizontal {{
        background: #1E2840;
        min-width: 20px;
        border-radius: 4px;
    }}

    QScrollBar::handle:horizontal:hover {{
        background: {accent};
    }}

    /* Progress Bar */
    QProgressBar {{
        background-color: #0D1220;
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 5px;
        text-align: center;
        color: #FFFFFF;
        font-weight: 600;
        font-size: 11px;
    }}

    QProgressBar::chunk {{
        background-color: {accent};
        border-radius: 4px;
    }}

    /* Lists, Tables, Trees */
    QListWidget, QTableWidget, QTreeWidget {{
        background-color: #0B0F1B;
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 6px;
        color: {COLOR_PRIMARY_TEXT};
        outline: none;
    }}

    QListWidget::item, QTableWidget::item, QTreeWidget::item {{
        padding: 8px 10px;
        border-radius: 4px;
        margin: 2px 4px;
        color: {COLOR_PRIMARY_TEXT};
    }}

    QListWidget::item:hover, QTableWidget::item:hover, QTreeWidget::item:hover {{
        background-color: #151D32;
        color: #FFFFFF;
    }}

    QListWidget::item:selected, QTableWidget::item:selected, QTreeWidget::item:selected {{
        background-color: rgba(0, 82, 204, 0.6);
        border-left: 3px solid {accent};
        color: #FFFFFF;
    }}

    QListWidget::item:disabled, QTableWidget::item:disabled, QTreeWidget::item:disabled {{
        color: {COLOR_DISABLED_TEXT};
    }}

    QHeaderView::section {{
        background-color: #0F1524;
        color: {COLOR_SECONDARY_TEXT};
        padding: 6px;
        border: none;
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        font-weight: 600;
    }}

    /* TabWidget */
    QTabWidget::pane {{
        border: 1px solid rgba(255, 255, 255, 0.08);
        background-color: #0C101D;
        border-radius: 8px;
    }}

    QTabBar::tab {{
        background-color: #0E1322;
        color: {COLOR_SECONDARY_TEXT};
        padding: 8px 16px;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
        margin-right: 2px;
    }}

    QTabBar::tab:hover {{
        background-color: #141B2D;
        color: #FFFFFF;
    }}

    QTabBar::tab:selected {{
        background-color: #141B2D;
        color: {accent};
        font-weight: bold;
        border-bottom: 2px solid {accent};
    }}

    QTabBar::tab:disabled {{
        color: {COLOR_DISABLED_TEXT};
    }}

    /* Menus & Tooltips */
    QMenu {{
        background-color: #0C1424;
        color: {COLOR_PRIMARY_TEXT};
        border: 1px solid rgba(0, 240, 255, 0.35);
        border-radius: 8px;
        padding: 6px 0;
    }}

    QMenu::item {{
        padding: 6px 20px;
        color: {COLOR_PRIMARY_TEXT};
        background-color: transparent;
    }}

    QMenu::item:selected {{
        background-color: #0052CC;
        color: #FFFFFF;
    }}

    QMenu::item:disabled {{
        color: {COLOR_DISABLED_TEXT};
    }}

    QMenu::separator {{
        height: 1px;
        background: rgba(255, 255, 255, 0.08);
        margin: 4px 8px;
    }}

    QToolTip {{
        background-color: #0B0F1C;
        color: #00F0FF;
        border: 1px solid rgba(0, 240, 255, 0.4);
        padding: 5px 8px;
        border-radius: 4px;
        font-size: 11px;
    }}

    /* SpinBoxes & Sliders */
    QSpinBox, QDoubleSpinBox {{
        background-color: {COLOR_INPUT_SURFACE};
        color: {COLOR_INPUT_TEXT};
        border: 1px solid rgba(255, 255, 255, 0.15);
        border-radius: 6px;
        padding: 4px 8px;
    }}

    QSlider::groove:horizontal {{
        border: 1px solid rgba(255, 255, 255, 0.1);
        height: 6px;
        background: #0D1424;
        border-radius: 3px;
    }}

    QSlider::sub-page:horizontal {{
        background: {accent};
        border-radius: 3px;
    }}

    QSlider::handle:horizontal {{
        background: #FFFFFF;
        border: 1px solid {accent};
        width: 14px;
        margin-top: -4px;
        margin-bottom: -4px;
        border-radius: 7px;
    }}
    """
