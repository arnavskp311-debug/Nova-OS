"""
NOVA OS Dynamic Reactive Cyber Wallpaper.
Procedural, hardware-reactive canvas rendering an animated perspective cyber grid
and glowing particle waveforms synchronized to real-time CPU and telemetry metrics.
"""

import math
import random
from typing import List, Dict, Any
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QTimer, QPointF
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QLinearGradient

class Particle:
    def __init__(self, w: int, h: int):
        self.reset(w, h)

    def reset(self, w: int, h: int):
        self.x = random.uniform(0, max(100, w))
        self.y = random.uniform(0, max(100, h))
        self.vx = random.uniform(-0.5, 0.5)
        self.vy = random.uniform(-0.8, -0.2)
        self.size = random.uniform(1.5, 3.5)
        self.alpha = random.uniform(40, 160)
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
    """Animated futuristic canvas widget."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)  # Allow mouse clicks through to desktop icons
        self.cpu_percent = 15.0
        self.grid_offset = 0.0
        self.particles: List[Particle] = []
        self._enabled = True

        self._init_particles(35)

        # 30 FPS update timer (gentle on Intel Core i3)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._on_tick)
        self.timer.start(33)

    def _init_particles(self, count: int):
        self.particles = [Particle(1200, 800) for _ in range(count)]

    def set_telemetry(self, cpu_percent: float = 10.0, **kwargs):
        """Updates animation speed and pulse brightness based on live CPU load."""
        val = kwargs.get("cpu_load", cpu_percent)
        self.cpu_percent = max(5.0, min(100.0, float(val)))

    def _on_tick(self):
        if not self._enabled:
            return

        w = self.width()
        h = self.height()
        speed = 0.8 + (self.cpu_percent / 100.0) * 1.5

        self.grid_offset = (self.grid_offset + speed * 0.8) % 40.0
        for p in self.particles:
            p.update(w, h, speed_factor=speed)

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()

        # 1. Deep Space Radial Gradient Background
        bg_grad = QLinearGradient(0, 0, 0, h)
        bg_grad.setColorAt(0.0, QColor(5, 8, 17, 240))
        bg_grad.setColorAt(1.0, QColor(10, 14, 25, 250))
        painter.fillRect(0, 0, w, h, bg_grad)

        # 2. Perspective Ground Cyber Grid (Bottom 40% of screen)
        horizon = int(h * 0.65)
        painter.setPen(QPen(QColor(0, 240, 255, 35), 1))

        # Horizontal perspective lines
        num_h_lines = 10
        for i in range(num_h_lines):
            progress = (i / num_h_lines) ** 2.2
            y = horizon + progress * (h - horizon) + (self.grid_offset * (progress ** 1.5))
            if y < h:
                alpha = int(15 + progress * 50)
                painter.setPen(QPen(QColor(0, 240, 255, alpha), 1))
                painter.drawLine(0, int(y), w, int(y))

        # Vanishing vertical perspective lines converging to horizon center
        cx = w // 2
        for x_step in range(-12, 13):
            dest_x = cx + x_step * (w // 14) * 1.8
            painter.setPen(QPen(QColor(0, 240, 255, 30), 1))
            painter.drawLine(cx, horizon, int(dest_x), h)

        # 3. Floating Quantum Data Particles
        for p in self.particles:
            col = QColor(p.color)
            # Modulate brightness based on CPU load
            alpha = min(220, int(p.alpha * (0.8 + self.cpu_percent / 120.0)))
            col.setAlpha(alpha)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(col))
            painter.drawEllipse(QPointF(p.x, p.y), p.size, p.size)

        # 4. Subtle Ambient Corner HUD Accents
        hud_pen = QPen(QColor(0, 240, 255, 60), 1)
        painter.setPen(hud_pen)
        # Top-left reticle
        painter.drawLine(16, 16, 40, 16)
        painter.drawLine(16, 16, 16, 40)
        # Top-right reticle
        painter.drawLine(w - 40, 16, w - 16, 16)
        painter.drawLine(w - 16, 16, w - 16, 40)

        painter.end()
