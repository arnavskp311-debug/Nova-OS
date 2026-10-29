"""
Interactive 2D Game Canvas & Retro Synth Engine for Pajama.
Allows drawing primitives (rect, circle, text) and running built-in games
(Cyber Snake, Neon Pong) with keyboard interactions.
"""

from typing import List, Tuple, Optional
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFrame
from PySide6.QtCore import Qt, QTimer, QRect, QPoint
from PySide6.QtGui import QPainter, QColor, QFont, QPen, QBrush, QKeyEvent

class CyberCanvasWidget(QWidget):
    """2D Graphics Canvas widget for Pajama programs."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(500, 360)
        self.setFocusPolicy(Qt.StrongFocus)
        self.bg_color = QColor(10, 15, 28)
        self.draw_commands = []
        self.game_mode: Optional[str] = None

        # Game states
        self.snake_body = [(10, 10), (10, 11), (10, 12)]
        self.snake_dir = (0, -1)
        self.food_pos = (15, 15)
        self.score = 0
        self.game_over = False

        self.game_timer = QTimer(self)
        self.game_timer.timeout.connect(self.game_tick)

    def clear_canvas(self, color: str = "#0a0f1c"):
        self.bg_color = QColor(color)
        self.draw_commands.clear()
        self.update()

    def draw_rect(self, x: int, y: int, w: int, h: int, color: str = "#00f0ff"):
        self.draw_commands.append(("rect", x, y, w, h, QColor(color)))
        self.update()

    def draw_circle(self, x: int, y: int, radius: int, color: str = "#b026ff"):
        self.draw_commands.append(("circle", x, y, radius, QColor(color)))
        self.update()

    def draw_text(self, x: int, y: int, text: str, color: str = "#ffffff"):
        self.draw_commands.append(("text", x, y, text, QColor(color)))
        self.update()

    def start_snake(self):
        """Starts the retro Cyber Snake game."""
        self.game_mode = "snake"
        self.snake_body = [(10, 10), (10, 11), (10, 12)]
        self.snake_dir = (1, 0)
        self.food_pos = (18, 12)
        self.score = 0
        self.game_over = False
        self.game_timer.start(120)
        self.setFocus()
        self.update()

    def start_pong(self):
        """Starts the retro Neon Pong game."""
        self.game_mode = "pong"
        self.pong_ball = [250, 180]
        self.pong_vel = [4, 3]
        self.paddle_y = 140
        self.score = 0
        self.game_over = False
        self.game_timer.start(30)
        self.setFocus()
        self.update()

    def game_tick(self):
        if self.game_mode == "snake":
            self._tick_snake()
        elif self.game_mode == "pong":
            self._tick_pong()
        self.update()

    def _tick_snake(self):
        if self.game_over:
            return
        head_x, head_y = self.snake_body[0]
        dx, dy = self.snake_dir
        new_head = (head_x + dx, head_y + dy)

        # Wall collisions
        grid_w, grid_h = 50, 36
        if new_head[0] < 0 or new_head[0] >= grid_w or new_head[1] < 0 or new_head[1] >= grid_h or new_head in self.snake_body:
            self.game_over = True
            self.game_timer.stop()
            return

        self.snake_body.insert(0, new_head)
        if new_head == self.food_pos:
            self.score += 10
            import random
            self.food_pos = (random.randint(2, grid_w - 3), random.randint(2, grid_h - 3))
        else:
            self.snake_body.pop()

    def _tick_pong(self):
        if self.game_over:
            return
        self.pong_ball[0] += self.pong_vel[0]
        self.pong_ball[1] += self.pong_vel[1]

        # Top/Bottom bounce
        if self.pong_ball[1] <= 10 or self.pong_ball[1] >= self.height() - 10:
            self.pong_vel[1] *= -1

        # Right wall bounce
        if self.pong_ball[0] >= self.width() - 15:
            self.pong_vel[0] *= -1

        # Left paddle collision
        if self.pong_ball[0] <= 30:
            if self.paddle_y <= self.pong_ball[1] <= self.paddle_y + 80:
                self.pong_vel[0] = abs(self.pong_vel[0]) + 1
                self.score += 1
            else:
                self.game_over = True
                self.game_timer.stop()

    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()
        if self.game_mode == "snake":
            if key == Qt.Key_Up and self.snake_dir != (0, 1):
                self.snake_dir = (0, -1)
            elif key == Qt.Key_Down and self.snake_dir != (0, -1):
                self.snake_dir = (0, 1)
            elif key == Qt.Key_Left and self.snake_dir != (1, 0):
                self.snake_dir = (-1, 0)
            elif key == Qt.Key_Right and self.snake_dir != (-1, 0):
                self.snake_dir = (1, 0)
            elif key == Qt.Key_R and self.game_over:
                self.start_snake()
            event.accept()
        elif self.game_mode == "pong":
            if key == Qt.Key_Up:
                self.paddle_y = max(10, self.paddle_y - 25)
            elif key == Qt.Key_Down:
                self.paddle_y = min(self.height() - 90, self.paddle_y + 25)
            elif key == Qt.Key_R and self.game_over:
                self.start_pong()
            event.accept()
        else:
            super().keyPressEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), self.bg_color)

        if self.game_mode == "snake":
            # Draw Snake
            cell_size = 10
            painter.setBrush(QBrush(QColor(0, 240, 255)))
            painter.setPen(Qt.NoPen)
            for x, y in self.snake_body:
                painter.drawRect(x * cell_size, y * cell_size, cell_size - 1, cell_size - 1)

            # Draw Food
            painter.setBrush(QBrush(QColor(255, 42, 85)))
            fx, fy = self.food_pos
            painter.drawRect(fx * cell_size, fy * cell_size, cell_size - 1, cell_size - 1)

            # Draw Score
            painter.setPen(QColor(255, 255, 255))
            painter.setFont(QFont("Segoe UI", 10, QFont.Bold))
            painter.drawText(10, 20, f"CYBER SNAKE • SCORE: {self.score}")
            if self.game_over:
                painter.setPen(QColor(255, 42, 85))
                painter.setFont(QFont("Segoe UI", 16, QFont.Bold))
                painter.drawText(self.rect(), Qt.AlignCenter, "GAME OVER\nPress R to Restart")

        elif self.game_mode == "pong":
            # Draw Paddle
            painter.setBrush(QBrush(QColor(0, 255, 136)))
            painter.setPen(Qt.NoPen)
            painter.drawRect(16, self.paddle_y, 12, 80)

            # Draw Ball
            painter.setBrush(QBrush(QColor(0, 240, 255)))
            painter.drawEllipse(int(self.pong_ball[0]), int(self.pong_ball[1]), 12, 12)

            # Draw Score
            painter.setPen(QColor(255, 255, 255))
            painter.setFont(QFont("Segoe UI", 10, QFont.Bold))
            painter.drawText(10, 20, f"NEON PONG • SCORE: {self.score}")
            if self.game_over:
                painter.setPen(QColor(255, 42, 85))
                painter.setFont(QFont("Segoe UI", 16, QFont.Bold))
                painter.drawText(self.rect(), Qt.AlignCenter, "GAME OVER\nPress R to Restart")

        else:
            # Custom Pajama Draw Commands
            for cmd in self.draw_commands:
                ctype = cmd[0]
                if ctype == "rect":
                    _, x, y, w, h, col = cmd
                    painter.setBrush(QBrush(col))
                    painter.setPen(Qt.NoPen)
                    painter.drawRect(x, y, w, h)
                elif ctype == "circle":
                    _, x, y, r, col = cmd
                    painter.setBrush(QBrush(col))
                    painter.setPen(Qt.NoPen)
                    painter.drawEllipse(x - r, y - r, r * 2, r * 2)
                elif ctype == "text":
                    _, x, y, txt, col = cmd
                    painter.setPen(col)
                    painter.setFont(QFont("Segoe UI", 10))
                    painter.drawText(x, y, txt)

        painter.end()


class PajamaCanvasWindow(QFrame):
    """Standalone container window for 2D Canvas games and sketches."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Pajama 2D Game Canvas")
        self.setStyleSheet("background: #090e1a; border: 1px solid #00f0ff; border-radius: 8px;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # Toolbar
        bar = QHBoxLayout()
        title = QLabel("❖ PAJAMA 2D CANVAS")
        title.setStyleSheet("color: #00f0ff; font-weight: bold; font-size: 11px;")
        bar.addWidget(title)
        bar.addStretch()

        snake_btn = QPushButton("🐍 Cyber Snake")
        snake_btn.setStyleSheet("background: #111a30; color: #00ff88; border: 1px solid #00ff88; border-radius: 4px; padding: 4px 8px;")
        snake_btn.clicked.connect(self.play_snake)
        bar.addWidget(snake_btn)

        pong_btn = QPushButton("🏓 Neon Pong")
        pong_btn.setStyleSheet("background: #111a30; color: #ffaa00; border: 1px solid #ffaa00; border-radius: 4px; padding: 4px 8px;")
        pong_btn.clicked.connect(self.play_pong)
        bar.addWidget(pong_btn)

        layout.addLayout(bar)

        self.canvas = CyberCanvasWidget(self)
        layout.addWidget(self.canvas)

    def play_snake(self):
        self.canvas.start_snake()

    def play_pong(self):
        self.canvas.start_pong()
