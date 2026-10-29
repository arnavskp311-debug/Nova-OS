"""
Aero Edge Window Snapping Engine for NOVA OS.
Enables Windows-style smart window snapping:
- Left 50% snap
- Right 50% snap
- Top maximize snap
- 4-Corner quadrant snapping (Top-Left, Top-Right, Bottom-Left, Bottom-Right)
- Visual translucent snap preview zone
"""

from typing import Optional, Tuple
from PySide6.QtWidgets import QWidget, QFrame
from PySide6.QtCore import Qt, QRect

class SnapZone:
    NONE = "none"
    LEFT = "left"
    RIGHT = "right"
    MAXIMIZE = "maximize"
    TOP_LEFT = "top_left"
    TOP_RIGHT = "top_right"
    BOTTOM_LEFT = "bottom_left"
    BOTTOM_RIGHT = "bottom_right"


class SnapGuide(QFrame):
    """Translucent glowing outline showing where the snapped window will land."""

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setObjectName("SnapGuide")
        self.setStyleSheet("""
            QFrame#SnapGuide {
                background-color: rgba(0, 240, 255, 0.12);
                border: 2px dashed #00f0ff;
                border-radius: 8px;
            }
        """)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.hide()


class WindowSnapper:
    """Calculates snap zones and target geometries for floating windows."""

    THRESHOLD = 18  # Pixels from screen boundary to trigger snap

    @classmethod
    def detect_snap_zone(cls, frame_rect: QRect, parent_rect: QRect) -> str:
        """Determines if the window is currently positioned in a snap zone."""
        x = frame_rect.x()
        y = frame_rect.y()
        right = x + frame_rect.width()
        bottom = y + frame_rect.height()
        p_w = parent_rect.width()
        p_h = parent_rect.height()

        # Check corners first
        if x <= cls.THRESHOLD and y <= cls.THRESHOLD:
            return SnapZone.TOP_LEFT
        if right >= p_w - cls.THRESHOLD and y <= cls.THRESHOLD:
            return SnapZone.TOP_RIGHT
        if x <= cls.THRESHOLD and bottom >= p_h - cls.THRESHOLD:
            return SnapZone.BOTTOM_LEFT
        if right >= p_w - cls.THRESHOLD and bottom >= p_h - cls.THRESHOLD:
            return SnapZone.BOTTOM_RIGHT

        # Check top edge for maximize
        if y <= cls.THRESHOLD:
            return SnapZone.MAXIMIZE

        # Check side edges
        if x <= cls.THRESHOLD:
            return SnapZone.LEFT
        if right >= p_w - cls.THRESHOLD:
            return SnapZone.RIGHT

        return SnapZone.NONE

    @classmethod
    def get_snap_geometry(cls, zone: str, parent_rect: QRect) -> Optional[QRect]:
        """Returns the target QRect for a given snap zone."""
        w = parent_rect.width()
        h = parent_rect.height()
        half_w = w // 2
        half_h = h // 2

        if zone == SnapZone.LEFT:
            return QRect(0, 0, half_w, h)
        elif zone == SnapZone.RIGHT:
            return QRect(half_w, 0, half_w, h)
        elif zone == SnapZone.MAXIMIZE:
            return QRect(0, 0, w, h)
        elif zone == SnapZone.TOP_LEFT:
            return QRect(0, 0, half_w, half_h)
        elif zone == SnapZone.TOP_RIGHT:
            return QRect(half_w, 0, half_w, half_h)
        elif zone == SnapZone.BOTTOM_LEFT:
            return QRect(0, half_h, half_w, half_h)
        elif zone == SnapZone.BOTTOM_RIGHT:
            return QRect(half_w, half_h, half_w, half_h)

        return None
