"""
AI Assistant Chat Interface for NOVA OS.
Connects to local Ollama LLMs with streaming responses, conversation history,
and safe command detection/execution.
"""

import re
from typing import List, Dict, Any, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QComboBox, QScrollArea,
    QFrame, QSizePolicy, QMessageBox
)
from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtGui import QFont, QTextCursor

from nova.ollama_client import OllamaClient
from nova.database import (
    create_chat_session, get_chat_sessions,
    add_chat_message, get_chat_messages,
    update_chat_session_title
)
from nova.config import DEFAULT_MODEL, FALLBACK_MODEL
from nova.safety import analyze_command, execute_command_safely, RiskLevel
from nova.ui.widgets.approval_dialog import CommandApprovalDialog
from nova.voice import VoiceEngine
from nova.deterministic_actions import evaluate_deterministic_query

class OllamaStreamWorker(QThread):
    chunk_received = Signal(str)
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, client: OllamaClient, messages: List[Dict[str, str]], model: str, parent=None):
        super().__init__(parent)
        self.client = client
        self.messages = messages
        self.model = model
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        full_response = []
        try:
            for chunk in self.client.stream_chat(self.messages, model=self.model):
                if self._is_cancelled:
                    break
                full_response.append(chunk)
                self.chunk_received.emit(chunk)
            self.finished.emit("".join(full_response))
        except Exception as e:
            self.error.emit(str(e))

class ModelDiscoveryWorker(QThread):
    """Background worker to discover models without blocking UI thread."""
    discovery_finished = Signal(bool, list)

    def __init__(self, client: OllamaClient, force: bool = False, parent=None):
        super().__init__(parent)
        self.client = client
        self.force = force
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        if self._is_cancelled:
            return
        is_online = self.client.check_connection(force_refresh=self.force)
        if self._is_cancelled:
            return
        models = []
        if is_online:
            models = self.client.get_available_models(force_refresh=self.force)
        if not self._is_cancelled:
            self.discovery_finished.emit(is_online, models)

class MessageBubble(QFrame):
    def __init__(self, role: str, text: str, model_name: str = "", parent_chat=None):
        super().__init__()
        self.parent_chat = parent_chat
        self.role = role
        self.raw_text = text

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        # Sender Tag
        tag_layout = QHBoxLayout()
        if role == "user":
            self.setStyleSheet("""
                QFrame {
                    background-color: #162035;
                    border: 1px solid rgba(0, 240, 255, 0.3);
                    border-radius: 8px;
                }
            """)
            tag = QLabel("USER")
            tag.setStyleSheet("color: #00f0ff; font-weight: bold; font-size: 11px;")
        else:
            self.setStyleSheet("""
                QFrame {
                    background-color: #0f1424;
                    border: 1px solid rgba(176, 38, 255, 0.3);
                    border-radius: 8px;
                }
            """)
            model_info = f" ({model_name})" if model_name else ""
            tag = QLabel(f"NOVA CORE{model_info}")
            tag.setStyleSheet("color: #b026ff; font-weight: bold; font-size: 11px;")

        tag_layout.addWidget(tag)
        layout.addLayout(tag_layout)

        # Content Text
        self.content_lbl = QLabel(text)
        self.content_lbl.setWordWrap(True)
        self.content_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.content_lbl.setStyleSheet("color: #e2e8f0; font-size: 13px; line-height: 1.4;")
        layout.addWidget(self.content_lbl)

        # Detect executable code blocks
        if role == "assistant":
            cmd_match = self._extract_code_command(text)
            if cmd_match:
                cmd_btn = QPushButton(f"⚡ Run Safe Command Check: '{cmd_match[:35]}...'")
                cmd_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #1a233a;
                        color: #00f0ff;
                        border: 1px solid rgba(0, 240, 255, 0.4);
                        font-size: 11px;
                        padding: 4px 8px;
                    }
                    QPushButton:hover {
                        background-color: #00f0ff;
                        color: #050811;
                    }
                """)
                cmd_btn.clicked.connect(lambda: self.parent_chat.trigger_command_execution(cmd_match))
                layout.addWidget(cmd_btn)

    def _extract_code_command(self, text: str) -> Optional[str]:
        patterns = [
            r"```(?:bash|shell|sh|cmd|powershell|ps1)?\s*\n([\s\S]*?)\n```",
            r"`([^`]+)`"
        ]
        for pat in patterns:
            match = re.search(pat, text)
            if match:
                candidate = match.group(1).strip()
                # If single line or looks like a command
                if len(candidate) < 200 and "\n" not in candidate:
                    return candidate
        return None

    def update_text(self, new_text: str):
        self.raw_text = new_text
        self.content_lbl.setText(new_text)

class ChatWidget(QWidget):
    def __init__(self, ollama_client: OllamaClient, voice_engine: Optional[VoiceEngine] = None, parent=None):
        super().__init__(parent)
        self.ollama_client = ollama_client
        self.active_session_id = None
        self.worker: Optional[OllamaStreamWorker] = None
        self.discovery_worker: Optional[ModelDiscoveryWorker] = None
        self._tracked_workers: List[QThread] = []
        self.current_bubble: Optional[MessageBubble] = None
        self._owns_voice = (voice_engine is None)
        self.voice = voice_engine if voice_engine is not None else VoiceEngine(self)

        self.setup_ui()
        self.load_models()
        self.load_or_create_session()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(10)

        # Control Toolbar (Model Selector, Session Switcher, Status)
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        # Status Dot
        self.status_dot = QLabel("●")
        self.status_dot.setStyleSheet("color: #718096; font-size: 14px;")
        toolbar.addWidget(self.status_dot)

        self.status_text = QLabel("Checking Ollama...")
        self.status_text.setObjectName("MutedLabel")
        toolbar.addWidget(self.status_text)

        toolbar.addStretch()

        # Voice Readout Toggle
        self.voice_btn = QPushButton("🔊 Voice: ON")
        self.voice_btn.setToolTip("Toggle Speech Readout of AI responses")
        self.voice_btn.setStyleSheet("""
            QPushButton {
                background: #111a2f;
                border: 1px solid #00f0ff;
                border-radius: 4px;
                color: #00f0ff;
                font-size: 11px;
                padding: 4px 8px;
            }
            QPushButton:hover {
                background: #00f0ff;
                color: #050811;
            }
        """)
        self.voice_btn.clicked.connect(self.toggle_voice)
        toolbar.addWidget(self.voice_btn)

        # Model Selector
        model_lbl = QLabel("Model:")
        model_lbl.setStyleSheet("color: #EAF4FF; font-weight: bold; font-size: 11px;")
        toolbar.addWidget(model_lbl)
        self.model_combo = QComboBox()
        self.model_combo.setMinimumWidth(160)
        toolbar.addWidget(self.model_combo)

        # Refresh Models Button
        refresh_btn = QPushButton("↻")
        refresh_btn.setFixedWidth(30)
        refresh_btn.setToolTip("Reload Ollama Models")
        refresh_btn.clicked.connect(lambda: self.load_models(force=True))
        toolbar.addWidget(refresh_btn)

        # Session Selector Dropdown
        session_lbl = QLabel("Session:")
        session_lbl.setStyleSheet("color: #EAF4FF; font-weight: bold; font-size: 11px;")
        toolbar.addWidget(session_lbl)
        self.session_combo = QComboBox()
        self.session_combo.setMinimumWidth(180)
        self.session_combo.setToolTip("Switch between conversation threads")
        self.session_combo.currentIndexChanged.connect(self._on_session_combo_changed)
        toolbar.addWidget(self.session_combo)

        # New Session Button
        new_session_btn = QPushButton("+ New Chat")
        new_session_btn.setToolTip("Start a fresh conversation thread")
        new_session_btn.clicked.connect(self.start_new_session)
        toolbar.addWidget(new_session_btn)

        main_layout.addLayout(toolbar)

        # Messages Scroll Area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)

        self.messages_container = QWidget()
        self.messages_layout = QVBoxLayout(self.messages_container)
        self.messages_layout.setContentsMargins(0, 0, 0, 0)
        self.messages_layout.setSpacing(10)
        self.messages_layout.addStretch()

        self.scroll_area.setWidget(self.messages_container)
        main_layout.addWidget(self.scroll_area)

        # Suggestions Chips
        chips_layout = QHBoxLayout()
        chips_layout.setSpacing(6)
        suggestions = [
            "Summarize this webpage",
            "Search the web for information",
            "Help me write a document",
            "Analyze this file",
            "Diagnose system health"
        ]
        for s in suggestions:
            btn = QPushButton(s)
            btn.setStyleSheet("""
                QPushButton {
                    background: #0f1525;
                    color: #8da2bb;
                    border: 1px solid rgba(255,255,255,0.08);
                    border-radius: 12px;
                    padding: 3px 10px;
                    font-size: 11px;
                }
                QPushButton:hover {
                    border-color: #00f0ff;
                    color: #00f0ff;
                }
            """)
            btn.clicked.connect(lambda checked, text=s: self.send_prompt(text))
            chips_layout.addWidget(btn)
        chips_layout.addStretch()
        main_layout.addLayout(chips_layout)

        # Input Box & Send Button
        input_layout = QHBoxLayout()
        input_layout.setSpacing(8)

        self.input_edit = QTextEdit()
        self.input_edit.setPlaceholderText("Transmit query or directive to NOVA AI... (Shift+Enter for newline)")
        self.input_edit.setMaximumHeight(70)
        self.input_edit.setFont(QFont("Segoe UI", 12))
        input_layout.addWidget(self.input_edit)

        # Voice Mic Button
        self.mic_btn = QPushButton("🎤")
        self.mic_btn.setFixedSize(36, 36)
        self.mic_btn.setToolTip("Voice Input / Quick Directive Presets")
        self.mic_btn.setStyleSheet("""
            QPushButton {
                background: #141c30;
                border: 1px solid #00f0ff;
                border-radius: 18px;
                color: #00f0ff;
                font-size: 14px;
            }
            QPushButton:hover {
                background: #00f0ff;
                color: #050811;
            }
        """)
        self.mic_btn.clicked.connect(self.on_mic_clicked)
        input_layout.addWidget(self.mic_btn)

        btn_box = QVBoxLayout()
        self.send_btn = QPushButton("Transmit")
        self.send_btn.setObjectName("PrimaryButton")
        self.send_btn.setMinimumHeight(34)
        self.send_btn.clicked.connect(self.on_send_clicked)
        btn_box.addWidget(self.send_btn)

        self.stop_btn = QPushButton("Halt")
        self.stop_btn.setObjectName("DangerButton")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.on_stop_clicked)
        btn_box.addWidget(self.stop_btn)

        input_layout.addLayout(btn_box)
        main_layout.addLayout(input_layout)

    def load_models(self, force: bool = False):
        """Asynchronously discovers local Ollama models on a background thread."""
        self.status_dot.setStyleSheet("color: #ffaa00; font-size: 14px;")
        self.status_text.setText("Connecting...")

        if self.discovery_worker and self.discovery_worker.isRunning():
            try:
                self.discovery_worker.cancel()
                self.discovery_worker.quit()
                self.discovery_worker.wait(1500)
            except Exception:
                pass
        
        worker = ModelDiscoveryWorker(self.ollama_client, force=force, parent=None)
        self.discovery_worker = worker
        self._tracked_workers.append(worker)
        worker.discovery_finished.connect(self.on_models_discovered)
        worker.finished.connect(lambda w=worker: self._cleanup_worker(w))
        worker.start()

    @Slot(bool, list)
    def on_models_discovered(self, is_online: bool, models: list):
        if is_online:
            self.status_dot.setStyleSheet("color: #00ff88; font-size: 14px;")
            self.status_text.setText("Ollama Online")
            self.model_combo.clear()
            if models:
                self.model_combo.addItems(models)
                if DEFAULT_MODEL in models:
                    self.model_combo.setCurrentText(DEFAULT_MODEL)
                elif FALLBACK_MODEL in models:
                    self.model_combo.setCurrentText(FALLBACK_MODEL)
            else:
                self.model_combo.addItem("No models found")
        else:
            self.status_dot.setStyleSheet("color: #ff2a55; font-size: 14px;")
            self.status_text.setText("Ollama Offline")
            self.model_combo.clear()
            self.model_combo.addItem("Ollama unreachable")

    def _populate_sessions(self, target_id: Optional[int] = None):
        if not hasattr(self, "session_combo"):
            return
        sessions = get_chat_sessions()
        self.session_combo.blockSignals(True)
        self.session_combo.clear()
        target_index = 0
        current_target = target_id if target_id is not None else self.active_session_id
        for idx, s in enumerate(sessions):
            title = s.get("title", f"Session #{s['id']}")
            display = f"#{s['id']} {title[:20]}"
            self.session_combo.addItem(display, s["id"])
            if s["id"] == current_target:
                target_index = idx
        if self.session_combo.count() > 0:
            self.session_combo.setCurrentIndex(target_index)
        self.session_combo.blockSignals(False)

    def _on_session_combo_changed(self, index: int):
        if index < 0:
            return
        session_id = self.session_combo.itemData(index)
        if session_id and session_id != self.active_session_id:
            self.switch_to_session(session_id, update_combo=False)

    def load_or_create_session(self):
        sessions = get_chat_sessions()
        if sessions:
            self.switch_to_session(sessions[0]["id"])
        else:
            self.start_new_session()

    def start_new_session(self):
        session_id = create_chat_session("Transmission " + str(len(get_chat_sessions()) + 1))
        self.switch_to_session(session_id)

    def switch_to_session(self, session_id: int, update_combo: bool = True):
        self.active_session_id = session_id
        if update_combo:
            self._populate_sessions(session_id)
        # Clear UI bubbles
        while self.messages_layout.count() > 1:
            item = self.messages_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        # Load stored messages
        msgs = get_chat_messages(session_id)
        if not msgs:
            # Add initial welcome
            welcome = (
                "Greetings. I am NOVA, your synthetic intelligence companion. "
                "I am running safely within this trial container on your Windows system. "
                "How may I assist your workflow today?"
            )
            add_chat_message(session_id, "assistant", welcome, "NOVA CORE")
            msgs = get_chat_messages(session_id)

        for m in msgs:
            bubble = MessageBubble(m["role"], m["content"], m.get("model", ""), parent_chat=self)
            self.messages_layout.insertWidget(self.messages_layout.count() - 1, bubble)

        self._scroll_to_bottom()

    def send_prompt(self, prompt: str):
        self.input_edit.setPlainText(prompt)
        self.on_send_clicked()

    def on_send_clicked(self):
        prompt = self.input_edit.toPlainText().strip()
        if not prompt or not self.active_session_id:
            return

        # Check deterministic actions first (instant local response in < 1ms)
        det_result = evaluate_deterministic_query(prompt)
        if det_result:
            self.input_edit.clear()
            user_bubble = MessageBubble("user", prompt, parent_chat=self)
            self.messages_layout.insertWidget(self.messages_layout.count() - 1, user_bubble)
            add_chat_message(self.active_session_id, "user", prompt, "Deterministic")

            answer_text = f"{det_result['icon']} {det_result['title']}:\n{det_result['result']}"
            asst_bubble = MessageBubble("assistant", answer_text, "NOVA Deterministic Core", parent_chat=self)
            self.messages_layout.insertWidget(self.messages_layout.count() - 1, asst_bubble)
            add_chat_message(self.active_session_id, "assistant", answer_text, "Deterministic Core")
            self._scroll_to_bottom()
            if self.voice and self.voice.enabled:
                self.voice.speak(det_result['result'])
            return

        selected_model = self.model_combo.currentText()
        if "unreachable" in selected_model or "No models" in selected_model:
            QMessageBox.warning(
                self,
                "Ollama Not Ready",
                "Local Ollama server is offline or has no models installed.\n"
                "Please run `ollama serve` and `ollama run qwen2.5:0.5b`."
            )
            return

        # Clear input
        self.input_edit.clear()

        # Add user bubble
        user_bubble = MessageBubble("user", prompt, parent_chat=self)
        self.messages_layout.insertWidget(self.messages_layout.count() - 1, user_bubble)
        add_chat_message(self.active_session_id, "user", prompt, selected_model)

        # Update session title if first user prompt
        msgs = get_chat_messages(self.active_session_id)
        if len(msgs) <= 3:
            title = prompt[:25] + ("..." if len(prompt) > 25 else "")
            update_chat_session_title(self.active_session_id, title)
            self._populate_sessions(self.active_session_id)

        # Prepare assistant bubble
        self.current_bubble = MessageBubble("assistant", "Thinking...", selected_model, parent_chat=self)
        self.messages_layout.insertWidget(self.messages_layout.count() - 1, self.current_bubble)
        self._scroll_to_bottom()

        # Format conversation messages for LLM
        history = []
        for m in msgs:
            history.append({"role": m["role"], "content": m["content"]})
        history.append({"role": "user", "content": prompt})

        # Start Stream Worker Thread
        self.send_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

        if self.worker and self.worker.isRunning():
            self.worker.cancel()

        worker = OllamaStreamWorker(self.ollama_client, history, selected_model, parent=self)
        self.worker = worker
        self._tracked_workers.append(worker)
        self.accumulated_text = ""
        worker.chunk_received.connect(self.on_chunk_received)
        worker.finished.connect(self.on_stream_finished)
        worker.error.connect(self.on_stream_error)
        worker.finished.connect(lambda w=worker: self._cleanup_worker(w))
        worker.start()

    @Slot(str)
    def on_chunk_received(self, chunk: str):
        self.accumulated_text += chunk
        if self.current_bubble:
            self.current_bubble.update_text(self.accumulated_text)
            self._scroll_to_bottom()

    @Slot(str)
    def on_stream_finished(self, full_text: str):
        self.send_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        if self.active_session_id:
            add_chat_message(self.active_session_id, "assistant", full_text, self.model_combo.currentText())
        if self.voice and self.voice.enabled and full_text.strip():
            self.voice.speak(full_text.strip())
        self.current_bubble = None

    @Slot(str)
    def on_stream_error(self, err_msg: str):
        self.send_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        if self.current_bubble:
            self.current_bubble.update_text(f"[Transmission Interrupted: {err_msg}]")
        self.current_bubble = None

    def _cleanup_worker(self, worker):
        if worker in self._tracked_workers:
            self._tracked_workers.remove(worker)
        if self.worker is worker:
            self.worker = None
        if hasattr(self, "discovery_worker") and self.discovery_worker is worker:
            self.discovery_worker = None
        try:
            worker.deleteLater()
        except Exception:
            pass

    def on_stop_clicked(self):
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.stop_btn.setEnabled(False)
            self.send_btn.setEnabled(True)
            if self.current_bubble:
                text = (self.accumulated_text + " [Generation Halted by User]").strip()
                self.current_bubble.update_text(text)
                if self.active_session_id:
                    add_chat_message(self.active_session_id, "assistant", text, self.model_combo.currentText())
                self.current_bubble = None
        if self.voice:
            self.voice.stop_speaking()

    def toggle_voice(self):
        if self.voice:
            self.voice.enabled = not self.voice.enabled
            if self.voice.enabled:
                self.voice_btn.setText("🔊 Voice: ON")
                self.voice_btn.setStyleSheet("""
                    QPushButton {
                        background: #111a2f;
                        border: 1px solid #00f0ff;
                        border-radius: 4px;
                        color: #00f0ff;
                        font-size: 11px;
                        padding: 4px 8px;
                    }
                    QPushButton:hover {
                        background: #00f0ff;
                        color: #050811;
                    }
                """)
            else:
                self.voice.stop_speaking()
                self.voice_btn.setText("🔇 Voice: OFF")
                self.voice_btn.setStyleSheet("""
                    QPushButton {
                        background: #181c26;
                        border: 1px solid #64748b;
                        border-radius: 4px;
                        color: #64748b;
                        font-size: 11px;
                        padding: 4px 8px;
                    }
                """)

    def on_mic_clicked(self):
        from PySide6.QtWidgets import QMenu
        from PySide6.QtCore import QPoint
        menu = QMenu(self)
        menu.addAction("🎤 'What time is it?'", lambda: self.send_prompt("What time is it?"))
        menu.addAction("🎤 'Diagnose system health'", lambda: self.send_prompt("Diagnose system health"))
        menu.addAction("🎤 'Calculate 25 * 40'", lambda: self.send_prompt("25 * 40"))
        menu.addAction("🎤 'Convert 16 gb to mb'", lambda: self.send_prompt("16 gb to mb"))
        menu.addAction("🎤 'What is today\\'s date?'", lambda: self.send_prompt("What date is it?"))
        menu.exec(self.mic_btn.mapToGlobal(QPoint(0, self.mic_btn.height())))

    def cleanup(self):
        if self.voice:
            self.voice.stop_speaking()
            if getattr(self, "_owns_voice", False):
                self.voice.cleanup()

        # Stop and join discovery worker
        if hasattr(self, "discovery_worker") and self.discovery_worker:
            try:
                self.discovery_worker.cancel()
                if self.discovery_worker.isRunning():
                    self.discovery_worker.quit()
                    self.discovery_worker.wait(1500)
            except Exception:
                pass
            self.discovery_worker = None

        # Stop and join active streaming worker
        if self.worker:
            try:
                self.worker.cancel()
                if self.worker.isRunning():
                    self.worker.quit()
                    self.worker.wait(1500)
            except Exception:
                pass
            self.worker = None

        # Stop and join any remaining tracked workers
        for w in list(self._tracked_workers):
            try:
                if hasattr(w, "cancel"):
                    w.cancel()
                if w.isRunning():
                    w.quit()
                    w.wait(1500)
            except Exception:
                pass
        self._tracked_workers.clear()

    def closeEvent(self, event):
        self.cleanup()
        super().closeEvent(event)

    def trigger_command_execution(self, command: str):
        """Invoked when user clicks on a command suggested by NOVA."""
        analysis = analyze_command(command)
        dialog = CommandApprovalDialog(command, analysis, self)
        if dialog.exec():
            final_cmd = dialog.edited_command
            success, output = execute_command_safely(final_cmd, approved_by_user=True)
            QMessageBox.information(
                self,
                "Command Output",
                f"Executed: {final_cmd}\nStatus: {'SUCCESS' if success else 'FAILED'}\n\nOutput:\n{output}"
            )

    def _scroll_to_bottom(self):
        QTimer_single = self.scroll_area.verticalScrollBar()
        QTimer_single.setValue(QTimer_single.maximum())
