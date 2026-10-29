"""
Virtual Desktops & Multi-Workspace Manager for NOVA OS.
Enables independent workspace desktops (Desktop 1, 2, 3, 4) with window partitioning,
seamless task switching, and taskbar navigation pills.
"""

from typing import Dict, List, Set, Optional, Tuple
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QLabel, QFrame
)
from PySide6.QtCore import Qt, Signal

Tuple_Transition = Tuple[Set[object], Set[object]]

class VirtualDesktopManager:
    """Tracks windows per virtual workspace desktop."""

    def __init__(self, count: int = 3):
        self.total_desktops = count
        self.current_desktop = 1
        # Map: desktop_id -> set of window IDs or WindowFrame instances
        self.desktop_map: Dict[int, Set[object]] = {i: set() for i in range(1, count + 1)}

    def add_window(self, window_obj: object, desktop_id: Optional[int] = None):
        d_id = desktop_id if desktop_id is not None else self.current_desktop
        if d_id not in self.desktop_map:
            self.desktop_map[d_id] = set()
        self.desktop_map[d_id].add(window_obj)

    def remove_window(self, window_obj: object):
        for s in self.desktop_map.values():
            s.discard(window_obj)

    def switch_desktop(self, target_desktop: int) -> Tuple_Transition:
        if target_desktop < 1 or target_desktop > self.total_desktops or target_desktop == self.current_desktop:
            return set(), set()

        old_desktop = self.current_desktop
        self.current_desktop = target_desktop

        to_hide = self.desktop_map.get(old_desktop, set())
        to_show = self.desktop_map.get(target_desktop, set())

        return to_hide, to_show


class VirtualDesktopPillWidget(QFrame):
    desktop_changed = Signal(int)

    def __init__(self, manager: VirtualDesktopManager, parent=None):
        super().__init__(parent)
        self.manager = manager
        self.pills: Dict[int, QPushButton] = {}
        self.setup_ui()

    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(4)

        for d_id in range(1, self.manager.total_desktops + 1):
            btn = QPushButton(f"{d_id}")
            btn.setFixedSize(26, 26)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setToolTip(f"Switch to Virtual Desktop {d_id} (Ctrl+Win+{d_id})")
            btn.clicked.connect(lambda chk, d=d_id: self.select_desktop(d))
            layout.addWidget(btn)
            self.pills[d_id] = btn

        self.update_styles()

    def select_desktop(self, d_id: int):
        if d_id != self.manager.current_desktop:
            to_hide, to_show = self.manager.switch_desktop(d_id)
            for w in to_hide:
                if hasattr(w, "hide"):
                    w.hide()
            for w in to_show:
                if hasattr(w, "show"):
                    w.show()
            self.update_styles()
            self.desktop_changed.emit(d_id)

    def update_styles(self):
        curr = self.manager.current_desktop
        for d_id, btn in self.pills.items():
            if d_id == curr:
                btn.setStyleSheet("""
                    QPushButton {
                        background: #00f0ff;
                        color: #050811;
                        font-weight: 800;
                        font-size: 11px;
                        border-radius: 13px;
                        border: 1px solid #00f0ff;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background: #101729;
                        color: #94a3b8;
                        font-weight: 600;
                        font-size: 11px;
                        border-radius: 13px;
                        border: 1px solid rgba(255,255,255,0.08);
                    }
                    QPushButton:hover {
                        border-color: #00f0ff;
                        color: #ffffff;
                    }
                """)
