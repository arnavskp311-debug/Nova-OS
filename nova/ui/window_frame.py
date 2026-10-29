"""
Futuristic Window Container & Manager for NOVA OS.
Provides draggable, resizable, floating OS-style window frames with cyber controls
and Aero edge window snapping (Left, Right, Maximize, Corner Quadrants).
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QSizeGrip
)
from PySide6.QtCore import Qt, QPoint, Signal, QRect
from PySide6.QtGui import QMouseEvent

from nova.ui.window_snapping import WindowSnapper, SnapZone, SnapGuide

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
        self._snap_guide: Optional[SnapGuide] = None
        self._active_snap_zone: str = SnapZone.NONE

        self.setup_ui()

    def setup_ui(self):
        self.setObjectName("WindowFrame")
        self.setStyleSheet("""
            QFrame#WindowFrame {
                background-color: #09101f;
                border: 1px solid rgba(0, 210, 230, 0.25);
                border-radius: 8px;
            }
        """)
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
                background-color: #0e172b;
                border-top-left-radius: 7px;
                border-top-right-radius: 7px;
                border-bottom: 1px solid rgba(0, 210, 230, 0.18);
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
        if self._drag_pos and event.buttons() == Qt.LeftButton:
            parent = self.parentWidget()
            if self.is_maximized:
                # If dragging while maximized, restore normal size and anchor to cursor
                if self.normal_geometry:
                    self.setGeometry(self.normal_geometry)
                self.is_maximized = False
                self.max_btn.setText("▢")

            new_pos = event.globalPosition().toPoint() - self._drag_pos
            if parent:
                max_x = parent.width() - 40
                max_y = parent.height() - 40
                new_x = max(-self.width() + 40, min(new_pos.x(), max_x))
                new_y = max(0, min(new_pos.y(), max_y))
                self.move(new_x, new_y)

                # Check edge snapping zone
                zone = WindowSnapper.detect_snap_zone(self.geometry(), parent.rect())
                self._active_snap_zone = zone
                if zone != SnapZone.NONE:
                    guide_geom = WindowSnapper.get_snap_geometry(zone, parent.rect())
                    if guide_geom:
                        if not self._snap_guide:
                            self._snap_guide = SnapGuide(parent)
                        self._snap_guide.setGeometry(guide_geom)
                        self._snap_guide.show()
                        self._snap_guide.raise_()
                else:
                    if self._snap_guide:
                        self._snap_guide.hide()
            else:
                self.move(new_pos)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if self._drag_pos:
            self._drag_pos = None
            if self._snap_guide:
                self._snap_guide.hide()

            parent = self.parentWidget()
            if parent and self._active_snap_zone != SnapZone.NONE:
                snap_geom = WindowSnapper.get_snap_geometry(self._active_snap_zone, parent.rect())
                if snap_geom:
                    if not self.normal_geometry:
                        self.normal_geometry = self.geometry()
                    self.setGeometry(snap_geom)
                    if self._active_snap_zone == SnapZone.MAXIMIZE:
                        self.is_maximized = True
                        self.max_btn.setText("❐")
                self._active_snap_zone = SnapZone.NONE

        super().mouseReleaseEvent(event)

    def on_minimize(self):
        self.hide()
        self.window_minimized.emit(self)

    def maximize_window(self):
        parent = self.parentWidget()
        if not parent:
            return
        if not self.is_maximized and self.geometry().width() > 0:
            self.normal_geometry = self.geometry()
        self.setGeometry(0, 0, parent.width(), parent.height())
        self.is_maximized = True
        self.max_btn.setText("❐")
        self.max_btn.setToolTip("Restore Window (Esc)")

    def restore_window(self):
        parent = self.parentWidget()
        if not self.is_maximized:
            return
        if self.normal_geometry and parent:
            gw = min(self.normal_geometry.width(), max(420, parent.width() - 40))
            gh = min(self.normal_geometry.height(), max(320, parent.height() - 40))
            gx = max(20, min(self.normal_geometry.x(), max(20, parent.width() - gw - 20)))
            gy = max(20, min(self.normal_geometry.y(), max(20, parent.height() - gh - 20)))
            self.setGeometry(gx, gy, gw, gh)
        elif parent:
            gw = min(920, max(420, parent.width() - 80))
            gh = min(680, max(320, parent.height() - 80))
            gx = max(20, (parent.width() - gw) // 2)
            gy = max(20, (parent.height() - gh) // 2)
            self.setGeometry(gx, gy, gw, gh)
        self.is_maximized = False
        self.max_btn.setText("▢")
        self.max_btn.setToolTip("Maximize Window")

    def on_toggle_maximize(self):
        if not self.is_maximized:
            self.maximize_window()
        else:
            self.restore_window()

    def on_close(self):
        self.hide()
        self.window_closed.emit(self)
