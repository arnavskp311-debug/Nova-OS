"""
NOVA OS File Explorer & Safe Sandbox Viewer.
Allows safe inspection of project and data directories, code viewing, and logs exploration.
"""

from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTreeView, QFileSystemModel,
    QTextEdit, QSplitter, QFrame, QMessageBox,
    QFileDialog, QLineEdit
)
from PySide6.QtCore import Qt, QDir
from PySide6.QtGui import QFont
from nova.config import (
    BASE_DIR, DATA_DIR, LOGS_DIR, BACKUPS_DIR,
    WORKSPACE_DIR, WORKSPACE_REPORTS_DIR, WORKSPACE_NOTES_DIR,
    WORKSPACE_DOWNLOADS_DIR
)

class FileViewerWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # Header
        header = QHBoxLayout()
        title = QLabel("NOVA FILES // SANDBOX EXPLORER")
        title.setObjectName("HeaderTitle")
        header.addWidget(title)

        header.addStretch()

        # Action Buttons for User-Approved File Access
        self.open_custom_btn = QPushButton("📂 Open External File...")
        self.open_custom_btn.setToolTip("Select and authorize opening any external file into the viewer")
        self.open_custom_btn.clicked.connect(self.on_open_external_file)
        header.addWidget(self.open_custom_btn)

        self.logs_btn = QPushButton("📜 View App Logs")
        self.logs_btn.clicked.connect(self.on_view_logs)
        header.addWidget(self.logs_btn)

        self.export_btn = QPushButton("💾 Export Preview...")
        self.export_btn.clicked.connect(self.on_export_preview)
        header.addWidget(self.export_btn)

        layout.addLayout(header)

        # Quick Workspace Folder Toolbar
        folder_bar = QHBoxLayout()
        folder_bar.setSpacing(6)
        ws_folders = [
            ("🏠 Workspace", WORKSPACE_DIR),
            ("📊 Reports", WORKSPACE_REPORTS_DIR),
            ("📝 Notes", WORKSPACE_NOTES_DIR),
            ("📥 Downloads", WORKSPACE_DOWNLOADS_DIR),
            ("📜 Logs", LOGS_DIR),
            ("📦 Backups", BACKUPS_DIR),
        ]
        btn_style = """
            QPushButton {
                background: #0d1527;
                border: 1px solid rgba(0, 210, 230, 0.25);
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
                color: #e2e8f0;
            }
            QPushButton:hover {
                background: #142036;
                border-color: #00d2e6;
                color: #ffffff;
            }
        """
        for label, path in ws_folders:
            btn = QPushButton(label)
            btn.setStyleSheet(btn_style)
            btn.clicked.connect(lambda checked=False, p=path: self.navigate_to_folder(p))
            folder_bar.addWidget(btn)
        folder_bar.addStretch()
        layout.addLayout(folder_bar)

        # Breadcrumbs bar & file filter
        nav_bar = QHBoxLayout()
        self.breadcrumb_lbl = QLabel(f"Path: {WORKSPACE_DIR}")
        self.breadcrumb_lbl.setStyleSheet("color: #94a3b8; font-size: 11px; font-family: 'Segoe UI', monospace;")
        nav_bar.addWidget(self.breadcrumb_lbl, stretch=1)

        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Filter files by name...")
        self.filter_input.setFixedWidth(200)
        self.filter_input.setStyleSheet("""
            QLineEdit {
                background: #090e1a;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 4px;
                padding: 4px 8px;
                color: #f0f6fc;
                font-size: 11px;
            }
            QLineEdit:focus {
                border-color: #00d2e6;
            }
        """)
        self.filter_input.textChanged.connect(self.on_filter_changed)
        nav_bar.addWidget(self.filter_input)
        layout.addLayout(nav_bar)

        # Splitter (Left: Tree, Right: Preview)
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(4)

        # Left Panel (File Tree)
        self.model = QFileSystemModel()
        self.model.setRootPath(str(BASE_DIR))
        self.model.setReadOnly(True)

        self.tree = QTreeView()
        self.tree.setModel(self.model)
        self.tree.setRootIndex(self.model.index(str(BASE_DIR)))
        self.tree.setAnimated(True)
        self.tree.setIndentation(18)
        self.tree.setSortingEnabled(True)
        self.tree.hideColumn(2) # Hide Type column
        self.tree.setColumnWidth(0, 220)
        self.tree.clicked.connect(self.on_file_clicked)
        splitter.addWidget(self.tree)

        # Right Panel (File Viewer)
        right_panel = QFrame()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(8, 0, 0, 0)
        right_layout.setSpacing(6)

        self.file_info_lbl = QLabel("Select a file to inspect content...")
        self.file_info_lbl.setObjectName("AccentLabel")
        right_layout.addWidget(self.file_info_lbl)

        self.preview_edit = QTextEdit()
        self.preview_edit.setReadOnly(True)
        self.preview_edit.setFont(QFont("Consolas", 10))
        right_layout.addWidget(self.preview_edit)

        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter)

    def load_file_content(self, p: Path):
        """Safely loads file content with size limits and robust decoding."""
        if not p.exists():
            self.file_info_lbl.setText(f"File Not Found: {p.name}")
            self.preview_edit.setPlainText("[The requested file does not exist or was moved.]")
            return

        size = p.stat().st_size
        self.file_info_lbl.setText(f"Viewing: {p.name} ({round(size / 1024, 1)} KB)")

        # Enforce preview limit to prevent memory bloat
        if size > 350 * 1024:
            try:
                with open(p, "r", encoding="utf-8", errors="replace") as f:
                    chunk = f.read(100 * 1024)
                self.preview_edit.setPlainText(chunk + "\n\n[... Truncated for performance: File exceeds 350KB ...]")
            except Exception as e:
                self.preview_edit.setPlainText(f"[Unable to read preview: {e}]")
            return

        try:
            with open(p, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            self.preview_edit.setPlainText(content)
        except Exception as e:
            self.preview_edit.setPlainText(f"[Unable to read file: {e}]")

    def navigate_to_folder(self, p: Path):
        """Navigates file tree view directly to requested folder."""
        p.mkdir(parents=True, exist_ok=True)
        idx = self.model.index(str(p))
        if idx.isValid():
            self.tree.setRootIndex(idx)
            self.breadcrumb_lbl.setText(f"Path: {p}")
            self.tree.expand(idx)

    def on_filter_changed(self, text: str):
        query = text.strip()
        if query:
            self.model.setNameFilters([f"*{query}*"])
            self.model.setNameFilterDisables(False)
        else:
            self.model.setNameFilters([])
            self.model.setNameFilterDisables(True)

    def on_file_clicked(self, index):
        file_path_str = self.model.filePath(index)
        p = Path(file_path_str)
        self.breadcrumb_lbl.setText(f"Path: {p}")
        if p.is_file():
            self.load_file_content(p)
        else:
            self.file_info_lbl.setText(f"Folder: {p.name}")
            self.preview_edit.setPlainText("[Directory selected. Click an individual file above to inspect its contents.]")

    def on_open_external_file(self):
        """User-approved file selection via standard Windows file picker."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Authorized File to Inspect",
            str(BASE_DIR),
            "Text & Code Files (*.py *.txt *.log *.json *.md *.html *.css *.sql *.bat);;All Files (*.*)"
        )
        if file_path:
            p = Path(file_path)
            self.load_file_content(p)

    def on_view_logs(self):
        log_file = LOGS_DIR / "nova_os.log"
        if log_file.exists():
            self.load_file_content(log_file)
        else:
            self.file_info_lbl.setText("No log file found.")
            self.preview_edit.setPlainText("[Log file has not been created yet.]")

    def on_export_preview(self):
        text = self.preview_edit.toPlainText().strip()
        if not text:
            QMessageBox.information(self, "Export", "Preview pane is empty. Nothing to export.")
            return

        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Preview Content",
            str(BASE_DIR / "exported_preview.txt"),
            "Text Files (*.txt);;Markdown Files (*.md);;All Files (*.*)"
        )
        if save_path:
            try:
                with open(save_path, "w", encoding="utf-8") as f:
                    f.write(text)
                QMessageBox.information(self, "Export Successful", f"Saved to:\n{save_path}")
            except Exception as e:
                QMessageBox.warning(self, "Export Failed", f"Could not save file: {e}")

