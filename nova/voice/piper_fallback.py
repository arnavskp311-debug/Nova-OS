"""
NOVA Voice — Lightweight Local Piper TTS Fallback Engine.
Provides ultra-fast local neural speech synthesis for low-resource hardware (Core i3 / 4 GB RAM).
License: MIT
"""

import os
import re
import time
import hashlib
import psutil
import logging
import threading
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from PySide6.QtCore import QObject, QThread, Signal

from nova.config import BASE_DIR

logger = logging.getLogger("nova.voice.piper_fallback")

DEFAULT_PIPER_DIR = BASE_DIR / "data" / "models" / "piper"
DEFAULT_CACHE_DIR = BASE_DIR / "data" / "audio_cache" / "piper"


class PiperChunkWorker(QThread):
    """Background worker that synthesizes text chunks via Piper TTS."""
    chunk_ready = Signal(object, int, str)  # np.ndarray, sample_rate, chunk_text
    generation_finished = Signal()
    generation_stopped = Signal()
    error_occurred = Signal(str)

    def __init__(self, piper_engine, text: str, speed: float = 1.0, parent=None):
        super().__init__(parent)
        self.engine = piper_engine
        self.text = text
        self.speed = speed
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        try:
            chunks = self.engine.split_text_into_sentences(self.text)
            for chunk_text in chunks:
                if self._is_cancelled:
                    self.generation_stopped.emit()
                    return

                if not chunk_text.strip():
                    continue

                samples, sr = self.engine.synthesize_text_chunk(chunk_text, speed=self.speed)

                if self._is_cancelled:
                    self.generation_stopped.emit()
                    return

                if samples is not None and len(samples) > 0:
                    self.chunk_ready.emit(samples, sr, chunk_text)

            if not self._is_cancelled:
                self.generation_finished.emit()
        except Exception as e:
            logger.error(f"Piper chunk worker error: {e}")
            self.error_occurred.emit(str(e))


class PiperTTSEngine(QObject):
    """
    Lightweight local Piper TTS engine.
    Executes in ~0.2x real-time on Core i3 CPU with ~85 MB RAM.
    """
    model_loaded = Signal(bool, str)

    def __init__(self, model_dir: Optional[Path] = None, cache_dir: Optional[Path] = None, parent=None):
        super().__init__(parent)
        self.model_dir = Path(model_dir) if model_dir else DEFAULT_PIPER_DIR
        self.cache_dir = Path(cache_dir) if cache_dir else DEFAULT_CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.voice = None
        self._load_lock = threading.Lock()
        self.speed = 1.0
        self.sample_rate = 22050
        self.enable_cache = True

    @property
    def is_model_available(self) -> bool:
        """Checks if Piper ONNX model and config are present on disk."""
        model_file = self.model_dir / "en_US-lessac-medium.onnx"
        config_file = self.model_dir / "en_US-lessac-medium.onnx.json"
        return (model_file.exists() and config_file.exists())

    def load_model(self) -> bool:
        with self._load_lock:
            if self.voice is not None:
                return True

            model_file = self.model_dir / "en_US-lessac-medium.onnx"
            config_file = self.model_dir / "en_US-lessac-medium.onnx.json"

            if not model_file.exists() or not config_file.exists():
                err = f"Piper model files missing in {self.model_dir}"
                self.model_loaded.emit(False, err)
                return False

            try:
                from piper import PiperVoice
                t0 = time.perf_counter()
                self.voice = PiperVoice.load(str(model_file), config_path=str(config_file))
                self.sample_rate = self.voice.config.sample_rate
                load_time = (time.perf_counter() - t0) * 1000
                logger.info(f"Loaded Piper TTS in {load_time:.1f}ms")
                self.model_loaded.emit(True, f"Piper TTS loaded in {load_time:.0f}ms")
                return True
            except Exception as e:
                logger.error(f"Piper load error: {e}")
                self.model_loaded.emit(False, str(e))
                return False

    def split_text_into_sentences(self, text: str) -> List[str]:
        clean_text = text.strip()
        if not clean_text:
            return []
        pattern = r'(?<=[.!?;\n])\s+'
        raw = re.split(pattern, clean_text)
        return [r.strip() for r in raw if r.strip()]

    def synthesize_text_chunk(self, text: str, speed: Optional[float] = None) -> Tuple[Optional[np.ndarray], int]:
        target_speed = speed or self.speed
        cache_key = hashlib.sha256(f"{text}|{target_speed:.2f}".encode("utf-8")).hexdigest()[:24]
        cache_file = self.cache_dir / f"{cache_key}.npy"

        if self.enable_cache and cache_file.exists():
            try:
                samples = np.load(cache_file)
                return samples, self.sample_rate
            except Exception:
                pass

        if self.voice is None:
            if not self.load_model():
                raise RuntimeError("Piper TTS model could not be loaded.")

        # Synthesize audio chunks and combine
        audio_chunks = []
        for chunk in self.voice.synthesize(text):
            audio_chunks.append(chunk.audio_int16_bytes)

        if not audio_chunks:
            return None, self.sample_rate

        raw_bytes = b"".join(audio_chunks)
        samples = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32) / 32768.0

        if self.enable_cache:
            try:
                np.save(cache_file, samples)
            except Exception:
                pass

        return samples, self.sample_rate

    def create_stream_worker(self, text: str, speed: Optional[float] = None) -> PiperChunkWorker:
        return PiperChunkWorker(self, text=text, speed=speed or self.speed, parent=self)

    def clear_cache(self) -> int:
        deleted = 0
        if self.cache_dir.exists():
            for f in self.cache_dir.glob("*.npy"):
                try:
                    f.unlink()
                    deleted += 1
                except Exception:
                    pass
        return deleted

    def benchmark(self, sample_text: str = "Hello. I am NOVA Voice, running on Piper TTS.") -> Dict[str, Any]:
        proc = psutil.Process()
        mem_start = proc.memory_info().rss / (1024 * 1024)

        t0 = time.perf_counter()
        loaded = self.load_model()
        t_load = (time.perf_counter() - t0) * 1000
        mem_after_load = proc.memory_info().rss / (1024 * 1024)

        if not loaded:
            return {"status": "error", "message": "Failed to load Piper TTS model"}

        t1 = time.perf_counter()
        samples, sr = self.synthesize_text_chunk(sample_text)
        t_gen = (time.perf_counter() - t1) * 1000
        mem_after_gen = proc.memory_info().rss / (1024 * 1024)

        audio_duration = len(samples) / sr if (samples is not None and sr > 0) else 0.0
        rtf = (t_gen / 1000.0) / audio_duration if audio_duration > 0 else 0.0

        return {
            "status": "success",
            "model_variant": "Piper en_US-lessac-medium",
            "model_load_ms": round(t_load, 1),
            "generation_latency_ms": round(t_gen, 1),
            "audio_duration_sec": round(audio_duration, 2),
            "real_time_factor": round(rtf, 3),
            "ram_load_delta_mb": round(mem_after_load - mem_start, 1),
            "peak_process_ram_mb": round(mem_after_gen, 1),
            "sample_rate_hz": sr,
            "license": "MIT"
        }
