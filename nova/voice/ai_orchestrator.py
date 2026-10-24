"""
NOVA Voice — AI Orchestrator & Conversational Engine.
Coordinates intent classification, instant deterministic Python command execution,
streaming Ollama qwen2.5:0.5b responses, and pipeline sentence chunking into TTS playback.
"""

import re
import time
import logging
from typing import Optional, Dict, Any, List, Callable
from PySide6.QtCore import QObject, QThread, Signal

from nova.config import DEFAULT_MODEL, FALLBACK_MODEL
from nova.ollama_client import OllamaClient
from nova.deterministic_actions import evaluate_deterministic_query, evaluate_math_expression

logger = logging.getLogger("nova.voice.orchestrator")

VOICE_SYSTEM_PROMPT = (
    "You are NOVA, a personal, natural, and helpful AI desktop voice assistant running inside NOVA OS. "
    "Respond in a natural, friendly, conversational tone. "
    "Keep answers concise—typically 1 to 3 sentences—so they are clear when spoken aloud. "
    "Avoid formatting with markdown tables, code blocks, or heavy bullet points unless specifically requested. "
    "Direct and accurate answers are best."
)


class OllamaVoiceStreamWorker(QThread):
    """
    Background worker streaming tokens from Ollama qwen2.5:0.5b.
    Buffers tokens into complete sentences and emits each sentence immediately for TTS.
    """
    token_emitted = Signal(str)           # Raw streaming token
    sentence_ready = Signal(str)          # Clean complete sentence chunk for TTS
    response_completed = Signal(str)      # Full response text
    error_occurred = Signal(str)

    def __init__(self, ollama_client: OllamaClient, messages: List[Dict[str, str]], model: str = DEFAULT_MODEL):
        super().__init__()
        self.client = ollama_client
        self.messages = messages
        self.model = model
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        try:
            full_text = []
            sentence_buffer = ""
            sentence_split_re = re.compile(r'(?<=[.!?])\s+')

            for token in self.client.stream_chat(self.messages, model=self.model):
                if self._is_cancelled:
                    return

                full_text.append(token)
                self.token_emitted.emit(token)

                sentence_buffer += token
                # Check if buffer has sentence delimiter
                parts = sentence_split_re.split(sentence_buffer)
                if len(parts) > 1:
                    complete_sentence = parts[0].strip()
                    if complete_sentence:
                        self.sentence_ready.emit(complete_sentence)
                    sentence_buffer = parts[1]

            # Emit remainder
            if not self._is_cancelled and sentence_buffer.strip():
                self.sentence_ready.emit(sentence_buffer.strip())

            if not self._is_cancelled:
                self.response_completed.emit("".join(full_text).strip())

        except Exception as e:
            logger.error(f"Ollama voice stream error: {e}")
            self.error_occurred.emit(str(e))


class VoiceOrchestrator(QObject):
    """
    Central brain for NOVA Voice:
    1. Evaluates fast deterministic commands in < 0.01 ms.
    2. Streams conversational responses from local Ollama model.
    3. Feeds sentences to TTS engine and audio playback queue.
    4. Handles immediate interruption and consequential action safety gates.
    """
    state_changed = Signal(str)               # "idle", "listening", "thinking", "speaking", "error"
    user_transcript_ready = Signal(str)       # User's spoken / typed query
    nova_reply_token = Signal(str)            # Live token from LLM
    nova_reply_sentence = Signal(str)         # Completed sentence ready for TTS
    nova_reply_complete = Signal(str)         # Entire final response text
    action_executed = Signal(str, str)        # action_type, description
    confirmation_requested = Signal(str, str, object) # action_name, prompt, callback
    error_occurred = Signal(str)

    def __init__(self, ollama_client: OllamaClient, parent=None):
        super().__init__(parent)
        self.ollama_client = ollama_client
        self.active_model = DEFAULT_MODEL
        self.chat_history: List[Dict[str, str]] = []
        self._stream_worker: Optional[OllamaVoiceStreamWorker] = None
        self._is_interrupted = False
        self.deterministic_handlers = {}

    def register_action_handler(self, action_name: str, handler: Callable):
        """Registers a deterministic desktop callback (e.g. app launcher, theme switcher)."""
        self.deterministic_handlers[action_name] = handler

    def process_user_query(self, query: str):
        """
        Main entry point for processing a user utterance or text query.
        """
        clean_query = query.strip()
        if not clean_query:
            return

        self._is_interrupted = False
        self.user_transcript_ready.emit(clean_query)

        # ---------------- 1. Instant Deterministic Actions (< 0.01 ms) ----------------
        deterministic_response = self._check_deterministic_command(clean_query)
        if deterministic_response is not None:
            self.state_changed.emit("speaking")
            self.nova_reply_sentence.emit(deterministic_response)
            self.nova_reply_complete.emit(deterministic_response)
            return

        # ---------------- 2. Check Consequential Safety Gate ----------------
        if self._is_consequential_request(clean_query):
            self.state_changed.emit("idle")
            self.confirmation_requested.emit(
                "System Action Confirmation",
                f"You asked to execute: '{clean_query}'. This action modifies your environment. Do you confirm?",
                lambda: self._execute_confirmed_query(clean_query)
            )
            return

        # ---------------- 3. Conversational AI via Ollama ----------------
        self._execute_confirmed_query(clean_query)

    def _execute_confirmed_query(self, query: str):
        self.state_changed.emit("thinking")

        if not self.ollama_client.check_connection():
            fallback_msg = "Ollama is currently offline. You can still ask me for the time, calculator, notes, or app commands."
            self.state_changed.emit("speaking")
            self.nova_reply_sentence.emit(fallback_msg)
            self.nova_reply_complete.emit(fallback_msg)
            return

        # Build message history with voice-tailored system prompt
        messages = [{"role": "system", "content": VOICE_SYSTEM_PROMPT}]
        # Include recent turns (keep last 4 for low-RAM efficiency)
        messages.extend(self.chat_history[-4:])
        messages.append({"role": "user", "content": query})

        # Cancel previous if running
        if self._stream_worker and self._stream_worker.isRunning():
            self._stream_worker.cancel()

        self._stream_worker = OllamaVoiceStreamWorker(
            self.ollama_client,
            messages=messages,
            model=self.active_model
        )
        self._stream_worker.token_emitted.connect(self.nova_reply_token)
        self._stream_worker.sentence_ready.connect(self._on_sentence_ready)
        self._stream_worker.response_completed.connect(self._on_response_completed)
        self._stream_worker.error_occurred.connect(self._on_error)
        self._stream_worker.start()

    def _on_sentence_ready(self, sentence: str):
        if not self._is_interrupted:
            self.state_changed.emit("speaking")
            self.nova_reply_sentence.emit(sentence)

    def _on_response_completed(self, full_text: str):
        if not self._is_interrupted:
            # Update history
            self.chat_history.append({"role": "assistant", "content": full_text})
            self.nova_reply_complete.emit(full_text)

    def _on_error(self, err_msg: str):
        self.state_changed.emit("error")
        self.error_occurred.emit(err_msg)

    def interrupt(self):
        """Immediately interrupts the LLM stream and resets conversational state."""
        self._is_interrupted = True
        if self._stream_worker and self._stream_worker.isRunning():
            self._stream_worker.cancel()
            self._stream_worker = None
        self.state_changed.emit("idle")

    def _check_deterministic_command(self, query: str) -> Optional[str]:
        q_lower = query.lower()

        # Direct navigation / app launches
        apps = {
            "browser": ["open browser", "launch browser", "start browser", "web browser"],
            "dashboard": ["open dashboard", "system monitor", "telemetry", "hardware status"],
            "chat": ["open chat", "open ai", "start chat"],
            "notes": ["open notes", "launch notes", "novapad"],
            "terminal": ["open terminal", "launch terminal", "safe terminal"],
            "files": ["open files", "file vault", "file explorer"],
            "settings": ["open settings", "control center", "preferences"]
        }
        for app_id, triggers in apps.items():
            if any(t in q_lower for t in triggers):
                if "launch_app" in self.deterministic_handlers:
                    self.deterministic_handlers["launch_app"](app_id)
                self.action_executed.emit("app_launch", f"Opened {app_id.capitalize()}")
                return f"Opening the {app_id.capitalize()} application now."

        # Clock & Date
        if any(w in q_lower for w in ["what time is it", "current time", "what's the time", "clock"]):
            t_res = evaluate_deterministic_query("time")
            return f"The current time is {t_res['result']}."

        if any(w in q_lower for w in ["what date is it", "today's date", "what is today"]):
            d_res = evaluate_deterministic_query("date")
            return f"Today is {d_res['result']}."

        # Cache cleaning
        if any(w in q_lower for w in ["clean cache", "clear cache", "free storage", "purge memory"]):
            if "purge_cache" in self.deterministic_handlers:
                res = self.deterministic_handlers["purge_cache"]()
                return f"Transient cache purged. Reclaimed {res.get('freed_mb', 0)} megabytes of storage."

        # Math / conversions
        det = evaluate_deterministic_query(query)
        if det:
            if det["type"] == "calc":
                val = det.get("value", "")
                return f"The answer is {val}."
            elif det["type"] == "unit":
                return f"Result: {det['result']}."

        return None

    def _is_consequential_request(self, query: str) -> bool:
        """Identifies potentially disruptive or modifying requests requiring approval."""
        q_lower = query.lower()
        risky_terms = ["delete all", "wipe", "format", "reset database", "purge all notes", "kill all"]
        return any(term in q_lower for term in risky_terms)
