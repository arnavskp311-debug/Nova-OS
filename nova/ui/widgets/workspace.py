"""
Workspace Profiles Widget for NOVA OS (Feature 3).
Displays and switches workspace profiles matching Panel 3 of the NOVA concept specification.
"""

from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QListWidget, QListWidgetItem, QFrame,
    QGridLayout, QMessageBox, QInputDialog
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from nova.workspace_manager import WorkspaceManager

APP_ICONS = {
    "browser": ("🌐", "NOVA Browser"),
    "notes": ("📝", "NovaPad Notes"),
    "files": ("📁", "File Vault"),
    "chat": ("🤖", "NOVA AI"),
    "terminal": ("💻", "Cyber Terminal"),
    "dashboard": ("📊", "Telemetry"),
    "settings": ("⚙", "Settings"),
    "calendar": ("📅", "Calendar"),
    "automation": ("⚡", "Automation"),
}

WORKSPACE_ICONS = {
    "study": "🎓",
    "coding": "💻",
    "research": "🔬",
    "personal": "👤",
    "entertainment": "🎮",
}


class WorkspaceWidget(QWidget):
    workspace_applied = Signal(dict)  # Emits workspace dict when activated
    app_launch_requested = Signal(str)

    def __init__(self, workspace_manager: Optional[WorkspaceManager] = None, parent=None):
        super().__init__(parent)
        self.manager = workspace_manager or WorkspaceManager(self)
        self.selected_ws = None
        self.setup_ui()
        self.load_workspaces()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # Header
        head_layout = QHBoxLayout()
        icon_lbl = QLabel("🗂")
        icon_lbl.setStyleSheet("font-size: 20px;")
        head_layout.addWidget(icon_lbl)

        title_lbl = QLabel("WORKSPACE MANAGER // PROFILES")
        title_lbl.setStyleSheet("font-size: 15px; font-weight: bold; color: #00f0ff; letter-spacing: 1px;")
        head_layout.addWidget(title_lbl)
        head_layout.addStretch()

        add_btn = QPushButton("➕ New Workspace")
        add_btn.setStyleSheet("""
            QPushButton {
                background: #111d33;
                border: 1px solid #00f0ff;
                border-radius: 6px;
                color: #00f0ff;
                font-weight: 600;
                padding: 5px 12px;
            }
            QPushButton:hover {
                background: #00f0ff;
                color: #050811;
            }
        """)
        add_btn.clicked.connect(self.prompt_new_workspace)
        head_layout.addWidget(add_btn)
        main_layout.addLayout(head_layout)

        # Split Layout: Left List, Right Profile Details
        content_layout = QHBoxLayout()
        content_layout.setSpacing(14)

        # Left List Panel
        self.ws_list = QListWidget()
        self.ws_list.setFixedWidth(200)
        self.ws_list.setStyleSheet("""
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
        self.ws_list.currentItemChanged.connect(self.on_selection_changed)
        content_layout.addWidget(self.ws_list)

        # Right Detail Card (Matching Panel 3)
        self.detail_card = QFrame()
        self.detail_card.setStyleSheet("""
            QFrame {
                background: #0b1222;
                border: 1px solid rgba(0, 240, 255, 0.3);
                border-radius: 10px;
                padding: 16px;
            }
        """)
        detail_layout = QVBoxLayout(self.detail_card)
        detail_layout.setSpacing(14)

        # Workspace Hero Row
        hero_box = QHBoxLayout()
        self.badge_icon = QLabel("🎓")
        self.badge_icon.setStyleSheet("font-size: 36px; padding: 6px; background: #131e36; border-radius: 10px; border: 1px solid #00f0ff;")
        hero_box.addWidget(self.badge_icon)

        title_box = QVBoxLayout()
        self.ws_name_lbl = QLabel("Study Workspace")
        self.ws_name_lbl.setStyleSheet("font-size: 20px; font-weight: bold; color: #ffffff;")
        title_box.addWidget(self.ws_name_lbl)

        self.ws_desc_lbl = QLabel("Focus • Learn • Achieve")
        self.ws_desc_lbl.setStyleSheet("color: #7dd3fc; font-size: 13px; font-style: italic;")
        title_box.addWidget(self.ws_desc_lbl)
        hero_box.addLayout(title_box)
        hero_box.addStretch()

        self.active_tag = QLabel("ACTIVE")
        self.active_tag.setStyleSheet("""
            background: #082820;
            color: #00ff88;
            border: 1px solid #00ff88;
            border-radius: 12px;
            font-size: 10px;
            font-weight: bold;
            padding: 4px 10px;
        """)
        hero_box.addWidget(self.active_tag)
        detail_layout.addLayout(hero_box)

        # Theme indicator
        self.theme_info_lbl = QLabel("Theme: Cyber Cyan (Dark Blue)")
        self.theme_info_lbl.setStyleSheet("color: #94a3b8; font-size: 12px; font-weight: 500;")
        detail_layout.addWidget(self.theme_info_lbl)

        # Pinned Applications Section
        pinned_lbl = QLabel("PINNED APPS")
        pinned_lbl.setStyleSheet("color: #00f0ff; font-weight: bold; font-size: 11px; letter-spacing: 1px;")
        detail_layout.addWidget(pinned_lbl)

        self.apps_container = QWidget()
        self.apps_grid = QHBoxLayout(self.apps_container)
        self.apps_grid.setContentsMargins(0, 0, 0, 0)
        self.apps_grid.setSpacing(10)
        detail_layout.addWidget(self.apps_container)

        detail_layout.addStretch()

        # Switch Workspace Action Button
        btn_row = QHBoxLayout()
        self.switch_btn = QPushButton("⚡ Switch Workspace")
        self.switch_btn.setStyleSheet("""
            QPushButton {
                background: #0052cc;
                border: 1px solid #00f0ff;
                border-radius: 6px;
                color: #ffffff;
                font-size: 13px;
                font-weight: bold;
                padding: 10px 24px;
            }
            QPushButton:hover {
                background: #00f0ff;
                color: #050811;
            }
            QPushButton:disabled {
                background: #111a2e;
                border-color: rgba(255,255,255,0.1);
                color: #64748b;
            }
        """)
        self.switch_btn.clicked.connect(self.activate_current_workspace)
        btn_row.addWidget(self.switch_btn)
        btn_row.addStretch()
        detail_layout.addLayout(btn_row)

        content_layout.addWidget(self.detail_card, stretch=1)
        main_layout.addLayout(content_layout)

        # Safety & Process Isolation Disclosure
        disclaimer = QLabel("🛡️ Workspace switching organizes your application workflows and visual theme within NOVA OS. It does not isolate Windows processes or user accounts.")
        disclaimer.setStyleSheet("color: #64748b; font-size: 11px;")
        disclaimer.setWordWrap(True)
        main_layout.addWidget(disclaimer)

    def load_workspaces(self):
        self.ws_list.clear()
        workspaces = self.manager.get_all_workspaces()
        active_row = 0
        for i, ws in enumerate(workspaces):
            icon = WORKSPACE_ICONS.get(ws["id"], "❖")
            active_marker = " ●" if ws.get("is_active") else ""
            item = QListWidgetItem(f"{icon}  {ws['name']}{active_marker}")
            item.setData(Qt.UserRole, ws)
            self.ws_list.addItem(item)
            if ws.get("is_active"):
                active_row = i

        if self.ws_list.count() > 0:
            self.ws_list.setCurrentRow(active_row)

    def on_selection_changed(self, current: Optional[QListWidgetItem], previous=None):
        if not current:
            return
        ws = current.data(Qt.UserRole)
        self.selected_ws = ws
        self.ws_name_lbl.setText(ws["name"])
        self.ws_desc_lbl.setText(ws.get("description", ""))
        self.badge_icon.setText(WORKSPACE_ICONS.get(ws["id"], "❖"))
        self.theme_info_lbl.setText(f"Accent Theme: {ws.get('theme', 'Cyber Cyan')}")

        is_active = bool(ws.get("is_active"))
        self.active_tag.setVisible(is_active)
        self.switch_btn.setEnabled(not is_active)
        self.switch_btn.setText("Current Active Workspace" if is_active else "⚡ Switch Workspace")

        # Clear and render pinned app chips
        while self.apps_grid.count() > 0:
            item = self.apps_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        pinned = ws.get("pinned_apps", [])
        for app_id in pinned:
            icon, name = APP_ICONS.get(app_id, ("❖", app_id.capitalize()))
            btn = QPushButton(f"{icon}\n{name}")
            btn.setFixedSize(85, 75)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background: #121c32;
                    border: 1px solid rgba(0, 240, 255, 0.2);
                    border-radius: 8px;
                    color: #cbd5e1;
                    font-size: 11px;
                    font-weight: 600;
                    padding: 6px;
                }
                QPushButton:hover {
                    background: #1c2b4c;
                    border-color: #00f0ff;
                    color: #ffffff;
                }
            """)
            btn.clicked.connect(lambda checked, a=app_id: self.app_launch_requested.emit(a))
            self.apps_grid.addWidget(btn)
        self.apps_grid.addStretch()

    def activate_current_workspace(self):
        if not self.selected_ws:
            return
        ws_id = self.selected_ws["id"]
        if self.manager.switch_to(ws_id):
            self.load_workspaces()
            self.workspace_applied.emit(self.selected_ws)

    def prompt_new_workspace(self):
        name, ok = QInputDialog.getText(self, "New Workspace", "Enter workspace name (e.g. Design, Deep Work):")
        if ok and name.strip():
            ws_id = name.strip().lower().replace(" ", "_")
            desc, _ = QInputDialog.getText(self, "Workspace Focus", "Enter focus motto or description:")
            self.manager.create_custom(
                ws_id, name.strip(), desc.strip() or "Custom Focus Workspace", "Cyber Cyan",
                ["browser", "notes", "chat"]
            )
            self.load_workspaces()
