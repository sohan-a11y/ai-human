"""
Speech-to-Text — the agent can listen for voice commands.
Uses faster-whisper (offline, runs on CPU, any language) as primary.
Falls back to speech_recognition with Google STT if whisper unavailable.
Runs in a background thread, pushes recognized text to EventBus.
"""

from __future__ import annotations

import threading
import queue
from utils.logger import get_logger

log = get_logger(__name__)


class STT:
    """
    Listens to the microphone and emits recognized text.
    Usage:
        stt = STT()
        stt.start(callback=lambda text: agent.set_goal(text))
        stt.stop()
    """

    def __init__(self):
        self._running = False
        self._thread: threading.Thread | None = None
        self._callback = None
        self._method = self._detect_method()

    def _detect_method(self) -> str:
        try:
            import faster_whisper
            log.info("STT: using faster-whisper (offline)")
            return "whisper"
        except ImportError:
            pass
        try:
            import speech_recognition
            log.info("STT: using SpeechRecognition (Google online)")
            return "google"
        except ImportError:
            pass
        log.warning("No STT available. Install: pip install faster-whisper")
        return "none"

    def start(self, callback) -> None:
        """Start listening in background. callback(text) called on each utterance."""
        if self._method == "none":
            return
        self._callback = callback
        self._running = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True, name="STT")
        self._thread.start()

    def stop(self) -> None:
        self._running = False

    def _listen_loop(self) -> None:
        if self._method == "whisper":
            self._whisper_loop()
        elif self._method == "google":
            self._google_loop()

    def _whisper_loop(self) -> None:
        try:
            import sounddevice as sd
            import numpy as np
            from faster_whisper import WhisperModel

            model = WhisperModel("tiny", device="cpu", compute_type="int8")
            log.info("Whisper tiny model loaded (39 MB, runs offline)")

            sample_rate = 16000
            chunk_seconds = 5

            while self._running:
                audio = sd.rec(
                    int(chunk_seconds * sample_rate),
                    samplerate=sample_rate,
                    channels=1,
                    dtype="float32",
                )
                sd.wait()
                audio_flat = audio.flatten()

                segments, _ = model.transcribe(audio_flat, language=None)
                text = " ".join(seg.text for seg in segments).strip()
                if text and self._callback:
                    log.info(f"STT heard: {text}")
                    self._callback(text)

        except Exception as e:
            log.error(f"Whisper STT failed: {e}")

    def _google_loop(self) -> None:
        try:
            import speech_recognition as sr
            r = sr.Recognizer()
            mic = sr.Microphone()

            with mic as source:
                r.adjust_for_ambient_noise(source)

            while self._running:
                with mic as source:
                    try:
                        audio = r.listen(source, timeout=5, phrase_time_limit=10)
                        text = r.recognize_google(audio)
                        if text and self._callback:
                            log.info(f"STT heard: {text}")
                            self._callback(text)
                    except sr.WaitTimeoutError:
                        pass
                    except sr.UnknownValueError:
                        pass
                    except Exception as e:
                        log.debug(f"STT error: {e}")

        except Exception as e:
            log.error(f"Google STT failed: {e}")
