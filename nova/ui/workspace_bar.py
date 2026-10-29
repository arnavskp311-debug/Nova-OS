"""
NOVA OS: Bottom Workspace Switcher Card Deck.
Matches the official reference design layout:
- Header: "Workspaces"
- Thumbnail cards: Desktop (Active), Research, Development, + New Workspace.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor

class WorkspaceThumbnailCard(QFrame):
    clicked = Signal(str)

    def __init__(self, key: str, title: str, icon: str, is_active: bool = False, parent=None):
        super().__init__(parent)
        self.key = key
        self.title = title
        self.icon = icon
        self.is_active = is_active
        self.setFixedSize(85, 52)
        self.setCursor(Qt.PointingHandCursor)
        self.init_ui()

    def init_ui(self):
        self._apply_style()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)
        layout.setAlignment(Qt.AlignCenter)

        i_lbl = QLabel(self.icon)
        i_lbl.setAlignment(Qt.AlignCenter)
        i_lbl.setFont(QFont("Segoe UI Emoji", 14))
        layout.addWidget(i_lbl)

        t_lbl = QLabel(self.title)
        t_lbl.setAlignment(Qt.AlignCenter)
        t_lbl.setFont(QFont("Segoe UI", 8, QFont.Bold if self.is_active else QFont.Normal))
        t_lbl.setStyleSheet("color: #FFFFFF;" if self.is_active else "color: #94A3B8;")
        layout.addWidget(t_lbl)

    def set_active(self, active: bool):
        self.is_active = active
        self._apply_style()

    def _apply_style(self):
        if self.is_active:
            self.setStyleSheet("""
                QFrame {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 rgba(0, 82, 204, 0.6), stop:1 rgba(0, 210, 230, 0.22));
                    border: 1.5px solid #00D2E6;
                    border-radius: 6px;
                }
            """)
        else:
            self.setStyleSheet("""
                QFrame {
                    background: rgba(15, 23, 42, 0.7);
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    border-radius: 6px;
                }
                QFrame:hover {
                    background: rgba(0, 240, 255, 0.15);
                    border-color: rgba(0, 240, 255, 0.4);
                }
            """)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.key)
        super().mousePressEvent(event)


class WorkspaceThumbnailBar(QFrame):
    """
    Bottom-left workspace switcher dock card matching reference image.
    """
    workspace_changed = Signal(str)

    WORKSPACES = [
        ("desktop", "General", "🌌"),
        ("research", "Research", "🔍"),
        ("dev", "Coding", "💻"),
        ("personal", "Personal", "👤"),
        ("new", "Manage", "⚙")
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("WorkspaceThumbnailBar")
        self._cards = {}
        self.active_ws = "desktop"
        self.init_ui()

    def init_ui(self):
        self.setStyleSheet("""
            QFrame#WorkspaceThumbnailBar {
                background: rgba(8, 14, 26, 0.85);
                border: 1px solid rgba(0, 210, 230, 0.22);
                border-radius: 8px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)

        header = QLabel("Workspaces")
        header.setFont(QFont("Segoe UI", 9, QFont.Bold))
        header.setStyleSheet("color: #E2E8F0;")
        layout.addWidget(header)

        cards_row = QHBoxLayout()
        cards_row.setSpacing(6)

        for key, title, icon in self.WORKSPACES:
            is_active = (key == self.active_ws)
            card = WorkspaceThumbnailCard(key, title, icon, is_active=is_active)
            card.clicked.connect(self._on_card_clicked)
            self._cards[key] = card
            cards_row.addWidget(card)

        layout.addLayout(cards_row)

    def set_active_workspace(self, key: str):
        if key in self._cards:
            self.active_ws = key
            for k, c in self._cards.items():
                c.set_active(k == key)

    def _on_card_clicked(self, key: str):
        if key != "new":
            self.set_active_workspace(key)
        self.workspace_changed.emit(key)
