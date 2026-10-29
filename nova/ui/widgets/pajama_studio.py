"""
PAJAMA STUDIO // NATIVE SCRIPTING IDE & AI WORKBENCH FOR NOVA OS.
Full-featured IDE with syntax highlighting, line numbers, real-time telemetry,
AI prompt-to-code generation, one-click template loading, and non-blocking execution.
"""

import re
import time
from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QPlainTextEdit, QLineEdit, QComboBox, QSplitter, QFrame,
    QProgressBar, QMessageBox
)
from PySide6.QtCore import Qt, QThread, Signal, Slot, QRect, QSize
from PySide6.QtGui import (
    QFont, QTextCursor, QColor, QPainter, QTextFormat,
    QSyntaxHighlighter, QTextCharFormat
)

from nova.pajama.runtime import PajamaInterpreter
from nova.pajama.ai_assistant import PajamaAIAssistant, PAJAMA_PRESET_TEMPLATES
from nova.ollama_client import OllamaClient


# =============================================================================
# Syntax Highlighter for Pajama (.pj)
# =============================================================================

class PajamaSyntaxHighlighter(QSyntaxHighlighter):
    """Real-time cyberpunk syntax highlighter for the Pajama language."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.rules = []

        # Keywords (Neon Cyan / Bold)
        kw_fmt = QTextCharFormat()
        kw_fmt.setForeground(QColor("#00e5ff"))
        kw_fmt.setFontWeight(QFont.Bold)
        keywords = [
            r"\bsay\b", r"\bask\b", r"\bwait\b", r"\bsleep\b",
            r"\bset\b", r"\bto\b", r"\bincrease\b", r"\bdecrease\b", r"\bby\b",
            r"\bif\b", r"\botherwise\b", r"\belse\b", r"\belif\b",
            r"\brepeat\b", r"\btimes\b", r"\bwhile\b", r"\bfor\b", r"\beach\b", r"\bin\b",
            r"\broutine\b", r"\bdef\b", r"\bfunction\b", r"\bgive\b", r"\breturn\b",
            r"\bis\b", r"\bnot\b", r"\band\b", r"\bor\b"
        ]
        for kw in keywords:
            self.rules.append((re.compile(kw, re.IGNORECASE), kw_fmt))

        # Native OS Primitives (Neon Magenta / Bold)
        os_fmt = QTextCharFormat()
        os_fmt.setForeground(QColor("#ff2a6d"))
        os_fmt.setFontWeight(QFont.Bold)
        os_verbs = [
            r"\bcpu\b", r"\bram\b", r"\bplay\b", r"\bnotify\b",
            r"\bnote\b", r"\bremind\b", r"\bresearch\b", r"\bflush\b"
        ]
        for v in os_verbs:
            self.rules.append((re.compile(v, re.IGNORECASE), os_fmt))

        # Literals: Numbers (Amber Gold)
        num_fmt = QTextCharFormat()
        num_fmt.setForeground(QColor("#ffb800"))
        self.rules.append((re.compile(r"\b\d+(\.\d+)?\b"), num_fmt))

        # Literals: Booleans & Null (Purple)
        bool_fmt = QTextCharFormat()
        bool_fmt.setForeground(QColor("#bd93f9"))
        self.rules.append((re.compile(r"\b(true|false|yes|no|none|null)\b", re.IGNORECASE), bool_fmt))

        # Strings (Soft Green)
        str_fmt = QTextCharFormat()
        str_fmt.setForeground(QColor("#50fa7b"))
        self.rules.append((re.compile(r'".*?"'), str_fmt))
        self.rules.append((re.compile(r"'.*?'"), str_fmt))

        # Comments (Muted Gray / Italic)
        comment_fmt = QTextCharFormat()
        comment_fmt.setForeground(QColor("#6272a4"))
        comment_fmt.setFontItalic(True)
        self.rules.append((re.compile(r"//.*"), comment_fmt))
        self.rules.append((re.compile(r"#.*"), comment_fmt))

    def highlightBlock(self, text: str):
        for pattern, fmt in self.rules:
            for match in pattern.finditer(text):
                start = match.start()
                length = match.end() - start
                self.setFormat(start, length, fmt)


# =============================================================================
# Line Number Area & Code Editor
# =============================================================================

class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self):
        return QSize(self.editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.editor.line_number_area_paint_event(event)


class PajamaCodeEditor(QPlainTextEdit):
    """Pajama Code Editor with line numbers, indentation handling, and syntax highlighting."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.line_number_area = LineNumberArea(self)
        self.highlighter = PajamaSyntaxHighlighter(self.document())

        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.highlight_current_line)

        self.update_line_number_area_width(0)

        # Editor Styling
        font = QFont("Consolas", 11)
        font.setStyleHint(QFont.Monospace)
        self.setFont(font)
        self.setStyleSheet("""
            QPlainTextEdit {
                background-color: #0d1117;
                color: #e6edf3;
                border: 1px solid #30363d;
                border-radius: 4px;
                padding: 4px;
                selection-background-color: #1f6feb;
            }
        """)

    def line_number_area_width(self) -> int:
        digits = 1
        max_num = max(1, self.blockCount())
        while max_num >= 10:
            max_num //= 10
            digits += 1
        space = 15 + self.fontMetrics().horizontalAdvance('9') * digits
        return space

    def update_line_number_area_width(self, _):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height()))

    def line_number_area_paint_event(self, event):
        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), QColor("#161b22"))

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + round(self.blockBoundingRect(block).height())

        painter.setPen(QColor("#484f58"))
        font = self.font()
        font.setPointSize(9)
        painter.setFont(font)

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.drawText(
                    0, top, self.line_number_area.width() - 6,
                    self.fontMetrics().height(), Qt.AlignRight, number
                )
            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
            block_number += 1

    def highlight_current_line(self):
        extra_selections = []
        if not self.isReadOnly():
            selection = QTextEditSelection() if hasattr(self, "QTextEditSelection") else None
            # Standard light selection line
            from PySide6.QtWidgets import QTextEdit
            line_selection = QTextEdit.ExtraSelection()
            line_color = QColor("#1f242c")
            line_selection.format.setBackground(line_color)
            line_selection.format.setProperty(QTextFormat.FullWidthSelection, True)
            line_selection.cursor = self.textCursor()
            line_selection.cursor.clearSelection()
            extra_selections.append(line_selection)
        self.setExtraSelections(extra_selections)


# =============================================================================
# Background Workers (Script Execution & AI Generation)
# =============================================================================

class ScriptExecutionWorker(QThread):
    """Executes a Pajama script safely off the main UI thread."""
    output_emitted = Signal(str)
    finished_execution = Signal(bool, str, float)

    def __init__(self, source: str, parent=None):
        super().__init__(parent)
        self.source = source
        self.interpreter = PajamaInterpreter(output_callback=self._on_output)
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True
        self.interpreter.cancel()

    def _on_output(self, text: str):
        self.output_emitted.emit(text)

    def run(self):
        start = time.time()
        try:
            output = self.interpreter.run(self.source)
            elapsed = (time.time() - start) * 1000
            self.finished_execution.emit(True, output, elapsed)
        except Exception as e:
            elapsed = (time.time() - start) * 1000
            self.finished_execution.emit(False, str(e), elapsed)


class AIGenerationWorker(QThread):
    """Runs Ollama AI generation off the UI thread."""
    generation_finished = Signal(str, str)  # action_type, result_text

    def __init__(self, assistant: PajamaAIAssistant, action: str, prompt_or_code: str, error_msg: str = "", parent=None):
        super().__init__(parent)
        self.assistant = assistant
        self.action = action
        self.payload = prompt_or_code
        self.error_msg = error_msg

    def run(self):
        try:
            if self.action == "generate":
                result = self.assistant.generate_code(self.payload)
            elif self.action == "explain":
                result = self.assistant.explain_code(self.payload)
            elif self.action == "fix":
                result = self.assistant.fix_code(self.payload, self.error_msg)
            else:
                result = "// Unknown action"
            self.generation_finished.emit(self.action, result)
        except Exception as e:
            self.generation_finished.emit(self.action, f"// Error: {str(e)}")


# =============================================================================
# Main Pajama Studio Widget
# =============================================================================

class PajamaStudioWidget(QWidget):
    """Complete Pajama IDE with AI assistant, editor, console, and templates."""

    def __init__(self, ollama_client: Optional[OllamaClient] = None, parent=None):
        super().__init__(parent)
        self.ollama_client = ollama_client or OllamaClient()
        self.ai_assistant = PajamaAIAssistant(self.ollama_client)
        self.active_script_worker: Optional[ScriptExecutionWorker] = None
        self.active_ai_worker: Optional[AIGenerationWorker] = None
        self.last_error_message = ""

        self.setup_ui()
        self.load_default_template()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(6)

        # 1. Top Cyber Bar & Telemetry
        top_bar = QHBoxLayout()
        title_label = QLabel("PAJAMA STUDIO // NATIVE SCRIPTING IDE")
        title_label.setFont(QFont("Consolas", 12, QFont.Bold))
        title_label.setStyleSheet("color: #00e5ff; letter-spacing: 1px;")
        top_bar.addWidget(title_label)

        top_bar.addStretch()

        # Templates Dropdown
        tmpl_label = QLabel("Templates:")
        tmpl_label.setStyleSheet("color: #8b949e;")
        top_bar.addWidget(tmpl_label)

        self.template_combo = QComboBox()
        self.template_combo.setStyleSheet("""
            QComboBox {
                background-color: #161b22;
                color: #58a6ff;
                border: 1px solid #30363d;
                border-radius: 4px;
                padding: 4px 8px;
                min-width: 180px;
            }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView {
                background-color: #161b22;
                color: #e6edf3;
                selection-background-color: #1f6feb;
            }
        """)
        for name in PAJAMA_PRESET_TEMPLATES:
            self.template_combo.addItem(name)
        self.template_combo.currentTextChanged.connect(self.on_template_selected)
        top_bar.addWidget(self.template_combo)

        main_layout.addLayout(top_bar)

        # 2. AI Assistant Prompt Drawer
        ai_box = QFrame()
        ai_box.setStyleSheet("""
            QFrame {
                background-color: #131924;
                border: 1px solid #1f6feb;
                border-radius: 6px;
                padding: 4px;
            }
        """)
        ai_layout = QHBoxLayout(ai_box)
        ai_layout.setContentsMargins(6, 4, 6, 4)
        ai_layout.setSpacing(6)

        ai_icon = QLabel("🤖 PAJAMA AI:")
        ai_icon.setFont(QFont("Consolas", 9, QFont.Bold))
        ai_icon.setStyleSheet("color: #ff2a6d;")
        ai_layout.addWidget(ai_icon)

        self.ai_input = QLineEdit()
        self.ai_input.setPlaceholderText("Ask AI: e.g. Monitor RAM and flush if over 75%, or calculate squares in a loop...")
        self.ai_input.setStyleSheet("""
            QLineEdit {
                background-color: #0d1117;
                color: #f0f6fc;
                border: 1px solid #30363d;
                border-radius: 4px;
                padding: 5px 8px;
                font-family: Consolas;
            }
            QLineEdit:focus { border: 1px solid #00e5ff; }
        """)
        self.ai_input.returnPressed.connect(self.on_ai_generate_clicked)
        ai_layout.addWidget(self.ai_input)

        self.btn_generate = QPushButton("✨ Generate Code")
        self.btn_generate.setStyleSheet("""
            QPushButton {
                background-color: #1f6feb;
                color: #ffffff;
                border-radius: 4px;
                padding: 5px 12px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #388bfd; }
            QPushButton:disabled { background-color: #21262d; color: #484f58; }
        """)
        self.btn_generate.clicked.connect(self.on_ai_generate_clicked)
        ai_layout.addWidget(self.btn_generate)

        self.btn_explain = QPushButton("💡 Explain")
        self.btn_explain.setStyleSheet("""
            QPushButton {
                background-color: #238636;
                color: #ffffff;
                border-radius: 4px;
                padding: 5px 10px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #2ea043; }
        """)
        self.btn_explain.clicked.connect(self.on_ai_explain_clicked)
        ai_layout.addWidget(self.btn_explain)

        self.btn_fix = QPushButton("🛠️ Fix Code")
        self.btn_fix.setStyleSheet("""
            QPushButton {
                background-color: #8957e5;
                color: #ffffff;
                border-radius: 4px;
                padding: 5px 10px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #a371f7; }
        """)
        self.btn_fix.clicked.connect(self.on_ai_fix_clicked)
        ai_layout.addWidget(self.btn_fix)

        main_layout.addWidget(ai_box)

        # 3. Main Splitter: Code Editor & Console
        splitter = QSplitter(Qt.Vertical)
        splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #30363d;
                height: 3px;
            }
        """)

        # Editor Container
        editor_container = QWidget()
        editor_layout = QVBoxLayout(editor_container)
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_layout.setSpacing(4)

        editor_header = QHBoxLayout()
        editor_title = QLabel("PAJAMA SCRIPT EDITOR (.pj)")
        editor_title.setStyleSheet("color: #8b949e; font-weight: bold; font-size: 10px;")
        editor_header.addWidget(editor_title)

        editor_header.addStretch()

        self.status_label = QLabel("Pajama AI Ready")
        self.status_label.setStyleSheet("color: #3fb950; font-size: 10px; font-weight: bold;")
        editor_header.addWidget(self.status_label)

        editor_layout.addLayout(editor_header)

        self.editor = PajamaCodeEditor()
        editor_layout.addWidget(self.editor)
        splitter.addWidget(editor_container)

        # Console Container
        console_container = QWidget()
        console_layout = QVBoxLayout(console_container)
        console_layout.setContentsMargins(0, 0, 0, 0)
        console_layout.setSpacing(4)

        console_header = QHBoxLayout()
        console_title = QLabel("EXECUTION CONSOLE & DIAGNOSTICS")
        console_title.setStyleSheet("color: #8b949e; font-weight: bold; font-size: 10px;")
        console_header.addWidget(console_title)

        console_header.addStretch()

        self.clear_btn = QPushButton("🧹 Clear")
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #21262d;
                color: #c9d1d9;
                border: 1px solid #30363d;
                border-radius: 3px;
                padding: 2px 8px;
                font-size: 10px;
            }
            QPushButton:hover { background-color: #30363d; }
        """)
        self.clear_btn.clicked.connect(self.clear_console)
        console_header.addWidget(self.clear_btn)

        console_layout.addLayout(console_header)

        self.console = QPlainTextEdit()
        self.console.setReadOnly(True)
        self.console.setFont(QFont("Consolas", 10))
        self.console.setStyleSheet("""
            QPlainTextEdit {
                background-color: #090d13;
                color: #58a6ff;
                border: 1px solid #21262d;
                border-radius: 4px;
                padding: 6px;
            }
        """)
        console_layout.addWidget(self.console)
        splitter.addWidget(console_container)

        splitter.setSizes([380, 180])
        main_layout.addWidget(splitter)

        # 4. Action Bar (Run, Stop, Status)
        action_bar = QHBoxLayout()

        self.run_btn = QPushButton("▶ Run Script")
        self.run_btn.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.run_btn.setStyleSheet("""
            QPushButton {
                background-color: #238636;
                color: #ffffff;
                border-radius: 4px;
                padding: 8px 24px;
            }
            QPushButton:hover { background-color: #2ea043; }
            QPushButton:disabled { background-color: #21262d; color: #484f58; }
        """)
        self.run_btn.clicked.connect(self.on_run_clicked)
        action_bar.addWidget(self.run_btn)

        self.stop_btn = QPushButton("⏹ Stop")
        self.stop_btn.setEnabled(False)
        self.stop_btn.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #da3633;
                color: #ffffff;
                border-radius: 4px;
                padding: 8px 18px;
            }
            QPushButton:hover { background-color: #f85149; }
            QPushButton:disabled { background-color: #21262d; color: #484f58; }
        """)
        self.stop_btn.clicked.connect(self.on_stop_clicked)
        action_bar.addWidget(self.stop_btn)

        action_bar.addStretch()

        self.timing_label = QLabel("Ready")
        self.timing_label.setStyleSheet("color: #8b949e; font-size: 11px;")
        action_bar.addWidget(self.timing_label)

        main_layout.addLayout(action_bar)

    def load_default_template(self):
        default_tmpl = PAJAMA_PRESET_TEMPLATES["System Health Guardian"]
        self.editor.setPlainText(default_tmpl)
        self.console.appendPlainText("[NOVA OS] Pajama Studio initialized. Type Pajama code or prompt the AI above.")

    def on_template_selected(self, name: str):
        if name in PAJAMA_PRESET_TEMPLATES:
            self.editor.setPlainText(PAJAMA_PRESET_TEMPLATES[name])
            self.timing_label.setText(f"Loaded template: {name}")

    def clear_console(self):
        self.console.clear()

    # -------------------------------------------------------------------------
    # Script Running & Cancellation
    # -------------------------------------------------------------------------

    def on_run_clicked(self):
        source = self.editor.toPlainText().strip()
        if not source:
            self.console.appendPlainText("[Warning] Editor is empty. Nothing to run.")
            return

        self.run_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.timing_label.setText("Running script...")
        self.console.appendPlainText(f"\n--- PAJAMA EXECUTION START [{time.strftime('%H:%M:%S')}] ---")

        if self.active_script_worker and self.active_script_worker.isRunning():
            self.active_script_worker.cancel()
            self.active_script_worker.wait(400)

        self.active_script_worker = ScriptExecutionWorker(source, parent=self)
        self.active_script_worker.output_emitted.connect(self._on_worker_output)
        self.active_script_worker.finished_execution.connect(self._on_worker_finished)
        self.active_script_worker.start()

    def on_stop_clicked(self):
        if self.active_script_worker and self.active_script_worker.isRunning():
            self.active_script_worker.cancel()
            self.timing_label.setText("Cancelling script...")
            self.stop_btn.setEnabled(False)

    @Slot(str)
    def _on_worker_output(self, text: str):
        self.console.appendPlainText(text)
        self._scroll_console_bottom()

    @Slot(bool, str, float)
    def _on_worker_finished(self, success: bool, result_or_err: str, elapsed_ms: float):
        self.run_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

        if success:
            self.timing_label.setText(f"Completed in {elapsed_ms:.1f} ms")
            self.console.appendPlainText(f"--- FINISHED (Exit Code: 0, Elapsed: {elapsed_ms:.1f}ms) ---")
            self.last_error_message = ""
        else:
            self.timing_label.setText(f"Error ({elapsed_ms:.1f} ms)")
            self.console.appendPlainText(f"[ERROR]: {result_or_err}")
            self.console.appendPlainText("--- EXECUTION HALTED ON ERROR ---")
            self.last_error_message = result_or_err

        self._scroll_console_bottom()

    def _scroll_console_bottom(self):
        cursor = self.console.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.console.setTextCursor(cursor)

    # -------------------------------------------------------------------------
    # AI Assistant Integrations
    # -------------------------------------------------------------------------

    def on_ai_generate_clicked(self):
        prompt = self.ai_input.text().strip()
        if not prompt:
            self.ai_input.setFocus()
            return

        p_lower = prompt.lower()
        # Intelligent routing: if user asks to explain, don't overwrite editor with English prose
        if p_lower.startswith(("explain", "why", "what is", "how does", "what does")):
            self.on_ai_explain_clicked()
            return

        # If user asks to fix error, route to fix
        if p_lower.startswith(("fix", "repair", "debug")):
            self.on_ai_fix_clicked()
            return

        self._set_ai_busy(True, "AI Generating Pajama Code...")
        self.active_ai_worker = AIGenerationWorker(
            self.ai_assistant, action="generate", prompt_or_code=prompt, parent=self
        )
        self.active_ai_worker.generation_finished.connect(self._on_ai_finished)
        self.active_ai_worker.start()

    def on_ai_explain_clicked(self):
        code = self.editor.toPlainText().strip()
        if not code:
            self.console.appendPlainText("[AI Notice] Editor contains no code to explain.")
            return

        self._set_ai_busy(True, "AI Analyzing Code...")
        self.active_ai_worker = AIGenerationWorker(
            self.ai_assistant, action="explain", prompt_or_code=code, parent=self
        )
        self.active_ai_worker.generation_finished.connect(self._on_ai_finished)
        self.active_ai_worker.start()

    def on_ai_fix_clicked(self):
        code = self.editor.toPlainText().strip()
        err = self.last_error_message or "General code improvement requested"

        self._set_ai_busy(True, "AI Repairing Code...")
        self.active_ai_worker = AIGenerationWorker(
            self.ai_assistant, action="fix", prompt_or_code=code, error_msg=err, parent=self
        )
        self.active_ai_worker.generation_finished.connect(self._on_ai_finished)
        self.active_ai_worker.start()

    @Slot(str, str)
    def _on_ai_finished(self, action: str, result: str):
        self._set_ai_busy(False, "Pajama AI Ready")

        if action == "generate":
            if result.strip().startswith(("// Pajama Script Analysis", "### Pajama Script")):
                self.console.appendPlainText(f"\n=== PAJAMA AI EXPLANATION ===\n{result}\n=============================")
                self._scroll_console_bottom()
                self.timing_label.setText("Explanation provided 💡")
            else:
                self.editor.setPlainText(result)
                self.console.appendPlainText(f"\n[Pajama AI] Generated new script for: \"{self.ai_input.text().strip()}\"")
                self.timing_label.setText("Code generated ✨")
        elif action == "explain":
            self.console.appendPlainText(f"\n=== PAJAMA AI CODE EXPLANATION ===\n{result}\n==================================")
            self._scroll_console_bottom()
            self.timing_label.setText("Code explanation provided 💡")
        elif action == "fix":
            self.editor.setPlainText(result)
            self.console.appendPlainText("\n[Pajama AI] Code repaired and updated in the editor.")
            self.timing_label.setText("Code fixed 🛠️")

    def _set_ai_busy(self, busy: bool, message: str):
        self.status_label.setText(message)
        self.btn_generate.setEnabled(not busy)
        self.btn_explain.setEnabled(not busy)
        self.btn_fix.setEnabled(not busy)
        self.ai_input.setEnabled(not busy)

    def cleanup(self):
        """Cancels any running workers when closing."""
        if self.active_script_worker and self.active_script_worker.isRunning():
            self.active_script_worker.cancel()
            self.active_script_worker.wait(300)
        if self.active_ai_worker and self.active_ai_worker.isRunning():
            self.active_ai_worker.wait(300)

    def closeEvent(self, event):
        self.cleanup()
        super().closeEvent(event)
