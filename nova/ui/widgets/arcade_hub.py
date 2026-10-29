"""
NOVA Arcade Hub & Retro Game Launcher.
Provides a multi-tab gaming center:
1. Neon Space Invaders (2D Arcade Shooter)
2. Cyber Roguelike Dungeon Crawler
3. Classic Cyber Snake & Neon Pong
4. Hall of Fame High Scores Leaderboard
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTabWidget, QTableWidget, QTableWidgetItem,
    QHeaderView, QFrame
)
from PySide6.QtCore import Qt

from nova.arcade import SpaceInvadersWidget, CyberRoguelikeWidget, HighScoresManager
from nova.pajama.canvas import CyberCanvasWidget

class ArcadeHubWidget(QWidget):
    """Arcade gaming center for NOVA OS."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # Header
        head = QHBoxLayout()
        icon = QLabel("👾")
        icon.setStyleSheet("font-size: 22px;")
        head.addWidget(icon)

        title = QLabel("NOVA RETRO ARCADE & EMULATION HUB")
        title.setStyleSheet("color: #00f0ff; font-weight: bold; font-size: 13px; letter-spacing: 1px;")
        head.addWidget(title)
        head.addStretch()
        layout.addLayout(head)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid rgba(0, 240, 255, 0.25); background: #090e1a; border-radius: 6px; }
            QTabBar::tab { background: #0f1629; color: #94a3b8; padding: 6px 14px; margin-right: 4px; border-radius: 4px; font-weight: 600; }
            QTabBar::tab:selected { background: #0052cc; color: #ffffff; border: 1px solid #00f0ff; }
        """)

        # Tab 1: Space Invaders
        self.invaders_game = SpaceInvadersWidget()
        self.tabs.addTab(self.invaders_game, "🚀 Space Invaders")

        # Tab 2: Roguelike
        self.roguelike_game = CyberRoguelikeWidget()
        self.tabs.addTab(self.roguelike_game, "⚔️ Cyber Dungeon")

        # Tab 3: Snake & Pong
        self.tab_retro = self._create_retro_tab()
        self.tabs.addTab(self.tab_retro, "🐍 Snake & Pong")

        # Tab 4: Hall of Fame
        self.tab_hof = self._create_hof_tab()
        self.tabs.addTab(self.tab_hof, "🏆 Hall of Fame")

        layout.addWidget(self.tabs)

    def _create_retro_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(10, 10, 10, 10)

        bar = QHBoxLayout()
        snake_btn = QPushButton("Play Snake")
        snake_btn.setStyleSheet("background: #0052cc; color: #ffffff; font-weight: bold; padding: 6px 12px; border-radius: 4px;")
        snake_btn.clicked.connect(lambda: self.retro_canvas.start_snake())
        bar.addWidget(snake_btn)

        pong_btn = QPushButton("Play Pong")
        pong_btn.setStyleSheet("background: #111a30; border: 1px solid #ffaa00; color: #ffaa00; font-weight: bold; padding: 6px 12px; border-radius: 4px;")
        pong_btn.clicked.connect(lambda: self.retro_canvas.start_pong())
        bar.addWidget(pong_btn)
        bar.addStretch()
        lay.addLayout(bar)

        self.retro_canvas = CyberCanvasWidget()
        self.retro_canvas.start_snake()
        lay.addWidget(self.retro_canvas, alignment=Qt.AlignCenter)
        return w

    def _create_hof_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(14, 14, 14, 14)
        lay.setSpacing(10)

        lay.addWidget(QLabel("HIGH SCORES LEADERBOARD"))
        self.hof_table = QTableWidget()
        self.hof_table.setColumnCount(4)
        self.hof_table.setHorizontalHeaderLabels(["Game", "Initials", "Score", "Date"])
        self.hof_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.hof_table.setStyleSheet("background: #0d1424; color: #e2e8f0;")
        lay.addWidget(self.hof_table)

        self._refresh_hof()
        return w

    def _refresh_hof(self):
        rows = []
        for g_id, name in [("space_invaders", "Space Invaders"), ("cyber_snake", "Cyber Snake"), ("roguelike", "Cyber Dungeon")]:
            scores = HighScoresManager.get_scores(g_id)
            for s in scores:
                rows.append((name, s["initials"], str(s["score"]), s.get("date", "")))

        self.hof_table.setRowCount(len(rows))
        for r, (g, ini, sc, dt) in enumerate(rows):
            self.hof_table.setItem(r, 0, QTableWidgetItem(g))
            ini_item = QTableWidgetItem(ini)
            ini_item.setForeground(Qt.cyan)
            self.hof_table.setItem(r, 1, ini_item)
            sc_item = QTableWidgetItem(sc)
            sc_item.setForeground(Qt.green)
            self.hof_table.setItem(r, 2, sc_item)
            self.hof_table.setItem(r, 3, QTableWidgetItem(dt))
