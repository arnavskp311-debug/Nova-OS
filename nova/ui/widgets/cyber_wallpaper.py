"""
NOVA OS Dynamic Reactive Cyber Wallpaper.
Procedural, hardware-reactive canvas rendering an animated perspective cyber grid
and glowing particle waveforms synchronized to real-time CPU and telemetry metrics.
Fidelity modes: Clean (no effects, max readability), Balanced (subtle, low power), Cyber (controlled neon).
"""

import math
import random
from typing import List, Dict, Any, Optional
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QTimer, QPointF
from PySide6.QtGui import QPainter, QColor, QPen, QBrush

from nova.database import get_setting, set_setting


class Particle:
    def __init__(self, w: int, h: int, max_alpha: int = 40):
        self.max_alpha = max_alpha
        self.reset(w, h)

    def reset(self, w: int, h: int):
        self.x = random.uniform(0, max(100, w))
        self.y = random.uniform(0, max(100, h))
        self.vx = random.uniform(-0.25, 0.25)
        self.vy = random.uniform(-0.45, -0.15)
        self.size = random.uniform(1.2, 2.2)
        self.alpha = random.uniform(15, self.max_alpha)
        self.color = random.choice([
            QColor(0, 240, 255),    # Cyan
            QColor(176, 38, 255),   # Purple
            QColor(0, 255, 136),    # Emerald
        ])

    def update(self, w: int, h: int, speed_factor: float = 1.0):
        self.x += self.vx * speed_factor
        self.y += self.vy * speed_factor
        if self.y < 0 or self.x < 0 or self.x > w:
            self.reset(w, h)
            self.y = h


class CyberWallpaperWidget(QWidget):
    """
    Animated futuristic background canvas widget.
    Renders purely as a non-interactive background layer below icons and windows.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)  # Never intercepts clicks or drags
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setStyleSheet("background: transparent;")

        self.cpu_percent = 10.0
        self.grid_offset = 0.0
        self.particles: List[Particle] = []
        self._enabled = True
        self.effects_mode = "balanced"

        # Update timer (gentle on Intel Core i3)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._on_tick)

        # Load persisted mode (default to Balanced for best readability & efficiency)
        initial_mode = get_setting("desktop_effects_mode", "Balanced")
        self.set_effects_mode(initial_mode)

    def set_effects_mode(self, mode: str):
        """Sets the visual effects mode: 'Clean', 'Balanced', or 'Cyber'."""
        mode_str = (mode or "Balanced").lower().split()[0]
        if mode_str not in ("clean", "balanced", "cyber"):
            mode_str = "balanced"
        self.effects_mode = mode_str

        if self.effects_mode == "clean":
            self._enabled = False
            self.particles.clear()
            self.timer.stop()
            self.update()
        elif self.effects_mode == "balanced":
            self._enabled = True
            self._init_particles(10, max_alpha=40)
            self.timer.setInterval(50)  # 20 FPS
            if not self.timer.isActive():
                self.timer.start()
            self.update()
        else:  # "cyber"
            self._enabled = True
            self._init_particles(16, max_alpha=65)
            self.timer.setInterval(40)  # 25 FPS
            if not self.timer.isActive():
                self.timer.start()
            self.update()

    def _init_particles(self, count: int, max_alpha: int = 40):
        w = max(100, self.width() or 1200)
        h = max(100, self.height() or 800)
        self.particles = [Particle(w, h, max_alpha=max_alpha) for _ in range(count)]

    def pause(self):
        """Pauses animation loop (e.g. when OS is minimized)."""
        if self.timer.isActive():
            self.timer.stop()

    def resume(self):
        """Resumes animation loop if enabled."""
        if self._enabled and self.effects_mode != "clean" and not self.timer.isActive():
            self.timer.start()

    def set_telemetry(self, cpu_percent: float = 10.0, **kwargs):
        """Updates animation speed and pulse brightness based on live CPU load."""
        val = kwargs.get("cpu_load", cpu_percent)
        try:
            self.cpu_percent = max(5.0, min(100.0, float(val)))
        except (ValueError, TypeError):
            self.cpu_percent = 10.0

    def _on_tick(self):
        if not self._enabled or self.effects_mode == "clean":
            return

        w = self.width()
        h = self.height()
        if w <= 0 or h <= 0:
            return

        speed_scale = 0.35 if self.effects_mode == "balanced" else 0.65
        speed = speed_scale * (0.8 + (self.cpu_percent / 150.0))

        self.grid_offset = (self.grid_offset + speed * 0.6) % 35.0
        for p in self.particles:
            p.update(w, h, speed_factor=speed)

        self.update()

    def paintEvent(self, event):
        if not self._enabled or self.effects_mode == "clean":
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        if w <= 0 or h <= 0:
            painter.end()
            return

        # NO dark full-screen overlay! Allows wallpaper underneath to stay bright and readable.

        # 1. Perspective Ground Cyber Grid (Subtle, strictly in bottom area)
        horizon = int(h * (0.75 if self.effects_mode == "balanced" else 0.70))
        num_h_lines = 6 if self.effects_mode == "balanced" else 8
        base_alpha = 10 if self.effects_mode == "balanced" else 18

        # Horizontal perspective lines
        for i in range(num_h_lines):
            progress = (i / num_h_lines) ** 2.2
            y = horizon + progress * (h - horizon) + (self.grid_offset * (progress ** 1.4))
            if y < h:
                alpha = int(base_alpha + progress * (12 if self.effects_mode == "balanced" else 18))
                painter.setPen(QPen(QColor(0, 240, 255, alpha), 1))
                painter.drawLine(0, int(y), w, int(y))

        # Vanishing vertical perspective lines converging to horizon center
        cx = w // 2
        step_range = 8 if self.effects_mode == "balanced" else 11
        for x_step in range(-step_range, step_range + 1):
            dest_x = cx + x_step * (w // 14) * 1.6
            painter.setPen(QPen(QColor(0, 240, 255, base_alpha), 1))
            painter.drawLine(cx, horizon, int(dest_x), h)

        # 2. Floating Quantum Data Particles (Soft, low-opacity ambient dust)
        for p in self.particles:
            col = QColor(p.color)
            alpha = min(75, int(p.alpha * (0.8 + self.cpu_percent / 200.0)))
            col.setAlpha(alpha)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(col))
            painter.drawEllipse(QPointF(p.x, p.y), p.size, p.size)

        # 3. Subtle Corner HUD Accents (Only in Cyber mode)
        if self.effects_mode == "cyber":
            hud_pen = QPen(QColor(0, 240, 255, 30), 1)
            painter.setPen(hud_pen)
            painter.drawLine(16, 16, 36, 16)
            painter.drawLine(16, 16, 16, 36)
            painter.drawLine(w - 36, 16, w - 16, 16)
            painter.drawLine(w - 16, 16, w - 16, 36)

        painter.end()
