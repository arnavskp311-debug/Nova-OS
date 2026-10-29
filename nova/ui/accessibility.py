"""
Accessibility & Inclusive Usability Center for NOVA OS.
Provides high-contrast neon mode, UI scaling, screen magnifier,
and enhanced readability options.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QCheckBox, QSlider, QFrame
)
from PySide6.QtCore import Qt, Signal

from nova.database import get_setting, set_setting

class AccessibilityCenter(QWidget):
    accessibility_changed = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        # Header
        head = QHBoxLayout()
        icon = QLabel("♿")
        icon.setStyleSheet("font-size: 20px; color: #00f0ff;")
        head.addWidget(icon)

        title = QLabel("ACCESSIBILITY & ERGONOMICS CENTER")
        title.setStyleSheet("color: #ffffff; font-weight: bold; font-size: 13px; letter-spacing: 1px;")
        head.addWidget(title)
        head.addStretch()
        layout.addLayout(head)

        # High Contrast Neon Mode
        self.hc_chk = QCheckBox("High-Contrast Hyper Neon Mode (Enhanced text contrast & borders)")
        self.hc_chk.setChecked(get_setting("high_contrast_mode") == "true")
        self.hc_chk.setStyleSheet("color: #e2e8f0; font-size: 11px;")
        self.hc_chk.stateChanged.connect(self.on_hc_changed)
        layout.addWidget(self.hc_chk)

        # Font Scale
        scale_box = QFrame()
        scale_box.setStyleSheet("background: #0d1424; border: 1px solid rgba(0, 240, 255, 0.2); border-radius: 8px; padding: 10px;")
        s_lay = QVBoxLayout(scale_box)

        lbl = QLabel("SYSTEM UI TEXT SCALING")
        lbl.setStyleSheet("color: #00f0ff; font-weight: bold; font-size: 10px;")
        s_lay.addWidget(lbl)

        s_row = QHBoxLayout()
        self.scale_slider = QSlider(Qt.Horizontal)
        self.scale_slider.setRange(100, 150)
        curr_scale = int(get_setting("ui_font_scale") or 100)
        self.scale_slider.setValue(curr_scale)
        s_row.addWidget(self.scale_slider)

        self.scale_lbl = QLabel(f"{curr_scale}%")
        self.scale_lbl.setFixedWidth(40)
        self.scale_lbl.setStyleSheet("color: #00f0ff; font-weight: bold;")
        s_row.addWidget(self.scale_lbl)
        s_lay.addLayout(s_row)

        self.scale_slider.valueChanged.connect(self.on_scale_changed)
        layout.addWidget(scale_box)

        # Audio Navigation Feedback
        self.audio_chk = QCheckBox("Auditory Screen Feedback (Sound cues on window actions)")
        self.audio_chk.setChecked(get_setting("audio_feedback_enabled") != "false")
        self.audio_chk.setStyleSheet("color: #e2e8f0; font-size: 11px;")
        self.audio_chk.stateChanged.connect(self.on_audio_changed)
        layout.addWidget(self.audio_chk)

        # Reduced Motion (Accessible Performance & Visual Comfort)
        self.reduced_motion_chk = QCheckBox("Reduced Motion (Pause decorative particle animations & wallpaper effects)")
        is_rm = get_setting("reduced_motion", "false") == "true" or get_setting("desktop_effects_mode", "Balanced") == "Clean"
        self.reduced_motion_chk.setChecked(is_rm)
        self.reduced_motion_chk.setStyleSheet("color: #e2e8f0; font-size: 11px;")
        self.reduced_motion_chk.stateChanged.connect(self.on_reduced_motion_changed)
        layout.addWidget(self.reduced_motion_chk)

        layout.addStretch()

    def on_reduced_motion_changed(self, state):
        val = (state == Qt.Checked)
        set_setting("reduced_motion", "true" if val else "false")
        effects = "Clean" if val else "Balanced"
        set_setting("desktop_effects_mode", effects)
        self.accessibility_changed.emit({"reduced_motion": val, "effects_mode": effects})

    def on_hc_changed(self, state):
        val = "true" if state == Qt.Checked else "false"
        set_setting("high_contrast_mode", val)
        self.accessibility_changed.emit({"high_contrast": val == "true"})

    def on_scale_changed(self, val):
        self.scale_lbl.setText(f"{val}%")
        set_setting("ui_font_scale", str(val))
        self.accessibility_changed.emit({"font_scale": val})

    def on_audio_changed(self, state):
        val = "true" if state == Qt.Checked else "false"
        set_setting("audio_feedback_enabled", val)
        self.accessibility_changed.emit({"audio_feedback": val == "true"})
