"""
NOVA Autonomous Intelligence & Multi-Step Agent Cockpit.
Deploys autonomous multi-step agents that plan, execute sandboxed tasks,
log synthetic thoughts in real time, and coordinate system tools.
"""

from typing import Optional, List, Dict, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QListWidget, QListWidgetItem,
    QProgressBar, QPlainTextEdit, QFrame, QSplitter, QTabWidget
)
from PySide6.QtCore import Qt, Slot, Signal
from PySide6.QtGui import QFont, QColor

from nova.agent_engine import AgentEngine, AgentWorker
from nova.ollama_client import OllamaClient
from nova.sound_fx import play_sound
from nova.ui.widgets.research_cockpit import ResearchCockpitWidget

class AgentHubWidget(QWidget):
    """Mission control cockpit for autonomous multi-step intelligence."""

    def __init__(self, ollama_client: Optional[OllamaClient] = None, parent=None):
        super().__init__(parent)
        self.ollama_client = ollama_client or OllamaClient()
        self.engine = AgentEngine(self.ollama_client)
        self.active_worker: Optional[AgentWorker] = None

        self.setup_ui()

    def setup_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.hub_tabs = QTabWidget()
        self.hub_tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid rgba(0, 240, 255, 0.2);
                border-radius: 6px;
                background: #0A0E19;
            }
            QTabBar::tab {
                background: #0d1424;
                color: #798fa7;
                padding: 8px 16px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                font-weight: bold;
                font-size: 11px;
            }
            QTabBar::tab:selected {
                background: #0A0E19;
                color: #00F0FF;
            }
        """)

        # Tab 1: Autonomous Internet Research Cockpit
        self.research_cockpit = ResearchCockpitWidget(self)
        self.hub_tabs.addTab(self.research_cockpit, "🌐 Autonomous Internet Research Agent")

        # Tab 2: System Directives & Sandboxed Automation
        directives_widget = QWidget()
        layout = QVBoxLayout(directives_widget)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # Header Title
        header = QHBoxLayout()
        title = QLabel("NOVA LOCAL DIRECTIVE ENGINE")
        title.setObjectName("HeaderTitle")
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #00F0FF;")
        header.addWidget(title)
        header.addStretch()

        self.status_badge = QLabel("[STATUS: IDLE // STANDBY]")
        self.status_badge.setStyleSheet("color: #718096; font-weight: bold; font-family: Consolas; font-size: 11px;")
        header.addWidget(self.status_badge)
        layout.addLayout(header)

        # Goal Input Bar
        goal_box = QHBoxLayout()
        goal_lbl = QLabel("Objective:")
        goal_lbl.setStyleSheet("color: #EAF4FF; font-weight: bold;")
        goal_box.addWidget(goal_lbl)

        self.goal_input = QLineEdit()
        self.goal_input.setFont(QFont("Segoe UI", 12))
        self.goal_input.setPlaceholderText("Enter multi-step autonomous goal (e.g. diagnose system health and create report)...")
        self.goal_input.setStyleSheet("""
            QLineEdit {
                background-color: #0A0E19;
                color: #EAF4FF;
                border: 1px solid rgba(0, 240, 255, 0.3);
                border-radius: 6px;
                padding: 8px 12px;
            }
            QLineEdit:focus {
                border-color: #00F0FF;
            }
        """)
        self.goal_input.returnPressed.connect(self.on_deploy_agent)
        goal_box.addWidget(self.goal_input)

        self.deploy_btn = QPushButton("Deploy Agent 🚀")
        self.deploy_btn.setObjectName("PrimaryButton")
        self.deploy_btn.setStyleSheet("""
            QPushButton {
                background: #00F0FF;
                color: #050811;
                font-weight: bold;
                border-radius: 6px;
                padding: 8px 18px;
            }
            QPushButton:hover {
                background: #50f5ff;
            }
        """)
        self.deploy_btn.clicked.connect(self.on_deploy_agent)
        goal_box.addWidget(self.deploy_btn)

        self.abort_btn = QPushButton("Abort")
        self.abort_btn.setEnabled(False)
        self.abort_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 0, 85, 0.2);
                color: #ff3366;
                border: 1px solid rgba(255, 0, 85, 0.5);
                border-radius: 6px;
                padding: 8px 14px;
            }
            QPushButton:hover {
                background: rgba(255, 0, 85, 0.4);
            }
        """)
        self.abort_btn.clicked.connect(self.on_abort)
        goal_box.addWidget(self.abort_btn)

        layout.addLayout(goal_box)

        # Quick Preset Chips
        preset_row = QHBoxLayout()
        preset_row.setSpacing(6)
        presets = [
            ("⚡ System Health & RAM Flush", "diagnose system health and generate report"),
            ("🔬 Research & Summarize Topic", "research quantum computing and draft brief"),
            ("📐 Calculate & Record Metrics", "calculate 125 * 45 and record calculation in notes"),
        ]
        for label, prompt in presets:
            btn = QPushButton(label)
            btn.setStyleSheet("""
                QPushButton {
                    background: #0d1424;
                    color: #798fa7;
                    border: 1px solid rgba(255,255,255,0.08);
                    border-radius: 4px;
                    padding: 3px 8px;
                    font-size: 11px;
                }
                QPushButton:hover {
                    border-color: #00f0ff;
                    color: #00f0ff;
                }
            """)
            btn.clicked.connect(lambda checked, p=prompt: self._set_prompt(p))
            preset_row.addWidget(btn)
        preset_row.addStretch()
        layout.addLayout(preset_row)

        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #0A0E19;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 4px;
                text-align: center;
                color: #EAF4FF;
                height: 16px;
                font-size: 10px;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00F0FF, stop:1 #B026FF);
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.progress_bar)

        # Main Splitter (Left: Step Checklist, Right: Thought & Execution Log)
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(4)

        # Left: Steps Checklist
        left_frame = QFrame()
        left_layout = QVBoxLayout(left_frame)
        left_layout.setContentsMargins(0, 0, 6, 0)
        left_layout.setSpacing(6)

        steps_lbl = QLabel("Decomposed Action Plan:")
        steps_lbl.setStyleSheet("color: #A9BCD4; font-weight: bold; font-size: 12px;")
        left_layout.addWidget(steps_lbl)

        self.step_list = QListWidget()
        self.step_list.setStyleSheet("""
            QListWidget {
                background-color: #0A0E19;
                border: 1px solid rgba(0, 240, 255, 0.2);
                border-radius: 6px;
                color: #EAF4FF;
                padding: 6px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            }
            QListWidget::item:selected {
                background-color: rgba(0, 240, 255, 0.15);
                color: #00F0FF;
            }
        """)
        left_layout.addWidget(self.step_list)
        splitter.addWidget(left_frame)

        # Right: Real-time Execution Log
        right_frame = QFrame()
        right_layout = QVBoxLayout(right_frame)
        right_layout.setContentsMargins(6, 0, 0, 0)
        right_layout.setSpacing(6)

        log_lbl = QLabel("Autonomous Thought Stream & Tool Outputs:")
        log_lbl.setStyleSheet("color: #A9BCD4; font-weight: bold; font-size: 12px;")
        right_layout.addWidget(log_lbl)

        self.log_console = QPlainTextEdit()
        self.log_console.setReadOnly(True)
        self.log_console.setFont(QFont("Consolas", 10))
        self.log_console.setStyleSheet("""
            QPlainTextEdit {
                background-color: #050811;
                color: #00ff88;
                border: 1px solid rgba(0, 255, 136, 0.2);
                border-radius: 6px;
                padding: 8px;
            }
        """)
        right_layout.addWidget(self.log_console)
        splitter.addWidget(right_frame)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter)
        self.hub_tabs.addTab(directives_widget, "⚡ Local Directives & Tasks")
        root_layout.addWidget(self.hub_tabs)

    def _set_prompt(self, p: str):
        self.goal_input.setText(p)
        self.goal_input.setFocus()

    def on_deploy_agent(self):
        goal = self.goal_input.text().strip()
        if not goal:
            return

        # Prepare UI
        self.step_list.clear()
        self.log_console.clear()
        self.progress_bar.setValue(0)
        self.status_badge.setText("[STATUS: PLANNING MISSION...]")
        self.status_badge.setStyleSheet("color: #00F0FF; font-weight: bold; font-family: Consolas;")

        self.deploy_btn.setEnabled(False)
        self.abort_btn.setEnabled(True)

        # Generate plan preview
        plan = self.engine.plan_mission(goal)
        for s in plan:
            item = QListWidgetItem(f"⏳ Step {s['step']}: {s['desc']} [{s['tool']}]")
            self.step_list.addItem(item)

        self.log_console.appendPlainText(f"=== NOVA AUTONOMOUS MISSION INITIALIZED ===\nObjective: {goal}\nPlan: {len(plan)} discrete actions formulated.\n")

        # Launch Worker
        self.active_worker = AgentWorker(self.engine, goal, parent=None)
        self.active_worker.step_started.connect(self.on_step_started)
        self.active_worker.step_finished.connect(self.on_step_finished)
        self.active_worker.mission_progress.connect(self.on_mission_progress)
        self.active_worker.mission_completed.connect(self.on_mission_completed)
        self.active_worker.mission_failed.connect(self.on_mission_failed)
        self.active_worker.start()

    @Slot(int, str, str)
    def on_step_started(self, step_num: int, tool: str, desc: str):
        self.status_badge.setText(f"[STATUS: EXECUTING STEP {step_num}...]")
        row = step_num - 1
        if row < self.step_list.count():
            item = self.step_list.item(row)
            item.setText(f"⚙️ Step {step_num}: {desc} [RUNNING]")
            item.setForeground(QColor("#00F0FF"))
            self.step_list.setCurrentRow(row)

        self.log_console.appendPlainText(f"[*] Executing Step {step_num}: '{tool}' -> {desc}...")

    @Slot(int, bool, str)
    def on_step_finished(self, step_num: int, success: bool, output: str):
        row = step_num - 1
        if row < self.step_list.count():
            item = self.step_list.item(row)
            icon = "✅" if success else "❌"
            tag = "DONE" if success else "FAILED"
            text_curr = item.text().replace("[RUNNING]", "").strip()
            item.setText(f"{icon} {text_curr} [{tag}]")
            item.setForeground(QColor("#00ff88" if success else "#ff3366"))

        status_str = "SUCCESS" if success else "ERROR"
        clean_out = output.strip() if len(output.strip()) < 300 else output.strip()[:300] + "... [truncated]"
        self.log_console.appendPlainText(f"    [{status_str}] Output: {clean_out}\n")

    @Slot(int, int)
    def on_mission_progress(self, curr: int, total: int):
        pct = int((curr / max(1, total)) * 100)
        self.progress_bar.setValue(pct)

    @Slot(str)
    def on_mission_completed(self, summary: str):
        self.deploy_btn.setEnabled(True)
        self.abort_btn.setEnabled(False)
        self.progress_bar.setValue(100)
        self.status_badge.setText("[STATUS: MISSION ACCOMPLISHED]")
        self.status_badge.setStyleSheet("color: #00ff88; font-weight: bold; font-family: Consolas;")
        self.log_console.appendPlainText(f"\n=== MISSION COMPLETED ===\n{summary}\n")
        self.active_worker = None

    @Slot(str)
    def on_mission_failed(self, err: str):
        self.deploy_btn.setEnabled(True)
        self.abort_btn.setEnabled(False)
        self.status_badge.setText("[STATUS: MISSION ABORTED]")
        self.status_badge.setStyleSheet("color: #ff3366; font-weight: bold; font-family: Consolas;")
        self.log_console.appendPlainText(f"\n[MISSION HALTED]: {err}\n")
        self.active_worker = None

    def on_abort(self):
        if self.active_worker and self.active_worker.isRunning():
            self.active_worker.cancel()
            self.active_worker.quit()
            self.active_worker.wait(1000)
            self.active_worker = None
        self.deploy_btn.setEnabled(True)
        self.abort_btn.setEnabled(False)
        self.status_badge.setText("[STATUS: ABORTED]")

    def cleanup(self):
        """Cooperatively joins active worker before destruction."""
        if self.active_worker and self.active_worker.isRunning():
            try:
                self.active_worker.step_started.disconnect(self.on_step_started)
                self.active_worker.step_finished.disconnect(self.on_step_finished)
                self.active_worker.mission_progress.disconnect(self.on_mission_progress)
                self.active_worker.mission_completed.disconnect(self.on_mission_completed)
                self.active_worker.mission_failed.disconnect(self.on_mission_failed)
            except Exception:
                pass
            self.active_worker.cancel()
            self.active_worker.quit()
            self.active_worker.wait(1500)
            self.active_worker = None

    def closeEvent(self, event):
        self.cleanup()
        super().closeEvent(event)
