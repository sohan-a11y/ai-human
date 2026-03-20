"""
Text-to-Speech — the agent can speak out loud.
Uses pyttsx3 (offline, no API key) as primary.
Falls back to Windows SAPI via subprocess if pyttsx3 fails.
"""

from __future__ import annotations

import threading
from utils.logger import get_logger

log = get_logger(__name__)


class TTS:

    def __init__(self):
        self._engine = None
        self._lock = threading.Lock()
        self._available = False
        self._init()

    def _init(self) -> None:
        try:
            import pyttsx3
            self._engine = pyttsx3.init()
            self._engine.setProperty("rate", 175)   # speaking speed
            self._engine.setProperty("volume", 0.9)
            # Pick a good Windows voice if available
            voices = self._engine.getProperty("voices")
            for voice in voices:
                if "zira" in voice.name.lower() or "david" in voice.name.lower():
                    self._engine.setProperty("voice", voice.id)
                    break
            self._available = True
            log.info("TTS ready (pyttsx3)")
        except Exception as e:
            log.warning(f"pyttsx3 not available: {e}. Install: pip install pyttsx3")

    def speak(self, text: str, block: bool = False) -> None:
        """Speak text. Non-blocking by default so agent loop continues."""
        if not text.strip():
            return
        if block:
            self._speak_now(text)
        else:
            t = threading.Thread(target=self._speak_now, args=(text,), daemon=True)
            t.start()

    def _speak_now(self, text: str) -> None:
        if self._engine:
            with self._lock:
                try:
                    self._engine.say(text[:500])
                    self._engine.runAndWait()
                except Exception as e:
                    log.debug(f"TTS error: {e}")
                    self._fallback_speak(text)
        else:
            self._fallback_speak(text)

    def _fallback_speak(self, text: str) -> None:
        """Windows PowerShell SAPI fallback."""
        try:
            import subprocess
            safe = text.replace("'", "").replace('"', '')[:300]
            subprocess.run(
                ["powershell", "-Command", f"Add-Type -AssemblyName System.Speech; "
                 f"(New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak('{safe}')"],
                timeout=15, capture_output=True
            )
        except Exception:
            pass

    @property
    def available(self) -> bool:
        return self._available
