"""
NOVA OS Cybernetic Sound Synthesizer.
Programmatic sci-fi UI sound generation and asynchronous playback.
Generates futuristic auditory cues purely in-memory with zero external assets.
"""

import sys
import math
import struct
import io
import wave
import threading
import logging
from typing import Dict, Optional

logger = logging.getLogger("nova.sound_fx")

class SoundFXEngine:
    """Synthesizes and plays lightweight cyber UI sound cues."""

    def __init__(self):
        self._cache: Dict[str, bytes] = {}
        self._enabled = True
        self._is_windows = sys.platform == "win32"
        self._pregenerate_sounds()

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool):
        self._enabled = bool(value)

    def _create_wav_bytes(self, samples: list, sample_rate: int = 22050) -> bytes:
        """Encodes float samples (-1.0 to 1.0) into 16-bit PCM WAV bytes."""
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(sample_rate)
            # Pack samples as 16-bit signed integers
            int_samples = [max(-32767, min(32767, int(s * 32767))) for s in samples]
            data = struct.pack(f"<{len(int_samples)}h", *int_samples)
            wav_file.writeframes(data)
        return buffer.getvalue()

    def _synth_click(self) -> bytes:
        """Crisp mechanical micro-click (12ms)."""
        sr = 22050
        duration = 0.012
        total_samples = int(sr * duration)
        samples = []
        for i in range(total_samples):
            t = i / sr
            # Sharp 1200Hz tick with fast exponential decay
            env = math.exp(-t * 400)
            val = math.sin(2 * math.pi * 1200 * t) * env * 0.4
            samples.append(val)
        return self._create_wav_bytes(samples, sr)

    def _synth_terminal_blip(self) -> bytes:
        """Futuristic pitch-shifted cyber blip (45ms)."""
        sr = 22050
        duration = 0.045
        total_samples = int(sr * duration)
        samples = []
        for i in range(total_samples):
            t = i / sr
            freq = 900 + (1.0 - t / duration) * 600  # Sweeps down from 1500Hz to 900Hz
            env = math.exp(-t * 70)
            val = math.sin(2 * math.pi * freq * t) * env * 0.35
            samples.append(val)
        return self._create_wav_bytes(samples, sr)

    def _synth_notification_chime(self) -> bytes:
        """Futuristic dual-harmonic transmission chime (180ms)."""
        sr = 22050
        duration = 0.18
        total_samples = int(sr * duration)
        samples = []
        for i in range(total_samples):
            t = i / sr
            env = math.exp(-t * 18)
            # Chord: C5 (523Hz) + G5 (784Hz) + C6 (1046Hz)
            v1 = math.sin(2 * math.pi * 523.25 * t) * 0.3
            v2 = math.sin(2 * math.pi * 783.99 * t) * 0.2
            v3 = math.sin(2 * math.pi * 1046.50 * t) * 0.15
            samples.append((v1 + v2 + v3) * env)
        return self._create_wav_bytes(samples, sr)

    def _synth_success_cue(self) -> bytes:
        """Ascending high-tech confirmation triad (220ms)."""
        sr = 22050
        samples = []
        notes = [659.25, 830.61, 987.77]  # E5, G#5, B5 (Major triad)
        note_dur = 0.07
        for note_freq in notes:
            n_samples = int(sr * note_dur)
            for i in range(n_samples):
                t = i / sr
                env = math.exp(-t * 22)
                samples.append(math.sin(2 * math.pi * note_freq * t) * env * 0.3)
        return self._create_wav_bytes(samples, sr)

    def _synth_alert_cue(self) -> bytes:
        """Subtle futuristic caution chirp (90ms)."""
        sr = 22050
        duration = 0.09
        total_samples = int(sr * duration)
        samples = []
        for i in range(total_samples):
            t = i / sr
            freq = 440 if t < 0.045 else 330
            env = 0.3 * (1.0 - (t / duration) ** 2)
            samples.append(math.sin(2 * math.pi * freq * t) * env)
        return self._create_wav_bytes(samples, sr)

    def _pregenerate_sounds(self):
        """Generates all sound byte arrays into memory on initialization."""
        try:
            self._cache["click"] = self._synth_click()
            self._cache["blip"] = self._synth_terminal_blip()
            self._cache["chime"] = self._synth_notification_chime()
            self._cache["success"] = self._synth_success_cue()
            self._cache["alert"] = self._synth_alert_cue()
        except Exception as e:
            logger.error(f"Error pre-generating sound effects: {e}")

    def get_wav_bytes(self, sound_name: str) -> Optional[bytes]:
        """Returns the in-memory WAV byte stream for a sound cue."""
        return self._cache.get(sound_name)

    def play(self, sound_name: str):
        """Asynchronously plays an in-memory sound cue."""
        if not self._enabled:
            return

        data = self._cache.get(sound_name)
        if not data:
            return

        if self._is_windows:
            try:
                import winsound
                # SND_MEMORY (0x0004) | SND_ASYNC (0x0001) | SND_NODEFAULT (0x0002)
                winsound.PlaySound(data, winsound.SND_MEMORY | winsound.SND_ASYNC | winsound.SND_NODEFAULT)
            except Exception as e:
                logger.debug(f"Winsound playback note: {e}")
        else:
            # Fallback thread for non-Windows test environments
            def _play_dummy():
                pass
            threading.Thread(target=_play_dummy, daemon=True).start()

_sound_engine_instance = None

def get_sound_engine() -> SoundFXEngine:
    global _sound_engine_instance
    if _sound_engine_instance is None:
        _sound_engine_instance = SoundFXEngine()
    return _sound_engine_instance

def play_sound(sound_name: str):
    """Global helper to play a sound cue."""
    get_sound_engine().play(sound_name)
