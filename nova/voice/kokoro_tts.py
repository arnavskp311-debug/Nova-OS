"""
NOVA Voice — Kokoro-82M Primary Text-to-Speech Engine.
Integrates Kokoro-82M ONNX model for natural, expressive, chunked neural speech synthesis.
Optimized for low-RAM Windows 11 execution on Intel Core i3.
License: Apache 2.0
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
from typing import List, Dict, Any, Optional, Generator, Tuple
from PySide6.QtCore import QObject, QThread, Signal

from nova.config import BASE_DIR

logger = logging.getLogger("nova.voice.kokoro_tts")

DEFAULT_KOKORO_DIR = BASE_DIR / "data" / "models" / "kokoro"
DEFAULT_CACHE_DIR = BASE_DIR / "data" / "audio_cache" / "kokoro"

# Priority English voices available in Kokoro-82M
RECOMMENDED_VOICES = [
    ("af_nova", "NOVA Voice (Neural Female - Balanced)", "American"),
    ("af_heart", "Heart (Warm & Natural Female)", "American"),
    ("af_bella", "Bella (Dynamic Expressive Female)", "American"),
    ("af_sarah", "Sarah (Professional Female)", "American"),
    ("am_adam", "Adam (Confident Deep Male)", "American"),
    ("am_michael", "Michael (Calm Informative Male)", "American"),
    ("bf_emma", "Emma (Polished British Female)", "British"),
    ("bm_george", "George (Distinguished British Male)", "British"),
]


class KokoroChunkWorker(QThread):
    """
    Background worker that synthesizes text chunks using Kokoro-82M
    and emits audio chunks as soon as each chunk is generated.
    """
    chunk_ready = Signal(object, int, str)  # np.ndarray, sample_rate, chunk_text
    generation_finished = Signal()
    generation_stopped = Signal()
    error_occurred = Signal(str)

    def __init__(self, kokoro_engine, text: str, voice: str = "af_nova", speed: float = 1.0):
        super().__init__()
        self.engine = kokoro_engine
        self.text = text
        self.voice = voice
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

                samples, sr = self.engine.synthesize_text_chunk(
                    chunk_text,
                    voice=self.voice,
                    speed=self.speed
                )

                if self._is_cancelled:
                    self.generation_stopped.emit()
                    return

                if samples is not None and len(samples) > 0:
                    self.chunk_ready.emit(samples, sr, chunk_text)

            if not self._is_cancelled:
                self.generation_finished.emit()
        except Exception as e:
            logger.error(f"Kokoro chunk generation error: {e}")
            self.error_occurred.emit(str(e))


class KokoroTTSEngine(QObject):
    """
    Kokoro-82M Neural Speech Engine wrapper using ONNX Runtime.
    Manages lazy model loading, sentence chunking, caching, and benchmarks.
    """
    model_loaded = Signal(bool, str)

    def __init__(self, model_dir: Optional[Path] = None, cache_dir: Optional[Path] = None, parent=None):
        super().__init__(parent)
        self.model_dir = Path(model_dir) if model_dir else DEFAULT_KOKORO_DIR
        self.cache_dir = Path(cache_dir) if cache_dir else DEFAULT_CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.kokoro = None
        self._is_loading = False
        self._load_lock = threading.Lock()
        self.default_voice = "af_nova"
        self.speed = 1.0
        self.sample_rate = 24000
        self.enable_cache = True

    @property
    def is_model_available(self) -> bool:
        """Checks if Kokoro ONNX model and voices file are present on disk."""
        model_file = self._get_model_path()
        voices_file = self.model_dir / "voices-v1.0.bin"
        return (model_file is not None and model_file.exists() and voices_file.exists())

    def _get_model_path(self) -> Optional[Path]:
        """Prefers int8 quantized model for Core i3 / 4 GB RAM, with fp16/fp32 fallback."""
        for candidate in ["kokoro-v1.0.int8.onnx", "kokoro-v1.0.fp16.onnx", "kokoro-v1.0.onnx", "kokoro-v0_19.onnx"]:
            p = self.model_dir / candidate
            if p.exists() and p.stat().st_size > 1000:
                return p
        return None

    def load_model(self) -> bool:
        """Loads Kokoro-82M ONNX model into memory if not already loaded."""
        with self._load_lock:
            if self.kokoro is not None:
                return True

            model_path = self._get_model_path()
            voices_path = self.model_dir / "voices-v1.0.bin"

            if not model_path or not model_path.exists():
                err = f"Kokoro ONNX model not found in {self.model_dir}"
                logger.warning(err)
                self.model_loaded.emit(False, err)
                return False

            if not voices_path.exists():
                err = f"Kokoro voices-v1.0.bin not found in {self.model_dir}"
                logger.warning(err)
                self.model_loaded.emit(False, err)
                return False

            try:
                from kokoro_onnx import Kokoro
                t0 = time.perf_counter()
                self.kokoro = Kokoro(str(model_path), str(voices_path))
                load_time = (time.perf_counter() - t0) * 1000
                logger.info(f"Loaded Kokoro-82M ({model_path.name}) in {load_time:.1f}ms")
                self.model_loaded.emit(True, f"Kokoro-82M loaded in {load_time:.0f}ms")
                return True
            except Exception as e:
                logger.error(f"Failed to load Kokoro-82M: {e}")
                self.model_loaded.emit(False, str(e))
                return False

    def get_available_voices(self) -> List[str]:
        """Returns list of voice IDs available in Kokoro voices file."""
        if self.kokoro:
            try:
                return self.kokoro.get_voices()
            except Exception:
                pass
        return [v[0] for v in RECOMMENDED_VOICES]

    def split_text_into_sentences(self, text: str) -> List[str]:
        """
        Splits long responses into speech chunks at natural punctuation pauses
        so audio playback can begin as soon as chunk 1 is ready.
        """
        clean_text = text.strip()
        if not clean_text:
            return []

        # Split on sentence terminals while keeping punctuation
        pattern = r'(?<=[.!?;\n])\s+'
        raw_chunks = re.split(pattern, clean_text)
        chunks = []
        current = ""

        for part in raw_chunks:
            part = part.strip()
            if not part:
                continue
            # If current is very short (< 20 chars), combine with next part for better prosody
            if len(current) > 0 and len(current) < 25:
                current += " " + part
            else:
                if current:
                    chunks.append(current)
                current = part

        if current:
            chunks.append(current)

        return chunks if chunks else [clean_text]

    def synthesize_text_chunk(self, text: str, voice: Optional[str] = None, speed: Optional[float] = None) -> Tuple[Optional[np.ndarray], int]:
        """
        Synthesizes a single chunk of text into a numpy float32 audio array.
        Uses audio cache if enabled.
        """
        target_voice = voice or self.default_voice
        target_speed = speed or self.speed

        # Check audio disk cache
        cache_key = self._get_cache_key(text, target_voice, target_speed)
        cache_file = self.cache_dir / f"{cache_key}.npy"

        if self.enable_cache and cache_file.exists():
            try:
                samples = np.load(cache_file)
                return samples, self.sample_rate
            except Exception:
                pass

        # Load model on demand if needed
        if self.kokoro is None:
            if not self.load_model():
                raise RuntimeError("Kokoro-82M model could not be loaded.")

        # Ensure selected voice exists, or fallback
        avail = self.get_available_voices()
        if target_voice not in avail:
            target_voice = "af_nova" if "af_nova" in avail else (avail[0] if avail else "af_heart")

        samples, sr = self.kokoro.create(
            text,
            voice=target_voice,
            speed=target_speed,
            lang="en-us"
        )
        self.sample_rate = sr

        # Cache generated samples
        if self.enable_cache:
            try:
                np.save(cache_file, samples)
            except Exception as e:
                logger.debug(f"Audio cache write error: {e}")

        return samples, sr

    def create_stream_worker(self, text: str, voice: Optional[str] = None, speed: Optional[float] = None) -> KokoroChunkWorker:
        """Creates a background worker thread that emits audio chunks as generated."""
        return KokoroChunkWorker(
            self,
            text=text,
            voice=voice or self.default_voice,
            speed=speed or self.speed
        )

    def _get_cache_key(self, text: str, voice: str, speed: float) -> str:
        """Generates a stable cache key based on text, voice, and speed."""
        raw = f"{text.strip()}|{voice}|{speed:.2f}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]

    def clear_cache(self) -> int:
        """Clears all cached Kokoro audio files from disk."""
        deleted = 0
        if self.cache_dir.exists():
            for f in self.cache_dir.glob("*.npy"):
                try:
                    f.unlink()
                    deleted += 1
                except Exception:
                    pass
        return deleted

    def get_cache_size_mb(self) -> float:
        """Returns total size of cached audio in MB."""
        total_bytes = 0
        if self.cache_dir.exists():
            for f in self.cache_dir.glob("*.npy"):
                try:
                    total_bytes += f.stat().st_size
                except Exception:
                    pass
        return round(total_bytes / (1024 * 1024), 2)

    def benchmark(self, sample_text: str = "Hello. I am NOVA Voice, running on Kokoro 82M.") -> Dict[str, Any]:
        """
        Executes a real-device benchmark measuring model load time, peak RAM,
        synthesis latency, and Real-Time Factor (RTF).
        """
        proc = psutil.Process()
        mem_start = proc.memory_info().rss / (1024 * 1024)

        t0 = time.perf_counter()
        loaded = self.load_model()
        t_load = (time.perf_counter() - t0) * 1000
        mem_after_load = proc.memory_info().rss / (1024 * 1024)

        if not loaded:
            return {"status": "error", "message": "Failed to load Kokoro-82M model"}

        # Measure single sentence generation
        t1 = time.perf_counter()
        samples, sr = self.synthesize_text_chunk(sample_text, voice=self.default_voice, speed=1.0)
        t_gen = (time.perf_counter() - t1) * 1000
        mem_after_gen = proc.memory_info().rss / (1024 * 1024)

        audio_duration = len(samples) / sr if (samples is not None and sr > 0) else 0.0
        rtf = (t_gen / 1000.0) / audio_duration if audio_duration > 0 else 0.0

        return {
            "status": "success",
            "model_variant": self._get_model_path().name if self._get_model_path() else "Unknown",
            "model_load_ms": round(t_load, 1),
            "generation_latency_ms": round(t_gen, 1),
            "audio_duration_sec": round(audio_duration, 2),
            "real_time_factor": round(rtf, 3),
            "ram_load_delta_mb": round(mem_after_load - mem_start, 1),
            "peak_process_ram_mb": round(mem_after_gen, 1),
            "sample_rate_hz": sr,
            "license": "Apache 2.0"
        }
