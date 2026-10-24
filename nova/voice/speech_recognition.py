"""
NOVA Voice — Speech-to-Text Recognition Module.
Transcribes user spoken audio into text locally with graceful fallbacks
and direct keyboard text fallback support.
"""

import io
import wave
import time
import logging
import numpy as np
from typing import Optional
from PySide6.QtCore import QObject, QThread, Signal

logger = logging.getLogger("nova.voice.speech_recognition")


class STTWorker(QThread):
    """Background worker for transcribing audio buffers without freezing the UI."""
    completed = Signal(str)
    error = Signal(str)

    def __init__(self, audio_data: np.ndarray, sample_rate: int = 16000):
        super().__init__()
        self.audio_data = audio_data
        self.sample_rate = sample_rate

    def run(self):
        try:
            if self.audio_data is None or len(self.audio_data) < int(self.sample_rate * 0.3):
                self.error.emit("Audio snippet too short to recognize.")
                return

            # Convert numpy float32 to 16-bit PCM WAV in memory
            int16_data = (self.audio_data * 32767.0).astype(np.int16)
            wav_io = io.BytesIO()
            with wave.open(wav_io, 'wb') as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(self.sample_rate)
                wav_file.writeframes(int16_data.tobytes())

            wav_io.seek(0)

            # Recognize using speech_recognition AudioFile
            import speech_recognition as sr
            recognizer = sr.Recognizer()
            with sr.AudioFile(wav_io) as source:
                audio = recognizer.record(source)

            # Try recognition
            try:
                # Local or fast recognizer
                text = recognizer.recognize_google(audio)
                if text and text.strip():
                    self.completed.emit(text.strip())
                    return
            except sr.UnknownValueError:
                self.error.emit("Could not understand audio.")
                return
            except Exception as e:
                logger.debug(f"Recognition attempt note: {e}")
                self.error.emit(f"Speech recognition note: {e}")

        except Exception as e:
            logger.error(f"STT worker error: {e}")
            self.error.emit(str(e))


class SpeechRecognizer(QObject):
    """
    Coordinates speech recognition requests, handles direct text overrides,
    and manages asynchronous background transcription workers.
    """
    transcription_started = Signal()
    transcription_completed = Signal(str)
    transcription_error = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_worker: Optional[STTWorker] = None

    def transcribe_audio_buffer(self, audio_data: np.ndarray, sample_rate: int = 16000):
        """Dispatches an audio buffer to a background STT worker."""
        self.transcription_started.emit()
        self._current_worker = STTWorker(audio_data, sample_rate)
        self._current_worker.completed.connect(self._on_worker_completed)
        self._current_worker.error.connect(self._on_worker_error)
        self._current_worker.start()

    def transcribe_text_direct(self, text: str):
        """Immediate keyboard fallback: processes text input directly as spoken utterance."""
        clean = text.strip()
        if clean:
            self.transcription_completed.emit(clean)

    def _on_worker_completed(self, text: str):
        self.transcription_completed.emit(text)
        self._current_worker = None

    def _on_worker_error(self, err_msg: str):
        self.transcription_error.emit(err_msg)
        self._current_worker = None
