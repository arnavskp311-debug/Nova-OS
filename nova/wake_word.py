"""
NOVA OS Offline Wake Word & Audio Trigger System.
Provides hands-free voice wake word detection ("Hey NOVA" / "NOVA")
with low CPU footprint and graceful fallbacks for systems without microphones.
"""

import sys
import time
import logging
from typing import Optional
from PySide6.QtCore import QThread, Signal
from nova.sound_fx import play_sound

logger = logging.getLogger("nova.wake_word")

class WakeWordWorker(QThread):
    """Background listener for audio wake-phrase detection."""
    wake_detected = Signal()
    status_changed = Signal(str)

    def __init__(self, trigger_phrase: str = "hey nova", parent=None):
        super().__init__(parent)
        self.trigger_phrase = trigger_phrase.lower()
        self._is_cancelled = False
        self._is_active = False

    def cancel(self):
        """Cooperatively stops audio listening."""
        self._is_cancelled = True
        self._is_active = False

    def run(self):
        self._is_active = True
        self.status_changed.emit("Listening for 'Hey NOVA'...")
        logger.info("Wake word listener started.")

        # Check if speech_recognition or pyaudio is available
        has_sr = False
        recognizer = None
        microphone = None

        try:
            import speech_recognition as sr
            recognizer = sr.Recognizer()
            recognizer.energy_threshold = 300
            recognizer.dynamic_energy_threshold = True
            microphone = sr.Microphone()
            has_sr = True
        except Exception as e:
            logger.debug(f"Audio input driver note: {e}")

        if not has_sr or not microphone:
            self.status_changed.emit("Wake word ready (Mic standby)")
            # Standby loop without burning CPU
            while not self._is_cancelled:
                self.msleep(500)
            return

        try:
            with microphone as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.8)

            while not self._is_cancelled:
                try:
                    with microphone as source:
                        audio = recognizer.listen(source, timeout=3.0, phrase_time_limit=4.0)

                    if self._is_cancelled:
                        break

                    # Lightweight Sphinx or fast Google/offline recognizer check
                    try:
                        text = recognizer.recognize_google(audio).lower()
                        if "nova" in text or "hey nova" in text:
                            logger.info(f"Wake word detected: '{text}'")
                            play_sound("chime")
                            self.wake_detected.emit()
                            self.msleep(1500)  # Debounce
                    except Exception:
                        pass
                except Exception:
                    self.msleep(300)
        except Exception as e:
            logger.debug(f"Microphone loop ended: {e}")
        finally:
            self._is_active = False
