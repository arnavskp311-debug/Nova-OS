"""
Futuristic Window Container & Manager for NOVA OS.
Provides draggable, resizable, floating OS-style window frames with cyber controls.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QSizeGrip
)
from PySide6.QtCore import Qt, QPoint, Signal
from PySide6.QtGui import QMouseEvent

class WindowFrame(QFrame):
    window_closed = Signal(object)
    window_minimized = Signal(object)
    window_focused = Signal(object)

    def __init__(self, title: str, content_widget: QWidget, icon_text: str = "◈", parent=None):
        super().__init__(parent)
        self.title_text = title
        self.content_widget = content_widget
        self.icon_text = icon_text
        self.is_maximized = False
        self.normal_geometry = None
        self._drag_pos = None

        self.setup_ui()

    def setup_ui(self):
        self.setObjectName("GlassPanel")
        self.setMinimumSize(420, 320)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(2, 2, 2, 2)
        main_layout.setSpacing(0)

        # Title Bar
        self.title_bar = QFrame()
        self.title_bar.setObjectName("TitleBar")
        self.title_bar.setFixedHeight(34)
        self.title_bar.setStyleSheet("""
            QFrame#TitleBar {
                background-color: #0c1222;
                border-top-left-radius: 9px;
                border-top-right-radius: 9px;
                border-bottom: 1px solid rgba(0, 240, 255, 0.2);
            }
        """)

        tb_layout = QHBoxLayout(self.title_bar)
        tb_layout.setContentsMargins(10, 0, 8, 0)
        tb_layout.setSpacing(8)

        # Icon and Title
        self.icon_lbl = QLabel(self.icon_text)
        self.icon_lbl.setStyleSheet("color: #00f0ff; font-weight: bold; font-size: 14px;")
        tb_layout.addWidget(self.icon_lbl)

        self.title_lbl = QLabel(self.title_text)
        self.title_lbl.setStyleSheet("color: #ffffff; font-weight: 600; font-size: 12px; letter-spacing: 0.5px;")
        tb_layout.addWidget(self.title_lbl)

        tb_layout.addStretch()

        # Window Controls
        btn_style = """
            QPushButton {
                background: transparent;
                border: none;
                color: #8fa0b5;
                font-size: 13px;
                font-weight: bold;
                padding: 2px 6px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.1);
                color: #ffffff;
            }
        """

        self.min_btn = QPushButton("—")
        self.min_btn.setStyleSheet(btn_style)
        self.min_btn.clicked.connect(self.on_minimize)
        tb_layout.addWidget(self.min_btn)

        self.max_btn = QPushButton("▢")
        self.max_btn.setStyleSheet(btn_style)
        self.max_btn.clicked.connect(self.on_toggle_maximize)
        tb_layout.addWidget(self.max_btn)

        self.close_btn = QPushButton("✕")
        self.close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #8fa0b5;
                font-size: 13px;
                padding: 2px 6px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background: #ff2a55;
                color: #ffffff;
            }
        """)
        self.close_btn.clicked.connect(self.on_close)
        tb_layout.addWidget(self.close_btn)

        main_layout.addWidget(self.title_bar)

        # Content Area
        self.content_widget.setParent(self)
        main_layout.addWidget(self.content_widget)

        # Bottom Grip for Resizing
        bottom_layout = QHBoxLayout()
        bottom_layout.setContentsMargins(0, 0, 4, 4)
        bottom_layout.addStretch()
        self.size_grip = QSizeGrip(self)
        self.size_grip.setFixedSize(14, 14)
        self.size_grip.setStyleSheet("background: transparent;")
        bottom_layout.addWidget(self.size_grip)
        main_layout.addLayout(bottom_layout)

    def mousePressEvent(self, event: QMouseEvent):
        self.window_focused.emit(self)
        self.raise_()
        if event.button() == Qt.LeftButton and self.title_bar.geometry().contains(event.pos()):
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._drag_pos and event.buttons() == Qt.LeftButton and not self.is_maximized:
            parent = self.parentWidget()
            new_pos = event.globalPosition().toPoint() - self._drag_pos
            if parent:
                # Constrain inside desktop area
                max_x = parent.width() - 80
                max_y = parent.height() - 80
                new_x = max(0, min(new_pos.x(), max_x))
                new_y = max(0, min(new_pos.y(), max_y))
                self.move(new_x, new_y)
            else:
                self.move(new_pos)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._drag_pos = None
        super().mouseReleaseEvent(event)

    def on_minimize(self):
        self.hide()
        self.window_minimized.emit(self)

    def on_toggle_maximize(self):
        parent = self.parentWidget()
        if not parent:
            return

        if not self.is_maximized:
            self.normal_geometry = self.geometry()
            self.setGeometry(0, 0, parent.width(), parent.height())
            self.is_maximized = True
            self.max_btn.setText("❐")
        else:
            if self.normal_geometry:
                self.setGeometry(self.normal_geometry)
            self.is_maximized = False
            self.max_btn.setText("▢")

    def on_close(self):
        self.hide()
        self.window_closed.emit(self)
