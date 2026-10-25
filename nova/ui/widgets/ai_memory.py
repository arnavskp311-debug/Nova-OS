"""
AI Memory Manager for NOVA OS (Feature 10).
Stores, reviews, and manages user-approved preferences, workspace defaults,
and key operational knowledge with explicit user consent.
Matching Panel 10 of the reference design.
"""

from typing import Optional, List, Dict, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QListWidget, QListWidgetItem, QFrame,
    QMessageBox, QInputDialog, QDialog, QLineEdit,
    QComboBox, QCheckBox
)
from PySide6.QtCore import Qt, Signal

from nova.database import (
    get_ai_memories, add_ai_memory, update_ai_memory,
    delete_ai_memory, clear_all_ai_memory
)


class AIMemoryWidget(QWidget):
    notification_requested = Signal(str, str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.load_memories()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        # Header (Matching Panel 10)
        head = QHBoxLayout()
        icon = QLabel("🧠")
        icon.setStyleSheet("font-size: 20px;")
        head.addWidget(icon)

        title = QLabel("NOVA MEMORY // USER-APPROVED CONTEXT")
        title.setStyleSheet("font-size: 14px; font-weight: bold; color: #00f0ff; letter-spacing: 1px;")
        head.addWidget(title)
        head.addStretch()

        add_btn = QPushButton("➕ Add Memory")
        add_btn.setStyleSheet("""
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
        add_btn.clicked.connect(self.prompt_add_memory)
        head.addWidget(add_btn)
        layout.addLayout(head)

        desc = QLabel("Save useful preferences and contextual facts only with your explicit approval. NOVA will never secretly profile you.")
        desc.setStyleSheet("color: #94a3b8; font-size: 12px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Memory Items List (Matching Panel 10)
        self.memory_list = QListWidget()
        self.memory_list.setStyleSheet("""
            QListWidget {
                background: #080d1a;
                border: 1px solid rgba(0, 240, 255, 0.2);
                border-radius: 8px;
                color: #e2e8f0;
                padding: 6px;
            }
            QListWidget::item {
                background: #0e1628;
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 6px;
                padding: 10px;
                margin-bottom: 6px;
            }
            QListWidget::item:hover {
                border-color: #00f0ff;
                background: #14203a;
            }
            QListWidget::item:selected {
                background: #162444;
                border-left: 3px solid #00f0ff;
            }
        """)
        layout.addWidget(self.memory_list)

        # Actions Row (Exact buttons from Panel 10: View Memory, Edit, Clear All)
        btns_row = QHBoxLayout()
        view_btn = QPushButton("👁 View Details")
        view_btn.setStyleSheet("""
            QPushButton {
                background: #101c32;
                border: 1px solid #00f0ff;
                border-radius: 4px;
                color: #ffffff;
                padding: 7px 16px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #00f0ff;
                color: #050811;
            }
        """)
        view_btn.clicked.connect(self.view_selected_memory)
        btns_row.addWidget(view_btn)

        edit_btn = QPushButton("✏ Edit")
        edit_btn.setStyleSheet("""
            QPushButton {
                background: #101c32;
                border: 1px solid rgba(255,255,255,0.15);
                border-radius: 4px;
                color: #ffffff;
                padding: 7px 16px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #1a2744;
                border-color: #00f0ff;
            }
        """)
        edit_btn.clicked.connect(self.edit_selected_memory)
        btns_row.addWidget(edit_btn)

        delete_btn = QPushButton("🗑 Delete")
        delete_btn.setStyleSheet("""
            QPushButton {
                background: #1f121d;
                border: 1px solid rgba(255, 42, 85, 0.3);
                border-radius: 4px;
                color: #ff6b8b;
                padding: 7px 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #ff2a55;
                color: #ffffff;
            }
        """)
        delete_btn.clicked.connect(self.delete_selected_memory)
        btns_row.addWidget(delete_btn)

        btns_row.addStretch()

        clear_btn = QPushButton("Clear All Memory")
        clear_btn.setObjectName("DangerButton")
        clear_btn.setStyleSheet("""
            QPushButton#DangerButton {
                background: #240c12;
                border: 1px solid #ff2a55;
                border-radius: 4px;
                color: #ff2a55;
                font-weight: bold;
                padding: 7px 16px;
            }
            QPushButton#DangerButton:hover {
                background: #ff2a55;
                color: #ffffff;
            }
        """)
        clear_btn.clicked.connect(self.clear_all)
        btns_row.addWidget(clear_btn)
        layout.addLayout(btns_row)

    def load_memories(self):
        self.memory_list.clear()
        memories = get_ai_memories(approved_only=False)
        for m in memories:
            apprv_marker = "🔘 [Approved]" if m.get("approved") else "○ [Pending Approval]"
            item_text = f"{apprv_marker}  {m['key']}  :  {m['value']}   ({m['category']})"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, m)
            self.memory_list.addItem(item)

        if self.memory_list.count() > 0:
            self.memory_list.setCurrentRow(0)

    def view_selected_memory(self):
        curr = self.memory_list.currentItem()
        if not curr:
            return
        m = curr.data(Qt.UserRole)
        status = "User Approved" if m.get("approved") else "Pending Review"
        QMessageBox.information(
            self,
            f"AI Memory Detail — {m['key']}",
            f"Category: {m['category']}\n"
            f"Key: {m['key']}\n"
            f"Saved Value: {m['value']}\n"
            f"Approval Status: {status}\n"
            f"Saved Timestamp: {m.get('created_at', 'N/A')}\n\n"
            "This information is used by NOVA Assistant only when responding in this context."
        )

    def prompt_add_memory(self):
        key, ok = QInputDialog.getText(self, "Add AI Memory", "Enter preference or fact key (e.g. 'Favorite search engine'):")
        if ok and key.strip():
            val, ok2 = QInputDialog.getText(self, "Memory Value", f"Enter value for '{key.strip()}':")
            if ok2 and val.strip():
                add_ai_memory("Custom", key.strip(), val.strip(), approved=1)
                self.load_memories()

    def edit_selected_memory(self):
        curr = self.memory_list.currentItem()
        if not curr:
            return
        m = curr.data(Qt.UserRole)
        new_val, ok = QInputDialog.getText(self, "Edit Memory", f"Update value for '{m['key']}':", text=m['value'])
        if ok and new_val.strip():
            update_ai_memory(m['id'], m['category'], m['key'], new_val.strip(), m.get('approved', 1))
            self.load_memories()

    def delete_selected_memory(self):
        curr = self.memory_list.currentItem()
        if not curr:
            return
        m = curr.data(Qt.UserRole)
        delete_ai_memory(m['id'])
        self.load_memories()

    def clear_all(self):
        reply = QMessageBox.question(
            self, "Clear AI Memory",
            "Are you sure you want to purge all stored AI memories?\nThis action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            clear_all_ai_memory()
            self.load_memories()
