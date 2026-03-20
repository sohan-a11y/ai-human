"""
Wake Word Detector — listens for a configurable trigger phrase ("Hey AI")
and fires a callback when detected.

Three detection backends in order of preference:
1. OpenWakeWord (best offline accuracy, pip install openwakeword)
2. Vosk (offline speech recognition, pip install vosk + model download)
3. faster-whisper (transcribes mic chunks, matches keyword — pip install faster-whisper)

All backends are offline and run on CPU — no cloud APIs required.
"""

from __future__ import annotations
import threading
import time
from typing import Callable, Optional
from utils.logger import get_logger

log = get_logger(__name__)


class WakeWordDetector:
    """
    Listens for a wake word in the background.
    Call start(callback) to begin listening.
    callback() is called (in a separate thread) when the wake word is heard.
    """

    def __init__(
        self,
        wake_word: str = "hey ai",
        sensitivity: float = 0.6,
        sample_rate: int = 16000,
    ):
        self._wake_word = wake_word.lower().strip()
        self._sensitivity = sensitivity
        self._sample_rate = sample_rate
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._callback: Optional[Callable] = None

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self, callback: Callable) -> None:
        """Start listening in background. callback() fired on detection."""
        if self._running:
            return
        self._callback = callback
        self._running = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()
        log.info(f"Wake word detector started. Listening for: '{self._wake_word}'")

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        log.info("Wake word detector stopped")

    def _listen_loop(self) -> None:
        """Try backends in order until one works."""
        if self._try_openwakeword():
            return
        if self._try_vosk():
            return
        if self._try_whisper():
            return
        log.warning(
            "No wake word backend available. Install one of:\n"
            "  pip install openwakeword\n"
            "  pip install vosk\n"
            "  pip install faster-whisper"
        )
        self._running = False

    # ── Backend: OpenWakeWord ─────────────────────────────────────────────────

    def _try_openwakeword(self) -> bool:
        try:
            import openwakeword
            from openwakeword.model import Model
            import pyaudio
            import numpy as np
        except ImportError:
            return False

        try:
            # Use built-in "hey_jarvis" or similar model — closest to "hey ai"
            # Users can add custom models via openwakeword
            oww_model = Model(
                wakeword_models=["hey_jarvis"],
                inference_framework="onnx"
            )

            pa = pyaudio.PyAudio()
            stream = pa.open(
                rate=self._sample_rate,
                channels=1,
                format=pyaudio.paInt16,
                input=True,
                frames_per_buffer=1280,
            )

            log.info("Wake word backend: OpenWakeWord")
            while self._running:
                audio_chunk = np.frombuffer(stream.read(1280, exception_on_overflow=False), dtype=np.int16)
                prediction = oww_model.predict(audio_chunk)
                # Check all models for any positive detection
                for model_name, score in prediction.items():
                    if score >= self._sensitivity:
                        log.info(f"Wake word detected! (model={model_name}, score={score:.2f})")
                        if self._callback:
                            threading.Thread(target=self._callback, daemon=True).start()
                        time.sleep(2.0)  # cooldown to avoid double triggers

            stream.stop_stream()
            stream.close()
            pa.terminate()
            return True
        except Exception as e:
            log.debug(f"OpenWakeWord failed: {e}")
            return False

    # ── Backend: Vosk ─────────────────────────────────────────────────────────

    def _try_vosk(self) -> bool:
        try:
            import vosk
            import pyaudio
            import json as _json
        except ImportError:
            return False

        # Try to find/download a small Vosk model
        model_path = self._get_vosk_model()
        if not model_path:
            return False

        try:
            model = vosk.Model(model_path)
            rec = vosk.KaldiRecognizer(model, self._sample_rate)

            pa = pyaudio.PyAudio()
            stream = pa.open(
                rate=self._sample_rate, channels=1,
                format=pyaudio.paInt16, input=True,
                frames_per_buffer=8000,
            )

            log.info("Wake word backend: Vosk")
            while self._running:
                data = stream.read(4000, exception_on_overflow=False)
                if rec.AcceptWaveform(data):
                    result = _json.loads(rec.Result())
                    text = result.get("text", "").lower()
                    if self._wake_word in text or self._is_similar(text, self._wake_word):
                        log.info(f"Wake word detected via Vosk: '{text}'")
                        if self._callback:
                            threading.Thread(target=self._callback, daemon=True).start()
                        time.sleep(2.0)

            stream.stop_stream()
            stream.close()
            pa.terminate()
            return True
        except Exception as e:
            log.debug(f"Vosk failed: {e}")
            return False

    def _get_vosk_model(self) -> Optional[str]:
        """Return path to a Vosk model, downloading if necessary."""
        from pathlib import Path
        model_dir = Path("data/vosk_model")
        if model_dir.exists() and any(model_dir.iterdir()):
            return str(model_dir)

        log.info("Downloading small Vosk English model (~50MB)...")
        try:
            import urllib.request
            import zipfile
            import io

            # Small Vosk English model
            url = "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"
            model_dir.mkdir(parents=True, exist_ok=True)
            data = urllib.request.urlopen(url, timeout=120).read()
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                zf.extractall(model_dir.parent)
            # Rename extracted folder
            extracted = list(model_dir.parent.glob("vosk-model-small*"))
            if extracted:
                extracted[0].rename(model_dir)
            return str(model_dir)
        except Exception as e:
            log.debug(f"Vosk model download failed: {e}")
            return None

    # ── Backend: faster-whisper (chunk transcription) ─────────────────────────

    def _try_whisper(self) -> bool:
        try:
            from faster_whisper import WhisperModel
            import pyaudio
            import numpy as np
        except ImportError:
            return False

        try:
            model = WhisperModel("tiny", device="cpu", compute_type="int8")
            pa = pyaudio.PyAudio()
            stream = pa.open(
                rate=self._sample_rate, channels=1,
                format=pyaudio.paInt16, input=True,
                frames_per_buffer=self._sample_rate,  # 1 second chunks
            )

            log.info("Wake word backend: faster-whisper (tiny model)")
            while self._running:
                # Collect 2 seconds of audio
                frames = []
                for _ in range(2):
                    data = stream.read(self._sample_rate, exception_on_overflow=False)
                    frames.append(np.frombuffer(data, dtype=np.int16))

                audio = np.concatenate(frames).astype(np.float32) / 32768.0
                segments, _ = model.transcribe(audio, language="en", beam_size=1)
                text = " ".join(s.text for s in segments).lower()

                if self._wake_word in text or self._is_similar(text, self._wake_word):
                    log.info(f"Wake word detected via Whisper: '{text}'")
                    if self._callback:
                        threading.Thread(target=self._callback, daemon=True).start()
                    time.sleep(2.0)

            stream.stop_stream()
            stream.close()
            pa.terminate()
            return True
        except Exception as e:
            log.debug(f"Whisper wake word failed: {e}")
            return False

    def _is_similar(self, text: str, target: str) -> bool:
        """Simple fuzzy match — check if all words of target appear in text."""
        target_words = target.lower().split()
        text_lower = text.lower()
        return all(word in text_lower for word in target_words)
