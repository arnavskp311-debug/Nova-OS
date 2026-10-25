"""
NOVA OS Universal Search (HUD / Command Palette / Spotlight).
Central search overlay for applications, notes, bookmarks, deterministic calculations,
and quick system directives. Triggered with Ctrl+Space or taskbar search.
"""

from typing import List, Dict, Any, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QFrame,
    QApplication, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, Signal, QPoint
from PySide6.QtGui import QFont, QColor

from nova.deterministic_actions import evaluate_deterministic_query
from nova.database import (
    get_notes, create_note, get_browser_bookmarks,
    get_browser_history, create_reminder
)

class UniversalSearchDialog(QFrame):
    app_launch_requested = Signal(str, dict)  # app_id, params
    notification_requested = Signal(str, str, str) # title, message, level

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("UniversalSearchHUD")
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self.setFixedSize(560, 460)

        self.setup_ui()

    def setup_ui(self):
        self.setStyleSheet("""
            QFrame#UniversalSearchHUD {
                background-color: rgba(9, 14, 26, 0.98);
                border: 1px solid #00f0ff;
                border-radius: 10px;
            }
        """)

        # Add drop shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(25)
        shadow.setColor(QColor(0, 240, 255, 60))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        # Search Input Row
        search_row = QHBoxLayout()
        search_icon = QLabel("🔍")
        search_icon.setStyleSheet("font-size: 18px;")
        search_row.addWidget(search_icon)

        self.input_edit = QLineEdit()
        self.input_edit.setFont(QFont("Segoe UI", 13))
        self.input_edit.setPlaceholderText("Search apps, notes, bookmarks, math (e.g. 24*5), or directives (note:, remind:)...")
        self.input_edit.setStyleSheet("""
            QLineEdit {
                background: #0d1527;
                border: 1px solid rgba(0, 240, 255, 0.3);
                border-radius: 6px;
                color: #ffffff;
                padding: 8px 12px;
            }
            QLineEdit:focus {
                border-color: #00f0ff;
            }
        """)
        self.input_edit.textChanged.connect(self.on_query_changed)
        self.input_edit.returnPressed.connect(self.on_item_activated)
        search_row.addWidget(self.input_edit)
        layout.addLayout(search_row)

        # Results List
        self.results_list = QListWidget()
        self.results_list.setStyleSheet("""
            QListWidget {
                background: #060a14;
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 6px;
                color: #cbd5e1;
                padding: 6px;
            }
            QListWidget::item {
                padding: 8px;
                border-radius: 4px;
                margin-bottom: 2px;
            }
            QListWidget::item:hover {
                background: #111a30;
                color: #00f0ff;
            }
            QListWidget::item:selected {
                background: #182645;
                color: #00f0ff;
                border-left: 3px solid #00f0ff;
            }
        """)
        self.results_list.itemDoubleClicked.connect(self.on_item_activated)
        layout.addWidget(self.results_list)

        # Footer Hint
        hint_lbl = QLabel("Enter to execute / open  •  ↑/↓ to navigate  •  Esc to dismiss")
        hint_lbl.setStyleSheet("color: #64748b; font-size: 11px; text-align: center;")
        layout.addWidget(hint_lbl)

    def show_centered(self, parent_window: QWidget):
        """Displays Universal Search centered within parent window."""
        self.input_edit.clear()
        self.populate_default_apps()
        p_geo = parent_window.geometry()
        x = p_geo.x() + (p_geo.width() - self.width()) // 2
        y = p_geo.y() + 80
        self.move(x, y)
        self.show()
        self.raise_()
        self.input_edit.setFocus()

    def populate_default_apps(self):
        self.results_list.clear()
        commands = [
            ("browser", "🌐 Open NOVA Browser", "Alt+B", "Fast, private browser with AI intelligence"),
            ("files", "📁 Open File Manager", "Alt+F", "Safe sandbox files and storage explorer"),
            ("workspace", "🗂 Switch Workspace", "Alt+W", "Study, Coding, Research, Personal profiles"),
            ("settings", "⚙ Open Settings", "Alt+S", "Themes, AI endpoints, performance & security"),
            ("docsearch", "🔍 Search Documents", "Alt+D", "AI document search across local projects & notes"),
            ("calculate", "🧮 Calculate", "Alt+C", "Fast math expressions, unit conversions & time"),
            ("dashboard", "📊 Performance Center", "Ctrl+1", "Real CPU, RAM, disk & network diagnostics"),
            ("chat", "🤖 NOVA AI Assistant", "Ctrl+2", "Local offline LLM powered by Ollama"),
            ("automation", "⚡ Automation Studio", "", "Create and execute safe custom workflows"),
            ("calendar", "📅 Calendar & Reminders", "", "Agendas, daily schedule & countdown timers"),
            ("memory", "🧠 AI Memory Manager", "", "View and control user-approved AI memories"),
            ("privacy", "🛡️ Privacy Dashboard", "", "History, permissions, microphone & retention controls"),
            ("backup", "📦 Backup & Restore", "", "Snapshot settings, workspaces, notes & browser data"),
            ("clipboard", "📋 Clipboard History", "Ctrl+Shift+V", "Browse and restore recent clipboard snippets"),
        ]
        for app_id, title, shortcut, desc in commands:
            sc_badge = f"[{shortcut}]" if shortcut else ""
            item = QListWidgetItem(f"{title:<34} {sc_badge:>10}   •   {desc}")
            item.setData(Qt.UserRole, {"type": "app", "id": app_id})
            self.results_list.addItem(item)

        if self.results_list.count() > 0:
            self.results_list.setCurrentRow(0)

    def on_query_changed(self, text: str):
        query = text.strip()
        if not query:
            self.populate_default_apps()
            return

        self.results_list.clear()
        q_lower = query.lower()

        # 1. Check for quick directives
        if q_lower.startswith("note:"):
            content = query[5:].strip()
            item = QListWidgetItem(f"📝 Quick Note: \"{content}\" (Press Enter to Save)")
            item.setData(Qt.UserRole, {"type": "directive", "action": "note", "content": content})
            self.results_list.addItem(item)

        elif q_lower.startswith("remind:"):
            content = query[7:].strip()
            item = QListWidgetItem(f"🔔 Quick Reminder: \"{content}\" (Press Enter to Set)")
            item.setData(Qt.UserRole, {"type": "directive", "action": "remind", "content": content})
            self.results_list.addItem(item)

        elif q_lower.startswith("web:"):
            url = query[4:].strip()
            item = QListWidgetItem(f"🌐 Open in Browser: {url}")
            item.setData(Qt.UserRole, {"type": "directive", "action": "web", "url": url})
            self.results_list.addItem(item)

        # 2. Check deterministic actions (math, date, time, units)
        det_result = evaluate_deterministic_query(query)
        if det_result:
            item = QListWidgetItem(f"{det_result['icon']} {det_result['title']}: {det_result['result']}")
            item.setData(Qt.UserRole, {"type": "deterministic", "data": det_result})
            self.results_list.addItem(item)

        # 3. Search Applications
        app_list = [
            ("browser", "🌐 NOVA Cyber Browser", "browser web internet chrome"),
            ("dashboard", "📊 System Telemetry Dashboard", "cpu ram performance monitor hardware"),
            ("chat", "🤖 NOVA AI Assistant", "ai ollama chat intelligence"),
            ("notes", "📝 NovaPad Knowledge", "notes scratchpad vault markdown"),
            ("terminal", "💻 Cyber Safe Terminal", "terminal cmd shell powershell"),
            ("files", "📁 Sandbox File Explorer", "files storage logs backup disk"),
            ("settings", "⚙ Control Center", "settings preferences themes accent backup"),
            ("clipboard", "📋 Clipboard History", "clipboard copy paste snippets"),
            ("reminders", "🔔 Reminders & Scheduler", "reminders alerts schedule"),
        ]
        for app_id, title, keywords in app_list:
            if q_lower in title.lower() or any(q_lower in k for k in keywords.split()):
                item = QListWidgetItem(f"App: {title}")
                item.setData(Qt.UserRole, {"type": "app", "id": app_id})
                self.results_list.addItem(item)

        # 4. Search Notes
        try:
            notes = get_notes()
            for n in notes:
                if q_lower in n["title"].lower() or q_lower in n["content"].lower():
                    item = QListWidgetItem(f"📝 Note: {n['title']}")
                    item.setData(Qt.UserRole, {"type": "app", "id": "notes", "note_id": n["id"]})
                    self.results_list.addItem(item)
        except Exception:
            pass

        # 5. Search Browser Bookmarks & History
        try:
            bmarks = get_browser_bookmarks(query)
            for b in bmarks[:4]:
                item = QListWidgetItem(f"⭐ Bookmark: {b['title']} ({b['url']})")
                item.setData(Qt.UserRole, {"type": "web", "url": b["url"]})
                self.results_list.addItem(item)

            history = get_browser_history(query, limit=3)
            for h in history:
                item = QListWidgetItem(f"🕒 History: {h['title']} ({h['url']})")
                item.setData(Qt.UserRole, {"type": "web", "url": h["url"]})
                self.results_list.addItem(item)
        except Exception:
            pass

        if self.results_list.count() > 0:
            self.results_list.setCurrentRow(0)

    def on_item_activated(self):
        curr = self.results_list.currentItem()
        if not curr:
            return

        data = curr.data(Qt.UserRole)
        if not data:
            return

        self.hide()
        data_type = data.get("type")

        if data_type == "app":
            if data["id"] == "calculate":
                self.show()
                self.input_edit.setText("25 * 40")
                self.input_edit.selectAll()
                return
            self.app_launch_requested.emit(data["id"], data)

        elif data_type == "web":
            self.app_launch_requested.emit("browser", {"url": data["url"]})

        elif data_type == "directive":
            action = data.get("action")
            if action == "note":
                content = data.get("content", "")
                title = (content[:25] + "..") if len(content) > 25 else content
                create_note(title or "Quick Note", content, "quick")
                self.notification_requested.emit("NOTE SAVED", f"Created note: '{title}'", "success")
                self.app_launch_requested.emit("notes", {})
            elif action == "remind":
                content = data.get("content", "")
                from datetime import datetime, timedelta
                due_time = (datetime.now() + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M")
                create_reminder(content or "Reminder", due_time, "NORMAL")
                self.notification_requested.emit("REMINDER CREATED", f"Set for 1 hour from now: '{content}'", "reminder")
            elif action == "web":
                self.app_launch_requested.emit("browser", {"url": data.get("url")})

        elif data_type == "deterministic":
            res_str = data["data"]["result"]
            # Copy to clipboard and notify
            clip = QApplication.clipboard()
            if clip:
                clip.setText(res_str)
            self.notification_requested.emit("CALCULATION READY", f"Copied to clipboard:\n{res_str}", "info")
