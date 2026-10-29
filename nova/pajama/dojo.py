"""
Pajama Dojo - Gamified AI Coding Academy for NOVA OS.
10 progressive cyberpunk hacking challenges with automated code evaluation,
AI Sensei hints, and badge rewards.
"""

from typing import List, Dict, Any, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QListWidget, QListWidgetItem,
    QProgressBar, QFrame, QSplitter
)
from PySide6.QtCore import Qt, Signal

from nova.pajama.runtime import PajamaRuntime

DOJO_CHALLENGES: List[Dict[str, Any]] = [
    {
        "level": 1,
        "title": "Level 1: The First Spark",
        "badge": "⚡ Spark Initiate",
        "objective": "Print 'Hello Cyber World' and play a sound effect.",
        "starter": 'print "Hello Cyber World"\nplay sound "chime"\n',
        "validator": lambda out: "Hello Cyber World" in out
    },
    {
        "level": 2,
        "title": "Level 2: Memory Matrix",
        "badge": "🧠 Variable Core",
        "objective": "Create variable x with value 40, y with value 2, and print their sum.",
        "starter": 'set x to 40\nset y to 2\nset sum to x + y\nprint sum\n',
        "validator": lambda out: "42" in out
    },
    {
        "level": 3,
        "title": "Level 3: Security Perimeter",
        "badge": "🛡️ Logic Sentinel",
        "objective": "Check if power is greater than 50. If true, print 'SYSTEM_STABLE'.",
        "starter": 'set power to 75\nif power > 50:\n    print "SYSTEM_STABLE"\n',
        "validator": lambda out: "SYSTEM_STABLE" in out
    },
    {
        "level": 4,
        "title": "Level 4: Quantum Loop",
        "badge": "🌀 Loop Master",
        "objective": "Write a loop that repeats 3 times printing 'Pulse'.",
        "starter": 'repeat 3 times:\n    print "Pulse"\n',
        "validator": lambda out: out.count("Pulse") >= 3
    },
    {
        "level": 5,
        "title": "Level 5: Chiptune Synthesizer",
        "badge": "🎵 Cyber Maestro",
        "objective": "Emit two hardware sound beeps at frequencies 523 and 659.",
        "starter": 'beep 523, 100\nbeep 659, 100\nprint "MELODY_DONE"\n',
        "validator": lambda out: "MELODY_DONE" in out
    },
    {
        "level": 6,
        "title": "Level 6: File Data Vault",
        "badge": "💾 Storage Alchemist",
        "objective": "Write 'Secret Cipher' to file 'dojo_test.txt' and read it back.",
        "starter": 'write "dojo_test.txt", "Secret Cipher"\nset data to read "dojo_test.txt"\nprint data\n',
        "validator": lambda out: "Secret Cipher" in out
    },
    {
        "level": 7,
        "title": "Level 7: System Guardian",
        "badge": "⚙️ Kernel Watchdog",
        "objective": "Check system RAM and print RAM status.",
        "starter": 'set ram to system ram\nprint "RAM:", ram\n',
        "validator": lambda out: "RAM:" in out
    },
    {
        "level": 8,
        "title": "Level 8: Windows App Subsystem",
        "badge": "🪟 Windows Bridge",
        "objective": "Verify if 'calc.exe' or 'notepad.exe' is known to the system.",
        "starter": 'print "VERIFYING_WIN_APP"\n',
        "validator": lambda out: "VERIFYING_WIN_APP" in out
    },
    {
        "level": 9,
        "title": "Level 9: Stopwatch Controller",
        "badge": "⏱️ Chrono Weaver",
        "objective": "Launch the Pajama interactive stopwatch.",
        "starter": 'stopwatch\nprint "STOPWATCH_LAUNCHED"\n',
        "validator": lambda out: "STOPWATCH_LAUNCHED" in out
    },
    {
        "level": 10,
        "title": "Level 10: Master Cyber Alchemist",
        "badge": "👑 NOVA Archon",
        "objective": "Combine variables, a loop, and a sound into a final cyber sequence.",
        "starter": 'set level to 10\nrepeat 2 times:\n    print "ARCHON_POWER_ACTIVE"\nplay sound "success"\n',
        "validator": lambda out: "ARCHON_POWER_ACTIVE" in out
    }
]

class PajamaDojoWidget(QWidget):
    """Interactive Dojo Coding Academy GUI."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_idx = 0
        self.unlocked_levels = 1
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header
        head = QHBoxLayout()
        icon = QLabel("🥋")
        icon.setStyleSheet("font-size: 24px;")
        head.addWidget(icon)

        title_box = QVBoxLayout()
        t = QLabel("PAJAMA DOJO • CYBER CODING ACADEMY")
        t.setStyleSheet("color: #00f0ff; font-weight: bold; font-size: 13px; letter-spacing: 1px;")
        title_box.addWidget(t)

        sub = QLabel("10 Levels of Hands-On Interactive Programming Mastery")
        sub.setStyleSheet("color: #94a3b8; font-size: 10px;")
        title_box.addWidget(sub)
        head.addLayout(title_box)
        head.addStretch()

        self.badge_lbl = QLabel("Badge: ⚡ Spark Initiate")
        self.badge_lbl.setStyleSheet("color: #ffaa00; font-weight: bold; font-size: 11px;")
        head.addWidget(self.badge_lbl)
        layout.addLayout(head)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, len(DOJO_CHALLENGES))
        self.progress_bar.setValue(1)
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("QProgressBar::chunk { background: #00ff88; border-radius: 4px; }")
        layout.addWidget(self.progress_bar)

        # Splitter: Levels List on Left, Editor & Test on Right
        splitter = QSplitter(Qt.Horizontal)

        # Left list
        self.level_list = QListWidget()
        self.level_list.setFixedWidth(200)
        self.level_list.setStyleSheet("""
            QListWidget {
                background: #0d1424;
                border: 1px solid rgba(0, 240, 255, 0.2);
                border-radius: 8px;
                color: #e2e8f0;
            }
            QListWidget::item:selected {
                background: #0052cc;
                color: #ffffff;
            }
        """)
        for ch in DOJO_CHALLENGES:
            item = QListWidgetItem(f"L{ch['level']}: {ch['title'].split(':')[1].strip()}")
            self.level_list.addItem(item)
        self.level_list.currentRowChanged.connect(self.on_level_selected)
        splitter.addWidget(self.level_list)

        # Right pane
        right_pane = QWidget()
        r_lay = QVBoxLayout(right_pane)
        r_lay.setContentsMargins(8, 0, 0, 0)
        r_lay.setSpacing(8)

        self.obj_card = QFrame()
        self.obj_card.setStyleSheet("background: #111a30; border: 1px solid rgba(0, 255, 136, 0.3); border-radius: 8px; padding: 8px;")
        oc_lay = QVBoxLayout(self.obj_card)
        self.obj_title = QLabel("MISSION OBJECTIVE")
        self.obj_title.setStyleSheet("color: #00ff88; font-weight: bold; font-size: 11px;")
        oc_lay.addWidget(self.obj_title)

        self.obj_text = QLabel(DOJO_CHALLENGES[0]["objective"])
        self.obj_text.setStyleSheet("color: #cbd5e1; font-size: 11px;")
        self.obj_text.setWordWrap(True)
        oc_lay.addWidget(self.obj_text)
        r_lay.addWidget(self.obj_card)

        # Code Editor
        self.code_edit = QTextEdit()
        self.code_edit.setStyleSheet("""
            QTextEdit {
                background: #070b14;
                border: 1px solid rgba(0, 240, 255, 0.3);
                border-radius: 8px;
                color: #00f0ff;
                font-family: 'Consolas', monospace;
                font-size: 12px;
                padding: 8px;
            }
        """)
        self.code_edit.setPlainText(DOJO_CHALLENGES[0]["starter"])
        r_lay.addWidget(self.code_edit, stretch=1)

        # Output / Results Box
        self.result_lbl = QLabel("Ready for execution...")
        self.result_lbl.setStyleSheet("color: #94a3b8; font-size: 10px; font-weight: bold;")
        r_lay.addWidget(self.result_lbl)

        # Bottom Buttons
        btn_box = QHBoxLayout()
        self.run_btn = QPushButton("▶ Run & Evaluate Solution")
        self.run_btn.setStyleSheet("""
            QPushButton {
                background: #0052cc;
                border: 1px solid #00f0ff;
                border-radius: 6px;
                color: #ffffff;
                font-weight: bold;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background: #00f0ff;
                color: #050811;
            }
        """)
        self.run_btn.clicked.connect(self.evaluate_solution)
        btn_box.addWidget(self.run_btn)

        self.hint_btn = QPushButton("💡 AI Sensei Hint")
        self.hint_btn.setStyleSheet("""
            QPushButton {
                background: #1c152a;
                border: 1px solid #b026ff;
                border-radius: 6px;
                color: #e2b3ff;
                font-weight: bold;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background: #b026ff;
                color: #ffffff;
            }
        """)
        self.hint_btn.clicked.connect(self.show_hint)
        btn_box.addWidget(self.hint_btn)
        btn_box.addStretch()
        r_lay.addLayout(btn_box)

        splitter.addWidget(right_pane)
        layout.addWidget(splitter, stretch=1)

        self.level_list.setCurrentRow(0)

    def on_level_selected(self, row: int):
        if 0 <= row < len(DOJO_CHALLENGES):
            self.current_idx = row
            ch = DOJO_CHALLENGES[row]
            self.obj_title.setText(ch["title"].upper())
            self.obj_text.setText(ch["objective"])
            self.code_edit.setPlainText(ch["starter"])
            self.result_lbl.setStyleSheet("color: #94a3b8; font-size: 10px; font-weight: bold;")
            self.result_lbl.setText("Enter your solution and click 'Run & Evaluate'.")

    def evaluate_solution(self):
        ch = DOJO_CHALLENGES[self.current_idx]
        code = self.code_edit.toPlainText()

        output_lines = []
        runtime = PajamaRuntime(output_callback=lambda txt: output_lines.append(str(txt)))
        runtime.run_code(code)

        combined_output = "\n".join(output_lines)
        passed = ch["validator"](combined_output)

        if passed:
            self.result_lbl.setStyleSheet("color: #00ff88; font-size: 11px; font-weight: bold;")
            self.result_lbl.setText(f"✓ CHALLENGE PASSED! Badge Unlocked: {ch['badge']}")
            if self.current_idx + 1 > self.unlocked_levels:
                self.unlocked_levels = self.current_idx + 1
                self.progress_bar.setValue(self.unlocked_levels)
                self.badge_lbl.setText(f"Badge: {ch['badge']}")
        else:
            self.result_lbl.setStyleSheet("color: #ff2a55; font-size: 11px; font-weight: bold;")
            self.result_lbl.setText("✕ Verification failed. Review objective and try again.")

    def show_hint(self):
        ch = DOJO_CHALLENGES[self.current_idx]
        self.result_lbl.setStyleSheet("color: #b026ff; font-size: 10px; font-weight: bold;")
        self.result_lbl.setText(f"AI Sensei: Remember to match '{ch['objective']}'. Check syntax and spacing.")
