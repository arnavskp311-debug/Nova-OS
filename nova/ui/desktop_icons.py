"""
Desktop Shortcuts & Icon Manager for NOVA OS.
Provides draggable, double-clickable, customizable desktop icons with grid alignment,
persistence, and safe Windows target launching.
"""

import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QMenu, QInputDialog,
    QMessageBox, QFileDialog, QApplication
)
from PySide6.QtCore import Qt, QPoint, Signal, QRect
from PySide6.QtGui import QMouseEvent, QPainter, QColor, QFont, QCursor

from nova.config import DATA_DIR

logger = logging.getLogger("nova.desktop_icons")
SHORTCUTS_FILE = DATA_DIR / "desktop_shortcuts.json"

DEFAULT_SHORTCUTS = [
    {"id": "browser", "title": "NOVA Browser", "icon": "🌐", "type": "app", "target": "browser", "x": 30, "y": 30},
    {"id": "chat", "title": "NOVA AI", "icon": "🤖", "type": "app", "target": "chat", "x": 30, "y": 125},
    {"id": "agent", "title": "AI Agent", "icon": "🚀", "type": "app", "target": "agent", "x": 30, "y": 220},
    {"id": "vault", "title": "Doc Vault", "icon": "📚", "type": "app", "target": "vault", "x": 30, "y": 315},
    {"id": "dashboard", "title": "Telemetry", "icon": "📊", "type": "app", "target": "dashboard", "x": 30, "y": 410},
    {"id": "notes", "title": "NovaPad", "icon": "📝", "type": "app", "target": "notes", "x": 30, "y": 315},
    {"id": "files", "title": "File Vault", "icon": "📁", "type": "app", "target": "files", "x": 30, "y": 410},
    {"id": "terminal", "title": "Terminal", "icon": "💻", "type": "app", "target": "terminal", "x": 30, "y": 505},
    {"id": "settings", "title": "Settings", "icon": "⚙", "type": "app", "target": "settings", "x": 30, "y": 600},
]


class DesktopIconWidget(QWidget):
    """
    Individual desktop shortcut icon with cybernetic hover effects,
    drag-and-drop movement, and right-click context menu.
    """
    activated = Signal(dict)
    position_changed = Signal(dict, int, int)
    delete_requested = Signal(dict)
    rename_requested = Signal(dict, str)

    def __init__(self, shortcut_data: dict, parent=None):
        super().__init__(parent)
        self.data = shortcut_data
        self.setFixedSize(76, 82)
        self.setCursor(Qt.PointingHandCursor)
        self._is_dragging = False
        self._drag_start_pos = QPoint()
        self._drag_offset = QPoint()
        self._is_hovered = False

        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignCenter)

        # Icon Label
        self.icon_lbl = QLabel(self.data.get("icon", "❖"))
        self.icon_lbl.setAlignment(Qt.AlignCenter)
        self.icon_lbl.setStyleSheet("font-size: 28px; background: transparent;")
        layout.addWidget(self.icon_lbl)

        # Title Label
        self.title_lbl = QLabel(self.data.get("title", "Shortcut"))
        self.title_lbl.setAlignment(Qt.AlignCenter)
        self.title_lbl.setWordWrap(True)
        self.title_lbl.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font-size: 11px;
                font-weight: 600;
                background-color: rgba(9, 14, 26, 0.85);
                border: 1px solid rgba(0, 240, 255, 0.25);
                border-radius: 4px;
                padding: 2px 4px;
            }
        """)
        layout.addWidget(self.title_lbl)

        # Initial position
        self.move(self.data.get("x", 30), self.data.get("y", 30))

    def update_data(self, new_data: dict):
        self.data = new_data
        self.title_lbl.setText(self.data.get("title", "Shortcut"))
        self.icon_lbl.setText(self.data.get("icon", "❖"))

    def enterEvent(self, event):
        self._is_hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._is_hovered = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        if self._is_hovered or self._is_dragging:
            # Highlight border & glass background
            painter.setBrush(QColor(0, 240, 255, 30))
            painter.setPen(QColor(0, 240, 255, 160))
            painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 8, 8)
        else:
            # Subtle resting glass plate
            painter.setBrush(QColor(9, 14, 26, 140))
            painter.setPen(QColor(0, 240, 255, 45))
            painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 8, 8)

        painter.end()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self._is_dragging = True
            self._drag_start_pos = event.globalPosition().toPoint()
            self._drag_offset = event.pos()
            self.raise_()
            event.accept()
        elif event.button() == Qt.RightButton:
            self.show_context_menu(event.globalPosition().toPoint())
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._is_dragging and (event.buttons() & Qt.LeftButton):
            parent = self.parentWidget()
            if parent:
                new_pos = event.globalPosition().toPoint() - parent.mapToGlobal(QPoint(0, 0)) - self._drag_offset
                max_x = max(0, parent.width() - self.width())
                max_y = max(0, parent.height() - self.height())
                nx = max(0, min(new_pos.x(), max_x))
                ny = max(0, min(new_pos.y(), max_y))
                self.move(nx, ny)
                event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if self._is_dragging and event.button() == Qt.LeftButton:
            self._is_dragging = False
            self.data["x"] = self.x()
            self.data["y"] = self.y()
            self.position_changed.emit(self.data, self.x(), self.y())
            event.accept()
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.activated.emit(self.data)
            event.accept()
        else:
            super().mouseDoubleClickEvent(event)

    def show_context_menu(self, global_pos: QPoint):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #0c1424;
                color: #e2e8f0;
                border: 1px solid #00f0ff;
                border-radius: 8px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 20px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #0052cc;
                color: #ffffff;
            }
        """)

        open_act = menu.addAction(f"Open '{self.data.get('title')}'")
        open_loc_act = menu.addAction("Open File Location")
        menu.addSeparator()
        rename_act = menu.addAction("Rename Shortcut")
        remove_act = menu.addAction("Delete Shortcut")
        menu.addSeparator()
        prop_act = menu.addAction("Properties")

        chosen = menu.exec(global_pos)
        if chosen == open_act:
            self.activated.emit(self.data)
        elif chosen == open_loc_act:
            target = self.data.get("target", "")
            s_type = self.data.get("type", "app")
            if s_type in ("file", "folder") and os.path.exists(target):
                import subprocess
                subprocess.Popen(f'explorer /select,"{os.path.abspath(target)}"')
            else:
                QMessageBox.information(
                    self, "File Location",
                    f"Target Application: {self.data.get('title')}\nIdentifier: {target}\nIntegrated into NOVA Desktop Environment."
                )
        elif chosen == rename_act:
            new_title, ok = QInputDialog.getText(
                self, "Rename Shortcut", "Enter new name for shortcut:", text=self.data.get("title", "")
            )
            if ok and new_title.strip():
                self.rename_requested.emit(self.data, new_title.strip())
        elif chosen == remove_act:
            reply = QMessageBox.question(
                self,
                "Delete Shortcut",
                f"Delete the desktop shortcut for '{self.data.get('title')}'?\n(The original file or application will NOT be deleted.)",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.delete_requested.emit(self.data)
        elif chosen == prop_act:
            target = self.data.get("target", "N/A")
            s_type = self.data.get("type", "app").upper()
            QMessageBox.information(
                self,
                f"Shortcut Properties - {self.data.get('title')}",
                f"Name: {self.data.get('title')}\n"
                f"Type: {s_type}\n"
                f"Target: {target}\n"
                f"Position: X={self.x()}, Y={self.y()}\n"
                f"Status: Safe Desktop Shortcut\n"
                f"Environment: NOVA OS Workspace"
            )


class DesktopIconManager:
    """
    Manages loading, saving, rendering, and launching desktop shortcuts.
    """
    def __init__(self, canvas_widget: QWidget):
        self.canvas = canvas_widget
        self.shortcuts: List[Dict[str, Any]] = []
        self.widgets: Dict[str, DesktopIconWidget] = {}
        self.load_shortcuts()

    def load_shortcuts(self):
        """Loads shortcuts from JSON or initializes default shortcuts."""
        if SHORTCUTS_FILE.exists():
            try:
                with open(SHORTCUTS_FILE, "r", encoding="utf-8") as f:
                    self.shortcuts = json.load(f)
            except Exception as e:
                logger.error(f"Error loading shortcuts from {SHORTCUTS_FILE}: {e}")
                self.shortcuts = list(DEFAULT_SHORTCUTS)
        else:
            self.shortcuts = list(DEFAULT_SHORTCUTS)
            self.save_shortcuts()

    def save_shortcuts(self):
        """Persists shortcuts and their positions to JSON."""
        try:
            with open(SHORTCUTS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.shortcuts, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving shortcuts to {SHORTCUTS_FILE}: {e}")

    def render_icons(self, on_activate_callback):
        """Instantiates DesktopIconWidget objects on the canvas."""
        # Clear existing
        for w in self.widgets.values():
            w.deleteLater()
        self.widgets.clear()

        for s_data in self.shortcuts:
            s_id = s_data["id"]
            widget = DesktopIconWidget(s_data, parent=self.canvas)
            widget.activated.connect(on_activate_callback)
            widget.position_changed.connect(self._on_icon_moved)
            widget.delete_requested.connect(self._on_icon_deleted)
            widget.rename_requested.connect(self._on_icon_renamed)
            widget.show()
            self.widgets[s_id] = widget

    def add_shortcut(self, title: str, icon: str, s_type: str, target: str, on_activate_callback) -> bool:
        """Adds a new shortcut to the desktop."""
        import uuid
        s_id = f"custom_{uuid.uuid4().hex[:8]}"

        # Calculate open position
        x, y = self._find_next_grid_position()
        new_item = {
            "id": s_id,
            "title": title,
            "icon": icon,
            "type": s_type,
            "target": target,
            "x": x,
            "y": y
        }
        self.shortcuts.append(new_item)
        self.save_shortcuts()

        # Create widget
        widget = DesktopIconWidget(new_item, parent=self.canvas)
        widget.activated.connect(on_activate_callback)
        widget.position_changed.connect(self._on_icon_moved)
        widget.delete_requested.connect(self._on_icon_deleted)
        widget.rename_requested.connect(self._on_icon_renamed)
        widget.show()
        self.widgets[s_id] = widget
        return True

    def _find_next_grid_position(self) -> tuple:
        """Finds the next available (x, y) slot in standard grid coordinates."""
        used_slots = set((s.get("x", 30), s.get("y", 30)) for s in self.shortcuts)
        for col in range(8):
            x = 30 + (col * 95)
            for row in range(10):
                y = 30 + (row * 95)
                # Check proximity
                occupied = any(abs(x - ux) < 50 and abs(y - uy) < 50 for ux, uy in used_slots)
                if not occupied:
                    return (x, y)
        return (30, 30)

    def arrange_grid(self):
        """Snaps all desktop shortcuts into clean vertical columns on the left."""
        col = 0
        row = 0
        canvas_h = max(400, self.canvas.height() - 80)

        for s in self.shortcuts:
            x = 30 + (col * 95)
            y = 30 + (row * 95)
            s["x"] = x
            s["y"] = y

            if s["id"] in self.widgets:
                self.widgets[s["id"]].move(x, y)

            row += 1
            if 30 + ((row + 1) * 95) > canvas_h:
                row = 0
                col += 1

        self.save_shortcuts()

    def restore_default_layout(self, on_activate_callback=None):
        """Restores default desktop shortcuts and grid positioning."""
        import copy
        self.shortcuts = copy.deepcopy(DEFAULT_SHORTCUTS)
        self.save_shortcuts()
        if on_activate_callback:
            self.render_icons(on_activate_callback)
        else:
            self.arrange_grid()

    def _on_icon_moved(self, data: dict, x: int, y: int):
        for s in self.shortcuts:
            if s["id"] == data["id"]:
                s["x"] = x
                s["y"] = y
                break
        self.save_shortcuts()

    def _on_icon_deleted(self, data: dict):
        s_id = data["id"]
        self.shortcuts = [s for s in self.shortcuts if s["id"] != s_id]
        if s_id in self.widgets:
            self.widgets[s_id].deleteLater()
            del self.widgets[s_id]
        self.save_shortcuts()

    def _on_icon_renamed(self, data: dict, new_title: str):
        s_id = data["id"]
        for s in self.shortcuts:
            if s["id"] == data["id"]:
                s["title"] = new_title
                break
        if s_id in self.widgets:
            self.widgets[s_id].update_data(data)
        self.save_shortcuts()

    def launch_target(self, shortcut_data: dict, app_launcher_callback) -> bool:
        """Safely opens the shortcut target."""
        s_type = shortcut_data.get("type", "app")
        target = shortcut_data.get("target", "")

        if s_type == "app":
            app_launcher_callback(target)
            return True
        elif s_type in ["file", "folder"]:
            p = Path(target)
            if not p.exists():
                QMessageBox.warning(
                    self.canvas,
                    "Target Missing",
                    f"The file or folder target does not exist:\n{target}"
                )
                return False

            try:
                # Open with standard Windows default handler without cmd/shell injection
                os.startfile(str(p))
                return True
            except Exception as e:
                logger.error(f"Error opening target {target}: {e}")
                QMessageBox.critical(
                    self.canvas,
                    "Launch Error",
                    f"Failed to open target:\n{e}"
                )
                return False

        return False
