"""
NOVA OS Clipboard History Manager & HUD Dialog.
Monitors clipboard changes, stores recent snippets in SQLite,
and provides a quick search & paste dialog (Ctrl+Shift+V).
"""

from typing import List, Dict, Any, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QListWidget, QListWidgetItem,
    QFrame, QMessageBox, QApplication
)
from PySide6.QtCore import Qt, QObject, Signal, QTimer
from PySide6.QtGui import QFont, QClipboard
from nova.database import add_clipboard_entry, get_clipboard_history, clear_clipboard_history

class ClipboardListener(QObject):
    clipboard_updated = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._last_text = ""
        self._clipboard = QApplication.clipboard()
        if self._clipboard:
            self._clipboard.dataChanged.connect(self._on_data_changed)

    def _on_data_changed(self):
        try:
            text = self._clipboard.text()
            if text and text != self._last_text:
                self._last_text = text
                if add_clipboard_entry(text):
                    self.clipboard_updated.emit(text)
        except Exception:
            pass

class ClipboardHistoryDialog(QFrame):
    snippet_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("GlassPanel")
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self.setFixedSize(380, 440)
        self.setup_ui()
        self.load_history()

    def setup_ui(self):
        self.setStyleSheet("""
            QFrame#GlassPanel {
                background-color: rgba(10, 15, 28, 0.98);
                border: 1px solid #00f0ff;
                border-radius: 8px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # Header
        head = QHBoxLayout()
        icon = QLabel("📋")
        icon.setStyleSheet("font-size: 16px;")
        head.addWidget(icon)

        title = QLabel("CLIPBOARD HISTORY")
        title.setStyleSheet("color: #00f0ff; font-weight: bold; font-size: 13px; letter-spacing: 1px;")
        head.addWidget(title)
        head.addStretch()

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(20, 20)
        close_btn.setStyleSheet("background: transparent; border: none; color: #94a3b8; font-weight: bold;")
        close_btn.clicked.connect(self.hide)
        head.addWidget(close_btn)
        layout.addLayout(head)

        # Search Bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search clipboard snippets...")
        self.search_input.textChanged.connect(self.filter_snippets)
        layout.addWidget(self.search_input)

        # List Widget
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("""
            QListWidget {
                background: #090e1a;
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 6px;
                color: #e2e8f0;
                padding: 4px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid rgba(255,255,255,0.04);
                border-radius: 4px;
            }
            QListWidget::item:hover {
                background: #131c31;
                color: #00f0ff;
            }
            QListWidget::item:selected {
                background: #1a2744;
                color: #00f0ff;
            }
        """)
        self.list_widget.itemDoubleClicked.connect(self.on_item_double_clicked)
        layout.addWidget(self.list_widget)

        # Footer Actions
        footer = QHBoxLayout()
        self.clear_btn = QPushButton("Clear All")
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background: #1e131d;
                border: 1px solid #ff2a55;
                color: #ff2a55;
                border-radius: 4px;
                padding: 5px 10px;
                font-size: 11px;
            }
            QPushButton:hover {
                background: #ff2a55;
                color: #ffffff;
            }
        """)
        self.clear_btn.clicked.connect(self.on_clear_clicked)
        footer.addWidget(self.clear_btn)

        footer.addStretch()

        self.copy_btn = QPushButton("Copy to Clipboard")
        self.copy_btn.setObjectName("PrimaryButton")
        self.copy_btn.clicked.connect(self.on_copy_selected)
        footer.addWidget(self.copy_btn)

        layout.addLayout(footer)

    def load_history(self, filter_text: str = ""):
        self.list_widget.clear()
        items = get_clipboard_history(limit=30)
        query = filter_text.strip().lower()

        for it in items:
            content = it["content"]
            if query and query not in content.lower():
                continue
            first_line = content.splitlines()[0] if content.splitlines() else content
            short_line = (first_line[:40] + "...") if len(first_line) > 40 else first_line
            list_item = QListWidgetItem(f"📄 {short_line}")
            list_item.setToolTip(f"Created: {it.get('created_at', '')}\n\n{content[:500]}")
            list_item.setData(Qt.UserRole, content)
            self.list_widget.addItem(list_item)

    def filter_snippets(self, text: str):
        self.load_history(text)

    def on_item_double_clicked(self, item: QListWidgetItem):
        text = item.data(Qt.UserRole)
        if text:
            clipboard = QApplication.clipboard()
            if clipboard:
                clipboard.setText(text)
            self.snippet_selected.emit(text)
            self.hide()

    def on_copy_selected(self):
        curr = self.list_widget.currentItem()
        if curr:
            self.on_item_double_clicked(curr)

    def on_clear_clicked(self):
        reply = QMessageBox.question(
            self,
            "Clear Clipboard History",
            "Are you sure you want to delete all stored clipboard history snippets?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            clear_clipboard_history()
            self.load_history()
