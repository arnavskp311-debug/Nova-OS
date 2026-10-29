"""
WINDOWS APPLICATION BRIDGE & PROCESS MANAGER WIDGET.
Enables full access to all installed Windows applications, instant app launching,
desktop pinning, and cybernetic process management.
"""

from typing import List, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTabWidget, QScrollArea, QFrame, QGridLayout,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox
)
from PySide6.QtCore import Qt, Signal, Slot, QTimer
from PySide6.QtGui import QFont, QColor

from nova.windows_apps import get_windows_app_manager, WindowsAppInfo
from nova.sound_fx import play_sound
from nova.memory_optimizer import get_memory_optimizer


class WindowsAppCard(QFrame):
    """Card representing an individual Windows application."""

    launch_requested = Signal(str)
    pin_requested = Signal(object)

    def __init__(self, app_info: WindowsAppInfo, parent=None):
        super().__init__(parent)
        self.app_info = app_info
        self.setup_ui()

    def setup_ui(self):
        self.setStyleSheet("""
            QFrame {
                background-color: #131924;
                border: 1px solid #21262d;
                border-radius: 6px;
                padding: 6px;
            }
            QFrame:hover {
                border: 1px solid #00e5ff;
                background-color: #162030;
            }
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(10)

        # Icon
        icon_lbl = QLabel(self.app_info.icon)
        icon_lbl.setFont(QFont("Segoe UI Emoji", 18))
        icon_lbl.setStyleSheet("border: none; background: transparent;")
        layout.addWidget(icon_lbl)

        # Name and Category
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)

        name_lbl = QLabel(self.app_info.name)
        name_lbl.setFont(QFont("Segoe UI", 10, QFont.Bold))
        name_lbl.setStyleSheet("color: #e6edf3; border: none; background: transparent;")
        info_layout.addWidget(name_lbl)

        meta_layout = QHBoxLayout()
        meta_layout.setSpacing(6)

        cat_lbl = QLabel(f"[{self.app_info.category.upper()}]")
        cat_lbl.setFont(QFont("Consolas", 8, QFont.Bold))
        cat_lbl.setStyleSheet("color: #58a6ff; border: none; background: transparent;")
        meta_layout.addWidget(cat_lbl)

        if self.app_info.is_system:
            sys_lbl = QLabel("SYSTEM TOOL")
            sys_lbl.setFont(QFont("Consolas", 8, QFont.Bold))
            sys_lbl.setStyleSheet("color: #ffb800; border: none; background: transparent;")
            meta_layout.addWidget(sys_lbl)

        meta_layout.addStretch()
        info_layout.addLayout(meta_layout)
        layout.addLayout(info_layout, stretch=1)

        # Actions
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(6)

        self.btn_pin = QPushButton("📌 Pin")
        self.btn_pin.setStyleSheet("""
            QPushButton {
                background-color: #21262d;
                color: #8b949e;
                border: 1px solid #30363d;
                border-radius: 4px;
                padding: 5px 10px;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #30363d;
                color: #58a6ff;
                border-color: #58a6ff;
            }
        """)
        self.btn_pin.clicked.connect(lambda: self.pin_requested.emit(self.app_info))
        btn_layout.addWidget(self.btn_pin)

        self.btn_launch = QPushButton("▶ Launch")
        self.btn_launch.setFont(QFont("Segoe UI", 9, QFont.Bold))
        self.btn_launch.setStyleSheet("""
            QPushButton {
                background-color: #238636;
                color: #ffffff;
                border-radius: 4px;
                padding: 5px 14px;
            }
            QPushButton:hover { background-color: #2ea043; }
        """)
        self.btn_launch.clicked.connect(lambda: self.launch_requested.emit(self.app_info.path))
        btn_layout.addWidget(self.btn_launch)

        layout.addLayout(btn_layout)


class WindowsAppHubWidget(QWidget):
    """Complete Windows App Center & Task Manager Widget."""

    desktop_updated = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.app_manager = get_windows_app_manager()
        self.all_apps: List[WindowsAppInfo] = []
        self.active_category = "ALL"

        self.setup_ui()
        self.load_apps()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)

        # Top Header
        header = QHBoxLayout()
        title_lbl = QLabel("WINDOWS APPLICATION BRIDGE // NATIVE ECOSYSTEM")
        title_lbl.setFont(QFont("Consolas", 12, QFont.Bold))
        title_lbl.setStyleSheet("color: #00e5ff; letter-spacing: 1px;")
        header.addWidget(title_lbl)

        header.addStretch()

        self.count_lbl = QLabel("Scanning Windows apps...")
        self.count_lbl.setStyleSheet("color: #8b949e; font-size: 11px;")
        header.addWidget(self.count_lbl)

        main_layout.addLayout(header)

        # Tab Widget
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #30363d;
                border-radius: 4px;
                background-color: #0d1117;
            }
            QTabBar::tab {
                background-color: #161b22;
                color: #8b949e;
                padding: 6px 14px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background-color: #1f6feb;
                color: #ffffff;
            }
        """)

        # ---------------------------------------------------------------------
        # TAB 1: App Ecosystem
        # ---------------------------------------------------------------------
        apps_tab = QWidget()
        apps_layout = QVBoxLayout(apps_tab)
        apps_layout.setContentsMargins(8, 8, 8, 8)
        apps_layout.setSpacing(8)

        # Filter and Search Bar
        search_box = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search installed Windows apps (e.g. Chrome, Word, Calculator, VS Code)...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: #161b22;
                color: #f0f6fc;
                border: 1px solid #30363d;
                border-radius: 4px;
                padding: 6px 10px;
                font-family: Consolas;
            }
            QLineEdit:focus { border: 1px solid #00e5ff; }
        """)
        self.search_input.textChanged.connect(self.filter_apps)
        search_box.addWidget(self.search_input, stretch=1)

        self.btn_refresh = QPushButton("🔄 Refresh")
        self.btn_refresh.setStyleSheet("""
            QPushButton {
                background-color: #21262d;
                color: #c9d1d9;
                border: 1px solid #30363d;
                border-radius: 4px;
                padding: 6px 12px;
            }
            QPushButton:hover { background-color: #30363d; }
        """)
        self.btn_refresh.clicked.connect(lambda: self.load_apps(force_refresh=True))
        search_box.addWidget(self.btn_refresh)
        apps_layout.addLayout(search_box)

        # Category Buttons
        cat_box = QHBoxLayout()
        cat_box.setSpacing(4)
        categories = ["ALL", "Browsers", "Productivity", "Development", "Media", "System", "Tools"]
        self.cat_buttons = {}

        for cat in categories:
            btn = QPushButton(cat)
            btn.setCheckable(True)
            if cat == "ALL":
                btn.setChecked(True)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #161b22;
                    color: #8b949e;
                    border: 1px solid #30363d;
                    border-radius: 3px;
                    padding: 3px 8px;
                    font-size: 10px;
                    font-weight: bold;
                }
                QPushButton:checked {
                    background-color: #1f6feb;
                    color: #ffffff;
                    border-color: #58a6ff;
                }
            """)
            btn.clicked.connect(lambda checked, c=cat: self.on_category_clicked(c))
            self.cat_buttons[cat] = btn
            cat_box.addWidget(btn)

        cat_box.addStretch()
        apps_layout.addLayout(cat_box)

        # Scroll Area for Cards
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(6)
        self.cards_layout.addStretch()

        scroll.setWidget(self.cards_container)
        apps_layout.addWidget(scroll)

        self.tabs.addTab(apps_tab, "🪟 Windows Applications")

        # ---------------------------------------------------------------------
        # TAB 2: Process Manager & Task Killer
        # ---------------------------------------------------------------------
        proc_tab = QWidget()
        proc_layout = QVBoxLayout(proc_tab)
        proc_layout.setContentsMargins(8, 8, 8, 8)
        proc_layout.setSpacing(8)

        # Process Tools Bar
        proc_bar = QHBoxLayout()
        self.proc_search = QLineEdit()
        self.proc_search.setPlaceholderText("Filter running processes...")
        self.proc_search.setStyleSheet("""
            QLineEdit {
                background-color: #161b22;
                color: #f0f6fc;
                border: 1px solid #30363d;
                border-radius: 4px;
                padding: 5px 8px;
            }
        """)
        self.proc_search.textChanged.connect(self.filter_processes)
        proc_bar.addWidget(self.proc_search, stretch=1)

        self.btn_flush_mem = QPushButton("⚡ Flush RAM")
        self.btn_flush_mem.setStyleSheet("""
            QPushButton {
                background-color: #8957e5;
                color: #ffffff;
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #a371f7; }
        """)
        self.btn_flush_mem.clicked.connect(self.on_flush_ram)
        proc_bar.addWidget(self.btn_flush_mem)

        self.btn_kill_proc = QPushButton("🛑 Terminate Selected")
        self.btn_kill_proc.setStyleSheet("""
            QPushButton {
                background-color: #da3633;
                color: #ffffff;
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #f85149; }
        """)
        self.btn_kill_proc.clicked.connect(self.on_terminate_process)
        proc_bar.addWidget(self.btn_kill_proc)

        self.btn_refresh_proc = QPushButton("🔄 Refresh")
        self.btn_refresh_proc.setStyleSheet("""
            QPushButton {
                background-color: #21262d;
                color: #c9d1d9;
                border: 1px solid #30363d;
                border-radius: 4px;
                padding: 6px 10px;
            }
            QPushButton:hover { background-color: #30363d; }
        """)
        self.btn_refresh_proc.clicked.connect(self.refresh_processes)
        proc_bar.addWidget(self.btn_refresh_proc)

        proc_layout.addLayout(proc_bar)

        # Process Table
        self.proc_table = QTableWidget(0, 4)
        self.proc_table.setHorizontalHeaderLabels(["PID", "Process Name", "Memory (MB)", "CPU (%)"])
        self.proc_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.proc_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.proc_table.setSelectionMode(QTableWidget.SingleSelection)
        self.proc_table.setStyleSheet("""
            QTableWidget {
                background-color: #090d13;
                color: #e6edf3;
                border: 1px solid #21262d;
                gridline-color: #1f242c;
            }
            QTableWidget::item:selected {
                background-color: #1f6feb;
                color: #ffffff;
            }
            QHeaderView::section {
                background-color: #161b22;
                color: #8b949e;
                padding: 4px;
                font-weight: bold;
                border: none;
            }
        """)
        proc_layout.addWidget(self.proc_table)

        self.tabs.addTab(proc_tab, "📊 Process Monitor")
        main_layout.addWidget(self.tabs)

        # Auto refresh processes every 4s if tab 2 is active
        self.proc_timer = QTimer(self)
        self.proc_timer.setInterval(4000)
        self.proc_timer.timeout.connect(self._on_proc_timer)
        self.tabs.currentChanged.connect(self._on_tab_changed)

    def load_apps(self, force_refresh: bool = False):
        self.all_apps = self.app_manager.discover_apps(force_refresh=force_refresh)
        self.count_lbl.setText(f"{len(self.all_apps)} Windows Applications Discovered")
        self.filter_apps()

    def on_category_clicked(self, category: str):
        self.active_category = category
        for cat, btn in self.cat_buttons.items():
            btn.setChecked(cat == category)
        self.filter_apps()

    def filter_apps(self):
        query = self.search_input.text().lower().strip()

        # Clear existing card widgets
        while self.cards_layout.count() > 1:
            child = self.cards_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        count = 0
        for app in self.all_apps:
            if self.active_category != "ALL" and app.category.upper() != self.active_category.upper():
                continue
            if query and query not in app.name.lower() and query not in app.alias:
                continue

            card = WindowsAppCard(app, parent=self.cards_container)
            card.launch_requested.connect(self.on_launch_app)
            card.pin_requested.connect(self.on_pin_app)
            self.cards_layout.insertWidget(count, card)
            count += 1

    def on_launch_app(self, path: str):
        play_sound("click")
        ok, msg = self.app_manager.launch_app(path)
        if ok:
            play_sound("blip")
        else:
            play_sound("alert")
            QMessageBox.critical(self, "Launch Error", msg)

    def on_pin_app(self, app_info: WindowsAppInfo):
        ok, msg = self.app_manager.pin_to_desktop(app_info)
        if ok:
            play_sound("success")
            QMessageBox.information(self, "Pinned", msg)
            self.desktop_updated.emit()
        else:
            play_sound("alert")
            QMessageBox.warning(self, "Pin Warning", msg)

    # -------------------------------------------------------------------------
    # Process Monitor Logic
    # -------------------------------------------------------------------------

    def _on_tab_changed(self, index: int):
        if index == 1:
            self.refresh_processes()
            self.proc_timer.start()
        else:
            self.proc_timer.stop()

    def _on_proc_timer(self):
        if self.tabs.currentIndex() == 1:
            self.refresh_processes()

    def refresh_processes(self):
        query = self.proc_search.text().lower().strip()
        processes = self.app_manager.list_active_processes(limit=60)

        filtered = [
            p for p in processes
            if not query or query in str(p["pid"]) or query in p["name"].lower()
        ]

        self.proc_table.setRowCount(len(filtered))
        for row, p in enumerate(filtered):
            pid_item = QTableWidgetItem(str(p["pid"]))
            pid_item.setTextAlignment(Qt.AlignCenter)
            name_item = QTableWidgetItem(p["name"])
            mem_item = QTableWidgetItem(f"{p['memory_mb']:.1f} MB")
            mem_item.setTextAlignment(Qt.AlignRight)
            cpu_item = QTableWidgetItem(f"{p['cpu']:.1f}%")
            cpu_item.setTextAlignment(Qt.AlignRight)

            self.proc_table.setItem(row, 0, pid_item)
            self.proc_table.setItem(row, 1, name_item)
            self.proc_table.setItem(row, 2, mem_item)
            self.proc_table.setItem(row, 3, cpu_item)

    def filter_processes(self):
        self.refresh_processes()

    def on_terminate_process(self):
        selected_rows = self.proc_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.information(self, "Select Process", "Please select a process row to terminate.")
            return

        row = selected_rows[0].row()
        pid_item = self.proc_table.item(row, 0)
        name_item = self.proc_table.item(row, 1)
        if not pid_item or not name_item:
            return

        pid = pid_item.text()
        name = name_item.text()

        confirm = QMessageBox.question(
            self,
            "Confirm Terminate",
            f"Are you sure you want to terminate '{name}' (PID: {pid})?",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            ok, msg = self.app_manager.terminate_process(pid)
            if ok:
                play_sound("success")
                self.refresh_processes()
            else:
                play_sound("alert")
                QMessageBox.warning(self, "Error", msg)

    def on_flush_ram(self):
        play_sound("click")
        opt = get_memory_optimizer()
        res = opt.flush_quantum_memory()
        play_sound("success")
        QMessageBox.information(self, "RAM Flushed", f"Quantum working set trimmed successfully:\n{res}")
        self.refresh_processes()

    def cleanup(self):
        self.proc_timer.stop()

    def closeEvent(self, event):
        self.cleanup()
        super().closeEvent(event)
