"""
NOVA Autonomous Internet Research Cockpit Widget.
Interactive mission control for planning, deploying, pausing, resuming,
and reviewing multi-source internet investigations and generated dossiers.
"""

from typing import Optional, Dict, Any, List
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QProgressBar, QSplitter, QListWidget,
    QListWidgetItem, QPlainTextEdit, QTextBrowser, QTabWidget,
    QFrame, QMessageBox
)
from PySide6.QtCore import Qt, Slot, Signal
from PySide6.QtGui import QFont, QColor

from nova.research.research_orchestrator import ResearchOrchestrator, ResearchState
from nova.workspace import get_research_workspace
from nova.database import get_all_research_sessions, get_research_sources, get_research_artifacts
from nova.sound_fx import play_sound


class ResearchCockpitWidget(QWidget):
    """
    Dedicated autonomous internet research cockpit with full pause/resume/abort
    controls, live source tracking, and report dossier viewing.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.workspace = get_research_workspace()
        self.active_orchestrator: Optional[ResearchOrchestrator] = None
        self.last_report_markdown = ""
        self.last_report_path = ""

        self.setup_ui()
        self.refresh_artifacts_list()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(10)

        # Header Title & Status Badge
        header = QHBoxLayout()
        title = QLabel("NOVA AUTONOMOUS RESEARCH // INTELLIGENCE COCKPIT")
        title.setObjectName("HeaderTitle")
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #00F0FF; font-family: 'Segoe UI', system-ui;")
        header.addWidget(title)
        header.addStretch()

        self.status_badge = QLabel("[STATUS: IDLE // STANDBY]")
        self.status_badge.setStyleSheet("color: #718096; font-weight: bold; font-family: Consolas; font-size: 11px;")
        header.addWidget(self.status_badge)
        main_layout.addLayout(header)

        # Objective & Control Bar
        control_bar = QHBoxLayout()
        control_bar.setSpacing(8)

        lbl = QLabel("Research Goal:")
        lbl.setStyleSheet("color: #EAF4FF; font-weight: bold; font-size: 12px;")
        control_bar.addWidget(lbl)

        self.goal_input = QLineEdit()
        self.goal_input.setFont(QFont("Segoe UI", 11))
        self.goal_input.setPlaceholderText("Enter research objective (e.g. 'Investigate WebAssembly sandboxing and security guarantees')...")
        self.goal_input.setStyleSheet("""
            QLineEdit {
                background-color: #0A0E19;
                color: #EAF4FF;
                border: 1px solid rgba(0, 240, 255, 0.3);
                border-radius: 6px;
                padding: 8px 12px;
            }
            QLineEdit:focus {
                border-color: #00F0FF;
            }
        """)
        self.goal_input.returnPressed.connect(self.deploy_research)
        control_bar.addWidget(self.goal_input, 1)

        # Depth Profile Selector
        depth_lbl = QLabel("Depth:")
        depth_lbl.setStyleSheet("color: #A9BCD4; font-size: 11px;")
        control_bar.addWidget(depth_lbl)

        self.depth_combo = QComboBox()
        self.depth_combo.addItems(["Balanced (4 Sources)", "Quick (2 Sources)", "Deep (6 Sources)"])
        self.depth_combo.setStyleSheet("""
            QComboBox {
                background: #0d1424;
                color: #00F0FF;
                border: 1px solid rgba(0, 240, 255, 0.3);
                border-radius: 6px;
                padding: 6px 10px;
                font-weight: bold;
                font-size: 11px;
            }
        """)
        control_bar.addWidget(self.depth_combo)

        # Action Buttons
        self.deploy_btn = QPushButton("Deploy Research 🚀")
        self.deploy_btn.setObjectName("PrimaryButton")
        self.deploy_btn.setStyleSheet("""
            QPushButton {
                background: #00F0FF;
                color: #050811;
                font-weight: bold;
                border-radius: 6px;
                padding: 8px 18px;
            }
            QPushButton:hover {
                background: #50f5ff;
            }
        """)
        self.deploy_btn.clicked.connect(self.deploy_research)
        control_bar.addWidget(self.deploy_btn)

        self.pause_btn = QPushButton("Pause ⏸️")
        self.pause_btn.setEnabled(False)
        self.pause_btn.setStyleSheet("""
            QPushButton {
                background: #1a233a;
                color: #ffaa00;
                border: 1px solid rgba(255, 170, 0, 0.4);
                border-radius: 6px;
                padding: 8px 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #233152;
            }
        """)
        self.pause_btn.clicked.connect(self.toggle_pause)
        control_bar.addWidget(self.pause_btn)

        self.abort_btn = QPushButton("Abort 🛑")
        self.abort_btn.setEnabled(False)
        self.abort_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 0, 85, 0.2);
                color: #ff3366;
                border: 1px solid rgba(255, 0, 85, 0.5);
                border-radius: 6px;
                padding: 8px 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(255, 0, 85, 0.4);
            }
        """)
        self.abort_btn.clicked.connect(self.abort_research)
        control_bar.addWidget(self.abort_btn)

        main_layout.addLayout(control_bar)

        # Quick Preset Chips
        preset_row = QHBoxLayout()
        preset_row.setSpacing(6)
        presets = [
            ("🔬 Quantum Computing Advances", "Latest breakthroughs in quantum computing and error mitigation"),
            ("🛡️ Zero Trust Security", "Zero Trust Architecture principles and real-world implementation challenges"),
            ("⚡ Python 3.13 JIT", "Python 3.13 JIT compiler architecture and benchmark performance"),
            ("🤖 Local Small Language Models", "State of lightweight small language models for low-RAM offline devices")
        ]
        for label, prompt in presets:
            btn = QPushButton(label)
            btn.setStyleSheet("""
                QPushButton {
                    background: #0d1424;
                    color: #798fa7;
                    border: 1px solid rgba(255,255,255,0.08);
                    border-radius: 4px;
                    padding: 3px 8px;
                    font-size: 11px;
                }
                QPushButton:hover {
                    border-color: #00f0ff;
                    color: #00f0ff;
                }
            """)
            btn.clicked.connect(lambda checked, p=prompt: self._set_prompt(p))
            preset_row.addWidget(btn)
        preset_row.addStretch()
        main_layout.addLayout(preset_row)

        # Progress Bar & Stage Label
        prog_row = QHBoxLayout()
        self.stage_label = QLabel("Ready for autonomous research mission.")
        self.stage_label.setStyleSheet("color: #A9BCD4; font-size: 11px; font-family: Consolas;")
        prog_row.addWidget(self.stage_label)
        prog_row.addStretch()
        main_layout.addLayout(prog_row)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #0A0E19;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 4px;
                text-align: center;
                color: #EAF4FF;
                height: 14px;
                font-size: 10px;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00F0FF, stop:1 #B026FF);
                border-radius: 3px;
            }
        """)
        main_layout.addWidget(self.progress_bar)

        # Main Splitter (Left: Sources & Workspace Files, Right: Console & Dossier)
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(4)

        # Left Panel (Tabbed: Discovered Sources & Workspace Dossiers)
        left_tabs = QTabWidget()
        left_tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid rgba(0, 240, 255, 0.2);
                border-radius: 6px;
                background: #0A0E19;
            }
            QTabBar::tab {
                background: #0d1424;
                color: #798fa7;
                padding: 6px 12px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background: #0A0E19;
                color: #00f0ff;
                font-weight: bold;
            }
        """)

        # Sources List
        self.sources_list = QListWidget()
        self.sources_list.setStyleSheet("""
            QListWidget {
                background-color: #0A0E19;
                border: none;
                color: #EAF4FF;
                padding: 6px;
            }
            QListWidget::item {
                padding: 6px;
                border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            }
        """)
        left_tabs.addTab(self.sources_list, "Discovered Sources (0)")

        # Workspace Reports List
        reports_widget = QWidget()
        rep_layout = QVBoxLayout(reports_widget)
        rep_layout.setContentsMargins(4, 4, 4, 4)
        rep_layout.setSpacing(4)

        self.artifacts_list = QListWidget()
        self.artifacts_list.setStyleSheet("""
            QListWidget {
                background-color: #0A0E19;
                border: none;
                color: #EAF4FF;
                padding: 4px;
            }
            QListWidget::item {
                padding: 6px;
                border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            }
            QListWidget::item:selected {
                background: rgba(0, 240, 255, 0.15);
                color: #00F0FF;
            }
        """)
        self.artifacts_list.itemClicked.connect(self.on_artifact_selected)
        rep_layout.addWidget(self.artifacts_list)

        refresh_rep_btn = QPushButton("Refresh Workspace Dossiers 🔄")
        refresh_rep_btn.setStyleSheet("background: #12192c; color: #798fa7; border-radius: 4px; padding: 4px;")
        refresh_rep_btn.clicked.connect(self.refresh_artifacts_list)
        rep_layout.addWidget(refresh_rep_btn)

        left_tabs.addTab(reports_widget, "Workspace Dossiers")
        splitter.addWidget(left_tabs)

        # Right Panel (Tabbed: Live Thought Stream & Final Report Viewer)
        right_tabs = QTabWidget()
        right_tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid rgba(0, 255, 136, 0.2);
                border-radius: 6px;
                background: #050811;
            }
            QTabBar::tab {
                background: #0d1424;
                color: #798fa7;
                padding: 6px 12px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background: #050811;
                color: #00ff88;
                font-weight: bold;
            }
        """)

        # Console Log
        self.console_log = QPlainTextEdit()
        self.console_log.setReadOnly(True)
        self.console_log.setFont(QFont("Consolas", 10))
        self.console_log.setStyleSheet("""
            QPlainTextEdit {
                background-color: #050811;
                color: #00ff88;
                border: none;
                padding: 8px;
            }
        """)
        right_tabs.addTab(self.console_log, "Real-time Thought Stream & Tool Logs")

        # Dossier Report Viewer
        self.report_viewer = QTextBrowser()
        self.report_viewer.setReadOnly(True)
        self.report_viewer.setOpenExternalLinks(True)
        self.report_viewer.setFont(QFont("Segoe UI", 10))
        self.report_viewer.setStyleSheet("""
            QTextBrowser {
                background-color: #070a14;
                color: #d1dced;
                border: none;
                padding: 12px;
            }
        """)
        self.report_viewer.setHtml("<p style='color:#718096;'>No research dossier generated yet. Deploy an autonomous research goal to begin.</p>")
        right_tabs.addTab(self.report_viewer, "Synthesized Research Dossier")

        self.right_tabs = right_tabs
        splitter.addWidget(right_tabs)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        main_layout.addWidget(splitter)

    def _set_prompt(self, p: str):
        self.goal_input.setText(p)
        self.goal_input.setFocus()

    def deploy_research(self):
        goal = self.goal_input.text().strip()
        if not goal:
            return

        depth_raw = self.depth_combo.currentText()
        depth = "balanced"
        if "Quick" in depth_raw:
            depth = "quick"
        elif "Deep" in depth_raw:
            depth = "deep"

        self.sources_list.clear()
        self.console_log.clear()
        self.progress_bar.setValue(0)
        self.status_badge.setText("[STATUS: INITIALIZING MISSION...]")
        self.status_badge.setStyleSheet("color: #00F0FF; font-weight: bold; font-family: Consolas;")

        self.deploy_btn.setEnabled(False)
        self.pause_btn.setEnabled(True)
        self.pause_btn.setText("Pause ⏸️")
        self.abort_btn.setEnabled(True)

        # Launch background worker
        self.active_orchestrator = ResearchOrchestrator(goal, depth=depth, parent=self)
        self.active_orchestrator.state_changed.connect(self.on_state_changed)
        self.active_orchestrator.step_progress.connect(self.on_step_progress)
        self.active_orchestrator.source_discovered.connect(self.on_source_discovered)
        self.active_orchestrator.source_fetched.connect(self.on_source_fetched)
        self.active_orchestrator.log_emitted.connect(self.on_log_emitted)
        self.active_orchestrator.report_generated.connect(self.on_report_generated)
        self.active_orchestrator.mission_completed.connect(self.on_mission_completed)
        self.active_orchestrator.mission_failed.connect(self.on_mission_failed)
        self.active_orchestrator.start()

    def toggle_pause(self):
        if not self.active_orchestrator:
            return

        if self.active_orchestrator.current_state == ResearchState.PAUSED:
            self.active_orchestrator.resume()
            self.pause_btn.setText("Pause ⏸️")
            self.status_badge.setText("[STATUS: RESUMING...]")
            self.status_badge.setStyleSheet("color: #00F0FF; font-weight: bold; font-family: Consolas;")
        else:
            self.active_orchestrator.pause()
            self.pause_btn.setText("Resume ▶️")
            self.status_badge.setText("[STATUS: PAUSED BY OPERATOR]")
            self.status_badge.setStyleSheet("color: #ffaa00; font-weight: bold; font-family: Consolas;")

    def abort_research(self):
        if self.active_orchestrator:
            self.active_orchestrator.abort()
            self.status_badge.setText("[STATUS: ABORTED]")
            self.status_badge.setStyleSheet("color: #ff3366; font-weight: bold; font-family: Consolas;")
            self.deploy_btn.setEnabled(True)
            self.pause_btn.setEnabled(False)
            self.abort_btn.setEnabled(False)

    @Slot(str)
    def on_state_changed(self, state_str: str):
        color = "#00F0FF"
        if state_str == "PAUSED":
            color = "#ffaa00"
        elif state_str in ("COMPLETED", "SYNTHESIZING"):
            color = "#00ff88"
        elif state_str in ("ABORTED", "FAILED"):
            color = "#ff3366"

        self.status_badge.setText(f"[STATUS: {state_str}]")
        self.status_badge.setStyleSheet(f"color: {color}; font-weight: bold; font-family: Consolas;")

    @Slot(int, int, str)
    def on_step_progress(self, current: int, total: int, desc: str):
        pct = int((current / max(1, total)) * 100)
        self.progress_bar.setValue(pct)
        self.stage_label.setText(f"Stage {current}/{total}: {desc}")

    @Slot(dict)
    def on_source_discovered(self, src: dict):
        item = QListWidgetItem(f"🌐 [{src.get('domain', 'web')}] {src.get('title', '')[:45]}")
        item.setToolTip(src.get("url", ""))
        item.setForeground(QColor("#798fa7"))
        self.sources_list.addItem(item)

    @Slot(dict)
    def on_source_fetched(self, doc: dict):
        # Update matching list item
        for i in range(self.sources_list.count()):
            item = self.sources_list.item(i)
            if doc.get("domain", "") in item.text():
                item.setText(f"✅ [{doc.get('domain')}] {doc.get('title')[:45]} ({doc.get('char_count')} chars)")
                item.setForeground(QColor("#00ff88"))
                break

    @Slot(str)
    def on_log_emitted(self, msg: str):
        self.console_log.appendPlainText(msg)

    @Slot(str, str)
    def on_report_generated(self, report_path: str, markdown_content: str):
        self.last_report_path = report_path
        self.last_report_markdown = markdown_content
        # Render markdown as HTML preview
        html = self._convert_markdown_to_html(markdown_content)
        self.report_viewer.setHtml(html)
        self.right_tabs.setCurrentIndex(1)  # Switch to report view tab

    @Slot(dict)
    def on_mission_completed(self, summary: dict):
        self.deploy_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.abort_btn.setEnabled(False)
        self.stage_label.setText(f"Completed! Dossier: {summary.get('report_filename')}")
        self.refresh_artifacts_list()

    @Slot(str)
    def on_mission_failed(self, err_msg: str):
        self.deploy_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.abort_btn.setEnabled(False)
        self.stage_label.setText(f"Mission failed: {err_msg}")
        QMessageBox.warning(self, "Research Failure", f"The autonomous research mission encountered an error:\n\n{err_msg}")

    def refresh_artifacts_list(self):
        self.artifacts_list.clear()
        files = self.workspace.list_files("reports")
        for f in reversed(files):
            item = QListWidgetItem(f"📄 {f['name']}\n   {f['modified_at']} • {f['size_bytes']:,} bytes")
            item.setData(Qt.UserRole, f["path"])
            self.artifacts_list.addItem(item)

    def on_artifact_selected(self, item: QListWidgetItem):
        file_path = item.data(Qt.UserRole)
        if file_path and Path(file_path).exists():
            try:
                content = self.workspace.read_file(file_path)
                html = self._convert_markdown_to_html(content)
                self.report_viewer.setHtml(html)
                self.right_tabs.setCurrentIndex(1)
            except Exception as e:
                self.report_viewer.setPlainText(f"Failed to read artifact: {e}")

    def _convert_markdown_to_html(self, md_text: str) -> str:
        """Converts Markdown text into cyber-styled HTML for previewing."""
        # Simple, fast pure Python markdown-to-HTML conversion
        lines = md_text.split("\n")
        html_lines = []
        in_table = False

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("# "):
                html_lines.append(f"<h1 style='color:#00f0ff; border-bottom: 1px solid rgba(0,240,255,0.3); padding-bottom:6px;'>{stripped[2:]}</h1>")
            elif stripped.startswith("## "):
                html_lines.append(f"<h2 style='color:#b026ff; margin-top:20px;'>{stripped[3:]}</h2>")
            elif stripped.startswith("### "):
                html_lines.append(f"<h3 style='color:#00ff88;'>{stripped[4:]}</h3>")
            elif stripped.startswith("- "):
                html_lines.append(f"<li style='margin-bottom:6px;'>{stripped[2:]}</li>")
            elif stripped.startswith("> "):
                html_lines.append(f"<blockquote style='border-left: 3px solid #00f0ff; padding-left:12px; color:#a9bcd4; margin:10px 0;'>{stripped[2:]}</blockquote>")
            elif stripped.startswith("|") and stripped.endswith("|"):
                if not in_table:
                    html_lines.append("<table border='1' cellpadding='6' cellspacing='0' style='border-color:rgba(255,255,255,0.1); width:100%; margin:12px 0;'>")
                    in_table = True
                cols = [c.strip() for c in stripped.strip("|").split("|")]
                if all(c.startswith(":") or c.startswith("-") for c in cols):
                    continue  # Separator row
                row_cells = "".join(f"<td style='padding:6px; border:1px solid rgba(255,255,255,0.1);'>{c}</td>" for c in cols)
                html_lines.append(f"<tr>{row_cells}</tr>")
            else:
                if in_table and not stripped.startswith("|"):
                    html_lines.append("</table>")
                    in_table = False
                if stripped:
                    html_lines.append(f"<p style='line-height:1.6; margin-bottom:10px;'>{stripped}</p>")

        if in_table:
            html_lines.append("</table>")

        body_content = "\n".join(html_lines)
        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{
            background: #070a14;
            color: #d1dced;
            font-family: 'Segoe UI', system-ui, sans-serif;
            font-size: 13px;
            padding: 10px;
        }}
        a {{ color: #00f0ff; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        code {{ background: rgba(0,240,255,0.1); color: #00f0ff; padding: 2px 4px; border-radius: 3px; font-family: Consolas; }}
    </style>
</head>
<body>
    {body_content}
</body>
</html>"""
