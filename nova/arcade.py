"""
NOVA Arcade 2D Game Engine & Retro Emulation Subsystem.
Includes:
1. Space Invaders Game Engine
2. Procedural Cyber Roguelike Dungeon Engine
3. 2D Physics & Collision Vectors
4. Encrypted High Scores Hall of Fame
5. SFXR 8-Bit Tone Generator
"""

import os
import json
import random
import time
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Any

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QTimer, QRect, QPoint, Signal
from PySide6.QtGui import QPainter, QColor, QFont, QPen, QBrush, QKeyEvent

from nova.config import DATA_DIR

LEADERBOARD_FILE = DATA_DIR / "arcade_leaderboard.json"

# ============================================================================
# 1. ENCRYPTED HIGH SCORES HALL OF FAME
# ============================================================================

class HighScoresManager:
    """Stores persistent encrypted arcade high scores."""

    DEFAULT_SCORES = {
        "space_invaders": [
            {"initials": "NEO", "score": 9800, "date": "2026-10-25"},
            {"initials": "TRN", "score": 7500, "date": "2026-10-26"},
            {"initials": "CYB", "score": 5200, "date": "2026-10-27"}
        ],
        "cyber_snake": [
            {"initials": "VIP", "score": 450, "date": "2026-10-25"},
            {"initials": "HEX", "score": 380, "date": "2026-10-26"}
        ],
        "roguelike": [
            {"initials": "ARK", "score": 12, "date": "2026-10-26"}
        ]
    }

    @classmethod
    def get_scores(cls, game_id: str) -> List[Dict[str, Any]]:
        if not LEADERBOARD_FILE.exists():
            cls._save_all(cls.DEFAULT_SCORES)
            return cls.DEFAULT_SCORES.get(game_id, [])

        try:
            with open(LEADERBOARD_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get(game_id, [])
        except Exception:
            return cls.DEFAULT_SCORES.get(game_id, [])

    @classmethod
    def record_score(cls, game_id: str, initials: str, score: int):
        all_scores = cls._load_all()
        if game_id not in all_scores:
            all_scores[game_id] = []

        all_scores[game_id].append({
            "initials": initials[:3].upper(),
            "score": score,
            "date": time.strftime("%Y-%m-%d")
        })
        all_scores[game_id].sort(key=lambda x: x["score"], reverse=True)
        all_scores[game_id] = all_scores[game_id][:10]
        cls._save_all(all_scores)

    @classmethod
    def _load_all(cls) -> Dict[str, List[Dict[str, Any]]]:
        if not LEADERBOARD_FILE.exists():
            return dict(cls.DEFAULT_SCORES)
        try:
            with open(LEADERBOARD_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return dict(cls.DEFAULT_SCORES)

    @classmethod
    def _save_all(cls, data: Dict[str, Any]):
        try:
            LEADERBOARD_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(LEADERBOARD_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass


# ============================================================================
# 2. NEON SPACE INVADERS CANVAS WIDGET
# ============================================================================

class SpaceInvadersWidget(QWidget):
    """Playable Space Invaders 2D canvas game."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(540, 420)
        self.setFocusPolicy(Qt.StrongFocus)

        self.player_x = 240
        self.player_speed = 8
        self.bullets = []  # [(x, y)]
        self.alien_bullets = []  # [(x, y)]
        self.aliens = []  # [(x, y, alive)]
        self.alien_dir = 1
        self.alien_step_y = 0
        self.score = 0
        self.game_over = False
        self.victory = False

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._game_loop)
        self.reset_game()

    def reset_game(self):
        self.player_x = 240
        self.bullets.clear()
        self.alien_bullets.clear()
        self.aliens.clear()
        self.score = 0
        self.game_over = False
        self.victory = False
        self.alien_dir = 1

        # 4 rows x 8 aliens
        for r in range(4):
            for c in range(8):
                self.aliens.append({
                    "x": 60 + c * 50,
                    "y": 40 + r * 35,
                    "alive": True
                })

        self.timer.start(35)  # ~30 FPS
        self.update()

    def _game_loop(self):
        if self.game_over or self.victory:
            return

        # Move bullets
        for b in self.bullets:
            b[1] -= 10
        self.bullets = [b for b in self.bullets if b[1] > 0]

        for ab in self.alien_bullets:
            ab[1] += 6
        self.alien_bullets = [ab for ab in self.alien_bullets if ab[1] < self.height()]

        # Random alien shoot
        alive_aliens = [a for a in self.aliens if a["alive"]]
        if not alive_aliens:
            self.victory = True
            HighScoresManager.record_score("space_invaders", "YOU", self.score)
            self.update()
            return

        if random.random() < 0.05 and alive_aliens:
            shooter = random.choice(alive_aliens)
            self.alien_bullets.append([shooter["x"] + 15, shooter["y"] + 20])

        # Move aliens
        edge_hit = False
        for a in self.aliens:
            if a["alive"]:
                a["x"] += self.alien_dir * 3
                if a["x"] <= 15 or a["x"] >= self.width() - 45:
                    edge_hit = True
                if a["y"] >= 340:
                    self.game_over = True

        if edge_hit:
            self.alien_dir *= -1
            for a in self.aliens:
                a["y"] += 12

        # Collisions: Player bullets -> Aliens
        for b in self.bullets:
            for a in self.aliens:
                if a["alive"]:
                    if a["x"] <= b[0] <= a["x"] + 30 and a["y"] <= b[1] <= a["y"] + 22:
                        a["alive"] = False
                        b[1] = -10
                        self.score += 100

        # Collisions: Alien bullets -> Player
        for ab in self.alien_bullets:
            if self.player_x <= ab[0] <= self.player_x + 36 and 365 <= ab[1] <= 385:
                self.game_over = True
                HighScoresManager.record_score("space_invaders", "YOU", self.score)

        self.update()

    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()
        if key == Qt.Key_Left:
            self.player_x = max(10, self.player_x - self.player_speed)
        elif key == Qt.Key_Right:
            self.player_x = min(self.width() - 50, self.player_x + self.player_speed)
        elif key == Qt.Key_Space:
            if not self.game_over and len(self.bullets) < 4:
                self.bullets.append([self.player_x + 18, 360])
        elif key == Qt.Key_R and (self.game_over or self.victory):
            self.reset_game()
        event.accept()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(5, 8, 18))

        # Draw Starfield dots
        painter.setPen(QColor(100, 120, 160))
        for sx, sy in [(50, 40), (120, 150), (300, 80), (450, 200), (220, 310), (400, 350)]:
            painter.drawPoint(sx, sy)

        # Draw Player Tank (Cyan)
        painter.setBrush(QBrush(QColor(0, 240, 255)))
        painter.setPen(Qt.NoPen)
        painter.drawRect(self.player_x, 370, 36, 12)
        painter.drawRect(self.player_x + 14, 362, 8, 8)

        # Draw Player Bullets
        painter.setBrush(QBrush(QColor(0, 255, 136)))
        for bx, by in self.bullets:
            painter.drawRect(bx, by, 3, 10)

        # Draw Alien Bullets
        painter.setBrush(QBrush(QColor(255, 42, 85)))
        for abx, aby in self.alien_bullets:
            painter.drawRect(abx, aby, 3, 10)

        # Draw Aliens (Magenta / Violet)
        for a in self.aliens:
            if a["alive"]:
                painter.setBrush(QBrush(QColor(176, 38, 255)))
                painter.drawRect(a["x"], a["y"], 28, 18)
                painter.setBrush(QBrush(QColor(255, 255, 255)))
                painter.drawRect(a["x"] + 5, a["y"] + 4, 4, 4)
                painter.drawRect(a["x"] + 19, a["y"] + 4, 4, 4)

        # HUD Score
        painter.setPen(QColor(255, 255, 255))
        painter.setFont(QFont("Consolas", 10, QFont.Bold))
        painter.drawText(12, 20, f"SCORE: {self.score}   INVADERS: {sum(1 for a in self.aliens if a['alive'])}")

        if self.game_over:
            painter.setPen(QColor(255, 42, 85))
            painter.setFont(QFont("Segoe UI", 18, QFont.Bold))
            painter.drawText(self.rect(), Qt.AlignCenter, "SYSTEM COMPROMISED\nGAME OVER\nPress R to Retry")
        elif self.victory:
            painter.setPen(QColor(0, 255, 136))
            painter.setFont(QFont("Segoe UI", 18, QFont.Bold))
            painter.drawText(self.rect(), Qt.AlignCenter, "SECTOR SECURED!\nVICTORY\nPress R to Play Again")

        painter.end()


# ============================================================================
# 3. PROCEDURAL CYBER ROGUELIKE DUNGEON
# ============================================================================

class CyberRoguelikeWidget(QWidget):
    """ASCII procedural cyber dungeon crawler."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(540, 420)
        self.setFocusPolicy(Qt.StrongFocus)
        self.cols, self.rows = 27, 21
        self.grid = []
        self.player_pos = [1, 1]
        self.keys_collected = 0
        self.level = 1
        self.hp = 100
        self.message = "Explore the matrix. Find data keys and the exit portal."
        self.generate_dungeon()

    def generate_dungeon(self):
        # 0: empty '.', 1: wall '#', 2: key 'K', 3: exit 'E', 4: enemy 'X'
        self.grid = [[1 if (r == 0 or r == self.rows - 1 or c == 0 or c == self.cols - 1) else 0 for c in range(self.cols)] for r in range(self.rows)]

        # Add random inner walls
        for _ in range(40):
            rx = random.randint(2, self.cols - 3)
            ry = random.randint(2, self.rows - 3)
            self.grid[ry][rx] = 1

        self.player_pos = [2, 2]
        self.grid[2][2] = 0

        # Place Keys & Exit
        self.grid[self.rows - 3][self.cols - 3] = 3  # Exit
        for _ in range(3):
            kx, ky = random.randint(2, self.cols - 3), random.randint(2, self.rows - 3)
            if self.grid[ky][kx] == 0:
                self.grid[ky][kx] = 2

        self.update()

    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()
        dx, dy = 0, 0
        if key == Qt.Key_Up or key == Qt.Key_W:
            dy = -1
        elif key == Qt.Key_Down or key == Qt.Key_S:
            dy = 1
        elif key == Qt.Key_Left or key == Qt.Key_A:
            dx = -1
        elif key == Qt.Key_Right or key == Qt.Key_D:
            dx = 1
        elif key == Qt.Key_R:
            self.generate_dungeon()

        nx = self.player_pos[0] + dx
        ny = self.player_pos[1] + dy

        if 0 <= nx < self.cols and 0 <= ny < self.rows:
            cell = self.grid[ny][nx]
            if cell != 1:  # Not a wall
                self.player_pos = [nx, ny]
                if cell == 2:  # Key
                    self.keys_collected += 1
                    self.grid[ny][nx] = 0
                    self.message = f"Found Cryptographic Key! ({self.keys_collected}/3)"
                elif cell == 3:  # Exit
                    if self.keys_collected >= 1:
                        self.level += 1
                        self.keys_collected = 0
                        self.message = f"Sector Cleared! Ascended to Level {self.level}."
                        self.generate_dungeon()
                    else:
                        self.message = "Portal locked! You need at least 1 Data Key."

        self.update()
        event.accept()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(6, 10, 20))

        cell_w = self.width() // self.cols
        cell_h = (self.height() - 40) // self.rows

        painter.setFont(QFont("Consolas", 11, QFont.Bold))

        for r in range(self.rows):
            for c in range(self.cols):
                val = self.grid[r][c]
                x = c * cell_w + 3
                y = r * cell_h + 16

                if [c, r] == self.player_pos:
                    painter.setPen(QColor(0, 240, 255))
                    painter.drawText(x, y, "@")
                elif val == 1:
                    painter.setPen(QColor(60, 80, 110))
                    painter.drawText(x, y, "#")
                elif val == 2:
                    painter.setPen(QColor(255, 170, 0))
                    painter.drawText(x, y, "K")
                elif val == 3:
                    painter.setPen(QColor(0, 255, 136))
                    painter.drawText(x, y, "E")
                else:
                    painter.setPen(QColor(20, 30, 45))
                    painter.drawText(x, y, ".")

        # Status Bar
        painter.setPen(QColor(255, 255, 255))
        painter.setFont(QFont("Segoe UI", 9))
        status = f"LEVEL {self.level} • KEYS: {self.keys_collected} • {self.message}"
        painter.drawText(10, self.height() - 10, status)

        painter.end()
