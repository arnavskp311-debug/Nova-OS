"""
NOVA OS Quick Command Palette & Floating Raycast-Style Launcher.
Frameless, translucent floating palette for instantaneous app navigation,
math calculations, note searches, system diagnostics, and AI queries.
"""

from typing import List, Dict, Any, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
    QListWidget, QListWidgetItem, QLabel, QFrame,
    QApplication, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, Signal, Slot, QPoint
from PySide6.QtGui import QFont, QColor, QKeyEvent

from nova.deterministic_actions import evaluate_deterministic_query
from nova.database import get_notes, create_note
from nova.safety import execute_command_safely, analyze_command, RiskLevel
from nova.memory_optimizer import get_memory_optimizer
from nova.vault import get_vault
from nova.sound_fx import play_sound

class QuickLauncherWidget(QWidget):
    """Floating translucent command palette inspired by Raycast / Spotlight."""
    action_triggered = Signal(str, dict)  # action_type, payload

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Popup)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedWidth(640)
        self.setFixedHeight(380)

        self.setup_ui()

    def setup_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(10, 10, 10, 10)

        # Container Frame with Neon Border and Glassmorphism styling
        self.container = QFrame(self)
        self.container.setObjectName("QuickLauncherContainer")
        self.container.setStyleSheet("""
            QFrame#QuickLauncherContainer {
                background-color: rgba(10, 14, 25, 0.96);
                border: 1px solid #00F0FF;
                border-radius: 12px;
            }
        """)

        # Drop shadow for floating effect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setColor(QColor(0, 240, 255, 90))
        shadow.setOffset(0, 4)
        self.container.setGraphicsEffect(shadow)

        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(14, 14, 14, 14)
        container_layout.setSpacing(10)

        # Search Input Bar
        search_row = QHBoxLayout()
        search_icon = QLabel("⚡")
        search_icon.setStyleSheet("font-size: 18px; color: #00F0FF;")
        search_row.addWidget(search_icon)

        self.input_edit = QLineEdit()
        self.input_edit.setFont(QFont("Segoe UI", 13))
        self.input_edit.setPlaceholderText("Type a command, calculation (e.g. 24*15), note search, or AI query...")
        self.input_edit.setStyleSheet("""
            QLineEdit {
                background: transparent;
                border: none;
                color: #EAF4FF;
                padding: 4px;
                font-weight: 500;
            }
            QLineEdit::placeholder {
                color: #8497B0;
            }
        """)
        self.input_edit.textChanged.connect(self.on_query_changed)
        self.input_edit.returnPressed.connect(self.on_item_activated)
        search_row.addWidget(self.input_edit)

        esc_hint = QLabel("ESC to close")
        esc_hint.setStyleSheet("color: #718096; font-size: 11px; font-weight: bold; padding-right: 4px;")
        search_row.addWidget(esc_hint)
        container_layout.addLayout(search_row)

        # Separator line
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background-color: rgba(255, 255, 255, 0.1); max-height: 1px;")
        container_layout.addWidget(sep)

        # Results List
        self.results_list = QListWidget()
        self.results_list.setStyleSheet("""
            QListWidget {
                background: transparent;
                border: none;
                color: #EAF4FF;
                font-size: 13px;
                outline: none;
            }
            QListWidget::item {
                padding: 8px 10px;
                border-radius: 6px;
                margin-bottom: 2px;
            }
            QListWidget::item:selected {
                background-color: rgba(0, 240, 255, 0.15);
                color: #00F0FF;
                border: 1px solid rgba(0, 240, 255, 0.4);
            }
            QListWidget::item:hover {
                background-color: rgba(255, 255, 255, 0.05);
            }
        """)
        self.results_list.itemActivated.connect(self.on_item_activated)
        container_layout.addWidget(self.results_list)

        # Footer Status bar
        footer_row = QHBoxLayout()
        self.footer_lbl = QLabel("↵ Execute Action  •  ↑↓ Navigate  •  TAB Autocomplete")
        self.footer_lbl.setStyleSheet("color: #718096; font-size: 11px;")
        footer_row.addWidget(self.footer_lbl)
        container_layout.addLayout(footer_row)

        root_layout.addWidget(self.container)

    def _eval_math(self, expression: str) -> Optional[str]:
        """Evaluates a mathematical expression safely via deterministic AST."""
        from nova.deterministic_actions import evaluate_math_expression
        try:
            res = evaluate_math_expression(expression)
            return str(res) if res is not None else None
        except Exception:
            return None

    def show_centered(self):
        """Displays the launcher centered on the active screen."""
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 3  # Position slightly above vertical center
        self.move(x, y)
        self.input_edit.clear()
        self.populate_default_actions()
        self.show()
        self.raise_()
        self.activateWindow()
        self.input_edit.setFocus()
        play_sound("blip")

    def populate_default_actions(self):
        """Populates quick system directives when input is empty."""
        self.results_list.clear()
        defaults = [
            ("⚡ Ask NOVA AI Assistant", "ask_ai", "Open chat or enter a question"),
            ("🧹 Flush Quantum Memory", "flush_ram", "Reclaim unused physical working set RAM"),
            ("📝 Open NovaPad (Notes Vault)", "open_notes", "Local markdown notes and knowledge"),
            ("🌐 Open NOVA Browser", "open_browser", "Tabbed web browsing with AI sidebar"),
            ("💻 Open Cyber Terminal", "open_terminal", "Unprivileged virtual sandbox shell"),
            ("⚙️ Open Control Center", "open_settings", "System preferences and visual themes"),
            ("🔍 Search Ingested Documents (Vault)", "open_vault", "Search local offline PDF & text files"),
        ]
        for title, action, subtitle in defaults:
            item = QListWidgetItem(f"{title}  —  {subtitle}")
            item.setData(Qt.UserRole, {"action": action, "value": ""})
            self.results_list.addItem(item)
        if self.results_list.count() > 0:
            self.results_list.setCurrentRow(0)

    @Slot(str)
    def on_query_changed(self, query: str):
        q = query.strip()
        if not q:
            self.populate_default_actions()
            return

        self.results_list.clear()

        # 1. Deterministic Math & Conversions
        det_result = evaluate_deterministic_query(q)
        if det_result:
            math_res = det_result.get("value") or det_result.get("result", "")
            item = QListWidgetItem(f"🔢 Calculation: {det_result.get('result', q)}")
            item.setData(Qt.UserRole, {"action": "copy_math", "value": math_res})
            self.results_list.addItem(item)

        # 2. Direct Terminal / Diagnostic commands
        analysis = analyze_command(q)
        if analysis["risk"] in [RiskLevel.SAFE, RiskLevel.SIMULATED]:
            item = QListWidgetItem(f"💻 Run Diagnostic: '{q}'  (Direct Safe Shell)")
            item.setData(Qt.UserRole, {"action": "run_terminal", "value": q})
            self.results_list.addItem(item)

        # 3. Always offer Ask AI
        item_ai = QListWidgetItem(f"🤖 Ask NOVA AI: \"{q}\"")
        item_ai.setData(Qt.UserRole, {"action": "ask_ai_query", "value": q})
        self.results_list.addItem(item_ai)

        # 4. Search NovaPad Notes
        notes = get_notes()
        matching_notes = [n for n in notes if q.lower() in n["title"].lower() or q.lower() in (n.get("tags") or "").lower()]
        for n in matching_notes[:3]:
            item = QListWidgetItem(f"📄 Note: {n['title']}  [Tags: {n.get('tags') or 'none'}]")
            item.setData(Qt.UserRole, {"action": "open_note_id", "value": n["id"]})
            self.results_list.addItem(item)

        # 5. Search Document Vault
        vault = get_vault()
        vault_chunks = vault.search_chunks(q, top_k=2)
        for c in vault_chunks:
            item = QListWidgetItem(f"📚 Vault Doc: {c['filename']} — \"{c['content'][:50]}...\"")
            item.setData(Qt.UserRole, {"action": "open_vault_query", "value": q})
            self.results_list.addItem(item)

        # 6. Quick create note
        item_create = QListWidgetItem(f"➕ Create New Note: \"{q}\"")
        item_create.setData(Qt.UserRole, {"action": "create_quick_note", "value": q})
        self.results_list.addItem(item_create)

        if self.results_list.count() > 0:
            self.results_list.setCurrentRow(0)

    @Slot()
    def on_item_activated(self):
        curr = self.results_list.currentItem()
        if not curr:
            return
        data = curr.data(Qt.UserRole)
        if not data:
            return

        action = data.get("action", "")
        value = data.get("value", "")

        play_sound("click")
        self.close()

        # Handle built-in quick actions directly
        if action == "flush_ram":
            res = get_memory_optimizer().flush_quantum_memory()
            play_sound("success")
            self.action_triggered.emit("notification", {"title": "RAM Flushed", "msg": f"Quantum flush complete. Available RAM: {res['available_after_mb']} MB"})
            return
        elif action == "copy_math":
            QApplication.clipboard().setText(str(value))
            play_sound("chime")
            self.action_triggered.emit("notification", {"title": "Result Copied", "msg": f"Copied '{value}' to clipboard."})
            return
        elif action == "create_quick_note":
            nid = create_note(str(value), f"# {value}\n\nCreated quickly via Quick Launcher.", "quick-note")
            play_sound("chime")
            self.action_triggered.emit("open_note_id", {"id": nid})
            return

        # Forward other actions to main application
        self.action_triggered.emit(action, {"value": value})

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Escape:
            self.close()
        elif event.key() == Qt.Key_Down:
            curr = self.results_list.currentRow()
            if curr < self.results_list.count() - 1:
                self.results_list.setCurrentRow(curr + 1)
        elif event.key() == Qt.Key_Up:
            curr = self.results_list.currentRow()
            if curr > 0:
                self.results_list.setCurrentRow(curr - 1)
        else:
            super().keyPressEvent(event)
