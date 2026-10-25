"""
NOVA Voice — Audio Playback Manager.
Handles asynchronous, chunked audio playback with immediate interruption,
real-time amplitude emission for visual waveforms, and volume control.
"""

import time
import queue
import threading
import logging
import numpy as np
from typing import Optional, Union
from PySide6.QtCore import QObject, Signal

logger = logging.getLogger("nova.voice.audio_playback")

try:
    import sounddevice as sd
    SOUNDDEVICE_AVAILABLE = True
except Exception as e:
    logger.warning(f"sounddevice import warning: {e}")
    SOUNDDEVICE_AVAILABLE = False


class AudioPlaybackManager(QObject):
    """
    Manages non-blocking audio queue playback with immediate stop support.
    Emits real-time amplitude values to drive UI voice orb / waveform animations.
    """
    playback_started = Signal()
    playback_finished = Signal()
    playback_stopped = Signal()
    amplitude_updated = Signal(float)  # Normalized 0.0 - 1.0
    error_occurred = Signal(str)

    def __init__(self, default_sample_rate: int = 24000, parent=None):
        super().__init__(parent)
        self.default_sample_rate = default_sample_rate
        self.volume = 1.0
        self._queue = queue.Queue()
        self._stop_event = threading.Event()
        self._is_playing = False
        self._worker_thread: Optional[threading.Thread] = None
        self._current_stream = None
        self._lock = threading.Lock()

    @property
    def is_playing(self) -> bool:
        return self._is_playing

    def set_volume(self, volume: float):
        """Sets playback volume between 0.0 and 1.0."""
        self.volume = max(0.0, min(1.0, float(volume)))

    def queue_chunk(self, audio_data: Union[np.ndarray, bytes], sample_rate: Optional[int] = None):
        """
        Appends an audio chunk to the playback queue and begins playback if idle.
        Accepts numpy float32/int16 array or raw 16-bit PCM bytes.
        """
        if not SOUNDDEVICE_AVAILABLE:
            self.error_occurred.emit("sounddevice is not available on this system.")
            return

        sr = sample_rate or self.default_sample_rate

        # Convert bytes to numpy array if needed
        if isinstance(audio_data, bytes):
            audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
        elif isinstance(audio_data, np.ndarray):
            if audio_data.dtype == np.int16:
                audio_array = audio_data.astype(np.float32) / 32768.0
            elif audio_data.dtype == np.float32 or audio_data.dtype == np.float64:
                audio_array = audio_data.astype(np.float32)
            else:
                audio_array = audio_data.astype(np.float32)
        else:
            logger.warning(f"Unsupported audio data type: {type(audio_data)}")
            return

        # Ensure 1D mono
        if audio_array.ndim > 1:
            audio_array = audio_array.mean(axis=1)

        self._queue.put((audio_array, sr))

        with self._lock:
            if not self._is_playing:
                self._stop_event.clear()
                self._is_playing = True
                self._worker_thread = threading.Thread(target=self._playback_loop, daemon=True)
                self._worker_thread.start()

    def stop(self):
        """Immediately interrupts playback and flushes queued audio chunks."""
        self._stop_event.set()
        # Empty queue
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
                self._queue.task_done()
            except Exception:
                break

        # Stop active sounddevice stream if open
        try:
            if SOUNDDEVICE_AVAILABLE:
                sd.stop()
        except Exception as e:
            logger.debug(f"Error stopping sounddevice stream: {e}")

        with self._lock:
            if self._is_playing:
                self._is_playing = False
                self._safe_emit(self.playback_stopped)
                self._safe_emit(self.amplitude_updated, 0.0)

    def _safe_emit(self, signal, *args):
        """Safely emits a Qt signal without crashing if parent QObject is destroyed during shutdown."""
        try:
            signal.emit(*args)
        except (RuntimeError, AttributeError):
            pass

    def _playback_loop(self):
        """Background thread worker that sequentially plays audio chunks."""
        self._safe_emit(self.playback_started)
        last_sr = None

        while not self._stop_event.is_set():
            try:
                chunk, sr = self._queue.get(timeout=0.25)
            except queue.Empty:
                # No more audio queued
                break

            if self._stop_event.is_set():
                break

            try:
                # Apply volume multiplier
                if self.volume != 1.0:
                    chunk = chunk * self.volume

                # Calculate RMS amplitude for UI feedback
                if len(chunk) > 0:
                    rms = float(np.sqrt(np.mean(np.square(chunk))))
                    norm_amp = min(1.0, rms * 3.5)
                    self._safe_emit(self.amplitude_updated, norm_amp)

                # Play chunk synchronously on the worker thread
                sd.play(chunk, samplerate=sr, blocking=True)

                # Check for stop after chunk finishes
                if self._stop_event.is_set():
                    break

            except Exception as e:
                logger.warning(f"Audio device playback error: {e}")
                self._safe_emit(self.error_occurred, str(e))
                # If audio device query failed (-1), flush queue and exit loop gracefully
                while not self._queue.empty():
                    try:
                        self._queue.get_nowait()
                        self._queue.task_done()
                    except Exception:
                        break
                break
            finally:
                self._queue.task_done()

        with self._lock:
            was_playing = self._is_playing
            self._is_playing = False

        self._safe_emit(self.amplitude_updated, 0.0)
        if not self._stop_event.is_set() and was_playing:
            self._safe_emit(self.playback_finished)
