"""
AI File & Local Document Search Widget for NOVA OS (Features 9 & 18).
Fast, private local file indexing and semantic query search across project notes, documents, and code files.
Matching Panels 9 and 18 of the reference design.
"""

import os
from pathlib import Path
from typing import List, Dict, Any, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QListWidget, QListWidgetItem,
    QFrame, QMessageBox, QFileDialog
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from nova.config import BASE_DIR, DATA_DIR
from nova.database import get_notes


class DocumentSearchWidget(QWidget):
    file_open_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.active_category = "All"
        self.indexed_files: List[Dict[str, Any]] = []
        self.setup_ui()
        self.scan_local_documents()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        # Header (Matching Panel 9 & 18)
        head_box = QHBoxLayout()
        icon = QLabel("🔍")
        icon.setStyleSheet("font-size: 20px;")
        head_box.addWidget(icon)

        title = QLabel("AI FILE & DOCUMENT SEARCH // PRIVATE LOCAL INDEX")
        title.setStyleSheet("font-size: 14px; font-weight: bold; color: #00f0ff; letter-spacing: 1px;")
        head_box.addWidget(title)
        head_box.addStretch()

        rescan_btn = QPushButton("🔄 Rescan Index")
        rescan_btn.setStyleSheet("""
            QPushButton {
                background: #111d33;
                border: 1px solid #00f0ff;
                border-radius: 4px;
                color: #00f0ff;
                font-size: 11px;
                font-weight: 600;
                padding: 4px 10px;
            }
            QPushButton:hover {
                background: #00f0ff;
                color: #000000;
            }
        """)
        rescan_btn.clicked.connect(self.scan_local_documents)
        head_box.addWidget(rescan_btn)
        layout.addLayout(head_box)

        # Search Input Bar
        search_row = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Find documents, keywords, project plans, or notes (e.g. 'planning', 'system')...")
        self.search_edit.setStyleSheet("""
            QLineEdit {
                background: #0d1527;
                border: 1px solid rgba(0, 240, 255, 0.35);
                border-radius: 6px;
                color: #ffffff;
                font-size: 13px;
                padding: 8px 12px;
            }
            QLineEdit:focus {
                border-color: #00f0ff;
            }
        """)
        self.search_edit.textChanged.connect(self.filter_results)
        search_row.addWidget(self.search_edit)

        self.clear_btn = QPushButton("✕")
        self.clear_btn.setFixedSize(32, 32)
        self.clear_btn.setStyleSheet("background: #111827; border: 1px solid rgba(255,255,255,0.1); border-radius: 4px; color: #cbd5e1;")
        self.clear_btn.clicked.connect(lambda: self.search_edit.clear())
        search_row.addWidget(self.clear_btn)
        layout.addLayout(search_row)

        # Category Filter Pills (Exact pills from Panel 9 & 18: All, Documents, PDFs, Notes, Code)
        pill_row = QHBoxLayout()
        pill_row.setSpacing(6)
        self.pills = {}
        for cat in ["All", "Documents", "PDFs", "Notes", "Code"]:
            btn = QPushButton(cat)
            btn.setCheckable(True)
            btn.setChecked(cat == "All")
            btn.setStyleSheet("""
                QPushButton {
                    background: #111a2e;
                    border: 1px solid rgba(0, 240, 255, 0.2);
                    border-radius: 12px;
                    color: #94a3b8;
                    font-size: 11px;
                    font-weight: 600;
                    padding: 4px 14px;
                }
                QPushButton:checked {
                    background: #0052cc;
                    border-color: #00f0ff;
                    color: #ffffff;
                }
            """)
            btn.clicked.connect(lambda checked, c=cat: self.set_category_filter(c))
            pill_row.addWidget(btn)
            self.pills[cat] = btn

        pill_row.addStretch()
        layout.addLayout(pill_row)

        # Results List View (Matching Panel 9 item cards)
        self.results_list = QListWidget()
        self.results_list.setStyleSheet("""
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
        self.results_list.itemDoubleClicked.connect(self.on_item_double_clicked)
        layout.addWidget(self.results_list)

        # Footer Actions
        footer = QHBoxLayout()
        self.stats_lbl = QLabel("0 documents indexed")
        self.stats_lbl.setStyleSheet("color: #64748b; font-size: 11px;")
        footer.addWidget(self.stats_lbl)
        footer.addStretch()

        open_btn = QPushButton("Open Selected Document")
        open_btn.setStyleSheet("""
            QPushButton {
                background: #0052cc;
                border: 1px solid #00f0ff;
                border-radius: 4px;
                color: #ffffff;
                font-weight: bold;
                padding: 6px 16px;
            }
            QPushButton:hover {
                background: #00f0ff;
                color: #000000;
            }
        """)
        open_btn.clicked.connect(self.open_selected)
        footer.addWidget(open_btn)
        layout.addLayout(footer)

    def set_category_filter(self, cat: str):
        self.active_category = cat
        for c, btn in self.pills.items():
            btn.setChecked(c == cat)
        self.filter_results(self.search_edit.text())

    def scan_local_documents(self):
        """Scans local project directories, user documents, and database notes."""
        self.indexed_files.clear()

        # 1. Index database notes
        try:
            notes = get_notes()
            for n in notes:
                self.indexed_files.append({
                    "id": f"note_{n['id']}",
                    "title": n["title"],
                    "category": "Notes",
                    "snippet": n["content"][:120].replace("\n", " "),
                    "full_content": n["content"],
                    "path": f"NovaPad Note #{n['id']}",
                    "type": "note",
                    "icon": "📝"
                })
        except Exception:
            pass

        # 2. Index project docs & readme
        scan_exts = {
            ".md": ("Documents", "📄"),
            ".txt": ("Documents", "📄"),
            ".pdf": ("PDFs", "📕"),
            ".docx": ("Documents", "📘"),
            ".py": ("Code", "🐍"),
            ".json": ("Code", "⚙")
        }

        search_roots = [BASE_DIR, BASE_DIR / "data"]
        for root in search_roots:
            if not root.exists():
                continue
            for p in root.rglob("*"):
                if p.is_file() and p.suffix.lower() in scan_exts and not any(part.startswith(".") for part in p.parts):
                    cat, icon = scan_exts[p.suffix.lower()]
                    snippet = ""
                    try:
                        if p.suffix.lower() in (".md", ".txt", ".py", ".json") and p.stat().st_size < 100000:
                            with open(p, "r", encoding="utf-8", errors="ignore") as f:
                                snippet = f.read(150).replace("\n", " ").strip()
                    except Exception:
                        snippet = ""

                    self.indexed_files.append({
                        "id": str(p),
                        "title": p.name,
                        "category": cat,
                        "snippet": snippet or f"File size: {round(p.stat().st_size/1024, 1)} KB",
                        "full_content": snippet,
                        "path": str(p),
                        "type": "file",
                        "icon": icon
                    })

        self.stats_lbl.setText(f"{len(self.indexed_files)} items in private local index")
        self.filter_results(self.search_edit.text())

    def filter_results(self, text: str):
        query = text.strip().lower()
        self.results_list.clear()

        for doc in self.indexed_files:
            # Check category
            if self.active_category != "All" and doc["category"] != self.active_category:
                continue

            # Check query match in title, snippet, or path
            if query:
                in_title = query in doc["title"].lower()
                in_snippet = query in doc.get("full_content", "").lower()
                in_path = query in doc["path"].lower()
                if not (in_title or in_snippet or in_path):
                    continue

            icon = doc["icon"]
            title = doc["title"]
            snippet = doc["snippet"]
            path = doc["path"]

            item_text = f"{icon}  {title}   [{doc['category']}]\n   • {snippet}\n   Path: {path}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, doc)
            self.results_list.addItem(item)

        if self.results_list.count() > 0:
            self.results_list.setCurrentRow(0)

    def on_item_double_clicked(self, item: QListWidgetItem):
        self.open_selected()

    def open_selected(self):
        curr = self.results_list.currentItem()
        if not curr:
            return
        doc = curr.data(Qt.UserRole)
        if not doc:
            return

        if doc["type"] == "file":
            p = doc["path"]
            if os.path.exists(p):
                os.startfile(p)
            else:
                QMessageBox.warning(self, "File Not Found", f"Cannot open: {p}")
        elif doc["type"] == "note":
            self.file_open_requested.emit("notes")
