"""
NOVA Voice Package.
Provides Siri-like conversational voice capabilities powered by Kokoro-82M,
Piper TTS fallback, local Speech-to-Text, and deterministic command routing.
"""

from nova.voice.audio_playback import AudioPlaybackManager
from nova.voice.kokoro_tts import KokoroTTSEngine, KokoroChunkWorker
from nova.voice.piper_fallback import PiperTTSEngine, PiperChunkWorker
from nova.voice.voice_input import VoiceInputManager
from nova.voice.speech_recognition import SpeechRecognizer, STTWorker
from nova.voice.ai_orchestrator import VoiceOrchestrator
from nova.voice.browser_context import BrowserVoiceContext

import sys
import subprocess
import logging
from typing import Optional
from PySide6.QtCore import QObject, QThread, Signal

logger = logging.getLogger("nova.voice")


class TTSWorker(QThread):
    """
    Backward-compatible lightweight TTS worker using native Windows SAPI
    for fast zero-dependency fallback.
    """
    finished = Signal()
    error = Signal(str)

    def __init__(self, text: str):
        super().__init__()
        self.text = text

    def run(self):
        try:
            clean_text = self.text.replace('"', '""').replace("'", "''")
            if len(clean_text) > 300:
                clean_text = clean_text[:300] + "... and more."

            ps_cmd = (
                f"Add-Type -AssemblyName System.Speech; "
                f"$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                f"$synth.Rate = 1; "
                f"$synth.Speak(\"{clean_text}\");"
            )
            subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
                capture_output=True,
                timeout=12,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            self.finished.emit()
        except Exception as e:
            logger.debug(f"TTS execution note: {e}")
            self.error.emit(str(e))


class VoiceEngine(QObject):
    """
    Master unified Voice Engine for NOVA OS.
    Manages active TTS engine (Kokoro-82M primary, Piper fast local fallback, SAPI instant fallback),
    speech playback, voice input, and speech recognition.
    """
    tts_started = Signal()
    tts_finished = Signal()
    stt_result_ready = Signal(str)
    engine_switched = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.enabled = True
        self.is_available = True
        self.active_engine_name = "kokoro"  # "kokoro", "piper", "sapi"

        # Initialize sub-engines
        self.playback = AudioPlaybackManager(parent=self)
        self.kokoro = KokoroTTSEngine(parent=self)
        self.piper = PiperTTSEngine(parent=self)
        self.voice_input = VoiceInputManager(parent=self)
        self.stt = SpeechRecognizer(parent=self)

        # Connect playback signals
        self.playback.playback_started.connect(self.tts_started)
        self.playback.playback_finished.connect(self.tts_finished)
        self.playback.playback_stopped.connect(self.tts_finished)

        # Connect echo suppression
        self.playback.playback_started.connect(lambda: self.voice_input.set_suppressed(True))
        self.playback.playback_finished.connect(lambda: self.voice_input.set_suppressed(False))
        self.playback.playback_stopped.connect(lambda: self.voice_input.set_suppressed(False))

        # Connect STT
        self.stt.transcription_completed.connect(self.stt_result_ready)

        self._active_tts_worker = None

    def set_engine(self, engine_name: str):
        """Switches active TTS engine between 'kokoro', 'piper', and 'sapi'."""
        name = engine_name.lower().strip()
        if name in ["kokoro", "piper", "sapi"]:
            self.active_engine_name = name
            self.engine_switched.emit(name)

    def speak(self, text: str, voice: Optional[str] = None, speed: float = 1.0):
        """Asynchronously synthesizes and plays speech using the active engine."""
        if not self.enabled or not text.strip():
            return

        # Stop any active playback first
        self.stop_speaking()

        clean_text = text.strip()

        # Engine 1: Kokoro-82M (Primary neural voice)
        if self.active_engine_name == "kokoro" and self.kokoro.is_model_available:
            self._active_tts_worker = self.kokoro.create_stream_worker(clean_text, voice=voice, speed=speed)
            self._active_tts_worker.chunk_ready.connect(lambda samples, sr, t: self.playback.queue_chunk(samples, sr))
            self._active_tts_worker.start()
            return

        # Engine 2: Piper TTS (Local fast fallback)
        if self.active_engine_name in ["kokoro", "piper"] and self.piper.is_model_available:
            self._active_tts_worker = self.piper.create_stream_worker(clean_text, speed=speed)
            self._active_tts_worker.chunk_ready.connect(lambda samples, sr, t: self.playback.queue_chunk(samples, sr))
            self._active_tts_worker.start()
            return

        # Engine 3: Windows SAPI (Instant zero-dependency fallback)
        self.tts_started.emit()
        self._active_tts_worker = TTSWorker(clean_text)
        self._active_tts_worker.finished.connect(self.tts_finished)
        self._active_tts_worker.error.connect(self.tts_finished)
        self._active_tts_worker.start()

    def stop_speaking(self):
        """Immediately interrupts speech generation and cuts audio output."""
        if self._active_tts_worker and self._active_tts_worker.isRunning():
            if hasattr(self._active_tts_worker, "cancel"):
                self._active_tts_worker.cancel()
            elif hasattr(self._active_tts_worker, "terminate"):
                self._active_tts_worker.terminate()
            self._active_tts_worker = None

        self.playback.stop()
        self.tts_finished.emit()


__all__ = [
    "VoiceEngine",
    "TTSWorker",
    "KokoroTTSEngine",
    "KokoroChunkWorker",
    "PiperTTSEngine",
    "PiperChunkWorker",
    "AudioPlaybackManager",
    "VoiceInputManager",
    "SpeechRecognizer",
    "STTWorker",
    "VoiceOrchestrator",
    "BrowserVoiceContext"
]
