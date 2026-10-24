"""
NOVA Voice — Siri-Like Cybernetic Voice Assistant HUD & Animated Orb.
Provides an original visual identity for NOVA Voice with live state animations,
real-time audio amplitude waveforms, streaming response bubbles, and accessible controls.
"""

import math
import logging
from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFrame, QScrollArea, QSlider, QComboBox,
    QGridLayout, QApplication, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, QTimer, QPoint, QRect, QRectF, Signal, Slot
from PySide6.QtGui import (
    QPainter, QColor, QPen, QRadialGradient, QBrush, QFont,
    QKeySequence, QShortcut
)

from nova.voice import (
    VoiceOrchestrator, VoiceInputManager, SpeechRecognizer,
    AudioPlaybackManager, KokoroTTSEngine, PiperTTSEngine,
    BrowserVoiceContext
)
from nova.voice.kokoro_tts import RECOMMENDED_VOICES
from nova.config import APP_NAME

logger = logging.getLogger("nova.ui.voice_ui")


class NovaVoiceOrbWidget(QWidget):
    """
    Animated Cybernetic Voice Orb.
    Visualizes assistant states (Idle, Listening, Thinking, Speaking, Error)
    and pulses dynamically in real time to microphone & speaker audio amplitudes.
    Optimized for low-spec CPU (< 2% CPU usage).
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(140, 140)
        self.state = "idle"  # "idle", "listening", "thinking", "speaking", "error"
        self.amplitude = 0.0 # 0.0 - 1.0
        self.target_amplitude = 0.0
        self.phase = 0.0
        self.particle_angle = 0.0

        # Animation timer (30 FPS)
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._update_animation)
        self.anim_timer.start(33)

    def set_state(self, state: str):
        self.state = state.lower()
        self.update()

    def set_amplitude(self, amp: float):
        """Sets normalized target amplitude (0.0 to 1.0) from mic or speaker."""
        self.target_amplitude = max(0.0, min(1.0, float(amp)))

    def _update_animation(self):
        # Smooth amplitude interpolation
        self.amplitude += (self.target_amplitude - self.amplitude) * 0.35
        self.phase += 0.08
        if self.phase > 2 * math.pi:
            self.phase -= 2 * math.pi

        if self.state == "thinking":
            self.particle_angle += 0.12
            if self.particle_angle > 2 * math.pi:
                self.particle_angle -= 2 * math.pi

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        cx = w / 2.0
        cy = h / 2.0

        # Color schemes by state
        if self.state == "listening":
            base_color = QColor(0, 240, 255)   # Cyber Cyan
            glow_color = QColor(0, 240, 255, 60)
        elif self.state == "speaking":
            base_color = QColor(176, 38, 255)  # Neon Violet
            glow_color = QColor(176, 38, 255, 70)
        elif self.state == "thinking":
            base_color = QColor(0, 255, 136)   # Emerald Matrix
            glow_color = QColor(0, 255, 136, 60)
        elif self.state == "error":
            base_color = QColor(255, 60, 90)   # Crimson Alert
            glow_color = QColor(255, 60, 90, 60)
        else: # idle
            base_color = QColor(0, 200, 255)
            glow_color = QColor(0, 200, 255, 35)

        # 1. Outer pulsating atmospheric aura
        pulse_factor = math.sin(self.phase) * 0.12
        aura_radius = 48 + (self.amplitude * 20.0) + (pulse_factor * 6.0)

        aura_grad = QRadialGradient(cx, cy, aura_radius)
        aura_grad.setColorAt(0.0, glow_color)
        aura_grad.setColorAt(0.65, QColor(glow_color.red(), glow_color.green(), glow_color.blue(), 25))
        aura_grad.setColorAt(1.0, QColor(glow_color.red(), glow_color.green(), glow_color.blue(), 0))
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(aura_grad))
        painter.drawEllipse(QPoint(int(cx), int(cy)), int(aura_radius), int(aura_radius))

        # 2. Concentric Frequency Rings
        ring_radius = 32 + (self.amplitude * 14.0)
        ring_pen = QPen(base_color)
        ring_pen.setWidth(2)
        painter.setPen(ring_pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(QPoint(int(cx), int(cy)), int(ring_radius), int(ring_radius))

        # Secondary outer subtle ring
        sec_radius = ring_radius + 9 + (pulse_factor * 4.0)
        sec_pen = QPen(QColor(base_color.red(), base_color.green(), base_color.blue(), 80))
        sec_pen.setWidth(1)
        sec_pen.setStyle(Qt.DashLine)
        painter.setPen(sec_pen)
        painter.drawEllipse(QPoint(int(cx), int(cy)), int(sec_radius), int(sec_radius))

        # 3. Inner Core Plasma Orb
        core_radius = 22 + (self.amplitude * 6.0)
        core_grad = QRadialGradient(cx - 3, cy - 3, core_radius)
        core_grad.setColorAt(0.0, QColor(255, 255, 255, 240))
        core_grad.setColorAt(0.4, base_color)
        core_grad.setColorAt(1.0, QColor(base_color.red() // 2, base_color.green() // 2, base_color.blue() // 2, 180))
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(core_grad))
        painter.drawEllipse(QPoint(int(cx), int(cy)), int(core_radius), int(core_radius))

        # 4. Orbiting Thinking Particles
        if self.state == "thinking":
            for i in range(3):
                ang = self.particle_angle + (i * (2 * math.pi / 3))
                orbit_r = 38.0
                px = cx + math.cos(ang) * orbit_r
                py = cy + math.sin(ang) * orbit_r
                painter.setBrush(QBrush(QColor(255, 255, 255, 220)))
                painter.drawEllipse(QPoint(int(px), int(py)), 3, 3)

        painter.end()


class NovaVoiceHUD(QFrame):
    """
    Siri-style Cybernetic Assistant HUD for NOVA OS.
    Features voice orb, live transcription, spoken response output,
    stop/mic controls, browser context integration, and voice engine configuration.
    """
    action_requested = Signal(str, dict)

    def __init__(self, voice_engine, orchestrator: VoiceOrchestrator, browser_context: Optional[BrowserVoiceContext] = None, parent=None):
        super().__init__(parent)
        self.voice_engine = voice_engine
        self.orchestrator = orchestrator
        self.browser_context = browser_context

        self.setObjectName("NovaVoiceHUD")
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self.setFixedSize(540, 520)

        self.setup_ui()
        self.connect_signals()

    def setup_ui(self):
        self.setStyleSheet("""
            QFrame#NovaVoiceHUD {
                background-color: rgba(9, 14, 26, 0.98);
                border: 1px solid #00f0ff;
                border-radius: 12px;
            }
        """)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(0, 240, 255, 75))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 16)
        layout.setSpacing(10)

        # 1. Top Header Bar
        header = QHBoxLayout()
        logo = QLabel("❖ NOVA VOICE")
        logo.setStyleSheet("color: #00f0ff; font-weight: bold; font-size: 13px; letter-spacing: 1px;")
        header.addWidget(logo)

        header.addStretch()

        self.state_pill = QLabel("● IDLE")
        self.state_pill.setStyleSheet("color: #94a3b8; font-size: 10px; font-weight: bold; background: #0c1424; padding: 2px 8px; border-radius: 4px; border: 1px solid rgba(255,255,255,0.1);")
        header.addWidget(self.state_pill)

        self.engine_pill = QLabel("KOKORO-82M [af_nova]")
        self.engine_pill.setStyleSheet("color: #b026ff; font-size: 10px; font-weight: bold; background: #0c1424; padding: 2px 8px; border-radius: 4px; border: 1px solid rgba(176,38,255,0.3);")
        header.addWidget(self.engine_pill)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(22, 22)
        close_btn.setStyleSheet("background: transparent; border: none; color: #64748b; font-weight: bold; font-size: 12px;")
        close_btn.clicked.connect(self.hide)
        header.addWidget(close_btn)
        layout.addLayout(header)

        # 2. Central Animated Orb
        orb_box = QHBoxLayout()
        orb_box.addStretch()
        self.orb = NovaVoiceOrbWidget(self)
        orb_box.addWidget(self.orb)
        orb_box.addStretch()
        layout.addLayout(orb_box)

        # 3. Live Transcription & Response Area
        convo_frame = QFrame()
        convo_frame.setStyleSheet("""
            QFrame {
                background: #060a14;
                border: 1px solid rgba(0, 240, 255, 0.2);
                border-radius: 8px;
            }
        """)
        convo_layout = QVBoxLayout(convo_frame)
        convo_layout.setContentsMargins(12, 10, 12, 10)
        convo_layout.setSpacing(6)

        self.user_bubble = QLabel("Press the microphone button or type below to speak with NOVA...")
        self.user_bubble.setWordWrap(True)
        self.user_bubble.setStyleSheet("color: #94a3b8; font-size: 12px; font-style: italic;")
        convo_layout.addWidget(self.user_bubble)

        self.nova_bubble = QLabel("Ready. Powered by Kokoro-82M and local Qwen 2.5.")
        self.nova_bubble.setWordWrap(True)
        self.nova_bubble.setStyleSheet("color: #ffffff; font-size: 13px; font-weight: 500; line-height: 1.4;")
        convo_layout.addWidget(self.nova_bubble)
        layout.addWidget(convo_frame)

        # 4. Browser Context Action Pills
        action_row = QHBoxLayout()
        action_row.setSpacing(6)

        self.btn_summarize_page = QPushButton("📄 Summarize Page")
        self.btn_summarize_page.setStyleSheet(self._pill_style("#00f0ff"))
        self.btn_summarize_page.clicked.connect(self._on_summarize_page_clicked)
        action_row.addWidget(self.btn_summarize_page)

        self.btn_explain_selection = QPushButton("🔍 Explain Selection")
        self.btn_explain_selection.setStyleSheet(self._pill_style("#b026ff"))
        self.btn_explain_selection.clicked.connect(self._on_explain_selection_clicked)
        action_row.addWidget(self.btn_explain_selection)

        action_row.addStretch()

        self.btn_settings_toggle = QPushButton("⚙ Voice Settings")
        self.btn_settings_toggle.setStyleSheet(self._pill_style("#cbd5e1"))
        self.btn_settings_toggle.clicked.connect(self._toggle_settings_panel)
        action_row.addWidget(self.btn_settings_toggle)
        layout.addLayout(action_row)

        # 5. Settings Drawer (Collapsible)
        self.settings_panel = QFrame()
        self.settings_panel.setVisible(False)
        self.settings_panel.setStyleSheet("""
            QFrame {
                background: #0a0f1d;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 6px;
                padding: 6px;
            }
        """)
        s_layout = QGridLayout(self.settings_panel)
        s_layout.setContentsMargins(8, 8, 8, 8)
        s_layout.setSpacing(6)

        # Engine selector
        s_layout.addWidget(QLabel("TTS Engine:"), 0, 0)
        self.engine_combo = QComboBox()
        self.engine_combo.addItems([
            "Kokoro-82M (Neural High-Fidelity)",
            "Piper TTS (Local Low-RAM Fast)",
            "Windows SAPI (Instant Fallback)"
        ])
        self.engine_combo.currentIndexChanged.connect(self._on_engine_changed)
        s_layout.addWidget(self.engine_combo, 0, 1)

        # Voice Profile selector
        s_layout.addWidget(QLabel("Voice Profile:"), 1, 0)
        self.voice_combo = QComboBox()
        for v_id, v_label, _ in RECOMMENDED_VOICES:
            self.voice_combo.addItem(f"{v_id} — {v_label}", v_id)
        self.voice_combo.currentIndexChanged.connect(self._on_voice_changed)
        s_layout.addWidget(self.voice_combo, 1, 1)

        # Speech Speed slider
        s_layout.addWidget(QLabel("Speech Speed:"), 2, 0)
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(50, 150)
        self.speed_slider.setValue(100)
        self.speed_slider.valueChanged.connect(self._on_speed_changed)
        s_layout.addWidget(self.speed_slider, 2, 1)

        # Cache clear button
        self.btn_clear_cache = QPushButton("🧹 Clear Audio Cache")
        self.btn_clear_cache.clicked.connect(self._on_clear_cache)
        s_layout.addWidget(self.btn_clear_cache, 3, 1)

        layout.addWidget(self.settings_panel)

        # 6. Bottom Interaction Bar (Push-to-Talk, Stop, Text Input)
        bot_row = QHBoxLayout()
        bot_row.setSpacing(8)

        # Mic Push-to-Talk Button
        self.mic_btn = QPushButton("🎙 Hold to Speak")
        self.mic_btn.setFixedHeight(38)
        self.mic_btn.setStyleSheet("""
            QPushButton {
                background: #0052cc;
                border: 1px solid #00f0ff;
                border-radius: 6px;
                color: #ffffff;
                font-weight: bold;
                font-size: 12px;
                padding: 0 14px;
            }
            QPushButton:hover {
                background: #00f0ff;
                color: #000000;
            }
        """)
        self.mic_btn.pressed.connect(self._on_mic_pressed)
        self.mic_btn.released.connect(self._on_mic_released)
        bot_row.addWidget(self.mic_btn)

        # Immediate Stop Speaking Button
        self.stop_btn = QPushButton("⏹ Stop")
        self.stop_btn.setFixedHeight(38)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background: #220810;
                border: 1px solid #ff2a55;
                border-radius: 6px;
                color: #ff2a55;
                font-weight: bold;
                font-size: 12px;
                padding: 0 12px;
            }
            QPushButton:hover {
                background: #ff2a55;
                color: #ffffff;
            }
        """)
        self.stop_btn.clicked.connect(self.stop_current_action)
        bot_row.addWidget(self.stop_btn)

        # Text Input Fallback
        self.text_input = QLineEdit()
        self.text_input.setFixedHeight(38)
        self.text_input.setPlaceholderText("Or type your question (e.g. 'What time is it?', 'Summarize this page')...")
        self.text_input.setStyleSheet("""
            QLineEdit {
                background: #0d1527;
                border: 1px solid rgba(0, 240, 255, 0.3);
                border-radius: 6px;
                color: #ffffff;
                padding: 0 10px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border-color: #00f0ff;
            }
        """)
        self.text_input.returnPressed.connect(self._on_text_entered)
        bot_row.addWidget(self.text_input, stretch=1)

        layout.addLayout(bot_row)

    def _pill_style(self, color_hex: str) -> str:
        return f"""
            QPushButton {{
                background: #0d1527;
                border: 1px solid {color_hex}55;
                border-radius: 4px;
                color: {color_hex};
                padding: 4px 8px;
                font-size: 10px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: {color_hex}22;
                border-color: {color_hex};
            }}
        """

    def connect_signals(self):
        # Voice Input Amplitude -> Orb Amplitude
        self.voice_engine.voice_input.amplitude_updated.connect(self._on_mic_amplitude)
        self.voice_engine.playback.amplitude_updated.connect(self._on_speaker_amplitude)

        # Orchestrator States
        self.orchestrator.state_changed.connect(self._on_state_changed)
        self.orchestrator.user_transcript_ready.connect(self._on_user_transcript)
        self.orchestrator.nova_reply_token.connect(self._on_reply_token)
        self.orchestrator.nova_reply_complete.connect(self._on_reply_complete)
        self.orchestrator.nova_reply_sentence.connect(self._on_sentence_to_speak)
        self.orchestrator.error_occurred.connect(self._on_error)

        # Voice Input -> STT -> Orchestrator
        self.voice_engine.voice_input.speech_ended.connect(self.voice_engine.stt.transcribe_audio_buffer)
        self.voice_engine.stt.transcription_completed.connect(self.orchestrator.process_user_query)

        # Browser Context Signals
        if self.browser_context:
            self.browser_context.page_text_ready.connect(self._on_browser_page_text)
            self.browser_context.selection_text_ready.connect(self._on_browser_selection_text)
            self.browser_context.error_occurred.connect(self._on_error)

    def show_centered(self, parent_window: QWidget):
        p_geo = parent_window.geometry()
        x = p_geo.x() + (p_geo.width() - self.width()) // 2
        y = p_geo.y() + 70
        self.move(x, y)
        self.show()
        self.raise_()
        self.text_input.setFocus()

    def _on_mic_pressed(self):
        self.voice_engine.stop_speaking()
        self.orchestrator.interrupt()
        self.mic_btn.setText("● Listening...")
        self.mic_btn.setStyleSheet("background: #00ff88; color: #000000; font-weight: bold; border-radius: 6px; padding: 0 14px;")
        self.user_bubble.setText("Listening...")
        self.voice_engine.voice_input.start_listening()
        self._on_state_changed("listening")

    def _on_mic_released(self):
        self.mic_btn.setText("🎙 Hold to Speak")
        self.mic_btn.setStyleSheet("""
            QPushButton {
                background: #0052cc;
                border: 1px solid #00f0ff;
                border-radius: 6px;
                color: #ffffff;
                font-weight: bold;
                padding: 0 14px;
            }
        """)
        recorded_audio = self.voice_engine.voice_input.stop_listening()
        if recorded_audio is not None and len(recorded_audio) > 1000:
            self._on_state_changed("thinking")
            self.voice_engine.stt.transcribe_audio_buffer(recorded_audio)
        else:
            self._on_state_changed("idle")

    def _on_text_entered(self):
        text = self.text_input.text().strip()
        if not text:
            return
        self.text_input.clear()
        self.orchestrator.process_user_query(text)

    def _on_mic_amplitude(self, amp: float):
        if self.orb.state == "listening":
            self.orb.set_amplitude(amp)

    def _on_speaker_amplitude(self, amp: float):
        if self.orb.state == "speaking":
            self.orb.set_amplitude(amp)

    def _on_state_changed(self, state: str):
        self.orb.set_state(state)
        colors = {
            "idle": ("#94a3b8", "● IDLE"),
            "listening": ("#00f0ff", "● LISTENING"),
            "thinking": ("#00ff88", "● THINKING..."),
            "speaking": ("#b026ff", "● SPEAKING"),
            "error": ("#ff2a55", "● ALERT")
        }
        color, text = colors.get(state, ("#94a3b8", state.upper()))
        self.state_pill.setText(text)
        self.state_pill.setStyleSheet(f"color: {color}; font-size: 10px; font-weight: bold; background: #0c1424; padding: 2px 8px; border-radius: 4px; border: 1px solid {color}55;")

    def _on_user_transcript(self, text: str):
        self.user_bubble.setText(f"You: \"{text}\"")
        self.nova_bubble.setText("...")

    def _on_reply_token(self, token: str):
        current = self.nova_bubble.text()
        if current == "...":
            current = ""
        self.nova_bubble.setText(current + token)

    def _on_sentence_to_speak(self, sentence: str):
        # Forward sentence directly to voice engine for audio playback with queue support
        voice_id = self.voice_combo.currentData() or "af_nova"
        speed = self.speed_slider.value() / 100.0
        self.voice_engine.speak(sentence, voice=voice_id, speed=speed, queue=True)

    def _on_reply_complete(self, full_text: str):
        self.nova_bubble.setText(full_text)
        self._on_state_changed("speaking" if self.voice_engine.playback.is_playing else "idle")

    def _on_error(self, err_msg: str):
        self._on_state_changed("error")
        self.nova_bubble.setText(f"[Error: {err_msg}]")

    def stop_current_action(self):
        """Halts speech playback and cancels current LLM turn immediately."""
        self.voice_engine.stop_speaking()
        self.orchestrator.interrupt()
        self._on_state_changed("idle")

    def _on_summarize_page_clicked(self):
        if self.browser_context:
            self.user_bubble.setText("You: \"Summarize this active webpage\"")
            self.browser_context.request_page_summary()
        else:
            self._on_error("NOVA Browser context not connected")

    def _on_explain_selection_clicked(self):
        if self.browser_context:
            self.user_bubble.setText("You: \"Explain the selected text on this page\"")
            self.browser_context.request_selection_explanation()
        else:
            self._on_error("NOVA Browser context not connected")

    def _on_browser_page_text(self, title: str, text: str):
        prompt = f"Please summarize the essential points of the webpage '{title}' in 2-3 clear spoken sentences:\n\n{text}"
        self.orchestrator.process_user_query(prompt)

    def _on_browser_selection_text(self, selection: str):
        prompt = f"Please explain the following selected excerpt clearly and concisely:\n\n{selection}"
        self.orchestrator.process_user_query(prompt)

    def _toggle_settings_panel(self):
        self.settings_panel.setVisible(not self.settings_panel.isVisible())

    def _on_engine_changed(self, idx: int):
        engines = ["kokoro", "piper", "sapi"]
        chosen = engines[min(idx, len(engines)-1)]
        self.voice_engine.set_engine(chosen)
        labels = {
            "kokoro": "KOKORO-82M [af_nova]",
            "piper": "PIPER TTS [lessac]",
            "sapi": "WINDOWS SAPI [offline]"
        }
        self.engine_pill.setText(labels.get(chosen, chosen.upper()))

    def _on_voice_changed(self, idx: int):
        v_id = self.voice_combo.currentData()
        if self.voice_engine.active_engine_name == "kokoro":
            self.engine_pill.setText(f"KOKORO-82M [{v_id}]")

    def _on_speed_changed(self, val: int):
        speed = val / 100.0
        self.voice_engine.kokoro.speed = speed
        self.voice_engine.piper.speed = speed

    def _on_clear_cache(self):
        k_freed = self.voice_engine.kokoro.clear_cache()
        p_freed = self.voice_engine.piper.clear_cache()
        self.user_bubble.setText(f"Cleared audio cache ({k_freed + p_freed} files purged).")
