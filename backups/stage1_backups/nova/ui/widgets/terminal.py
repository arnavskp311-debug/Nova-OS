"""
NOVA OS Cyber Terminal & Safe Shell.
Interactive command-line environment with security classification,
simulated controls, and approval gating for host protection.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QPlainTextEdit, QLineEdit, QFrame
)
from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtGui import QFont, QTextCursor, QColor
from nova.safety import analyze_command, execute_command_safely, RiskLevel
from nova.ui.widgets.approval_dialog import CommandApprovalDialog

class CommandWorker(QThread):
    finished = Signal(bool, str)

    def __init__(self, command: str, approved: bool):
        super().__init__()
        self.command = command
        self.approved = approved

    def run(self):
        success, output = execute_command_safely(self.command, approved_by_user=self.approved)
        self.finished.emit(success, output)

class TerminalWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.history = []
        self.history_index = -1
        self.active_worker = None

        self.setup_ui()
        self.print_banner()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # Top Bar
        top_bar = QHBoxLayout()
        title = QLabel("NOVA SECURE TERMINAL // SANDBOX SHELL")
        title.setObjectName("HeaderTitle")
        top_bar.addWidget(title)

        top_bar.addStretch()

        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.clear_console)
        top_bar.addWidget(clear_btn)

        layout.addLayout(top_bar)

        # Output Console
        self.console = QPlainTextEdit()
        self.console.setReadOnly(True)
        self.console.setFont(QFont("Consolas", 11))
        self.console.setStyleSheet("""
            QPlainTextEdit {
                background-color: #050811;
                color: #00ff88;
                border: 1px solid rgba(0, 255, 136, 0.2);
                border-radius: 6px;
                padding: 10px;
            }
        """)
        layout.addWidget(self.console)

        # Quick Commands Bar
        quick_layout = QHBoxLayout()
        quick_layout.setSpacing(6)
        quick_cmds = [
            ("Safe: whoami", "whoami"),
            ("Safe: dir", "dir"),
            ("Safe: ipconfig", "ipconfig"),
            ("Sim: reboot", "reboot"),
            ("Sim: shutdown", "shutdown"),
            ("Test: blocked", "format C:"),
        ]
        for label, cmd in quick_cmds:
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
            btn.clicked.connect(lambda checked, c=cmd: self.execute_input(c))
            quick_layout.addWidget(btn)
        quick_layout.addStretch()
        layout.addLayout(quick_layout)

        # Input Prompt Bar
        input_bar = QHBoxLayout()
        input_bar.setSpacing(8)

        prompt_lbl = QLabel("nova@sandbox:~$")
        prompt_lbl.setStyleSheet("color: #00f0ff; font-weight: bold; font-family: Consolas; font-size: 12px;")
        input_bar.addWidget(prompt_lbl)

        self.cmd_input = QLineEdit()
        self.cmd_input.setFont(QFont("Consolas", 11))
        self.cmd_input.setPlaceholderText("Enter safe command or simulation directive (e.g. dir, whoami, reboot)...")
        self.cmd_input.returnPressed.connect(self.on_enter_pressed)
        input_bar.addWidget(self.cmd_input)

        self.run_btn = QPushButton("Execute")
        self.run_btn.setObjectName("PrimaryButton")
        self.run_btn.clicked.connect(self.on_enter_pressed)
        input_bar.addWidget(self.run_btn)

        layout.addLayout(input_bar)

    def print_banner(self):
        banner = (
            "====================================================================\n"
            " NOVA OS VIRTUAL RUNTIME SHELL v1.0.0-trial\n"
            " Safe sandbox environment running unprivileged inside Windows.\n"
            " Destructive commands are blocked. Host system files are protected.\n"
            " Type 'help' for built-in capabilities or try quick buttons above.\n"
            "====================================================================\n"
        )
        self.console.appendPlainText(banner)

    def clear_console(self):
        self.console.clear()
        self.print_banner()

    def on_enter_pressed(self):
        cmd = self.cmd_input.text().strip()
        if not cmd:
            return
        self.cmd_input.clear()
        self.execute_input(cmd)

    def execute_input(self, cmd: str):
        # Save to history
        self.history.append(cmd)
        self.history_index = len(self.history)

        self.console.appendPlainText(f"\nnova@sandbox:~$ {cmd}")

        # Built-in help
        if cmd.lower() == "help":
            help_text = (
                "\nNOVA OS Shell Help:\n"
                "  - Safe commands (read-only): dir, whoami, ipconfig, date /t, hostname, python --version\n"
                "  - Simulated OS commands: reboot, shutdown, poweroff, kernel-upgrade, clear-cache\n"
                "  - Blocked commands: format, bcdedit, diskpart, del C:\\windows, registry edits\n"
                "  - Other commands: Require user confirmation via security approval dialog."
            )
            self.console.appendPlainText(help_text)
            self._scroll_bottom()
            return

        if cmd.lower() in ["cls", "clear"]:
            self.clear_console()
            return

        # Analyze command
        analysis = analyze_command(cmd)
        risk = analysis["risk"]

        if risk == RiskLevel.BLOCKED:
            self.console.appendPlainText(f"\n[SECURITY ALERT: COMMAND BLOCKED]\n{analysis['reason']}")
            self._scroll_bottom()
            return

        if analysis["is_simulated"]:
            # Run simulated command
            sim_output = analysis["simulated_output"]
            self.console.appendPlainText(f"\n{sim_output}")
            self._scroll_bottom()
            return

        # If requires approval, trigger approval dialog
        approved = False
        final_cmd = cmd
        if analysis["requires_approval"]:
            dialog = CommandApprovalDialog(cmd, analysis, self)
            if not dialog.exec():
                self.console.appendPlainText("\n[EXECUTION ABORTED BY USER]")
                self._scroll_bottom()
                return
            approved = dialog.approved
            final_cmd = dialog.edited_command

        # Execute
        self.run_btn.setEnabled(False)
        self.cmd_input.setEnabled(False)
        self.console.appendPlainText("\n[Executing in unprivileged sandbox...]")

        self.active_worker = CommandWorker(final_cmd, approved=approved)
        self.active_worker.finished.connect(self.on_command_finished)
        self.active_worker.start()

    @Slot(bool, str)
    def on_command_finished(self, success: bool, output: str):
        self.run_btn.setEnabled(True)
        self.cmd_input.setEnabled(True)
        self.cmd_input.setFocus()

        status_tag = "[SUCCESS]" if success else "[EXIT ERROR]"
        self.console.appendPlainText(f"{status_tag}\n{output.strip()}")
        self._scroll_bottom()
        self.active_worker = None

    def _scroll_bottom(self):
        cursor = self.console.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.console.setTextCursor(cursor)
