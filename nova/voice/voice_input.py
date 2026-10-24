"""
NOVA Voice — Microphone Audio Capture & Voice Activity Detection (VAD).
Captures microphone input, calculates real-time RMS amplitude for UI orb feedback,
detects user speech pauses, and prevents acoustic echo during speaker playback.
"""

import time
import queue
import logging
import threading
import numpy as np
from typing import Optional, Callable
from PySide6.QtCore import QObject, QTimer, Signal

logger = logging.getLogger("nova.voice.voice_input")

try:
    import sounddevice as sd
    SOUNDDEVICE_AVAILABLE = True
except Exception:
    SOUNDDEVICE_AVAILABLE = False


class VoiceInputManager(QObject):
    """
    Manages microphone stream capture, live audio amplitude calculation,
    speech detection, and push-to-talk / hands-free mode.
    """
    amplitude_updated = Signal(float)  # 0.0 to 1.0 (for UI orb pulse)
    speech_started = Signal()
    speech_ended = Signal(object)      # Emits recorded np.ndarray audio chunk
    listening_state_changed = Signal(bool)
    permission_status_changed = Signal(bool, str)

    def __init__(self, sample_rate: int = 16000, parent=None):
        super().__init__(parent)
        self.sample_rate = sample_rate
        self.is_muted = False
        self.is_listening = False
        self.is_suppressed = False      # True when NOVA is actively speaking (echo prevention)
        self.vad_threshold = 0.015     # Minimum RMS energy to register user speech
        self.silence_timeout = 1.2     # Seconds of silence after speech to trigger speech_ended

        self._stream: Optional[sd.InputStream] = None
        self._audio_buffer = []
        self._is_speaking_now = False
        self._last_speech_time = 0.0
        self._lock = threading.Lock()

    @property
    def has_microphone(self) -> bool:
        """Checks if at least one audio input device is available."""
        if not SOUNDDEVICE_AVAILABLE:
            return False
        try:
            devs = sd.query_devices()
            for d in devs:
                if d.get("max_input_channels", 0) > 0:
                    return True
            return False
        except Exception:
            return False

    def toggle_mute(self) -> bool:
        """Toggles microphone mute status."""
        self.is_muted = not self.is_muted
        if self.is_muted and self.is_listening:
            self.stop_listening()
        return self.is_muted

    def set_suppressed(self, suppressed: bool):
        """Suppresses mic processing while NOVA is outputting speaker audio (echo prevention)."""
        self.is_suppressed = suppressed

    def start_listening(self) -> bool:
        """Starts recording from default microphone."""
        if not SOUNDDEVICE_AVAILABLE:
            self.permission_status_changed.emit(False, "sounddevice library unavailable")
            return False

        if not self.has_microphone:
            self.permission_status_changed.emit(False, "No microphone detected on this PC")
            return False

        if self.is_muted:
            self.permission_status_changed.emit(False, "Microphone is currently muted")
            return False

        with self._lock:
            if self.is_listening:
                return True

            try:
                self._audio_buffer.clear()
                self._is_speaking_now = False
                self._last_speech_time = time.time()

                self._stream = sd.InputStream(
                    samplerate=self.sample_rate,
                    channels=1,
                    dtype='float32',
                    blocksize=int(self.sample_rate * 0.05),  # 50ms blocks
                    callback=self._audio_callback
                )
                self._stream.start()
                self.is_listening = True
                self.listening_state_changed.emit(True)
                self.permission_status_changed.emit(True, "Microphone active")
                return True
            except Exception as e:
                logger.error(f"Error starting mic stream: {e}")
                self.permission_status_changed.emit(False, str(e))
                return False

    def stop_listening(self) -> Optional[np.ndarray]:
        """Stops recording from microphone and returns accumulated audio buffer."""
        with self._lock:
            if not self.is_listening:
                return None

            self.is_listening = False
            try:
                if self._stream:
                    self._stream.stop()
                    self._stream.close()
                    self._stream = None
            except Exception as e:
                logger.debug(f"Error stopping stream: {e}")

            self.amplitude_updated.emit(0.0)
            self.listening_state_changed.emit(False)

            if self._audio_buffer:
                full_audio = np.concatenate(self._audio_buffer)
                self._audio_buffer.clear()
                return full_audio
            return None

    def _audio_callback(self, indata, frames, time_info, status):
        """Processes 50ms audio blocks in real time."""
        if not self.is_listening or self.is_muted or self.is_suppressed:
            self.amplitude_updated.emit(0.0)
            return

        chunk = indata[:, 0]
        rms = float(np.sqrt(np.mean(np.square(chunk))))
        norm_amp = min(1.0, rms * 8.0)
        self.amplitude_updated.emit(norm_amp)

        now = time.time()
        if rms >= self.vad_threshold:
            # User is speaking
            if not self._is_speaking_now:
                self._is_speaking_now = True
                self.speech_started.emit()
            self._last_speech_time = now
            self._audio_buffer.append(chunk.copy())
        elif self._is_speaking_now:
            # Silence detected after speech
            self._audio_buffer.append(chunk.copy())
            if now - self._last_speech_time > self.silence_timeout:
                # User finished turn
                self._is_speaking_now = False
                if self._audio_buffer:
                    recorded_audio = np.concatenate(self._audio_buffer)
                    self._audio_buffer.clear()
                    self.speech_ended.emit(recorded_audio)
