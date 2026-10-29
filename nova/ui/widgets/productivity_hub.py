"""
Interactive Productivity, Kanban & Knowledge Hub Widget for NOVA OS.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTabWidget, QListWidget, QListWidgetItem,
    QProgressBar, QLineEdit, QFrame, QGridLayout
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPainter, QColor, QFont, QPen, QBrush

from nova.productivity import KanbanManager, HabitTracker, KnowledgeGraphBuilder

class ProductivityHubWidget(QWidget):
    """Complete productivity workspace."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        head = QHBoxLayout()
        icon = QLabel("📊")
        icon.setStyleSheet("font-size: 22px;")
        head.addWidget(icon)

        title = QLabel("PRODUCTIVITY, KANBAN & FOCUS MATRIX")
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

        # Tab 1: Kanban
        self.tab_kanban = self._create_kanban_tab()
        self.tabs.addTab(self.tab_kanban, "📋 Kanban Board")

        # Tab 2: Pomodoro
        self.tab_pomo = self._create_pomodoro_tab()
        self.tabs.addTab(self.tab_pomo, "⏱️ Pomodoro Focus")

        # Tab 3: Habits
        self.tab_habits = self._create_habits_tab()
        self.tabs.addTab(self.tab_habits, "🔥 Habit Streaks")

        layout.addWidget(self.tabs)

    def _create_kanban_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(10, 10, 10, 10)

        cols_row = QHBoxLayout()
        cols_row.setSpacing(10)

        board = KanbanManager.get_board()
        self.col_lists = {}

        for col_key, col_title in [("todo", "📌 TO DO"), ("progress", "⚡ IN PROGRESS"), ("done", "✓ COMPLETED")]:
            col_box = QFrame()
            col_box.setStyleSheet("background: #0d1424; border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 8px;")
            cb_lay = QVBoxLayout(col_box)
            cb_lay.setSpacing(6)

            h = QLabel(col_title)
            h.setStyleSheet("color: #00f0ff; font-weight: bold; font-size: 11px;")
            cb_lay.addWidget(h)

            lw = QListWidget()
            lw.setStyleSheet("background: #070b14; color: #cbd5e1; border: none;")
            for card in board.get(col_key, []):
                lw.addItem(f"{card['title']} [{card.get('tag', 'Task')}]")
            cb_lay.addWidget(lw)
            self.col_lists[col_key] = lw

            cols_row.addWidget(col_box)

        lay.addLayout(cols_row)

        # Add Card
        add_row = QHBoxLayout()
        self.new_card_input = QLineEdit()
        self.new_card_input.setPlaceholderText("Enter task card title...")
        add_row.addWidget(self.new_card_input)

        add_btn = QPushButton("+ Add To-Do")
        add_btn.setStyleSheet("background: #0052cc; color: #ffffff; font-weight: bold; padding: 6px 14px; border-radius: 4px;")
        add_btn.clicked.connect(self._add_kanban_card)
        add_row.addWidget(add_btn)
        lay.addLayout(add_row)

        return w

    def _add_kanban_card(self):
        title = self.new_card_input.text().strip()
        if title:
            KanbanManager.add_card("todo", title)
            self.col_lists["todo"].addItem(f"{title} [Task]")
            self.new_card_input.clear()

    def _create_pomodoro_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(14)
        lay.setAlignment(Qt.AlignCenter)

        self.pomo_secs = 25 * 60
        self.pomo_running = False

        self.timer_lbl = QLabel("25:00")
        self.timer_lbl.setStyleSheet("color: #00f0ff; font-size: 54px; font-weight: 800; font-family: 'Segoe UI', monospace;")
        lay.addWidget(self.timer_lbl, alignment=Qt.AlignCenter)

        btn_row = QHBoxLayout()
        self.pomo_start_btn = QPushButton("▶ Start Focus")
        self.pomo_start_btn.setStyleSheet("background: #0052cc; color: #ffffff; font-weight: bold; padding: 10px 20px; border-radius: 6px;")
        self.pomo_start_btn.clicked.connect(self._toggle_pomodoro)
        btn_row.addWidget(self.pomo_start_btn)

        reset_btn = QPushButton("↺ Reset")
        reset_btn.setStyleSheet("background: #111a30; border: 1px solid #ff2a55; color: #ff2a55; font-weight: bold; padding: 10px 20px; border-radius: 6px;")
        reset_btn.clicked.connect(self._reset_pomodoro)
        btn_row.addWidget(reset_btn)

        lay.addLayout(btn_row)

        self.pomo_timer = QTimer(self)
        self.pomo_timer.timeout.connect(self._tick_pomodoro)
        return w

    def _toggle_pomodoro(self):
        if not self.pomo_running:
            self.pomo_running = True
            self.pomo_timer.start(1000)
            self.pomo_start_btn.setText("⏸ Pause")
        else:
            self.pomo_running = False
            self.pomo_timer.stop()
            self.pomo_start_btn.setText("▶ Resume")

    def _reset_pomodoro(self):
        self.pomo_running = False
        self.pomo_timer.stop()
        self.pomo_secs = 25 * 60
        self.timer_lbl.setText("25:00")
        self.pomo_start_btn.setText("▶ Start Focus")

    def _tick_pomodoro(self):
        if self.pomo_secs > 0:
            self.pomo_secs -= 1
            m = self.pomo_secs // 60
            s = self.pomo_secs % 60
            self.timer_lbl.setText(f"{m:02d}:{s:02d}")
        else:
            self._reset_pomodoro()

    def _create_habits_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(14, 14, 14, 14)
        lay.setSpacing(10)

        lay.addWidget(QLabel("Daily Habits & Consistency Streaks:"))
        habits = HabitTracker.get_habits()
        for h in habits:
            card = QFrame()
            card.setStyleSheet("background: #0d1628; border: 1px solid rgba(0, 240, 255, 0.2); border-radius: 8px; padding: 10px;")
            c_lay = QHBoxLayout(card)

            n_lbl = QLabel(f"🔥 {h['name']}")
            n_lbl.setStyleSheet("color: #ffffff; font-weight: 600; font-size: 11px;")
            c_lay.addWidget(n_lbl)
            c_lay.addStretch()

            st_lbl = QLabel(f"{h['streak']} Day Streak")
            st_lbl.setStyleSheet("color: #00ff88; font-weight: bold; font-size: 11px;")
            c_lay.addWidget(st_lbl)

            btn = QPushButton("✓ Done" if h["completed_today"] else "Mark Done")
            btn.setStyleSheet("background: #0052cc; color: white; border-radius: 4px; padding: 4px 10px;")
            c_lay.addWidget(btn)
            lay.addWidget(card)

        lay.addStretch()
        return w
