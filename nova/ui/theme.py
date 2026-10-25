"""
Cybernetic Sci-Fi Dark-Mode Theme and QSS Generator for NOVA OS.
Supports dynamic accent colors, glowing borders, and glassmorphic UI elements.
"""

from nova.config import ACCENT_COLORS, DEFAULT_ACCENT

def get_stylesheet(accent_name: str = DEFAULT_ACCENT) -> str:
    accent = ACCENT_COLORS.get(accent_name, ACCENT_COLORS[DEFAULT_ACCENT])
    
    # Calculate complementary tints
    return f"""
    /* NOVA OS Master Cyberpunk Theme */
    * {{
        font-family: 'Segoe UI', 'SF Pro Display', 'Roboto', 'Helvetica Neue', sans-serif;
        color: #d8e2ec;
        font-size: 13px;
    }}

    QMainWindow, QDialog, QWidget#DesktopWidget {{
        background-color: #080a10;
    }}

    /* Futuristic Panels & Containers - 100% Opaque Cyber Dark */
    QFrame#GlassPanel, QWidget#GlassPanel {{
        background-color: #090e1a;
        border: 1px solid rgba(0, 240, 255, 0.35);
        border-radius: 10px;
    }}

    QFrame#AccentCard {{
        background-color: #0d1527;
        border: 1px solid rgba(0, 240, 255, 0.22);
        border-radius: 8px;
    }}

    /* Labels */
    QLabel {{
        background: transparent;
        color: #cad5e2;
    }}

    QLabel#HeaderTitle {{
        font-size: 18px;
        font-weight: 700;
        color: #ffffff;
        letter-spacing: 1px;
    }}

    QLabel#AccentLabel {{
        color: {accent};
        font-weight: 600;
    }}

    QLabel#MutedLabel {{
        color: #6a778b;
        font-size: 11px;
    }}

    QLabel#MetricValue {{
        font-size: 26px;
        font-weight: bold;
        color: #ffffff;
    }}

    /* Buttons */
    QPushButton {{
        background-color: #141b2d;
        color: #e2e8f0;
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 6px;
        padding: 7px 14px;
        font-weight: 500;
    }}

    QPushButton:hover {{
        background-color: #1c263f;
        border: 1px solid {accent};
        color: #ffffff;
    }}

    QPushButton:pressed {{
        background-color: #0f1628;
    }}

    QPushButton#PrimaryButton {{
        background-color: {accent};
        color: #050811;
        font-weight: 700;
        border: 1px solid {accent};
    }}

    QPushButton#PrimaryButton:hover {{
        background-color: #ffffff;
        border: 1px solid #ffffff;
        color: #000000;
    }}

    QPushButton#DangerButton {{
        background-color: #3b141e;
        color: #ff5277;
        border: 1px solid #ff2a55;
    }}

    QPushButton#DangerButton:hover {{
        background-color: #ff2a55;
        color: #ffffff;
    }}

    /* Text Inputs */
    QLineEdit, QTextEdit, QPlainTextEdit {{
        background-color: #0a0e19;
        color: #e2e8f0;
        border: 1px solid rgba(255, 255, 255, 0.15);
        border-radius: 6px;
        padding: 8px;
        selection-background-color: {accent};
        selection-color: #050811;
    }}

    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
        border: 1px solid {accent};
        background-color: #0d1220;
    }}

    /* ComboBox */
    QComboBox {{
        background-color: #121829;
        color: #e2e8f0;
        border: 1px solid rgba(255, 255, 255, 0.15);
        border-radius: 6px;
        padding: 6px 12px;
        min-width: 130px;
    }}

    QComboBox:hover {{
        border: 1px solid {accent};
    }}

    QComboBox::drop-down {{
        subcontrol-origin: padding;
        subcontrol-position: top right;
        width: 25px;
        border-left: 1px solid rgba(255, 255, 255, 0.1);
    }}

    QComboBox QAbstractItemView {{
        background-color: #0f1422;
        border: 1px solid {accent};
        selection-background-color: {accent};
        selection-color: #050811;
        color: #ffffff;
        padding: 4px;
    }}

    /* Scrollbars */
    QScrollBar:vertical {{
        background: #090c14;
        width: 8px;
        margin: 0px;
        border-radius: 4px;
    }}

    QScrollBar::handle:vertical {{
        background: #1e2840;
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
        background: #090c14;
        height: 8px;
        margin: 0px;
        border-radius: 4px;
    }}

    QScrollBar::handle:horizontal {{
        background: #1e2840;
        min-width: 20px;
        border-radius: 4px;
    }}

    QScrollBar::handle:horizontal:hover {{
        background: {accent};
    }}

    /* Progress Bar */
    QProgressBar {{
        background-color: #0d1220;
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 5px;
        text-align: center;
        color: #ffffff;
        font-weight: 600;
        font-size: 11px;
    }}

    QProgressBar::chunk {{
        background-color: {accent};
        border-radius: 4px;
    }}

    /* Lists and Tables */
    QListWidget, QTableWidget, QTreeWidget {{
        background-color: #0b0f1b;
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 6px;
        color: #dbe3ed;
        outline: none;
    }}

    QListWidget::item {{
        padding: 8px 10px;
        border-radius: 4px;
        margin: 2px 4px;
    }}

    QListWidget::item:hover {{
        background-color: #151d32;
        color: #ffffff;
    }}

    QListWidget::item:selected {{
        background-color: rgba(0, 240, 255, 0.15);
        border-left: 3px solid {accent};
        color: #ffffff;
    }}

    QHeaderView::section {{
        background-color: #0f1524;
        color: #8da0b8;
        padding: 6px;
        border: none;
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        font-weight: 600;
    }}

    /* TabWidget */
    QTabWidget::pane {{
        border: 1px solid rgba(255, 255, 255, 0.08);
        background-color: #0c101d;
        border-radius: 8px;
    }}

    QTabBar::tab {{
        background-color: #0e1322;
        color: #8e9bb0;
        padding: 8px 16px;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
        margin-right: 2px;
    }}

    QTabBar::tab:selected {{
        background-color: #141b2d;
        color: {accent};
        font-weight: bold;
        border-bottom: 2px solid {accent};
    }}

    /* Tooltips */
    QToolTip {{
        background-color: #0b0f1c;
        color: #00f0ff;
        border: 1px solid rgba(0, 240, 255, 0.4);
        padding: 5px 8px;
        border-radius: 4px;
    }}
    """
