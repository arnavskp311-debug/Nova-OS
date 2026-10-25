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
        self.playback.playback_finished.connect(self._on_playback_finished)
        self.playback.playback_stopped.connect(self.tts_finished)

        # Connect echo suppression
        self.playback.playback_started.connect(lambda: self.voice_input.set_suppressed(True))
        self.playback.playback_finished.connect(lambda: self.voice_input.set_suppressed(False))
        self.playback.playback_stopped.connect(lambda: self.voice_input.set_suppressed(False))

        # Connect STT
        self.stt.transcription_completed.connect(self.stt_result_ready)

        self._active_tts_worker = None
        self._tracked_workers = []
        self._speech_queue = []
        self._is_synthesizing = False

    def set_engine(self, engine_name: str):
        """Switches active TTS engine between 'kokoro', 'piper', and 'sapi'."""
        name = engine_name.lower().strip()
        if name in ["kokoro", "piper", "sapi"]:
            self.active_engine_name = name
            self.engine_switched.emit(name)

    def speak(self, text: str, voice: Optional[str] = None, speed: float = 1.0, queue: bool = False):
        """
        Asynchronously synthesizes and plays speech using the active engine.
        If queue is True and speech synthesis is currently active, queues the text
        chunk so streaming LLM sentences are synthesized sequentially without crashing.
        """
        if not self.enabled or not text.strip():
            return

        clean_text = text.strip()

        # If queueing is requested and synthesis is currently in progress, enqueue
        if queue and (self._is_synthesizing or (self._active_tts_worker and self._active_tts_worker.isRunning())):
            self._speech_queue.append((clean_text, voice, speed))
            return

        # Starting a new conversational utterance: clear previous queue & cancel prior
        if not queue:
            self._speech_queue.clear()
            self._cancel_running_workers()

        self._start_worker(clean_text, voice=voice, speed=speed)

    def _start_worker(self, text: str, voice: Optional[str] = None, speed: float = 1.0):
        self._is_synthesizing = True

        # Engine 1: Kokoro-82M (Primary neural voice)
        if self.active_engine_name == "kokoro" and self.kokoro.is_model_available:
            worker = self.kokoro.create_stream_worker(text, voice=voice, speed=speed)
            self._track_and_start_worker(worker)
            return

        # Engine 2: Piper TTS (Local fast fallback)
        if self.active_engine_name in ["kokoro", "piper"] and self.piper.is_model_available:
            worker = self.piper.create_stream_worker(text, speed=speed)
            self._track_and_start_worker(worker)
            return

        # Engine 3: Windows SAPI (Instant zero-dependency fallback)
        self.tts_started.emit()
        worker = TTSWorker(text)
        self._track_and_start_worker(worker, is_sapi=True)

    def _track_and_start_worker(self, worker, is_sapi: bool = False):
        self._active_tts_worker = worker
        self._tracked_workers.append(worker)

        if is_sapi:
            worker.finished.connect(lambda: self._on_worker_completed(worker))
            worker.error.connect(lambda err: self._on_worker_completed(worker))
        else:
            worker.chunk_ready.connect(lambda samples, sr, t: self.playback.queue_chunk(samples, sr))
            worker.generation_finished.connect(lambda: self._on_worker_completed(worker))
            worker.generation_stopped.connect(lambda: self._on_worker_completed(worker))
            worker.error_occurred.connect(lambda err: self._on_worker_completed(worker))

        worker.finished.connect(lambda: self._cleanup_worker(worker))
        worker.start()

    def _on_worker_completed(self, worker):
        if self._active_tts_worker is worker:
            self._active_tts_worker = None
            self._is_synthesizing = False

            # If more sentences are queued, process next sentence
            if self._speech_queue:
                next_text, next_voice, next_speed = self._speech_queue.pop(0)
                self._start_worker(next_text, voice=next_voice, speed=next_speed)

    def _on_playback_finished(self):
        # Playback has exhausted all audio chunks in the output buffer
        if not self._is_synthesizing and not self._speech_queue:
            self.tts_finished.emit()

    def _cleanup_worker(self, worker):
        # Safely remove finished worker from reference tracker
        if worker in self._tracked_workers:
            self._tracked_workers.remove(worker)
        try:
            worker.deleteLater()
        except Exception:
            pass

    def _cancel_running_workers(self):
        if self._active_tts_worker and self._active_tts_worker.isRunning():
            if hasattr(self._active_tts_worker, "cancel"):
                self._active_tts_worker.cancel()
            self._active_tts_worker.quit()
            # Reference stays in self._tracked_workers until finished signal fires!

    def stop_speaking(self):
        """Immediately interrupts speech generation and cuts audio output."""
        self._speech_queue.clear()
        self._is_synthesizing = False
        self._cancel_running_workers()
        self._active_tts_worker = None
        self.playback.stop()
        self.tts_finished.emit()

    def cleanup(self):
        """Cleanly halts all speech synthesis workers and audio streams on app shutdown."""
        self.stop_speaking()
        for worker in list(self._tracked_workers):
            if worker.isRunning():
                try:
                    worker.wait(400)
                except Exception:
                    pass
        self._tracked_workers.clear()
        if hasattr(self, "voice_input"):
            self.voice_input.stop_listening()
        if hasattr(self, "stt"):
            self.stt.cleanup()


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
