"""
Automation Studio for NOVA OS (Feature 12).
Allows creating, editing, and executing sequential workflows matching Panel 12.
"""

from typing import Optional, List, Dict, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QListWidget, QListWidgetItem, QFrame,
    QProgressBar, QMessageBox, QTextEdit, QInputDialog
)
from PySide6.QtCore import Qt, Signal, QTimer

from nova.database import (
    get_workflows, get_workflow, create_workflow,
    delete_workflow, record_workflow_run
)


class AutomationStudioWidget(QWidget):
    action_requested = Signal(str, dict)  # action_name, params (e.g. "launch_app", "switch_workspace", "start_timer")
    notification_requested = Signal(str, str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_wf: Optional[Dict[str, Any]] = None
        self.executing_steps: List[Dict[str, Any]] = []
        self.step_index = 0
        self.setup_ui()
        self.load_workflows()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(12)

        # Header
        head = QHBoxLayout()
        icon = QLabel("⚡")
        icon.setStyleSheet("font-size: 20px;")
        head.addWidget(icon)

        title = QLabel("AUTOMATION STUDIO // SAFE DESKTOP WORKFLOWS")
        title.setStyleSheet("font-size: 14px; font-weight: bold; color: #00f0ff; letter-spacing: 1px;")
        head.addWidget(title)
        head.addStretch()

        new_btn = QPushButton("➕ Create Workflow")
        new_btn.setStyleSheet("""
            QPushButton {
                background: #111d33;
                border: 1px solid #00f0ff;
                border-radius: 4px;
                color: #00f0ff;
                font-size: 11px;
                font-weight: 600;
                padding: 5px 12px;
            }
            QPushButton:hover {
                background: #00f0ff;
                color: #050811;
            }
        """)
        new_btn.clicked.connect(self.prompt_create_workflow)
        head.addWidget(new_btn)
        main_layout.addLayout(head)

        desc = QLabel("Automate repetitive desktop tasks safely using chained NOVA directives. Never runs arbitrary unsandboxed scripts.")
        desc.setStyleSheet("color: #94a3b8; font-size: 12px;")
        main_layout.addWidget(desc)

        # Body Splitter: Left Sidebar (Workflows, Logs), Right Workflow Details
        body_layout = QHBoxLayout()
        body_layout.setSpacing(14)

        # Left List Panel
        self.wf_list = QListWidget()
        self.wf_list.setFixedWidth(220)
        self.wf_list.setStyleSheet("""
            QListWidget {
                background: #080d1a;
                border: 1px solid rgba(0, 240, 255, 0.25);
                border-radius: 8px;
                padding: 6px;
                color: #e2e8f0;
            }
            QListWidget::item {
                padding: 10px 12px;
                border-radius: 6px;
                margin-bottom: 4px;
                font-weight: 600;
                font-size: 12px;
            }
            QListWidget::item:hover {
                background: #121c32;
                color: #00f0ff;
            }
            QListWidget::item:selected {
                background: #152648;
                border-left: 3px solid #00f0ff;
                color: #ffffff;
            }
        """)
        self.wf_list.currentItemChanged.connect(self.on_workflow_selected)
        body_layout.addWidget(self.wf_list)

        # Right Detail Card (Matching Panel 12)
        self.detail_card = QFrame()
        self.detail_card.setStyleSheet("""
            QFrame {
                background: #0b1222;
                border: 1px solid rgba(0, 240, 255, 0.3);
                border-radius: 10px;
                padding: 16px;
            }
        """)
        card_layout = QVBoxLayout(self.detail_card)
        card_layout.setSpacing(12)

        self.wf_title_lbl = QLabel("Study Workspace Workflow")
        self.wf_title_lbl.setStyleSheet("font-size: 18px; font-weight: bold; color: #ffffff;")
        card_layout.addWidget(self.wf_title_lbl)

        self.wf_desc_lbl = QLabel("Automated startup sequence for focused study sessions.")
        self.wf_desc_lbl.setStyleSheet("color: #7dd3fc; font-size: 12px;")
        card_layout.addWidget(self.wf_desc_lbl)

        # Steps Container
        steps_lbl = QLabel("SEQUENTIAL STEPS:")
        steps_lbl.setStyleSheet("color: #00f0ff; font-weight: bold; font-size: 11px; letter-spacing: 1px;")
        card_layout.addWidget(steps_lbl)

        self.steps_view = QTextEdit()
        self.steps_view.setReadOnly(True)
        self.steps_view.setStyleSheet("""
            QTextEdit {
                background: #060a14;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 6px;
                color: #e2e8f0;
                font-family: 'Segoe UI', monospace;
                font-size: 12px;
                padding: 10px;
                line-height: 1.6;
            }
        """)
        card_layout.addWidget(self.steps_view)

        # Execution Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("QProgressBar::chunk { background-color: #00ff88; }")
        card_layout.addWidget(self.progress_bar)

        self.status_lbl = QLabel("Ready to run")
        self.status_lbl.setStyleSheet("color: #64748b; font-size: 11px;")
        card_layout.addWidget(self.status_lbl)

        # Action Buttons (Run, Edit, Delete)
        btns_row = QHBoxLayout()
        self.run_btn = QPushButton("▶ Run Workflow")
        self.run_btn.setStyleSheet("""
            QPushButton {
                background: #0052cc;
                border: 1px solid #00f0ff;
                border-radius: 6px;
                color: #ffffff;
                font-size: 12px;
                font-weight: bold;
                padding: 8px 20px;
            }
            QPushButton:hover {
                background: #00f0ff;
                color: #050811;
            }
        """)
        self.run_btn.clicked.connect(self.run_workflow)
        btns_row.addWidget(self.run_btn)

        self.edit_btn = QPushButton("✏ Edit Steps")
        self.edit_btn.setStyleSheet("""
            QPushButton {
                background: #111a2e;
                border: 1px solid rgba(255,255,255,0.15);
                border-radius: 6px;
                color: #ffffff;
                font-size: 12px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background: #1c2b4c;
                border-color: #00f0ff;
            }
        """)
        self.edit_btn.clicked.connect(self.edit_workflow)
        btns_row.addWidget(self.edit_btn)

        del_btn = QPushButton("🗑 Delete")
        del_btn.setObjectName("DangerButton")
        del_btn.setStyleSheet("""
            QPushButton#DangerButton {
                background: #1f121d;
                border: 1px solid #ff2a55;
                border-radius: 6px;
                color: #ff2a55;
                font-size: 12px;
                padding: 8px 14px;
            }
            QPushButton#DangerButton:hover {
                background: #ff2a55;
                color: #ffffff;
            }
        """)
        del_btn.clicked.connect(self.delete_current_workflow)
        btns_row.addWidget(del_btn)
        btns_row.addStretch()
        card_layout.addLayout(btns_row)

        body_layout.addWidget(self.detail_card, stretch=1)
        main_layout.addLayout(body_layout)

    def load_workflows(self):
        self.wf_list.clear()
        flows = get_workflows()
        for f in flows:
            item = QListWidgetItem(f"⚡ {f['name']}")
            item.setData(Qt.UserRole, f)
            self.wf_list.addItem(item)

        if self.wf_list.count() > 0:
            self.wf_list.setCurrentRow(0)

    def on_workflow_selected(self, current: Optional[QListWidgetItem], previous=None):
        if not current:
            return
        f = current.data(Qt.UserRole)
        self.selected_wf = f
        self.wf_title_lbl.setText(f["name"])
        self.wf_desc_lbl.setText(f.get("description", ""))

        steps = f.get("steps", [])
        lines = []
        for i, s in enumerate(steps, 1):
            desc = s.get("desc") or f"{s.get('action')} -> {s.get('target', '')}"
            lines.append(f"{i}. {desc}")
        self.steps_view.setPlainText("\n".join(lines))
        self.progress_bar.setValue(0)
        self.status_lbl.setText("Ready to run")

    def run_workflow(self):
        if not self.selected_wf:
            return
        steps = self.selected_wf.get("steps", [])
        if not steps:
            return

        self.executing_steps = steps
        self.step_index = 0
        self.run_btn.setEnabled(False)
        self.status_lbl.setText("Executing step 1...")
        self._execute_next_step()

    def _execute_next_step(self):
        if self.step_index >= len(self.executing_steps):
            self.progress_bar.setValue(100)
            self.status_lbl.setText("Workflow executed successfully!")
            self.run_btn.setEnabled(True)
            record_workflow_run(self.selected_wf["id"])
            self.notification_requested.emit(
                "WORKFLOW COMPLETE",
                f"Finished executing '{self.selected_wf['name']}'.",
                "success"
            )
            return

        step = self.executing_steps[self.step_index]
        pct = int(((self.step_index + 1) / len(self.executing_steps)) * 100)
        self.progress_bar.setValue(pct)
        self.status_lbl.setText(f"Running step {self.step_index + 1}: {step.get('desc', '')}")

        action = step.get("action")
        target = step.get("target")

        # Dispatch action
        if action == "launch_app":
            self.action_requested.emit("launch_app", {"app_id": target})
        elif action == "switch_workspace":
            self.action_requested.emit("switch_workspace", {"workspace_id": target})
        elif action == "purge_cache":
            self.action_requested.emit("purge_cache", {})
        elif action == "start_timer":
            self.action_requested.emit("start_timer", {"duration": step.get("duration", 25)})

        self.step_index += 1
        # Chain next step smoothly after 500ms
        QTimer.singleShot(600, self._execute_next_step)

    def prompt_create_workflow(self):
        name, ok = QInputDialog.getText(self, "Create Workflow", "Enter workflow title:")
        if ok and name.strip():
            wf_id = f"wf_{name.strip().lower().replace(' ', '_')}"
            desc, _ = QInputDialog.getText(self, "Description", "Enter short description:")
            steps = [
                {"action": "launch_app", "target": "browser", "desc": "Launch NOVA Cyber Browser"},
                {"action": "launch_app", "target": "notes", "desc": "Open NovaPad Notes"}
            ]
            create_workflow(wf_id, name.strip(), desc.strip() or "Custom workflow", steps)
            self.load_workflows()

    def edit_workflow(self):
        if not self.selected_wf:
            return
        QMessageBox.information(
            self, "Edit Steps",
            f"Workflow '{self.selected_wf['name']}' currently contains {len(self.selected_wf.get('steps', []))} verified safe actions.\n"
            "Actions can be triggered interactively from the Command Palette."
        )

    def delete_current_workflow(self):
        if not self.selected_wf:
            return
        wf_id = self.selected_wf["id"]
        delete_workflow(wf_id)
        self.load_workflows()
