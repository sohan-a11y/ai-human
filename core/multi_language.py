"""
Multi-Language Support — allows the AI Human to receive goals in any language,
translate them to English for processing, and return responses in the user's
language.

Translation backends (in priority order):
1. LLM-based translation (uses the agent's own LLM — zero extra dependencies)
2. deep-translator (free Google Translate, pip install deep-translator)
3. argostranslate (fully offline, pip install argostranslate)

Language detection uses langdetect (pip install langdetect) or LLM fallback.
"""

from __future__ import annotations
import re
from typing import Optional
from utils.logger import get_logger

log = get_logger(__name__)

# ISO 639-1 language codes and names
LANGUAGES = {
    "af": "Afrikaans", "sq": "Albanian", "am": "Amharic", "ar": "Arabic",
    "hy": "Armenian", "az": "Azerbaijani", "eu": "Basque", "be": "Belarusian",
    "bn": "Bengali", "bs": "Bosnian", "bg": "Bulgarian", "ca": "Catalan",
    "ceb": "Cebuano", "ny": "Chichewa", "zh": "Chinese", "co": "Corsican",
    "hr": "Croatian", "cs": "Czech", "da": "Danish", "nl": "Dutch",
    "en": "English", "eo": "Esperanto", "et": "Estonian", "tl": "Filipino",
    "fi": "Finnish", "fr": "French", "fy": "Frisian", "gl": "Galician",
    "ka": "Georgian", "de": "German", "el": "Greek", "gu": "Gujarati",
    "ht": "Haitian Creole", "ha": "Hausa", "haw": "Hawaiian", "he": "Hebrew",
    "hi": "Hindi", "hmn": "Hmong", "hu": "Hungarian", "is": "Icelandic",
    "ig": "Igbo", "id": "Indonesian", "ga": "Irish", "it": "Italian",
    "ja": "Japanese", "jw": "Javanese", "kn": "Kannada", "kk": "Kazakh",
    "km": "Khmer", "ko": "Korean", "ku": "Kurdish", "ky": "Kyrgyz",
    "lo": "Lao", "la": "Latin", "lv": "Latvian", "lt": "Lithuanian",
    "lb": "Luxembourgish", "mk": "Macedonian", "mg": "Malagasy", "ms": "Malay",
    "ml": "Malayalam", "mt": "Maltese", "mi": "Maori", "mr": "Marathi",
    "mn": "Mongolian", "my": "Burmese", "ne": "Nepali", "no": "Norwegian",
    "ps": "Pashto", "fa": "Persian", "pl": "Polish", "pt": "Portuguese",
    "pa": "Punjabi", "ro": "Romanian", "ru": "Russian", "sm": "Samoan",
    "gd": "Scots Gaelic", "sr": "Serbian", "st": "Sesotho", "sn": "Shona",
    "sd": "Sindhi", "si": "Sinhala", "sk": "Slovak", "sl": "Slovenian",
    "so": "Somali", "es": "Spanish", "su": "Sundanese", "sw": "Swahili",
    "sv": "Swedish", "tg": "Tajik", "ta": "Tamil", "te": "Telugu",
    "th": "Thai", "tr": "Turkish", "uk": "Ukrainian", "ur": "Urdu",
    "uz": "Uzbek", "vi": "Vietnamese", "cy": "Welsh", "xh": "Xhosa",
    "yi": "Yiddish", "yo": "Yoruba", "zu": "Zulu",
}


class MultiLanguageSupport:
    """Translate goals and responses between any language and English."""

    def __init__(self, llm_generate_fn=None):
        """
        llm_generate_fn: callable(messages) -> str
        Pass the agent's LLM generate function for LLM-based translation.
        """
        self._llm = llm_generate_fn
        self._detected_lang: Optional[str] = None
        self._translation_cache: dict[str, str] = {}

    def detect_language(self, text: str) -> str:
        """Detect language of text. Returns ISO 639-1 code or 'en'."""
        # Try langdetect first (fast, offline)
        try:
            from langdetect import detect
            code = detect(text)
            return code[:2]  # normalize to 2-char
        except ImportError:
            pass
        except Exception:
            pass

        # Fallback: use LLM
        if self._llm:
            try:
                prompt = (
                    f"Detect the language of this text. Reply with ONLY the ISO 639-1 "
                    f"two-letter code (e.g. 'en', 'fr', 'de', 'hi', 'zh').\n\nText: {text[:200]}"
                )
                result = self._llm([{"role": "user", "content": prompt}])
                code = result.strip().lower()[:5]
                if re.match(r"^[a-z]{2,3}$", code):
                    return code
            except Exception:
                pass

        # Heuristic: check for non-ASCII
        if any(ord(c) > 127 for c in text):
            return "unknown"
        return "en"

    def translate_to_english(self, text: str, source_lang: str = "auto") -> tuple[str, str]:
        """
        Translate text to English.
        Returns (translated_text, detected_source_language).
        """
        if source_lang == "auto":
            source_lang = self.detect_language(text)

        self._detected_lang = source_lang

        if source_lang in ("en", "english"):
            return text, "en"

        # Check cache
        cache_key = f"{source_lang}:{text[:100]}"
        if cache_key in self._translation_cache:
            return self._translation_cache[cache_key], source_lang

        translated = self._translate(text, source_lang, "en")
        self._translation_cache[cache_key] = translated
        return translated, source_lang

    def translate_from_english(self, text: str, target_lang: str) -> str:
        """Translate English text to target language."""
        if target_lang in ("en", "english"):
            return text
        return self._translate(text, "en", target_lang)

    def process_multilingual_goal(self, goal: str) -> tuple[str, str]:
        """
        Process a goal that may be in any language.
        Returns (english_goal, source_language_code).
        Always translates to English for consistent agent processing.
        """
        lang = self.detect_language(goal)
        if lang == "en":
            return goal, "en"

        lang_name = LANGUAGES.get(lang, lang)
        log.info(f"Detected language: {lang_name} ({lang}). Translating to English.")
        english_goal, source = self.translate_to_english(goal, lang)
        log.info(f"Translated: '{goal[:50]}' → '{english_goal[:50]}'")
        return english_goal, source

    def respond_in_user_language(self, response: str, user_lang: str = "en") -> str:
        """Translate agent response back to user's language."""
        if not user_lang or user_lang == "en":
            return response
        return self.translate_from_english(response, user_lang)

    def _translate(self, text: str, source: str, target: str) -> str:
        """Try translation backends in order."""
        # 1. deep-translator (Google Translate, free, online)
        result = self._deep_translator(text, source, target)
        if result:
            return result

        # 2. argostranslate (fully offline)
        result = self._argos_translate(text, source, target)
        if result:
            return result

        # 3. LLM translation (always available if agent has LLM)
        result = self._llm_translate(text, source, target)
        if result:
            return result

        log.warning(f"All translation backends failed for {source}→{target}")
        return text  # return original if all fail

    def _deep_translator(self, text: str, source: str, target: str) -> Optional[str]:
        try:
            from deep_translator import GoogleTranslator
            translated = GoogleTranslator(source=source, target=target).translate(text)
            return translated
        except ImportError:
            return None
        except Exception as e:
            log.debug(f"deep-translator failed: {e}")
            return None

    def _argos_translate(self, text: str, source: str, target: str) -> Optional[str]:
        try:
            import argostranslate.package
            import argostranslate.translate

            # Check if translation package is installed
            installed_langs = argostranslate.translate.get_installed_languages()
            from_lang = next((l for l in installed_langs if l.code == source), None)
            to_lang = next((l for l in installed_langs if l.code == target), None)

            if not from_lang or not to_lang:
                # Auto-download the package
                self._download_argos_package(source, target)
                installed_langs = argostranslate.translate.get_installed_languages()
                from_lang = next((l for l in installed_langs if l.code == source), None)
                to_lang = next((l for l in installed_langs if l.code == target), None)

            if from_lang and to_lang:
                translation = from_lang.get_translation(to_lang)
                if translation:
                    return translation.translate(text)
            return None
        except ImportError:
            return None
        except Exception as e:
            log.debug(f"argostranslate failed: {e}")
            return None

    def _download_argos_package(self, source: str, target: str) -> None:
        try:
            import argostranslate.package
            argostranslate.package.update_package_index()
            packages = argostranslate.package.get_available_packages()
            pkg = next(
                (p for p in packages if p.from_code == source and p.to_code == target),
                None
            )
            if pkg:
                log.info(f"Downloading argostranslate package: {source}→{target}")
                argostranslate.package.install_from_path(pkg.download())
        except Exception as e:
            log.debug(f"argostranslate package download failed: {e}")

    def _llm_translate(self, text: str, source: str, target: str) -> Optional[str]:
        if not self._llm:
            return None
        try:
            source_name = LANGUAGES.get(source, source)
            target_name = LANGUAGES.get(target, target)
            prompt = (
                f"Translate the following text from {source_name} to {target_name}.\n"
                f"Return ONLY the translated text, no explanation.\n\n"
                f"Text to translate:\n{text}"
            )
            result = self._llm([{"role": "user", "content": prompt}])
            return result.strip() if result else None
        except Exception as e:
            log.debug(f"LLM translation failed: {e}")
            return None

    def list_supported_languages(self) -> list[dict]:
        """Return list of all supported languages."""
        return [{"code": k, "name": v} for k, v in sorted(LANGUAGES.items(), key=lambda x: x[1])]
