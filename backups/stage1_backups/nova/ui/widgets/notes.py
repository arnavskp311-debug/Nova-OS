"""
NovaPad: Local Notes & Documentation for NOVA OS.
Stores notes in SQLite with search, tag filtering, and AI polish integration.
"""

from typing import Optional
from datetime import datetime, timedelta
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QTextEdit, QListWidget,
    QListWidgetItem, QSplitter, QMessageBox, QFrame,
    QTabWidget, QComboBox, QCheckBox
)
from PySide6.QtCore import Qt, QThread, Signal, Slot
from nova.database import (
    get_notes, create_note, update_note, delete_note,
    get_reminders, create_reminder, complete_reminder, delete_reminder
)
from nova.ollama_client import OllamaClient
from nova.config import DEFAULT_MODEL

class AIPolishWorker(QThread):
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, client: OllamaClient, content: str, default_model: str = DEFAULT_MODEL):
        super().__init__()
        self.client = client
        self.content = content
        self.default_model = default_model

    def run(self):
        try:
            if not self.client.check_connection():
                self.error.emit("Ollama is unreachable. Please run 'ollama serve'.")
                return

            models = self.client.get_available_models()
            model = self.default_model if self.default_model in models else (models[0] if models else "")
            if not model:
                self.error.emit("No installed Ollama models found.")
                return

            prompt = (
                "Please refine, organize, and format the following user note in clean, concise markdown. "
                "Keep the essential facts intact and improve readability:\n\n" + self.content
            )
            chunks = []
            for c in self.client.stream_chat([{"role": "user", "content": prompt}], model=model):
                chunks.append(c)
            self.finished.emit("".join(chunks))
        except Exception as e:
            self.error.emit(str(e))

class NotesWidget(QWidget):
    def __init__(self, ollama_client: OllamaClient, parent=None):
        super().__init__(parent)
        self.ollama_client = ollama_client
        self.active_note_id: Optional[int] = None
        self.polish_worker: Optional[AIPolishWorker] = None
        self.setup_ui()
        self.load_notes_list()
        self.load_reminders_list()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)

        self.tabs = QTabWidget()

        # ================= TAB 1: NOTES & KNOWLEDGE =================
        notes_widget = QWidget()
        notes_layout = QVBoxLayout(notes_widget)
        notes_layout.setContentsMargins(8, 8, 8, 8)
        notes_layout.setSpacing(10)

        # Header
        header = QHBoxLayout()
        title = QLabel("NOVAPAD // LOCAL KNOWLEDGE VAULT")
        title.setObjectName("HeaderTitle")
        header.addWidget(title)
        header.addStretch()

        self.new_btn = QPushButton("+ New Note")
        self.new_btn.setObjectName("PrimaryButton")
        self.new_btn.clicked.connect(self.on_new_note)
        header.addWidget(self.new_btn)

        self.del_btn = QPushButton("Delete")
        self.del_btn.setObjectName("DangerButton")
        self.del_btn.clicked.connect(self.on_delete_note)
        header.addWidget(self.del_btn)
        notes_layout.addLayout(header)

        # Main Splitter (Left: list & search, Right: editor)
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(4)

        # Left Panel
        left_panel = QFrame()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search notes or tags...")
        self.search_input.textChanged.connect(self.filter_notes)
        left_layout.addWidget(self.search_input)

        self.notes_list = QListWidget()
        self.notes_list.currentRowChanged.connect(self.on_note_selected)
        left_layout.addWidget(self.notes_list)
        splitter.addWidget(left_panel)

        # Right Panel (Editor)
        right_panel = QFrame()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(8, 0, 0, 0)
        right_layout.setSpacing(10)

        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Note Title...")
        self.title_input.setStyleSheet("font-size: 15px; font-weight: bold; padding: 6px; color: #EAF4FF; background-color: #0A0E19; border: 1px solid rgba(255, 255, 255, 0.15); border-radius: 6px;")
        right_layout.addWidget(self.title_input)

        self.tags_input = QLineEdit()
        self.tags_input.setPlaceholderText("Tags (comma separated e.g. system, ideas, ai)...")
        right_layout.addWidget(self.tags_input)

        self.content_edit = QTextEdit()
        self.content_edit.setPlaceholderText("Enter note content or directives...")
        self.content_edit.textChanged.connect(self.update_stats)
        right_layout.addWidget(self.content_edit)

        # Bottom Action Bar
        bottom_bar = QHBoxLayout()
        self.stats_lbl = QLabel("Words: 0 | Characters: 0")
        self.stats_lbl.setObjectName("MutedLabel")
        bottom_bar.addWidget(self.stats_lbl)
        bottom_bar.addStretch()

        self.ai_polish_btn = QPushButton("✨ AI Polish & Organize")
        self.ai_polish_btn.setToolTip("Use local Ollama model to format and summarize this note")
        self.ai_polish_btn.clicked.connect(self.on_ai_polish)
        bottom_bar.addWidget(self.ai_polish_btn)

        self.save_btn = QPushButton("Save Changes")
        self.save_btn.clicked.connect(self.save_current_note)
        bottom_bar.addWidget(self.save_btn)

        right_layout.addLayout(bottom_bar)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        notes_layout.addWidget(splitter)

        self.tabs.addTab(notes_widget, "📝 Notes & Knowledge")

        # ================= TAB 2: REMINDERS & SCHEDULER =================
        reminders_widget = QWidget()
        rem_layout = QVBoxLayout(reminders_widget)
        rem_layout.setContentsMargins(12, 12, 12, 12)
        rem_layout.setSpacing(10)

        rem_head = QLabel("🔔 REMINDERS & SCHEDULED DIRECTIVES")
        rem_head.setObjectName("HeaderTitle")
        rem_layout.addWidget(rem_head)

        # Add Reminder Form
        form_frame = QFrame()
        form_frame.setObjectName("AccentCard")
        form_layout = QHBoxLayout(form_frame)
        form_layout.setContentsMargins(10, 10, 10, 10)
        form_layout.setSpacing(8)

        self.rem_title_input = QLineEdit()
        self.rem_title_input.setPlaceholderText("Reminder description (e.g. Call client, run backup)...")
        form_layout.addWidget(self.rem_title_input, stretch=2)

        self.rem_due_input = QLineEdit()
        default_due = (datetime.now() + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M")
        self.rem_due_input.setText(default_due)
        self.rem_due_input.setPlaceholderText("YYYY-MM-DD HH:MM")
        self.rem_due_input.setFixedWidth(135)
        form_layout.addWidget(self.rem_due_input)

        self.rem_prio_combo = QComboBox()
        self.rem_prio_combo.addItems(["NORMAL", "HIGH", "URGENT"])
        self.rem_prio_combo.setFixedWidth(90)
        form_layout.addWidget(self.rem_prio_combo)

        self.add_rem_btn = QPushButton("+ Add Reminder")
        self.add_rem_btn.setObjectName("PrimaryButton")
        self.add_rem_btn.clicked.connect(self.on_add_reminder)
        form_layout.addWidget(self.add_rem_btn)

        rem_layout.addWidget(form_frame)

        # Filter row
        filter_row = QHBoxLayout()
        self.show_completed_cb = QCheckBox("Show completed reminders")
        self.show_completed_cb.stateChanged.connect(lambda: self.load_reminders_list())
        filter_row.addWidget(self.show_completed_cb)
        filter_row.addStretch()
        rem_layout.addLayout(filter_row)

        # Reminders List
        self.reminders_list = QListWidget()
        self.reminders_list.setStyleSheet("""
            QListWidget {
                background: #090e1a;
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 6px;
                color: #e2e8f0;
                padding: 6px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid rgba(255,255,255,0.04);
                border-radius: 4px;
            }
            QListWidget::item:hover {
                background: #131c31;
                color: #00f0ff;
            }
        """)
        rem_layout.addWidget(self.reminders_list)

        # Reminders action row
        rem_act_row = QHBoxLayout()
        self.complete_rem_btn = QPushButton("✓ Mark Completed")
        self.complete_rem_btn.clicked.connect(self.on_complete_reminder)
        rem_act_row.addWidget(self.complete_rem_btn)

        self.delete_rem_btn = QPushButton("🗑 Delete Reminder")
        self.delete_rem_btn.setObjectName("DangerButton")
        self.delete_rem_btn.clicked.connect(self.on_delete_reminder)
        rem_act_row.addWidget(self.delete_rem_btn)
        rem_act_row.addStretch()

        rem_layout.addLayout(rem_act_row)
        self.tabs.addTab(reminders_widget, "🔔 Reminders & Directives")

        main_layout.addWidget(self.tabs)

    # ================= REMINDER HANDLERS =================

    def load_reminders_list(self):
        self.reminders_list.clear()
        include_done = self.show_completed_cb.isChecked()
        rems = get_reminders(include_completed=include_done)
        for r in rems:
            prio = r.get("priority", "NORMAL")
            prio_icon = "🔴" if prio == "URGENT" else ("🟡" if prio == "HIGH" else "⚪")
            status_text = " [DONE]" if r.get("is_completed") else ""
            item = QListWidgetItem(f"{prio_icon} {r['title']}  •  Due: {r['due_at']}{status_text}")
            item.setData(Qt.UserRole, r["id"])
            if r.get("is_completed"):
                item.setForeground(Qt.gray)
            self.reminders_list.addItem(item)

    def on_add_reminder(self):
        title = self.rem_title_input.text().strip()
        due_str = self.rem_due_input.text().strip()
        prio = self.rem_prio_combo.currentText()
        if not title:
            QMessageBox.information(self, "Invalid Title", "Please enter a reminder title.")
            return

        create_reminder(title, due_str, prio)
        self.rem_title_input.clear()
        self.load_reminders_list()

    def on_complete_reminder(self):
        curr = self.reminders_list.currentItem()
        if curr:
            rem_id = curr.data(Qt.UserRole)
            complete_reminder(rem_id)
            self.load_reminders_list()

    def on_delete_reminder(self):
        curr = self.reminders_list.currentItem()
        if curr:
            rem_id = curr.data(Qt.UserRole)
            delete_reminder(rem_id)
            self.load_reminders_list()

    def load_notes_list(self):
        self.all_notes = get_notes()
        if not self.all_notes:
            # Create a sample note
            sample_content = (
                "# NOVA OS Trial Sandbox\n\n"
                "NOVA OS is a futuristic AI desktop application running safely inside Windows.\n\n"
                "- Safe architecture: No registry changes, no bootloader tampering.\n"
                "- Local intelligence: Powered by Ollama.\n"
                "- SQLite local storage: Notes and transmissions preserved locally."
            )
            create_note("Welcome to NOVA OS", sample_content, "system, welcome")
            self.all_notes = get_notes()

        self.filter_notes(self.search_input.text())
        if self.notes_list.count() > 0:
            self.notes_list.setCurrentRow(0)

    def filter_notes(self, query: str):
        query = query.strip().lower()
        self.notes_list.clear()
        for n in self.all_notes:
            title = n["title"].lower()
            tags = (n.get("tags") or "").lower()
            if not query or query in title or query in tags:
                item = QListWidgetItem(f"📄 {n['title']}")
                item.setData(Qt.UserRole, n["id"])
                self.notes_list.addItem(item)

    def on_note_selected(self, row: int):
        if row < 0:
            return
        item = self.notes_list.item(row)
        if not item:
            return
        note_id = item.data(Qt.UserRole)
        note = next((n for n in self.all_notes if n["id"] == note_id), None)
        if note:
            self.active_note_id = note["id"]
            self.title_input.setText(note["title"])
            self.tags_input.setText(note.get("tags") or "")
            self.content_edit.setPlainText(note["content"])
            self.update_stats()

    def on_new_note(self):
        new_id = create_note("Untitled Note", "", "")
        self.load_notes_list()
        # Find and select the new note
        for i in range(self.notes_list.count()):
            if self.notes_list.item(i).data(Qt.UserRole) == new_id:
                self.notes_list.setCurrentRow(i)
                break
        self.title_input.setFocus()

    def save_current_note(self):
        if not self.active_note_id:
            return
        title = self.title_input.text().strip() or "Untitled Note"
        tags = self.tags_input.text().strip()
        content = self.content_edit.toPlainText()
        update_note(self.active_note_id, title, content, tags)
        
        # Reload
        self.all_notes = get_notes()
        curr_row = self.notes_list.currentRow()
        self.filter_notes(self.search_input.text())
        if curr_row < self.notes_list.count():
            self.notes_list.setCurrentRow(curr_row)

    def on_delete_note(self):
        if not self.active_note_id:
            return
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you wish to delete this note?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            delete_note(self.active_note_id)
            self.active_note_id = None
            self.load_notes_list()

    def update_stats(self):
        text = self.content_edit.toPlainText()
        words = len(text.split())
        chars = len(text)
        self.stats_lbl.setText(f"Words: {words} | Characters: {chars}")

    def on_ai_polish(self):
        content = self.content_edit.toPlainText().strip()
        if not content:
            QMessageBox.information(self, "Empty Note", "Note contains no text to polish.")
            return

        self.ai_polish_btn.setEnabled(False)
        self.ai_polish_btn.setText("Polishing with AI...")

        self.polish_worker = AIPolishWorker(self.ollama_client, content)
        self.polish_worker.finished.connect(self.on_polish_success)
        self.polish_worker.error.connect(self.on_polish_error)
        self.polish_worker.start()

    @Slot(str)
    def on_polish_success(self, polished_text: str):
        self.ai_polish_btn.setEnabled(True)
        self.ai_polish_btn.setText("✨ AI Polish & Organize")
        self.content_edit.setPlainText(polished_text)
        self.save_current_note()
        QMessageBox.information(self, "AI Polish Complete", "Note has been refined and formatted.")

    @Slot(str)
    def on_polish_error(self, err_msg: str):
        self.ai_polish_btn.setEnabled(True)
        self.ai_polish_btn.setText("✨ AI Polish & Organize")
        QMessageBox.warning(self, "AI Polish Failed", f"Error during AI synthesis:\n{err_msg}")
