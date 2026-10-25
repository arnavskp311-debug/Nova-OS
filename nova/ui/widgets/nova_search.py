"""
Independent NOVA Search Portal for NOVA OS (Feature 19).
Independent cyber search portal combining local files, browser bookmarks, notes, and web search.
Matching Panel 19 of the reference design.
"""

from urllib.parse import quote_plus
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QListWidget, QListWidgetItem,
    QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from nova.database import get_notes, get_browser_bookmarks
from nova.deterministic_actions import evaluate_deterministic_query


class NovaSearchWidget(QWidget):
    search_activated = Signal(str, dict)  # type, payload (e.g. "web", "file", "note")

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)
        layout.setAlignment(Qt.AlignTop)

        # Hero Banner (Matching Panel 19)
        hero = QVBoxLayout()
        hero.setAlignment(Qt.AlignCenter)
        hero.setSpacing(6)

        logo = QLabel("❖ NOVA")
        logo.setStyleSheet("font-size: 38px; font-weight: bold; color: #00f0ff; letter-spacing: 3px;")
        logo.setAlignment(Qt.AlignCenter)
        hero.addWidget(logo)

        tagline = QLabel("SEARCH THE WEB, YOUR FILES, AND MORE...")
        tagline.setStyleSheet("color: #7dd3fc; font-size: 12px; font-weight: 600; letter-spacing: 1.5px;")
        tagline.setAlignment(Qt.AlignCenter)
        hero.addWidget(tagline)
        layout.addLayout(hero)

        # Big Glowing Search Omnibox
        search_box = QFrame()
        search_box.setStyleSheet("""
            QFrame {
                background: #090e1a;
                border: 2px solid #00f0ff;
                border-radius: 24px;
                padding: 4px 14px;
            }
        """)
        s_layout = QHBoxLayout(search_box)
        s_layout.setContentsMargins(4, 2, 4, 2)

        s_icon = QLabel("🔍")
        s_icon.setStyleSheet("font-size: 16px;")
        s_layout.addWidget(s_icon)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search documents, websites, notes, calculations...")
        self.search_input.setFont(QFont("Segoe UI", 12))
        self.search_input.setStyleSheet("""
            QLineEdit {
                background: transparent;
                border: none;
                color: #ffffff;
                padding: 6px;
            }
        """)
        self.search_input.textChanged.connect(self.on_search_query)
        self.search_input.returnPressed.connect(self.on_execute_search)
        s_layout.addWidget(self.search_input, stretch=1)

        go_btn = QPushButton("➔")
        go_btn.setFixedSize(32, 32)
        go_btn.setStyleSheet("""
            QPushButton {
                background: #0052cc;
                border: 1px solid #00f0ff;
                border-radius: 16px;
                color: #ffffff;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #00f0ff;
                color: #050811;
            }
        """)
        go_btn.clicked.connect(self.on_execute_search)
        s_layout.addWidget(go_btn)
        layout.addWidget(search_box)

        # Quick Portal Pills (Files, Bookmarks, Notes, Web matching Panel 19)
        pills_row = QHBoxLayout()
        pills_row.setAlignment(Qt.AlignCenter)
        pills_row.setSpacing(10)

        for icon, name, mode in [("📁", "Files", "files"), ("🔖", "Bookmarks", "bookmarks"), ("📝", "Notes", "notes"), ("🌐", "Web", "web")]:
            btn = QPushButton(f"{icon} {name}")
            btn.setStyleSheet("""
                QPushButton {
                    background: #111d33;
                    border: 1px solid rgba(0, 240, 255, 0.25);
                    border-radius: 14px;
                    color: #cbd5e1;
                    padding: 6px 16px;
                    font-size: 11px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background: #192947;
                    border-color: #00f0ff;
                    color: #ffffff;
                }
            """)
            btn.clicked.connect(lambda checked, m=mode: self.set_search_filter(m))
            pills_row.addWidget(btn)
        layout.addLayout(pills_row)

        # Search Results List
        self.results_list = QListWidget()
        self.results_list.setStyleSheet("""
            QListWidget {
                background: #060a14;
                border: 1px solid rgba(0, 240, 255, 0.2);
                border-radius: 8px;
                color: #e2e8f0;
                padding: 6px;
            }
            QListWidget::item {
                background: #0b1222;
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 6px;
                padding: 8px 12px;
                margin-bottom: 4px;
            }
            QListWidget::item:hover {
                background: #131e36;
                border-color: #00f0ff;
            }
            QListWidget::item:selected {
                background: #162646;
                border-left: 3px solid #00f0ff;
            }
        """)
        self.results_list.itemDoubleClicked.connect(self.on_item_double_clicked)
        layout.addWidget(self.results_list, stretch=1)

    def set_search_filter(self, mode: str):
        if mode == "web":
            self.search_input.setText("https://duckduckgo.com")
        elif mode == "files":
            self.search_activated.emit("launch_app", {"app_id": "files"})
        elif mode == "notes":
            self.search_activated.emit("launch_app", {"app_id": "notes"})
        elif mode == "bookmarks":
            self.search_input.setText("bookmark:")
            self.search_input.setFocus()

    def on_search_query(self, text: str):
        query = text.strip()
        self.results_list.clear()
        if not query:
            return

        q_lower = query.lower()

        # 1. Deterministic math
        det = evaluate_deterministic_query(query)
        if det:
            item = QListWidgetItem(f"{det['icon']} {det['title']}: {det['result']}")
            item.setData(Qt.UserRole, {"type": "copy", "text": det["result"]})
            self.results_list.addItem(item)

        # 2. Web search directive
        web_item = QListWidgetItem(f"🌐 Search Web for: \"{query}\" (DuckDuckGo)")
        web_url = f"https://duckduckgo.com/?q={quote_plus(query)}"
        web_item.setData(Qt.UserRole, {"type": "web", "url": web_url})
        self.results_list.addItem(web_item)

        # 3. Bookmarks
        try:
            bms = get_browser_bookmarks(query)
            for b in bms[:4]:
                item = QListWidgetItem(f"🔖 Bookmark: {b['title']} ({b['url']})")
                item.setData(Qt.UserRole, {"type": "web", "url": b["url"]})
                self.results_list.addItem(item)
        except Exception:
            pass

        # 4. Notes
        try:
            notes = get_notes(query)
            for n in notes[:4]:
                item = QListWidgetItem(f"📝 Note: {n['title']} — {n['content'][:50]}..")
                item.setData(Qt.UserRole, {"type": "note", "id": n["id"]})
                self.results_list.addItem(item)
        except Exception:
            pass

        if self.results_list.count() > 0:
            self.results_list.setCurrentRow(0)

    def on_execute_search(self):
        curr = self.results_list.currentItem()
        if curr:
            self.on_item_double_clicked(curr)
        else:
            query = self.search_input.text().strip()
            if query:
                web_url = f"https://duckduckgo.com/?q={quote_plus(query)}"
                self.search_activated.emit("web", {"url": web_url})

    def on_item_double_clicked(self, item: QListWidgetItem):
        data = item.data(Qt.UserRole)
        if not data:
            return
        if data["type"] == "web":
            self.search_activated.emit("web", {"url": data["url"]})
        elif data["type"] == "note":
            self.search_activated.emit("launch_app", {"app_id": "notes"})
        elif data["type"] == "copy":
            from PySide6.QtWidgets import QApplication
            QApplication.clipboard().setText(data["text"])
